import asyncio
import ipaddress
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
desistoDeMeEleger = False
em_eleicao = None

# Lista dos arquivos pertencentes a cada cliente. Mapeia o nome do arquivo para seus "donos"
indice_arquivos_local = {} 

consenso_lock = asyncio.Lock()
consenso_transacoes = {}

async def multicastSuperno(mensagem):
    ...

async def handle_voto_cliente(requisicao):
    """
    Processa um voto SIM ou NÃO de um cliente durante o 2PC.
    """
    comando = requisicao.get("comando")
    tid = requisicao.get("payload", {}).get("tid")

    if not tid:
        print("Consenso - Voto recebido sem TID. Ignorando.\n")
        return

    async with consenso_lock:
        transacao = consenso_transacoes.get(tid)
        if not transacao:
            print(f"Consenso - Voto recebido para TID desconhecido: {tid}. Ignorando.\n")
            return

        if transacao["resultado"]: # Resultado já decidido
            return

        print(f"Consenso - Voto recebido para TID {tid}: {comando}\n")

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
    
    print(f"Consenso - {tid[:6]} Iniciando replicação...\n")

    # if not writer_novo_superno:
    #     print("Consenso - teste: Nenhum writer_novo_superno fornecido")

    try: # Realiza a Fase 1
        print(f"Consenso {tid[:6]} Fase 1: Enviando Pedido de Votação (VOTE_REQUEST)...\n")
        
        soma_mestre = 0
        num_clientes_votantes = 0
        
        async with lock:
            # Calcula a soma mestre
            for donos_lista in indice_arquivos_local.values():
                for dono in donos_lista:
                    soma_mestre += dono.get("valor", 0)
            num_clientes_votantes = len(listaDeClientes)

        if num_clientes_votantes == 0:
            print(f"Consenso {tid[:6]} Nenhum cliente para votar. Comita sozinho.\n")
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
            print(f"Consenso {tid[:6]}  Aguardando {num_clientes_votantes} votos (Timeout de 20segundos)...\n")
            try:
                await asyncio.wait_for(evento_votacao.wait(), timeout=30.0)
                async with consenso_lock:
                    resultado_final = consenso_transacoes[tid]["resultado"]
            except asyncio.TimeoutError:
                print(f"Consenso{tid[:6]} Timeout! Clientes não responderam. Abortando.\n")
                resultado_final = "ABORT"

        # Fase 2
        if resultado_final == "COMMIT":
            print(f"Consenso{tid[:6]} Fase 2: Todos votaram SIM. Enviando COMMIT.\n")
            
            # Avisa todos que o consenso passou
            msg_commit = mensagens.cria_msg_global_commit(tid)
            async with lock:
                for cliente in listaDeClientes:
                    cliente["writer"].write(msg_commit.encode('utf-8') + b'\n')

            # Promoção de um cliente
            print("Escolhendo cliente para promover a Supernó...\n")
            
            cliente_escolhido = None
            async with lock:
                if listaDeClientes:
                    # Escolhe o último cliente registrado para ser promovido
                    cliente_escolhido = listaDeClientes[-1] 
            
            if cliente_escolhido:
                print(f"Enviando índice para {cliente_escolhido['ip']}:{cliente_escolhido['porta']}...\n")
                
                # Aqui acontece a replicação
                msg_promo = mensagens.criar_mensagem(
                    mensagens.CMD_SN2CLIENTE_PROMOCAO, 
                    indice=indice_arquivos_local
                )
                
                try:
                    cliente_escolhido["writer"].write(msg_promo.encode('utf-8') + b'\n')
                    await cliente_escolhido["writer"].drain()
                    print("Ordem enviada. O cliente deve reiniciar como Supernó.\n")

                    print("Redirecionando outros clientes...\n")
                    msg_redirect = mensagens.criar_mensagem("SN2CLIENTE_REDIRECT", ip=cliente_escolhido["ip"], porta=cliente_escolhido["porta"])

                    async with lock:
                        # Cria uma lista temporária para iterar sem modificar a original durante o loop
                        clientes_para_migrar = [c for c in listaDeClientes if c != cliente_escolhido]
                        
                        for cliente in clientes_para_migrar:
                            try:
                                print(f"Mandando cliente {cliente['porta']} ir para {cliente_escolhido['porta']}...\n")
                                cliente["writer"].write(msg_redirect.encode('utf-8') + b'\n')
                                await cliente["writer"].drain()
                            except Exception as e:
                                print(f"Erro ao redirecionar cliente {cliente['porta']}: {e}\n")
                        
                        # Limpa a lista local (eles vão sair)
                        listaDeClientes.clear()
                except Exception as e:
                    print(f"[ERRO] Falha ao enviar promoção: {e}\n")

                print("[MIGRAÇÃO] Redirecionando demais clientes e vizinhos para o novo Supernó...\n")

                novo_sn_ip = cliente_escolhido["ip"]
                novo_sn_porta = cliente_escolhido["porta"]
                
                msg_redirect = mensagens.cria_msg_redirect(novo_sn_ip, novo_sn_porta)
                
                async with lock:
                    for cliente in listaDeClientes:
                        # Não redireciona o próprio escolhido (ele já recebeu a promoção)
                        if cliente == cliente_escolhido:
                            continue
                            
                        try:
                            print(f"Mandando cliente {cliente['porta']} ir para {novo_sn_porta}...\n")
                            cliente["writer"].write(msg_redirect.encode('utf-8') + b'\n')
                            await cliente["writer"].drain()
                            # Opcional: fechar a conexão do lado do servidor ou esperar o cliente fechar
                        except Exception as e:
                            print(f"Erro ao redirecionar cliente: {e}\n")

                    listaDeClientes.clear()

                print("[MIGRAÇÃO] Redirecionando VIZINHOS (Supernós) para o novo Supernó...\n")
                msg_update_vizinho = mensagens.cria_msg_redirect_vizinho(novo_sn_ip, novo_sn_porta)

                # Percorre a lista de Supernós vizinhos (Ex: SN1)
                for vizinho in superNosVizinhos:
                    try:
                        print(f"Avisando vizinho {vizinho['info']['porta']} para conectar em {novo_sn_porta}...\n")
                        vizinho["writer"].write(msg_update_vizinho.encode('utf-8') + b'\n')
                        await vizinho["writer"].drain()
                        
                        # Opcional: Não fechamos a conexão aqui porque este vizinho 
                        # ainda precisa deste socket para falar com o Coordenador (nós).
                        # Ele quem deve atualizar a lista dele de "Vizinhos P2P".
                    except Exception as e:
                        print(f"Erro ao notificar vizinho: {e}\n")
                
                # Limpa a lista de vizinhos P2P deste nó, pois agora ele é Coordenador
                # e não deve mais participar da busca de arquivos (query flooding)
                superNosVizinhos.clear()
                print("[STATUS] Agora sou apenas Coordenador. Lista de vizinhos P2P limpa.\n")
            else:
                print("Nenhum cliente disponível para promover.\n")
        else:
            print(f"Consenso - {tid[:6]}] Fase 2: Voto NÃO. Enviando ABORT.\n")
            msg_abort = mensagens.cria_msg_global_abort(tid)
            async with lock:
                for cliente in listaDeClientes:
                    cliente["writer"].write(msg_abort.encode('utf-8') + b'\n')

    except Exception as e:
        print(f"Consenso - {tid[:6]}] Erro fatal no 2PC: {e}\n")
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
    print(f"Conectado ao coordenador em {ipServidor}:{portaCoordenador}\n")

    global portaSuperno, Coord, desistoDeMeEleger
    portaSuperno = int(sys.argv[1])
    print(f"porta: {portaSuperno}\n")

    msg_registro = mensagens.cria_requisicao_registro_superno(ipLocal, portaSuperno)
    writer.write(msg_registro.encode('utf-8') + b'\n')
    await writer.drain()
    print("Solicitação de registro enviada ao coordenador.\n")

    dados = await reader.readuntil(b'\n')
    resposta = mensagens.decodifica_mensagem(dados)
    minha_chave_global = resposta.get("payload", {}).get("chave_unica")
    print(f"Chave recebida: {minha_chave_global}\n")

    msg_ack = mensagens.cria_ack_resposta_para_coord(minha_chave_global)
    writer.write(msg_ack.encode('utf-8') + b'\n')
    await writer.drain()
    print("ACK enviado ao coordenador.\n")

    dados = await reader.readuntil(b'\n')
    confirmacao = mensagens.decodifica_mensagem(dados)
    global ListaDeSupernos
    ListaDeSupernos = confirmacao["payload"]["supernos"]
    print(f"Lista de supernos recebida: {ListaDeSupernos}\n")

    dados = await reader.readuntil(b'\n')
    confirmacao = mensagens.decodifica_mensagem(dados)
    print(f"Mensagem do coordenador: {confirmacao}\n")


    Coord["reader"] = reader
    Coord["writer"] = writer

    #asyncio.create_task(monitorar_lider())

    print("Registro finalizado. Conexão ativa.\n")

# Lida com a requisição de download de arquivo do cliente. 
async def handle_busca_cliente(cliente_writer, requisicao):
    filename = requisicao["payload"]["nome_arquivo"]
    print(f"Cliente {cliente_writer.get_extra_info('peername')} está buscando por {filename}.\n")

    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0] # Pega o primeiro dono da lista
        print(f"Arquivo {filename} encontrado no índice local. Dono: {info_dono['ip']}:{info_dono['porta']}\n")
        msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU,filename, info_dono)
        cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await cliente_writer.drain()
        return

    # Se não tiver no índice local, faz a inundação
    print(f"{filename} não encontrado localmente. Inundando a rede...\n")
    chave_identificadora = str(uuid.uuid4()) # Neste caso, utiliza o uuid4 somente para armazenar localmente na fila de queries o cliente
    #queries_pendentes[chave_identificadora] = cliente_writer # Guarda quem solicitou download

    msg_query = mensagens.cria_query_arquivo_sn(filename, chave_identificadora)
    
    # Envia a mensagem para todos os vizinhos
    for vizinho in superNosVizinhos:
        try:
            vizinho["writer"].write(msg_query.encode('utf-8') + b'\n')
            await vizinho["writer"].drain()
            print(f"Query por {filename} (ID: {chave_identificadora[:6]}) enviada para {vizinho['info']['ip']}:{vizinho['info']['porta']}\n")

            dados = await vizinho["reader"].readuntil(b'\n')
            resposta = mensagens.decodifica_mensagem(dados)
            comando = resposta.get('comando')

            if comando == mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU:
                msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU, filename, resposta["payload"]["info_dono"])
                cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
                await cliente_writer.drain()
                return


        except Exception as e:
            print(f"Falha ao enviar query para vizinho {vizinho['info']['ip']}: {e}\n")

    print("Arquivo não existe.....\n")
    msg_resposta = mensagens.cria_resposta_local_arquivo(mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_NAO_ACHOU, None, None)
    cliente_writer.write(msg_resposta.encode('utf-8') + b'\n')
    await cliente_writer.drain()


# Lida com um pedido de um cliente para indexar um novo arquivo.
async def handle_indexar_arquivo(writer, requisicao):
    nome_arquivo = requisicao["payload"]["nome_arquivo"]
    
    info_dono = None
    async with lock:
        for cliente in listaDeClientes:
            print(f"{cliente}\n")
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
                print(f"Arquivo {nome_arquivo} adicionado ao índice pelo cliente {info_dono['chave'][:6]}.\n")
            else:
                print(f"Cliente {info_dono['chave'][:6]} já havia indexado {nome_arquivo}.\n")

        # Envia um ACK de sucesso para o cliente
        msg_ack = mensagens.cria_ack_indexacao_arquivo(nome_arquivo, "SUCESSO")
        writer.write(msg_ack.encode('utf-8') + b'\n')
        await writer.drain()
        
    else:
        print(f"Falha na indexação do arquivo do cliente {writer.get_extra_info('peername')}.\n")
        msg_ack = mensagens.cria_ack_indexacao_arquivo(nome_arquivo, "FALHA_NAO_REGISTRADO")
        writer.write(msg_ack.encode('utf-8') + b'\n')
        await writer.drain()

# Lida com uma requisição vinda do super nó vizinho durante a inundação da busca por arquivos. 
async def handle_query_vizinho(vizinho_writer, requisicao):
    filename = requisicao["payload"]["nome_arquivo"]
    chave_identificadora = requisicao["payload"]["chave_identificadora"]
    addr_origem = vizinho_writer.get_extra_info('peername')
    print(f"Super nó {addr_origem} está buscando por {filename}.\n")


    # Verifica o índice local para responder ao vizinho
    if filename in indice_arquivos_local:
        info_dono = indice_arquivos_local[filename][0]
        print(f"Arquivo {filename} encontrado. Devolvendo resposta ao super nó de origem.\n")
        msg_resposta = mensagens.cria_resposta_arquivo_sn(mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU, filename, chave_identificadora, info_dono)
        vizinho_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await vizinho_writer.drain()
    else:
        print(f"Arquivo {filename} não encontrado no meu índice.\n")
        msg_resposta = mensagens.cria_resposta_arquivo_sn(mensagens.CMD_SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU, filename, None, None)
        vizinho_writer.write(msg_resposta.encode('utf-8') + b'\n')
        await vizinho_writer.drain()

# Lida com a solicitação de saída de um cliente.
async def handle_saida_cliente(writer, requisicao):
    chave_cliente_saindo = requisicao["payload"]["chave_cliente"]
    print(f"[Cliente {chave_cliente_saindo[:6]} solicitou saída.\n")

    async with lock:
        cliente_encontrado = None
        for cliente in listaDeClientes:
            if cliente["chave"] == chave_cliente_saindo:
                cliente_encontrado = cliente
                break
        
        if cliente_encontrado:
            listaDeClientes.remove(cliente_encontrado)
            print(f"Cliente {chave_cliente_saindo[:6]} removido da lista de clientes.\n")
        else:
            print(f"Cliente {chave_cliente_saindo[:6]} não estava na lista de clientes.\n")

        arquivos_para_limpar = []
        for nome_arquivo, donos in indice_arquivos_local.items():
            # Filtra a lista de donos, mantendo apenas quem não é o cliente que está saindo
            donos[:] = [dono for dono in donos if dono["chave"] != chave_cliente_saindo]
            
            # Se a lista de donos ficar vazia, da append no arquivo para remoção
            if not donos:
                arquivos_para_limpar.append(nome_arquivo)

        for nome_arquivo in arquivos_para_limpar:
            del indice_arquivos_local[nome_arquivo]
            print(f"Arquivo '{nome_arquivo}' removido do índice (sem donos).\n")
            
    try:
        writer.close()
        await writer.wait_closed()
        print(f"Conexão com {chave_cliente_saindo[:6]} fechada.\n")
    except Exception as e:
        print(f"Erro ao fechar conexão com cliente saindo: {e}\n")

async def servidorSuperNo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Cliente {addr} conectado.\n")


    try:
        sair = False
        while not sair:
            sair = await superno(reader, writer, addr)
    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}\n")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}\n")
    finally:
        print(f"Iniciando remoção do cliente {addr}...\n")
        cliente_para_remover = None
        async with lock:
            for cliente in listaDeClientes:
                if cliente["writer"] == writer:
                    cliente_para_remover = cliente
                    break
            
            if cliente_para_remover:
                chave_cliente_saindo = cliente_para_remover["chave"]
                listaDeClientes.remove(cliente_para_remover)
                print(f"Cliente {chave_cliente_saindo[:6]} removido da lista.\n")

                # Limpa os arquivos do índice
                arquivos_para_limpar = []
                for nome_arquivo, donos in indice_arquivos_local.items():
                    donos[:] = [dono for dono in donos if dono["chave"] != chave_cliente_saindo]
                    if not donos:
                        arquivos_para_limpar.append(nome_arquivo)
                
                for nome_arquivo in arquivos_para_limpar:
                    del indice_arquivos_local[nome_arquivo]
                    print(f"Arquivo '{nome_arquivo}' removido do índice.\n")
            else:
                print(f"Cliente {addr} não estava na lista de clientes registrados.\n")
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Erro ao fechar writer do cliente {addr}: {e}\n")
        
        print(f"Limpeza para {addr} concluída.\n")

async def coordenador(reader, writer, addr):
    print("coordenador chamado\n")
    dados = await reader.read(4096)

    msg_recebida = mensagens.decodifica_mensagem(dados)

    print(f"coordenado: mensage recebida -> {msg_recebida}\n")

    if msg_recebida:
        comando = msg_recebida.get("comando")

        if comando == mensagens.CMD_SN2COORD_FINISH:
            print(f"Supernó {addr} finalizou o registro dos clientes.\n")
        elif comando == mensagens.CMD_SN2COORD_SAIDA:
            print(f"Supernó {addr} solicitou a saída.\n")
            return True
        elif comando == mensagens.CMD_SN2COORD_PERGUNTA_ESTOU_VIVO:
            resposta = mensagens.cria_resposta_estou_vivo()
            writer.write(resposta.encode('utf-8'))
            print(f"Resposta enviada. Máquina: {addr}\n")
        elif comando == mensagens.CMD_SN2SN_INICIAR_ELEICAO:
            # responde
            print("Pediram para mim ser o coordenador, sendo que ja sou\n")
            mensagem = mensagens.cria_mensagem_resposta_eleicao()
            writer.write(mensagem.encode('utf-8'))
            await writer.drain()
        else:
            # Recebe demais requisições do super nó
            ...
    return False

async def superno(reader, writer, addr):
    print("superno chamado\n")
    dados = await reader.read(4096)

async def superno(reader, writer, addr):
    global ListaDeSupernos
    global superNosVizinhos

    dados = await reader.readuntil(b'\n')

    novoComando = mensagens.decodifica_mensagem(dados)
    comando = novoComando.get('comando')

    print(f"{novoComando}\n")

    if comando == mensagens.CMD_CLIENTESN2_REQUISICAO_REGISTRO:
        # Caso de requisição de registro vinda de um cliente
        await NovoCliente(reader, writer, novoComando)
    elif comando == mensagens.CMD_SN2COORD_FINISH:
        # Caso de recebimento do pacote finish vinda de um super nó
        print(f"superno {addr} finalizou registro de clientes\n")
    elif comando == mensagens.CMD_SN2SN_NOVO_COORDENADOR:
        global portaCoordenador, ipServidor, Coord
        print(f"Um novo nó coordenador foi eleito: {novoComando}\n")
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
        writer.write(mensagem.encode('utf-8') + b'\n')
        await writer.drain()

        #chama eleição
        if not em_eleicao:
            print("chamada de eleição de outro superno\n")
            await valentao()
        else:
            print("chamada de eleição de outro superno, mas ja esta em eleição\n")


    elif comando == mensagens.CMD_CLIENTE2SN_SAIDA:
        # Caso de um cliente avisando que está saindo
        await handle_saida_cliente(writer, novoComando)
        return True
    elif comando == mensagens.CMD_CLIENTE2SN_VOTO_SIM:
        await handle_voto_cliente(novoComando)  
    elif comando == mensagens.CMD_CLIENTE2SN_VOTO_NAO:
        await handle_voto_cliente(novoComando)
    elif comando == mensagens.CMD_SN2COORD_REQUISICAO_REGISTRO:
        print(f"Recebi pedido de registro de novo Supernó {addr}\n")
        
        # Gera uma chave nova para o colega
        nova_chave = str(uuid.uuid4().hex)
        
        # Responde com SUCESSO
        msg_resp = mensagens.cria_resposta_coordenador("SUCESSO", nova_chave)
        writer.write(msg_resp.encode('utf-8') + b'\n')
        await writer.drain()
        
        # Aguarda o ACK
        dados_ack = await reader.readuntil(b'\n')
        print(f"ACK recebido do novo Supernó.\n")
        
        # Adiciona à lista de supernós 
        print(f"Enviando lista de vizinhos para o novo no...\n")
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
    elif comando == mensagens.CMD_COORD2SN_LISTA_SUPERNOS:
        # Recebido quando um novo nó entra na rede e o Coord avisa
        print("Recebi atualização de lista de Supernós.\n")
        async with lock:
            ListaDeSupernos = novoComando["payload"]["supernos"]
            await conectarComOutrosSupernos()
    elif comando == mensagens.CMD_SN2SN_REDIRECT_NEIGHBOR:
        novo_ip = novoComando["payload"]["ip"]
        nova_porta = novoComando["payload"]["porta"]
        
        print(f"\n[ATUALIZAÇÃO] O Coordenador pediu para conectar no novo Supernó: {novo_ip}:{nova_porta}")
        
        # 1. Conecta no Novo Supernó
        try:
            reader_novo, writer_novo = await asyncio.open_connection(novo_ip, nova_porta)
            
            # Cria a estrutura do novo vizinho
            # Nota: A chave real viria num handshake, mas podemos usar temp ou pedir depois
            # Aqui simplificamos adicionando a conexão
            novo_vizinho = {
                "reader": reader_novo, 
                "writer": writer_novo, 
                "info": {"ip": novo_ip, "porta": nova_porta, "chave": "temp"}
            }
            
            superNosVizinhos.append(novo_vizinho)
            
            # Inicia a escuta desse novo vizinho
            asyncio.create_task(servidorSuperNo(reader_novo, writer_novo))
            print(f"[SUCESSO] Conectado ao novo vizinho {nova_porta}.")
            
            # 2. Remove o Coordenador (Remetente desta msg) da lista de VIZINHOS P2P
            # (Mas mantém a conexão física viva no objeto 'Coord' para heartbeats)
            # A variável 'writer' aqui é a conexão com o Coordenador
            
            # Filtra a lista mantendo apenas quem NÃO é o remetente desta mensagem
            superNosVizinhos = [sn for sn in superNosVizinhos if sn["writer"] != writer]

            print(f'SUPERNOS VIZINHOS {superNosVizinhos}')
            
            print("[INFO] Coordenador removido da lista de vizinhos de busca (Query).")

        except Exception as e:
            print(f"[ERRO] Falha ao conectar no novo vizinho: {e}")

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
            #asyncio.create_task(monitorar_lider())
            msg = mensagens.cria_pacote_finish()

            # Envia o pacote FINISH para o coordenador
            try:
                coord_writer = Coord.get("writer")
                if coord_writer:
                    coord_writer.write(msg.encode('utf-8') + b'\n')
                    await coord_writer.drain()
                    print("--> Pacote FINISH enviado para o Coordenador.\n")
                else:
                    print("Conexão com o Coordenador não encontrada para enviar FINISH.\n")
            except Exception as e:
                print(f"Falha ao enviar FINISH para o Coordenador: {e}\n")

            # Envia o pacote FINISH para os super nós vizinhos
            if superNosVizinhos:
                for sn in superNosVizinhos:
                    sn["writer"].write(msg.encode('utf-8') + b'\n')
                    await sn["writer"].drain()
                    print(f"FINISH enviado para {sn['info']['ip']}:{sn['info']['porta']}")

    msgACK = mensagens.cria_ack_resposta_para_cliente(novo_cliente["chave"])
    writer.write(msgACK.encode('utf-8') + b'\n')
    await writer.drain()
    print(f"ACK enviado para o cliente {novo_cliente['chave'][:10]}...\n")

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
    global isCoordenador
    
    reader = Coord.get("reader")
    writer = Coord.get("writer")
    
    if not reader or not writer:
        print("[ERRO] Conexão com Coordenador não encontrada para monitorar.\n")
        return

    print("Monitor do Coordenador iniciado (ping/listen).\n")

    while True:
        #Dorme pelo intervalo de verificação (ex: 5 segundos)
        await asyncio.sleep(10)

        if isCoordenador: # Se eu sou o coordenador, não faço nada
            continue

        try:
            # Envia um PING
            msg_ping = mensagens.cria_mensagem_alive()
            writer.write(msg_ping.encode('utf-8') + b'\n')
            await writer.drain()

            dados = await asyncio.wait_for(reader.readuntil(b'\n'), timeout=10.0)
            
            if not dados:
                raise ConnectionError("Líder fechou a conexão\n")

            msg = mensagens.decodifica_mensagem(dados)
            if not msg:
                continue

            comando = msg.get("comando")

            if comando == mensagens.CMD_COORD2SN_RESPOSTA_ESTOU_VIVO: # O pong
                print(f"Monitorando líder: ...Líder está VIVO.\n")
            elif comando == mensagens.CMD_COORD2SN_LISTA_SUPERNOS:
                async with lock:
                    global ListaDeSupernos
                    ListaDeSupernos = msg["payload"]["supernos"]
                    await conectarComOutrosSupernos()
                print(f"Monitorando líder: [BROADCAST] Lista de Supernós atualizada: {len(ListaDeSupernos)} nós.\n")
            
            else:
                print(f"Monitorando líder: [MSG] Recebida msg inesperada: {comando}\n")
        except asyncio.TimeoutError:
            #O LÍDER ESTÁ MORTO!
            print("!!! O LÍDER MORREU (timeout) !!!\n")
            await valentao()
            return

        except (ConnectionError, ConnectionResetError, asyncio.IncompleteReadError) as e:
            #O LÍDER TAMBÉM ESTÁ MORTO! (Conexão caiu)
            print(f"!!! O LÍDER MORREU (conexão perdida: {e}) !!!\n")
            await valentao()
            return


# Esta é a sua função, mas renomeada para ser a "lógica"
async def valentao():
    global desistoDeMeEleger, isCoordenador, em_eleicao

    # --- Proteção de entrada ---
    if isCoordenador:
        print("Eu já sou o coordenador, não vou iniciar eleição.\n")
        return

    async with lock:
        if em_eleicao:
            print("Já estou em um processo de eleição.\n")
            return
        em_eleicao = True

    desistoDeMeEleger = False  # Reseta a flag para esta nova eleição

    print("Começando lógica de eleição...\n")
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
        print("Não há vizinhos maiores. Eu sou o líder.\n")
        await anunciar_vitoria()
        return

    # 3. Se há vizinhos maiores, contacta-os A TODOS
    print(f"Contactando {len(vizinhos_maiores)} vizinhos maiores...\n")
    for no in vizinhos_maiores:
        # id_vizinho = int(ipaddress.ip_address(no["info"]["ip"])) #usar no lab
        id_vizinho = no["info"]["porta"]

        try:
            print(f"Enviando CMD_ELECTION para {id_vizinho}...\n")
            mensagem = mensagens.cria_mensagem_eleicao(no["info"]["chave"])
            no["writer"].write(mensagem.encode('utf-8') + b'\n')
            await no["writer"].drain()

            dados = await asyncio.wait_for(no["reader"].read(4096), timeout=10.0)

            if not dados:
                print(f"Vizinho {id_vizinho} fechou a conexão.\n")
                continue

            resposta = mensagens.decodifica_mensagem(dados)

            if resposta.get('comando') == mensagens.CMD_SN2SN_ELEICAO_INICIADO:
                # Ele respondeu "OK", registamos isso
                print(f"Vizinho {id_vizinho} respondeu OK.\n")

                # Registamos que PELO MENOS UM respondeu
                recebi_ok_de_um_maior = True

                # Marcamos a desistência geral, mas NÃO paramos o loop
                desistoDeMeEleger = True
                break

                # <<-- O 'break' FOI REMOVIDO DAQUI -->>
                # O loop continua para contactar os outros nós maiores

        except asyncio.TimeoutError:
            print(f"Vizinho {id_vizinho} não respondeu (timeout). Ignorando.\n")
            # Continuamos o loop, pois este "valentão" está fora do jogo

        except Exception as e:
            print(f"Erro ao contactar vizinho {id_vizinho}: {e}. Assumindo que está morto.\n")
            continue

    # 4. Avalia o resultado (APÓS o loop ter terminado)
    if not recebi_ok_de_um_maior:
        # Se NINGUÉM (vivo) respondeu OK, eu ganhei
        print("Nenhum vizinho maior respondeu OK. Serei o novo líder.\n")
        await anunciar_vitoria()
    else:
        # Se PELO MENOS UM respondeu OK, eu perdi
        print("Desistindo de me eleger, um nó maior está ativo.\n")
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
            no["writer"].write(msg_vitoria.encode('utf-8') + b'\n')
            await no["writer"].drain()
        except Exception as e:
            print(f"Falha ao anunciar vitória para {no['info']['ip']}: {e}\n")

    # Inicia o processo de replicação 2PC
    print("Iniciando processo de replicação (2PC)...\n")
    asyncio.create_task(iniciar_replicacao_consenso(None)) 


async def main():
    # Esta tarefa manterá o servidor de clientes/supernós rodando
    server_task = None
    coordinator_listener_task = None

    try:
        await registro()

        servidor = await asyncio.start_server(servidorSuperNo, "0.0.0.0", portaSuperno)
        print(f"Super nó escutando em 0.0.0.0:{portaSuperno} (Registrado com IP {ipLocal})\n")

        # Inicia a tarefa do servidor
        server_task = asyncio.create_task(servidor.serve_forever())
        coordinator_listener_task = asyncio.create_task(monitorar_lider())

        await asyncio.gather(server_task, coordinator_listener_task)

    except asyncio.CancelledError:
        print("Recebido sinal de cancelamento.\n")
    finally:
        print("Iniciando encerramento...\n")
        
        # Para o servidor de escuta
        if server_task:
            server_task.cancel()
        if coordinator_listener_task:
            coordinator_listener_task.cancel()
        
        # Avisa o coordenador
        coord_writer = Coord.get("writer")
        if coord_writer:
            try:
                print("Notificando o Coordenador sobre a saída...\n")
                msg_saida = mensagens.cria_mensagem_saida_superno(minha_chave_global)
                coord_writer.write(msg_saida.encode('utf-8') + b'\n')
                await coord_writer.drain()
                coord_writer.close()
                await coord_writer.wait_closed()
                print("Notificação de saída enviada.\n")
            except Exception as e:
                print(f"Falha ao notificar o coordenador: {e}\n")
        
        print("Supernó desligado.\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEncerrando supernó...\n")