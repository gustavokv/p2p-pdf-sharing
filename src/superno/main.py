import asyncio
import sys
import uuid
import os

#from sympy.codegen import Print

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '../../'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

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

# Lista dos arquivos pertencentes a cada cliente. Mapeia o nome do arquivo para seus donos
indice_arquivos_local = {} 

consenso_lock = asyncio.Lock()
consenso_transacoes = {}

async def handle_voto_cliente(requisicao):
    """
    Processa um voto SIM ou NÃO de um cliente durante o 2PC.
    """
    comando = requisicao.get("comando")
    tid = requisicao.get("payload", {}).get("tid")

    if not tid:
        print("Consenso - Voto recebido sem TID. Ignorando.")
        return

    async with consenso_lock:
        transacao = consenso_transacoes.get(tid)
        if not transacao:
            print(f"Consenso - Voto recebido para TID desconhecido: {tid}. Ignorando.")
            return

        if transacao["resultado"]: # Resultado já decidido
            return

        print(f"Consenso - Voto recebido para TID {tid}: {comando}")

        if comando == mensagens.CMD_CLIENTE2SN_VOTO_NAO:
            transacao["resultado"] = "ABORT"
            transacao["evento"].set() # Libera o await
        
        elif comando == mensagens.CMD_CLIENTE2SN_VOTO_SIM:
            transacao["votos_sim"] += 1
            if transacao["votos_sim"] == transacao["total_clientes"]:
                transacao["resultado"] = "COMMIT"
                transacao["evento"].set() # Libera o await

async def iniciar_replicacao_consenso(writer_novo_superno):
    """Inicia o 2PC e Voto do Cliente para replicar o índice."""
    
    tid = str(uuid.uuid4())
    evento_votacao = asyncio.Event()
    resultado_final = "ABORT" # Padrão
    
    print(f"Consenso - {tid[:6]} Iniciando replicação...")

    # if not writer_novo_superno:
    #     print("Consenso - teste: Nenhum writer_novo_superno fornecido")

    try: # Realiza a Fase 1
        print(f"Consenso {tid[:6]} Fase 1: Enviando Pedido de Votação (VOTE_REQUEST)...")
        
        soma_mestre = 0
        num_clientes_votantes = 0
        
        async with lock:
            # Calcula a soma mestre
            for donos_lista in indice_arquivos_local.values():
                for dono in donos_lista:
                    soma_mestre += dono.get("valor", 0)
            num_clientes_votantes = len(listaDeClientes)

        if num_clientes_votantes == 0:
            print(f"Consenso {tid[:6]} Nenhum cliente para votar. Comita sozinho.")
            resultado_final = "COMMIT"
        else:
            async with consenso_lock:
                consenso_transacoes[tid] = {
                    "evento": evento_votacao,
                    "total_clientes": num_clientes_votantes,
                    "votos_sim": 0,
                    "resultado": None
                }
            
            # Envia pedido de voto para todos os clientes
            msg_request = mensagens.cria_pedido_votacao(tid, indice_arquivos_local, soma_mestre)
            tasks = []
            async with lock:
                for cliente in listaDeClientes:
                    cliente["writer"].write(msg_request.encode('utf-8') + b'\n')
                    tasks.append(cliente["writer"].drain())
            await asyncio.gather(*tasks)

            # Espera pelos votos
            print(f"Consenso {tid[:6]}  Aguardando {num_clientes_votantes} votos (Timeout de 20segundos)...")
            try:
                await asyncio.wait_for(evento_votacao.wait(), timeout=20.0)
                async with consenso_lock:
                    resultado_final = consenso_transacoes[tid]["resultado"]
            except asyncio.TimeoutError:
                print(f"Consenso{tid[:6]} Timeout! Clientes não responderam. Abortando.")
                resultado_final = "ABORT"

        # Fase 2
        if resultado_final == "COMMIT":
            print(f"Consenso{tid[:6]} Fase 2: Todos votaram SIM. Enviando COMMIT.")
            
            # Avisa todos que o consenso passou
            msg_commit = mensagens.cria_msg_global_commit(tid)
            async with lock:
                for cliente in listaDeClientes:
                    cliente["writer"].write(msg_commit.encode('utf-8') + b'\n')

            # Promoção de um cliente
            print("Escolhendo cliente para promover a Supernó...")
            
            cliente_escolhido = None
            async with lock:
                if listaDeClientes:
                    # Escolhe o último cliente registrado para ser promovido
                    cliente_escolhido = listaDeClientes[-1] 
            
            if cliente_escolhido:
                print(f"Enviando índice para {cliente_escolhido['ip']}:{cliente_escolhido['porta']}...")
                
                # Aqui acontece a replicação
                msg_promo = mensagens.criar_mensagem(
                    mensagens.CMD_SN2CLIENTE_PROMOCAO, 
                    indice=indice_arquivos_local
                )
                
                try:
                    cliente_escolhido["writer"].write(msg_promo.encode('utf-8') + b'\n')
                    await cliente_escolhido["writer"].drain()
                    print("Ordem enviada. O cliente deve reiniciar como Supernó.")
                except Exception as e:
                    print(f"[ERRO] Falha ao enviar promoção: {e}")
            else:
                print("Nenhum cliente disponível para promover.")
        else:
            print(f"Consenso - {tid[:6]}] Fase 2: Voto NÃO. Enviando ABORT.")
            msg_abort = mensagens.cria_msg_global_abort(tid)
            async with lock:
                for cliente in listaDeClientes:
                    cliente["writer"].write(msg_abort.encode('utf-8') + b'\n')

    except Exception as e:
        print(f"Consenso - {tid[:6]}] Erro fatal no 2PC: {e}")
        # Tenta enviar um ABORT de emergência
        msg_abort = mensagens.cria_msg_global_abort(tid)
        async with lock:
            for cliente in listaDeClientes:
                cliente["writer"].write(msg_abort.encode('utf-8') + b'\n')
    finally:
        async with consenso_lock:
            consenso_transacoes.pop(tid, None) # Limpa a transação

async def registro():
    reader, writer = await asyncio.open_connection(ipServidor, portaCoordenador)
    print(f"Conectado ao coordenador em {ipServidor}:{portaCoordenador}")

    global portaSuperno, Coord
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
    chave_identificadora = str(uuid.uuid4()) # Neste caso, utiliza o uuid4 para armazenar localmente na fila de queries o cliente
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
            sair = await superno(reader, writer, addr)
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

        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Erro ao fechar writer do cliente {addr}: {e}")
        
        print(f"Limpeza para {addr} concluída.")

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
    elif comando == mensagens.CMD_CLIENTE2SN_BUSCA_ARQUIVO:
        # Caso de busca (solicitação de download) vinda de um cliente.
        await handle_busca_cliente(writer, novoComando)
    elif comando == mensagens.CMD_SN2SN_QUERY_ARQUIVO:
        # Caso de requisição vinda de outro super nó para realizar a verificação dos arquivos de índice do super nó atual
        await handle_query_vizinho(writer, novoComando)
    elif comando == mensagens.CMD_CLIENTE2SN_INDEXAR_ARQUIVO:
        # Caso de um cliente avisando que possui um arquivo
        await handle_indexar_arquivo(writer, novoComando)
    elif comando == mensagens.CMD_CLIENTE2SN_SAIDA:
        # Caso de um cliente avisando que está saindo
        await handle_saida_cliente(writer, novoComando)
        return True
    elif comando == mensagens.CMD_CLIENTE2SN_VOTO_SIM:
        await handle_voto_cliente(novoComando)  
    elif comando == mensagens.CMD_CLIENTE2SN_VOTO_NAO:
        await handle_voto_cliente(novoComando)
    elif comando == mensagens.CMD_SN2COORD_REQUISICAO_REGISTRO:
        print(f"Recebi pedido de registro de novo Supernó {addr}")
        
        # Gera uma chave nova para o colega
        nova_chave = str(uuid.uuid4().hex)
        
        # Responde com SUCESSO
        msg_resp = mensagens.cria_resposta_coordenador("SUCESSO", nova_chave)
        writer.write(msg_resp.encode('utf-8') + b'\n')
        await writer.drain()
        
        # Aguarda o ACK
        dados_ack = await reader.readuntil(b'\n')
        print(f"ACK recebido do novo Supernó.")
        
        # Adiciona à lista de supernós 
        print(f"Enviando lista de vizinhos para o novo no...")
        msg_lista = mensagens.cria_broadcast_lista_supernos(ListaDeSupernos)
        writer.write(msg_lista.encode('utf-8') + b'\n')
        await writer.drain()
        
        # envia mensagem final de confirmação
        msg_fim = mensagens.cria_confirmacao_registro()
        writer.write(msg_fim.encode('utf-8') + b'\n')
        await writer.drain()
    elif comando == mensagens.CMD_SN2COORD_PERGUNTA_ESTOU_VIVO:
        # O Supernó líder precisa responder que está vivo, se não os outros nós acham que ele morreu e fazem outrra eleição
        
        msg_pong = mensagens.cria_resposta_estou_vivo()
        writer.write(msg_pong.encode('utf-8') + b'\n')
        await writer.drain()
        
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
            msg = mensagens.cria_pacote_finish()

            # Envia o pacote FINISH para o coordenador
            try:
                coord_writer = Coord.get("writer")
                if coord_writer:
                    coord_writer.write(msg.encode('utf-8') + b'\n')
                    await coord_writer.drain()
                    print("-> Pacote FINISH enviado para o Coordenador.")
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
    """
    Verifica de vez em quando se o líder está vivo E
    processa mensagens de broadcast dele.
    """
    global isCoordenador

    reader = Coord.get("reader")
    writer = Coord.get("writer")
    
    if not reader or not writer:
        print("[ERRO] Conexão com Coordenador não encontrada para monitorar.")
        return

    print("Monitor do Coordenador iniciado (ping/listen).")
    
    while True:
        if isCoordenador: # Se eu sou o coordenador, não faço nada
            break
            
        try:
            # Envia um PING
            msg_ping = mensagens.cria_mensagem_alive()
            writer.write(msg_ping.encode('utf-8') + b'\n')
            await writer.drain()

            dados = await asyncio.wait_for(reader.readuntil(b'\n'), timeout=10.0)
            
            if not dados:
                raise ConnectionError("Líder fechou a conexão")

            msg = mensagens.decodifica_mensagem(dados)
            if not msg:
                continue

            comando = msg.get("comando")

            if comando == mensagens.CMD_COORD2SN_RESPOSTA_ESTOU_VIVO: # O pong
                print(f"Monitorando líder: ...Líder está VIVO.")
            
            elif comando == mensagens.CMD_COORD2SN_LISTA_SUPERNOS:
                async with lock:
                    global ListaDeSupernos
                    ListaDeSupernos = msg["payload"]["supernos"]
                    await conectarComOutrosSupernos()
                print(f"Monitorando líder: [BROADCAST] Lista de Supernós atualizada: {len(ListaDeSupernos)} nós.")
            
            else:
                print(f"Monitorando líder: [MSG] Recebida msg inesperada: {comando}")

        except asyncio.TimeoutError:
            print("!!! O LÍDER MORREU (timeout de 10s no heartbeat) !!!")
            # --- ADICIONE O GATILHO 2PC ---
            print("[ELEIÇÃO] SIMULADA! Eu sou o novo mestre.")
            isCoordenador = True
            print("Consenso - Disparando 2PC para replicar índice...")
            # Como não há um "novo" supernó, passamos None.
            asyncio.create_task(iniciar_replicacao_consenso(None)) 
            # ---------------------------
            break

        except (ConnectionError, ConnectionResetError, asyncio.IncompleteReadError) as e:
            print(f"!!! O LÍDER MORREU (conexão perdida: {e}) !!!")
            # --- ADICIONE O GATILHO 2PC ---
            print("[ELEIÇÃO] SIMULADA! Eu sou o novo mestre.")
            #global isCoordenador # já está no escopo
            isCoordenador = True
            print("Consenso - Disparando 2PC para replicar índice...")
            asyncio.create_task(iniciar_replicacao_consenso(None)) 
            # ---------------------------
            break
        
        # Espera 5 segundos antes de enviar o próximo ping
        await asyncio.sleep(5)

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