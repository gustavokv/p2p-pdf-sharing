import asyncio
import ipaddress
import sys
import uuid
import os

#from sympy.codegen import Print

from src.shared import mensagens

#USAR NO LAB
ipServidor = os.environ.get("COORDINATOR_IP", "127.0.0.1")  
ipLocal = os.environ.get("HOST_IP", "127.0.0.1")           
portaCoordenador = int(os.environ.get("COORDINATOR_PORT", 8000)) 

#ipServidor = "127.0.0.1"
#ipLocal = "127.0.0.1"
#portaCoordenador = 8000

listaDeClientes = []
ListaDeSupernos = []
superNosVizinhos = []
portaSuperno = None
nunClinteMax = 3
lock = asyncio.Lock()
Coord = {}
minha_chave_global = None
isCoordenador = False
desistoDeMeEleger = False
em_eleicao = None

# Lista dos arquivos pertencentes a cada cliente. Mapeia o nome do arquivo para seus "donos"
indice_arquivos_local = {} 

async def multicastSuperno(mensagem):
    ...

async def registro():
    reader, writer = await asyncio.open_connection(ipServidor, portaCoordenador)
    print(f"Conectado ao coordenador em {ipServidor}:{portaCoordenador}")

    global portaSuperno, Coord, desistoDeMeEleger
    portaSuperno = int(sys.argv[1])
    print(f"porta: {portaSuperno}")

    msg_registro = mensagens.cria_requisicao_registro_superno(ipLocal, portaSuperno)
    writer.write(msg_registro.encode('utf-8') + b'\n')
    await writer.drain()
    print("Solicitação de registro enviada ao coordenador.")

    dados = await reader.readuntil(b'\n')
    resposta = mensagens.decodifica_mensagem(dados)
    minha_chave_global = resposta.get("payload", {}).get("chave_unica")
    print(f"Chave recebida: {minha_chave_global}")

    msg_ack = mensagens.cria_ack_resposta_para_coord(minha_chave_global)
    writer.write(msg_ack.encode('utf-8') + b'\n')
    await writer.drain()
    print("ACK enviado ao coordenador.")

    dados = await reader.readuntil(b'\n')
    confirmacao = mensagens.decodifica_mensagem(dados)
    global ListaDeSupernos
    ListaDeSupernos = confirmacao["payload"]["supernos"]
    print(f"Lista de supernos recebida: {ListaDeSupernos}")

    dados = await reader.readuntil(b'\n')
    confirmacao = mensagens.decodifica_mensagem(dados)
    print(f"Mensagem do coordenador: {confirmacao}")


    Coord["reader"] = reader
    Coord["writer"] = writer

    #asyncio.create_task(monitorar_lider())

    print("Registro finalizado. Conexão ativa.")

# Lida com a requisição de download de arquivo do cliente. 
async def handle_busca_cliente(cliente_writer, requisicao):
    filename = requisicao["payload"]["nome_arquivo"]
    print(f"Cliente {cliente_writer.get_extra_info('peername')} está buscando por {filename}.")

    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0] # Pega o primeiro dono da lista
        print(f"Arquivo {filename} encontrado no índice local. Dono: {info_dono['ip']}:{info_dono['porta']}")
        msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU,filename, info_dono)
        cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await cliente_writer.drain()
        return

    # Se não tiver no índice local, faz a inundação
    print(f"{filename} não encontrado localmente. Inundando a rede...")
    chave_identificadora = str(uuid.uuid4()) # Neste caso, utiliza o uuid4 somente para armazenar localmente na fila de queries o cliente
    #queries_pendentes[chave_identificadora] = cliente_writer # Guarda quem solicitou download

    msg_query = mensagens.cria_query_arquivo_sn(filename, chave_identificadora)
    
    # Envia a mensagem para todos os vizinhos
    for vizinho in superNosVizinhos:
        try:
            vizinho["writer"].write(msg_query.encode('utf-8') + b'\n')
            await vizinho["writer"].drain()
            print(f"Query por {filename} (ID: {chave_identificadora[:6]}) enviada para {vizinho['info']['ip']}:{vizinho['info']['porta']}")

            dados = await vizinho["reader"].readuntil(b'\n')
            resposta = mensagens.decodifica_mensagem(dados)
            comando = resposta.get('comando')

            if comando == mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU:
                msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU, filename, resposta["payload"]["info_dono"])
                cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
                await cliente_writer.drain()
                return


        except Exception as e:
            print(f"Falha ao enviar query para vizinho {vizinho['info']['ip']}: {e}")

    print("Arquivo não existe.....")
    msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_NAO_ACHOU, None, None)
    cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
    await cliente_writer.drain()


# Lida com um pedido de um cliente para indexar um novo arquivo.
async def handle_indexar_arquivo(writer, requisicao):
    nome_arquivo = requisicao["payload"]["nome_arquivo"]
    
    info_dono = None
    async with lock:
        for cliente in listaDeClientes:
            print(f"{cliente}")
            if cliente["writer"] == writer:
                info_dono = {
                    "ip": cliente["ip"],
                    "porta": cliente["porta"],
                    "chave": cliente["chave"],
                    "valor": requisicao["payload"]["tamanho_arquivo"]
                }
                break
    
    if info_dono:
        # Adiciona o cliente como um dono deste arquivo
        async with lock:
            if nome_arquivo not in indice_arquivos_local:
                indice_arquivos_local[nome_arquivo] = []
            
            # Evita adicionar o mesmo dono varias vezes
            if info_dono not in indice_arquivos_local[nome_arquivo]:
                indice_arquivos_local[nome_arquivo].append(info_dono)
                print(f"Arquivo {nome_arquivo} adicionado ao índice pelo cliente {info_dono['chave'][:6]}.")
            else:
                print(f"Cliente {info_dono['chave'][:6]} já havia indexado {nome_arquivo}.")

        # Envia um ACK de sucesso para o cliente
        msg_ack = mensagens.cria_ack_indexacao_arquivo(nome_arquivo, "SUCESSO")
        writer.write(msg_ack.encode('utf-8') + b'\n')
        await writer.drain()
        
    else:
        print(f"Falha na indexação do arquivo do cliente {writer.get_extra_info('peername')}.")
        msg_ack = mensagens.cria_ack_indexacao_arquivo(nome_arquivo, "FALHA_NAO_REGISTRADO")
        writer.write(msg_ack.encode('utf-8') + b'\n')
        await writer.drain()

# Lida com uma requisição vinda do super nó vizinho durante a inundação da busca por arquivos. 
async def handle_query_vizinho(vizinho_writer, requisicao):
    filename = requisicao["payload"]["nome_arquivo"]
    chave_identificadora = requisicao["payload"]["chave_identificadora"]
    addr_origem = vizinho_writer.get_extra_info('peername')
    print(f"Super nó {addr_origem} está buscando por {filename}.")


    # Verifica o índice local para responder ao vizinho
    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0]
        print(f"Arquivo {filename} encontrado. Devolvendo resposta ao super nó de origem.")
        msg_resposta = mensagens.cria_resposta_arquivo_sn(mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU, filename, chave_identificadora, info_dono)
        vizinho_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await vizinho_writer.drain()
    else:
        print(f"Arquivo {filename} não encontrado no meu índice.")
        msg_resposta = mensagens.cria_resposta_arquivo_sn(mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU, filename, None, None)
        vizinho_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await vizinho_writer.drain()

# Lida com a solicitação de saída de um cliente.
async def handle_saida_cliente(writer, requisicao):
    chave_cliente_saindo = requisicao["payload"]["chave_cliente"]
    print(f"[Cliente {chave_cliente_saindo[:6]} solicitou saída.")

    async with lock:
        cliente_encontrado = None
        for cliente in listaDeClientes:
            if cliente["chave"] == chave_cliente_saindo:
                cliente_encontrado = cliente
                break
        
        if cliente_encontrado:
            listaDeClientes.remove(cliente_encontrado)
            print(f"Cliente {chave_cliente_saindo[:6]} removido da lista de clientes.")
        else:
            print(f"Cliente {chave_cliente_saindo[:6]} não estava na lista de clientes.")

        arquivos_para_limpar = []
        for nome_arquivo, donos in indice_arquivos_local.items():
            # Filtra a lista de donos, mantendo apenas quem não é o cliente que está saindo
            donos[:] = [dono for dono in donos if dono["chave"] != chave_cliente_saindo]
            
            # Se a lista de donos ficar vazia, da append no arquivo para remoção
            if not donos:
                arquivos_para_limpar.append(nome_arquivo)

        for nome_arquivo in arquivos_para_limpar:
            del indice_arquivos_local[nome_arquivo]
            print(f"Arquivo '{nome_arquivo}' removido do índice (sem donos).")
            
    try:
        writer.close()
        await writer.wait_closed()
        print(f"Conexão com {chave_cliente_saindo[:6]} fechada.")
    except Exception as e:
        print(f"Erro ao fechar conexão com cliente saindo: {e}")

async def servidorSuperNo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Cliente {addr} conectado.")


    try:
        sair = False
        while not sair:
            if not isCoordenador:
                sair = await superno(reader, writer, addr)
            else:
                #coordenador
                sair = await coordenador(reader, writer, addr)
    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}")
    finally:
        print(f"Iniciando remoção do cliente {addr}...")
        cliente_para_remover = None
        async with lock:
            for cliente in listaDeClientes:
                if cliente["writer"] == writer:
                    cliente_para_remover = cliente
                    break
            
            if cliente_para_remover:
                chave_cliente_saindo = cliente_para_remover["chave"]
                listaDeClientes.remove(cliente_para_remover)
                print(f"Cliente {chave_cliente_saindo[:6]} removido da lista.")

                # Limpa os arquivos do índice
                arquivos_para_limpar = []
                for nome_arquivo, donos in indice_arquivos_local.items():
                    donos[:] = [dono for dono in donos if dono["chave"] != chave_cliente_saindo]
                    if not donos:
                        arquivos_para_limpar.append(nome_arquivo)
                
                for nome_arquivo in arquivos_para_limpar:
                    del indice_arquivos_local[nome_arquivo]
                    print(f"Arquivo '{nome_arquivo}' removido do índice.")
            else:
                print(f"Cliente {addr} não estava na lista de clientes registrados.")

async def coordenador(reader, writer, addr):
    print("coordenador chamado")
    dados = await reader.read(4096)

    msg_recebida = mensagens.decodifica_mensagem(dados)

    print(f"coordenado: mensage recebida -> {msg_recebida}")

    if msg_recebida:
        comando = msg_recebida.get("comando")

        if comando == mensagens.CMD_SN2COORD_FINISH:
            print(f"Supernó {addr} finalizou o registro dos clientes.")
        elif comando == mensagens.CMD_SN2COORD_SAIDA:
            print(f"Supernó {addr} solicitou a saída.")
            return True
        elif comando == mensagens.CMD_SN2COORD_PERGUNTA_ESTOU_VIVO:
            resposta = mensagens.cria_resposta_estou_vivo()
            writer.write(resposta.encode('utf-8'))
            print(f"Resposta enviada. Máquina: {addr}")
        elif comando == mensagens.CMD_SN2SN_INICIAR_ELEICAO:
            # responde
            print("Pediram para mim ser o coordenador, sendo que ja sou")
            mensagem = mensagens.cria_mensagem_resposta_eleicao()
            writer.write(mensagem.encode('utf-8'))
            await writer.drain()
        else:
            # Recebe demais requisições do super nó
            ...
    return False

async def superno(reader, writer, addr):
    print("superno chamado")
    dados = await reader.read(4096)

async def superno(reader, writer, addr):
    dados = await reader.readuntil(b'\n')

    novoComando = mensagens.decodifica_mensagem(dados)
    comando = novoComando.get('comando')

    print(f"{novoComando}")

    if comando == mensagens.CMD_CLIENTESN2_REQUISICAO_REGISTRO:
        # Caso de requisição de registro vinda de um cliente
        await NovoCliente(reader, writer, novoComando)
    elif comando == mensagens.CMD_SN2COORD_FINISH:
        # Caso de recebimento do pacote finish vinda de um super nó
        print(f"superno {addr} finalizou registro de clientes")
    elif comando == mensagens.CMD_SN2SN_NOVO_COORDENADOR:
        global portaCoordenador, ipServidor, Coord
        print(f"Um novo nó coordenador foi eleito: {novoComando}")
        # ipServidor = novoComando["payload"]["ip"] #trocar no lab
        portaCoordenador = novoComando["payload"]["porta"]
        for no in superNosVizinhos:
            if no["info"]["porta"] == portaCoordenador: #trocar para ip no lab
                Coord["reader"] = no["reader"]
                Coord["writer"] = no["writer"]
                print("achou o novo coordenador")


        asyncio.create_task(monitorar_lider())
    elif comando == mensagens.CMD_CLIENTE2SN_BUSCA_ARQUIVO:
        # Caso de busca (solicitação de download) vinda de um cliente.
        await handle_busca_cliente(writer, novoComando)
    elif comando == mensagens.CMD_SN2SN_QUERY_ARQUIVO:
        # Caso de requisição vinda de outro super nó para realizar a verificação dos arquivos de índice do super nó atual
        await handle_query_vizinho(writer, novoComando)
    elif comando == mensagens.CMD_CLIENTE2SN_INDEXAR_ARQUIVO:
        # Caso de um cliente avisando que possui um arquivo
        await handle_indexar_arquivo(writer, novoComando)
    elif comando == mensagens.CMD_SN2SN_INICIAR_ELEICAO:
        #responde
        mensagem = mensagens.cria_mensagem_resposta_eleicao()
        writer.write(mensagem.encode('utf-8'))
        await writer.drain()

        #chama eleição
        if not em_eleicao:
            print("chamada de eleição de outro superno")
            await valentao()
        else:
            print("chamada de eleição de outro superno, mas ja esta em eleição")


    elif comando == mensagens.CMD_CLIENTE2SN_SAIDA:
        # Caso de um cliente avisando que está saindo
        await handle_saida_cliente(writer, novoComando)
        return True

    return False

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
            asyncio.create_task(monitorar_lider())
            msg = mensagens.cria_pacote_finish()

            # Envia o pacote FINISH para o coordenador
            try:
                coord_writer = Coord.get("writer")
                if coord_writer:
                    coord_writer.write(msg.encode('utf-8') + b'\n')
                    await coord_writer.drain()
                    print("--> Pacote FINISH enviado para o Coordenador.")
                else:
                    print("Conexão com o Coordenador não encontrada para enviar FINISH.")
            except Exception as e:
                print(f"Falha ao enviar FINISH para o Coordenador: {e}")

            # Envia o pacote FINISH para os super nós vizinhos
            if superNosVizinhos:
                for sn in superNosVizinhos:
                    sn["writer"].write(msg.encode('utf-8') + b'\n')
                    await sn["writer"].drain()
                    print(f"FINISH enviado para {sn['info']['ip']}:{sn['info']['porta']}")

    msgACK = mensagens.cria_ack_resposta_para_cliente(novo_cliente["chave"])
    writer.write(msgACK.encode('utf-8') + b'\n')
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
            print(f"Falha ao conectar com {sn['conectarComOutrosSupernos()ip']}:{sn['porta']} -> {e}")

    global superNosVizinhos
    superNosVizinhos = vizinhos


async def monitorar_lider():
    """Verifica periodicamente se o líder está vivo."""
    global Coord
    print("Iniciando monitoramento")
    while True:
        #Dorme pelo intervalo de verificação (ex: 5 segundos)
        await asyncio.sleep(5)

        if not isCoordenador:  # Não precisa monitorar a si mesmo
            try:
                print("Monitorando líder: ARE YOU ALIVE?")

                #Envia a mensagem de "ping"
                msg_ping = mensagens.cria_mensagem_alive()  # Crie esta função
                Coord["writer"].write(msg_ping.encode('utf-8'))
                await Coord["writer"].drain()

                #Usa wait_for para esperar a resposta ("pong")
                dados = await asyncio.wait_for(Coord["reader"].read(4096), timeout=20.0)

                if not dados:
                    raise ConnectionError("Líder fechou a conexão")

                #Decodifica e verifica se é a resposta certa
                resposta = mensagens.decodifica_mensagem(dados)
                if resposta.get('comando') == mensagens.CMD_COORD2SN_RESPOSTA_ESTOU_VIVO:
                    print(f"Monitorando líder: ...Líder está VIVO. Lider: {resposta["payload"]}")

            except asyncio.TimeoutError:
                #O LÍDER ESTÁ MORTO!
                print("!!! O LÍDER MORREU (timeout) !!!")
                await valentao()
                return

            except (ConnectionError, ConnectionResetError) as e:
                #O LÍDER TAMBÉM ESTÁ MORTO! (Conexão caiu)
                print(f"!!! O LÍDER MORREU (conexão perdida: {e}) !!!")
                await valentao()
                return

        else:
            return


# Esta é a sua função, mas renomeada para ser a "lógica"
async def valentao():
    global desistoDeMeEleger, isCoordenador, em_eleicao

    # --- Proteção de entrada ---
    if isCoordenador:
        print("Eu já sou o coordenador, não vou iniciar eleição.")
        return

    async with lock:
        if em_eleicao:
            print("Já estou em um processo de eleição.")
            return
        em_eleicao = True

    desistoDeMeEleger = False  # Reseta a flag para esta nova eleição

    print("Começando lógica de eleição...")
    # id_proprio = int(ipaddress.ip_address(ipLocal)) #usar no lab
    id_proprio = portaSuperno

    # Flag para saber se PELO MENOS UM "valentão" VIVO respondeu
    recebi_ok_de_um_maior = False

    # 1. Encontrar todos os vizinhos maiores
    vizinhos_maiores = []
    for no in superNosVizinhos:
        # id_vizinho = int(ipaddress.ip_address(no["info"]["ip"])) #usar no lab
        id_vizinho = no["info"]["porta"]
        if id_proprio < id_vizinho:
            vizinhos_maiores.append(no)

    # 2. Se não há vizinhos maiores, eu ganho automaticamente
    if not vizinhos_maiores:
        print("Não há vizinhos maiores. Eu sou o líder.")
        await anunciar_vitoria()
        return

    # 3. Se há vizinhos maiores, contacta-os A TODOS
    print(f"Contactando {len(vizinhos_maiores)} vizinhos maiores...")
    for no in vizinhos_maiores:
        # id_vizinho = int(ipaddress.ip_address(no["info"]["ip"])) #usar no lab
        id_vizinho = no["info"]["porta"]

        try:
            print(f"Enviando CMD_ELECTION para {id_vizinho}...")
            mensagem = mensagens.cria_mensagem_eleicao(no["info"]["chave"])
            no["writer"].write(mensagem.encode('utf-8'))
            await no["writer"].drain()

            dados = await asyncio.wait_for(no["reader"].read(4096), timeout=5.0)

            if not dados:
                print(f"Vizinho {id_vizinho} fechou a conexão.")
                continue

            resposta = mensagens.decodifica_mensagem(dados)

            if resposta.get('comando') == mensagens.CMD_SN2SN_ELEICAO_INICIADO:
                # Ele respondeu "OK", registamos isso
                print(f"Vizinho {id_vizinho} respondeu OK.")

                # Registamos que PELO MENOS UM respondeu
                recebi_ok_de_um_maior = True

                # Marcamos a desistência geral, mas NÃO paramos o loop
                desistoDeMeEleger = True

                # <<-- O 'break' FOI REMOVIDO DAQUI -->>
                # O loop continua para contactar os outros nós maiores

        except asyncio.TimeoutError:
            print(f"Vizinho {id_vizinho} não respondeu (timeout). Ignorando.")
            # Continuamos o loop, pois este "valentão" está fora do jogo

        except Exception as e:
            print(f"Erro ao contactar vizinho {id_vizinho}: {e}. Assumindo que está morto.")
            continue

    # 4. Avalia o resultado (APÓS o loop ter terminado)
    if not recebi_ok_de_um_maior:
        # Se NINGUÉM (vivo) respondeu OK, eu ganhei
        print("Nenhum vizinho maior respondeu OK. Serei o novo líder.")
        await anunciar_vitoria()
    else:
        # Se PELO MENOS UM respondeu OK, eu perdi
        print("Desistindo de me eleger, um nó maior está ativo.")
        async with lock:
            em_eleicao = False  # Reseta a flag

# Você deve criar esta função
async def anunciar_vitoria():
    global isCoordenador, em_eleicao
    # ...
    isCoordenador = True

    async with lock:
        em_eleicao = False  # <-- MUITO IMPORTANTE! A eleição terminou.

    # Envia CMD_VICTORY para TODOS os vizinhos
    msg_vitoria = mensagens.cria_mensagem_vitoria(ipLocal, portaSuperno)

    for no in superNosVizinhos:
        try:
            no["writer"].write(msg_vitoria.encode('utf-8'))
            await no["writer"].drain()
        except Exception as e:
            print(f"Falha ao anunciar vitória para {no['info']['ip']}: {e}")

    # Inicia o processo de replicação 2PC
    print("Iniciando processo de replicação (2PC)...")
    # asyncio.create_task(iniciar_replicacao_2pc())


async def main():
    # Esta tarefa manterá o servidor de clientes/supernós rodando
    server_task = None
    coordinator_listener_task = None

    try:
        await registro()

        servidor = await asyncio.start_server(servidorSuperNo, "0.0.0.0", portaSuperno)
        print(f"Super nó escutando em 0.0.0.0:{portaSuperno} (Registrado com IP {ipLocal})")

        # Inicia a tarefa do servidor
        server_task = asyncio.create_task(servidor.serve_forever())
        coordinator_listener_task = asyncio.create_task(monitorar_lider())

        await asyncio.gather(server_task, coordinator_listener_task)

    except asyncio.CancelledError:
        print("Recebido sinal de cancelamento.")
    finally:
        print("Iniciando encerramento...")
        
        # Para o servidor de escuta
        if server_task:
            server_task.cancel()
        if coordinator_listener_task:
            coordinator_listener_task.cancel()
        
        # Avisa o coordenador
        coord_writer = Coord.get("writer")
        if coord_writer:
            try:
                print("Notificando o Coordenador sobre a saída...")
                msg_saida = mensagens.cria_mensagem_saida_superno(minha_chave_global)
                coord_writer.write(msg_saida.encode('utf-8') + b'\n')
                await coord_writer.drain()
                coord_writer.close()
                await coord_writer.wait_closed()
                print("Notificação de saída enviada.")
            except Exception as e:
                print(f"Falha ao notificar o coordenador: {e}")
        
        print("Supernó desligado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEncerrando supernó...")