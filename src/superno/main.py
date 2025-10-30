import asyncio
import sys
from src.shared import mensagens

ipServidor = "127.0.0.1"
ipLocal = "127.0.0.1"
listaDeClientes = []
ListaDeSupernos = []
superNosVizinhos = None
portaCoordenador = 8000
portaSuperno = None
nunClinteMax = 1
lock = asyncio.Lock()
Coord = {}

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


async def servidorSuperNo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Cliente {addr} conectado.")


    try:
        dados = await reader.read(4096)
        novoComando = mensagens.decodifica_mensagem(dados)

        if novoComando["comando"] == mensagens.CMD_CLIENTESN2_REQUISICAO_REGISTRO:
            await NovoCliente(reader, writer, novoComando)

        if novoComando["comando"] == mensagens.CMD_SN2COORD_FINISH:
            print(f"superno {addr} finalizou registro de clientes")


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
            for sn in listaDeClientes:
                msg = mensagens.cria_pacote_finish()
                sn["writer"].write(msg.encode('utf-8'))
                await sn["writer"].drain()

    msgACK = mensagens.cria_ack_resposta_para_cliente(novo_cliente["chave"])
    writer.write(msgACK.encode('utf-8'))
    await writer.drain()

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
    print(f"Super nó escutando em {ipLocal}:{portaSuperno}")

    async with servidor:
        await servidor.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
