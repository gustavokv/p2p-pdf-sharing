import asyncio
import sys
import uuid
import os
from src.shared import mensagens

#USAR NO LAB
#ipServidor = os.environ.get("COORDINATOR_IP", "127.0.0.1")  # LÊ DO AMBIENTE
#ipLocal = os.environ.get("HOST_IP", "127.0.0.1")           # LÊ DO AMBIENTE
#portaCoordenador = int(os.environ.get("COORDINATOR_PORT", 8000)) # LÊ DO AMBIENTE

ipServidor = "127.0.0.1"
ipLocal = "127.0.0.1"
portaCoordenador = 8000

listaDeClientes = []
ListaDeSupernos = []
superNosVizinhos = []
portaSuperno = None
nunClinteMax = 1
lock = asyncio.Lock()
Coord = {}

# Lista dos arquivos pertencentes a cada cliente. Mapeia o nome do arquivo para seus "donos"
indice_arquivos_local = {} 
# Rastreia buscas enviadas para outros super nós
queries_pendentes = {}

async def registro():
    reader, writer = await asyncio.open_connection(ipServidor, portaCoordenador)
    print(f"Conectado ao coordenador em {ipServidor}:{portaCoordenador}")

    global portaSuperno
    portaSuperno = int(sys.argv[1])
    print(f"porta: {portaSuperno}")

    msg_registro = mensagens.cria_requisicao_registro_superno(ipLocal, portaSuperno)
    writer.write(msg_registro.encode('utf-8'))
    await writer.drain()
    print("Solicitação de registro enviada ao coordenador.")

    dados = await reader.read(4096)
    resposta = mensagens.decodifica_mensagem(dados)
    chave = resposta.get("payload", {}).get("chave_unica")
    print(f"Chave recebida: {chave}")

    msg_ack = mensagens.cria_ack_resposta_para_coord(chave)
    writer.write(msg_ack.encode('utf-8'))
    await writer.drain()
    print("ACK enviado ao coordenador.")

    dados = await reader.read(4096)
    confirmacao = mensagens.decodifica_mensagem(dados)
    global ListaDeSupernos
    ListaDeSupernos = confirmacao["payload"]["supernos"]
    print(f"Lista de supernos recebida: {ListaDeSupernos}")

    dados = await reader.read(4096)
    confirmacao = mensagens.decodifica_mensagem(dados)
    print(f"Mensagem do coordenador: {confirmacao}")


    Coord["reader"] = reader
    Coord["writer"] = writer

    print("Registro finalizado. Conexão ativa.")

async def handle_busca_cliente(cliente_writer, requisicao):
    """ Lida com a requisição de download de arquivo do cliente. """

    filename = requisicao["payload"]["nome_arquivo"]
    print(f"Cliente {cliente_writer.get_extra_info('peername')} está buscando por {filename}.")

    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0] # Pega o primeiro dono da lista
        print(f"Arquivo {filename} encontrado no índice local. Dono: {info_dono['ip']}:{info_dono['porta']}")
        msg_resposta = mensagens.cria_resposta_local_arquivo(filename, info_dono)
        cliente_writer.write(msg_resposta.encode('utf-8'))
        await cliente_writer.drain()
        return

    # Se não tiver no índice local, faz a inundação
    print(f"{filename} não encontrado localmente. Inundando a rede...")
    chave_identificadora = str(uuid.uuid4()) # Neste caso, utiliza o uuid4 somente para armazenar localmente na fila de queries o cliente
    queries_pendentes[chave_identificadora] = cliente_writer # Guarda quem solicitou download

    msg_query = mensagens.cria_query_arquivo_sn(filename, chave_identificadora)
    
    # Envia a mensagem para todos os vizinhos
    for vizinho in superNosVizinhos:
        try:
            vizinho["writer"].write(msg_query.encode('utf-8'))
            await vizinho["writer"].drain()
            print(f"Query por {filename} (ID: {chave_identificadora[:6]}) enviada para {vizinho['info']['ip']}:{vizinho['info']['porta']}")
        except Exception as e:
            print(f"Falha ao enviar query para vizinho {vizinho['info']['ip']}: {e}")

async def handle_query_vizinho(vizinho_writer, requisicao):
    """Lida com uma requisição vinda do super nó vizinho durante a inundação da busca por arquivos. """

    filename = requisicao["payload"]["nome_arquivo"]
    chave_identificadora = requisicao["payload"]["chave_identificadora"]
    addr_origem = vizinho_writer.get_extra_info('peername')
    print(f"Super nó {addr_origem} está buscando por {filename}.")

    # Verifica o índice local para responder ao vizinho
    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0]
        print(f"Arquivo {filename} encontrado. Devolvendo resposta ao super nó de origem.")
        msg_resposta = mensagens.cria_resposta_arquivo_sn(filename, chave_identificadora, info_dono)
        vizinho_writer.write(msg_resposta.encode('utf-8'))
        await vizinho_writer.drain()
    else:
        print(f"Arquivo {filename} não encontrado no meu índice.")
    # Se não estiver no arquivo de índice, não responde

async def handle_resposta_vizinho(requisicao):
    """Lida com uma resposta de um vizinho de uma busca da inundação que o super nó atual inciou """

    chave_identificadora = requisicao["payload"]["chave_identificadora"]
    info_dono = requisicao["payload"]["info_dono"]
    filename = requisicao["payload"]["nome_arquivo"]
    print(f"Resposta recebida para a busca ID {chave_identificadora[:6]}. Arquivo {filename} encontrado em {info_dono['ip']}.")

    # Indica o cliente que estava esperando esta resposta
    cliente_writer = queries_pendentes.pop(chave_identificadora, None)

    if cliente_writer:
        try:
            print(f"Encaminhando localização para o cliente original {cliente_writer.get_extra_info('peername')}.")
            msg_final = mensagens.cria_resposta_local_arquivo(filename, info_dono)
            cliente_writer.write(msg_final.encode('utf-8'))
            await cliente_writer.drain()
        except Exception as e:
            print(f"Falha ao encaminhar resposta para o cliente original: {e}")
    else:
        print(f"Resposta recebida para uma busca (ID: {chave_identificadora[:6]}) que não está mais pendente.")


async def servidorSuperNo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Cliente {addr} conectado.")

    try:
        while True:
            dados = await reader.read(4096)
            
            if not dados:
                print('Conexão com {addr} fechada.')
                break

            novoComando = mensagens.decodifica_mensagem(dados)
            comando = novoComando.get('comando')

            if comando == mensagens.CMD_CLIENTESN2_REQUISICAO_REGISTRO:
                """ Caso de requisição de registro vinda de um cliente """
                await NovoCliente(reader, writer, novoComando)
            elif comando == mensagens.CMD_SN2COORD_FINISH:
                """ Caso de recebimento do pacote finish vinda de um super nó """
                print(f"superno {addr} finalizou registro de clientes")
            elif comando == mensagens.CMD_CLIENTE2SN_BUSCA_ARQUIVO:
                """ Caso de busca (solicitação de download) vinda de um cliente. """
                await handle_busca_cliente(writer, novoComando)
            elif comando == mensagens.CMD_SN2SN_QUERY_ARQUIVO:
                """ Caso de requisição vinda de outro super nó para realizar a verificação dos arquivos de índice do super nó atual """
                await handle_query_vizinho(writer, novoComando)
            elif comando == mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO:
                """ Caso para o super nó que iniciou a inundação lidar com a resposta do super nó que encontrou o arquivo em seu índice. """
                await handle_resposta_vizinho(novoComando)

    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}")

async def NovoCliente(reader, writer, requisicao_registro):
    novo_cliente = {
        "writer": writer,
        "reader": reader,
        "chave": requisicao_registro["payload"]["chave_unica"],
        "ip": requisicao_registro["payload"]["endereco_ip"],
        "porta": requisicao_registro["payload"]["porta"]
    }

    async with lock:
        listaDeClientes.append(novo_cliente)
        if len(listaDeClientes) == nunClinteMax: #manda pacote finish
            await conectarComOutrosSupernos()
            msg = mensagens.cria_pacote_finish()

            # Envia o pacote FINISH para o coordenador
            try:
                coord_writer = Coord.get("writer")
                if coord_writer:
                    coord_writer.write(msg.encode('utf-8'))
                    await coord_writer.drain()
                    print("--> Pacote FINISH enviado para o Coordenador.")
                else:
                    print("Conexão com o Coordenador não encontrada para enviar FINISH.")
            except Exception as e:
                print(f"Falha ao enviar FINISH para o Coordenador: {e}")

            # Envia o pacote FINISH para os super nós vizinhos
            if superNosVizinhos:
                for sn in superNosVizinhos:
                    sn["writer"].write(msg.encode('utf-8'))
                    await sn["writer"].drain()
                    print(f"FINISH enviado para {sn['info']['ip']}:{sn['info']['porta']}")

    msgACK = mensagens.cria_ack_resposta_para_cliente(novo_cliente["chave"])
    writer.write(msgACK.encode('utf-8'))
    await writer.drain()
    print(f"ACK enviado para o cliente {novo_cliente['chave'][:10]}...")

async def conectarComOutrosSupernos():
    vizinhos = []
    for sn in ListaDeSupernos:
        if sn["ip"] == ipLocal and sn["porta"] == portaSuperno:
            continue  # Não conecta com ele mesmo
        try:
            reader, writer = await asyncio.open_connection(sn["ip"], sn["porta"])
            print(f"Conectado com supernó {sn['ip']}:{sn['porta']}")
            # Guarda as conexões em uma lista global
            vizinhos.append({"reader": reader, "writer": writer, "info": sn})
        except Exception as e:
            print(f"Falha ao conectar com {sn['ip']}:{sn['porta']} -> {e}")

    global superNosVizinhos
    superNosVizinhos = vizinhos


async def main():

    await registro()

    servidor = await asyncio.start_server(servidorSuperNo, ipLocal, portaSuperno)
    #servidor = await asyncio.start_server(servidorSuperNo, "0.0.0.0", portaSuperno) USAR NO LAB
    print(f"Super nó escutando em {ipLocal}:{portaSuperno}")

    async with servidor:
        await servidor.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
