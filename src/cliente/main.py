import asyncio
import sys
import uuid
import json
import os      
from src.shared import mensagens

#USAR NO LAB
ipLocal = os.environ.get("HOST_IP", "127.0.0.1")         
ipSuperno = os.environ.get("SUPERNODE_IP", "127.0.0.1") 
portaSuperno = int(os.environ.get("SUPERNODE_PORT", 8001))  

ipCoordenador = os.environ.get("COORDINATOR_IP", "127.0.0.1")
portaCoordenador = int(os.environ.get("COORDINATOR_PORT", 8000)) - 1

minhaPortaPeer = int(os.environ.get("PEER_PORT", 9001))
PASTA_ARQUIVOS = "shared_pdfs"

#ipLocal = "127.0.0.1"
#ipSuperno = "127.0.0.1"
#porta = 8001

reader_sn = None
writer_sn = None
chave_identificadora = None

global_reply_queue = asyncio.Queue()

async def handle_pedido_votacao(requisicao):
    """Chamado quando o supernó pede para votar no consenso. """
    print("\nConsenso - Pedido de Votação recebido do Supernó.")
    
    try:
        tid = requisicao["payload"]["tid"]
        indice_recebido = requisicao["payload"]["indice"]
        soma_mestre = requisicao["payload"]["soma"]

        # Cliente calcula sua própria soma dos tamanhos dos arquivos
        soma_cliente = 0
        for donos_lista in indice_recebido.values():
            for dono in donos_lista:
                # O 'valor' é o tamanho do arquivo
                soma_cliente += dono.get("valor", 0) 
        
        # Compara as somas e vota
        if soma_cliente == soma_mestre:
            print(f"Consenso - Verificação OK. Soma deu {soma_cliente}. Votando SIM.")
            msg_voto = mensagens.cria_voto_sim(tid)
        else:
            print(f"Consenso - FALHA NA SOMA! Mestre deu {soma_mestre}, Cliente deu {soma_cliente}. Votando NÃO.")
            msg_voto = mensagens.cria_voto_nao(tid)
        
        writer_sn.write(msg_voto.encode('utf-8') + b'\n')
        await writer_sn.drain()
        
    except Exception as e:
        print(f"Consenso -  Erro ao processar voto: {e}")

async def ouvir_superno_loop():
    """
    Tarefa dedicada a ouvir todas as mensagens do Supernó.
    """
    global reader_sn
    print("Ouvinte do Supernó iniciado!")
    
    try:
        while True:
            dados = await reader_sn.readuntil(b'\n')
            msg = mensagens.decodifica_mensagem(dados)
            if not msg:
                continue

            comando = msg.get("comando")

            # Lógica de 2PC 
            if comando == mensagens.CMD_SN2CLIENTE_PEDIDO_VOTACAO:
                await handle_pedido_votacao(msg)
            elif comando == mensagens.CMD_SN2CLIENTE_GLOBAL_COMMIT:
                print(f"\nConsenso - Transação {msg['payload']['tid'][:6]} COMITADA.")
            elif comando == mensagens.CMD_SN2CLIENTE_GLOBAL_ABORT:
                print(f"\nConsenso - Transação {msg['payload']['tid'][:6]} ABORTADA.")
            elif comando == mensagens.CMD_SN2CLIENTE_PROMOCAO:
                print("\n" + "="*40)
                print("!!! RECEBI ORDEM DE PROMOÇÃO: VIRANDO SUPERNÓ !!!")
                print("="*40)
                
                # Salva o índice recebido em um arquivo temp para o novo supernó carregar ao iniciar.
                novo_indice = msg.get("payload", {}).get("indice")
                with open("indice_replicado.json", "w") as f:
                    json.dump(novo_indice, f)

                # Fechar conexões
                if writer_sn:
                    writer_sn.close()
                
                # Substitui o processo atual pelo Supernó. Argumentos: python, superno.py, <PORTA_ATUAL>
                python_exe = sys.executable
                script_superno = "src/superno/main.py"
                
                print(f"Reiniciando como Supernó na porta {minhaPortaPeer}...")
                
                # Define a porta do Coordenador como a porta do Supernó que está nos promovendo.
                os.environ['COORDINATOR_PORT'] = str(portaSuperno)

                # Isso mata o cliente e sobe o supernó no mesmo terminal
                os.execl(python_exe, python_exe, script_superno, str(minhaPortaPeer))
            
            else:
                await global_reply_queue.put(msg) 

    except (asyncio.IncompleteReadError, ConnectionError) as e:
        print(f"\n[ERRO] Conexão com Supernó perdida (no ouvinte): {e}")
    except asyncio.CancelledError:
        pass # Encerramento normal
    except Exception as e:
        print(f"\n[ERRO] Erro no ouvinte do Supernó: {e}")
    finally:
        print("Ouvinte do Supernó encerrado.")

async def obter_lista_supernos():
    """Conecta-se ao Coordenador para obter a lista de supernós ativos."""
    print(f"Contatando Coordenador em {ipCoordenador}:{portaCoordenador} para obter lista de supernós...")
    try:
        reader, writer = await asyncio.open_connection(ipCoordenador, portaCoordenador)
        
        # Envia qualquer mensagem para pedir a lista
        writer.write(b"GET_LIST\n")
        await writer.drain()
        
        dados = await reader.readuntil(b'\n')
        resposta = mensagens.decodifica_mensagem(dados)
        
        writer.close()
        await writer.wait_closed()
        
        if resposta and resposta.get("comando") == mensagens.CMD_COORD2SN_LISTA_SUPERNOS:
            lista = resposta.get("payload", {}).get("supernos", [])
            print(f"Lista recebida com {len(lista)} supernós.")
            return lista
        else:
            print("Resposta inválida do Coordenador.")
            return None
            
    except Exception as e:
        print(f"Não foi possível contatar o Coordenador: {e}")
        return None

async def medir_latencia(ip, porta):
    """Mede o RTT de um envio de pacote para um supernó."""
    inicio = asyncio.get_event_loop().time()
    try:
        # Tenta conectar com um timeout curto
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, porta), 
            timeout=2.0
        )
        fim = asyncio.get_event_loop().time()
        
        # Fecha a conexão
        writer.close()
        await writer.wait_closed()
        
        latencia = (fim - inicio) * 1000 # em milissegundos
        print(f"  -> {ip}:{porta} respondeu em {latencia:.2f} ms")
        return latencia
        
    except (asyncio.TimeoutError, ConnectionRefusedError):
        print(f"  -> {ip}:{porta} falhou (Timeout/Recusado)")
        return float('inf') # Retorna infinito se falhar

async def registro():
    global chave_identificadora, reader_sn, writer_sn, ipLocal, ipSuperno, portaSuperno
    #porta = int(sys.argv[1])  REMOVER NO LAB

    try:
        reader_sn, writer_sn = await asyncio.open_connection(ipSuperno, portaSuperno)
        print(f"Conectado ao superno em {ipSuperno}:{portaSuperno}")
    except ConnectionRefusedError:
        print(f"Conexão recusada. O supernó {ipSuperno}:{portaSuperno} está offline?")
        return False # Indica falha no registro

    # Gera a chave única usando hash (SHA-1) do IP
    #chave_identificadora = uuid.uuid5(uuid.NAMESPACE_DNS, ipLocal)
    chave_identificadora = uuid.uuid4()

    print(f"Chave identificadora gerada (SHA-1): {chave_identificadora}")

    # Envia a requisição de registro
    msgDeregistro = mensagens.cria_requisicao_registro_cliente(ipLocal, minhaPortaPeer, str(chave_identificadora))
    writer_sn.write(msgDeregistro.encode('utf-8') + b'\n')
    await writer_sn.drain()

    #espera ack
    dados = await reader_sn.readuntil(b'\n')
    requisicao_registro = mensagens.decodifica_mensagem(dados)
    print("ACK recebido do supernó:", requisicao_registro)

    return True # Indica sucesso no registro 

async def handle_download_request(reader_peer, writer_peer):
    """Lida com um pedido de download de outro cliente."""
    addr_peer = writer_peer.get_extra_info('peername')
    print(f"\nConexão de {addr_peer} recebida.")

    try:
        dados = await reader_peer.readuntil(b'\n')
        requisicao = mensagens.decodifica_mensagem(dados)
        
        if not requisicao or requisicao.get("comando") != mensagens.CMD_PEER2PEER_REQUISICAO_DOWNLOAD:
            print(f"Pedido inválido de {addr_peer}. Fechando.")
            return

        nome_arquivo = requisicao["payload"]["nome_arquivo"]
        caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
        
        print(f"Peer {addr_peer} solicitou o arquivo: {nome_arquivo}")

        if os.path.exists(caminho_arquivo):
            print(f"Arquivo encontrado. Enviando...")
            try:
                writer_peer.write(b"OK\n")
                await writer_peer.drain()
                
                # Envia o arquivo em blocos
                with open(caminho_arquivo, 'rb') as f:
                    while True:
                        bloco = f.read(4096)
                        if not bloco:
                            break # Fim do arquivo
                        writer_peer.write(bloco)
                        await writer_peer.drain()
                
                print(f"Envio de {nome_arquivo} para {addr_peer} concluído.")

                # Sinaliza para o outro lado que não há mais dados (Envia um pacote FIN).
                if writer_peer.can_write_eof():
                    writer_peer.write_eof()

                await writer_peer.drain()

            except Exception as e:
                print(f"Erro durante a transferência para {addr_peer}: {e}")
        else:
            print(f"Arquivo {nome_arquivo} não encontrado localmente. Avisando peer.")
            writer_peer.write(b"ERROR_NOT_FOUND\n")
            await writer_peer.drain()

    except (ConnectionResetError, asyncio.IncompleteReadError):
        print(f"Conexão com {addr_peer} perdida.")
    except Exception as e:
        print(f"Erro inesperado com {addr_peer}: {e}")
    finally:
        await asyncio.sleep(0.1) # Garante que o FIN será enviado
        if writer_peer and not writer_peer.is_closing():
            writer_peer.close()
            await writer_peer.wait_closed()


async def enviar_arquivo_possuido(nome_arquivo):
    """Envia ao supernó o nome de um arquivo que este cliente possui."""

    if not writer_sn:
        print("Não está conectado. Tente reiniciar.")
        return
    
    caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
    if not os.path.exists(caminho_arquivo):
        print(f"Arquivo '{nome_arquivo}' não encontrado na pasta '{PASTA_ARQUIVOS}'.")
        print("Por favor, crie a pasta 'pdf_files' e coloque seus arquivos lá.")
        return
    
    tamanho_arquivo = os.path.getsize(caminho_arquivo)
    
    msg = mensagens.cria_requisicao_indexar_arquivo(nome_arquivo, tamanho_arquivo)
    writer_sn.write(msg.encode('utf-8') + b'\n')
    await writer_sn.drain()

    print("Aguardando ACK da indexação...")
    resposta = await global_reply_queue.get()
    global_reply_queue.task_done()

    print(f"[Supernó]: {resposta}")


async def buscar_arquivo(nome_arquivo):
    """Solicita ao supernó onde encontrar um arquivo específico."""

    if not writer_sn:
        print("Não está conectado. Tente reiniciar.")
        return

    msg = mensagens.cria_requisicao_busca_cliente(nome_arquivo)
    writer_sn.write(msg.encode('utf-8') + b'\n')
    await writer_sn.drain()

    print("Aguardando resposta da busca...")
    resposta = await global_reply_queue.get()
    global_reply_queue.task_done()

    print(f"[Supernó]: {resposta}")

    comando = resposta.get("comando")
    
    if comando == mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU:
        info_dono = resposta["payload"]["info_dono"]
        ip_dono = info_dono["ip"]
        porta_dono = info_dono["porta"]
        
        print(f"Arquivo encontrado! Dono está em: {ip_dono}:{porta_dono}")
        
        # Pergunta ao usuário se quer baixar
        if ip_dono == ipLocal and porta_dono == minhaPortaPeer:
            print("Este arquivo já pertence a você.")
            return

        escolha_raw = await asyncio.to_thread(input, "Deseja iniciar o download? (s/n): ")
        escolha = escolha_raw.strip().lower()
        if escolha == 's':
            await realizar_download(nome_arquivo, ip_dono, porta_dono)
        else:
            print("Download cancelado.")
            
    elif comando == mensagens.CMD_SN2CLIENTE_RESPOSTA_BUSCA_NAO_ACHOU:
        print(f"Arquivo '{nome_arquivo}' não foi encontrado na rede.")
    else:
        print(f"Resposta inesperada: {resposta}")

async def realizar_download(nome_arquivo, ip_dono, porta_dono):
    """Conecta-se a outro peer e baixa o arquivo."""
    print(f"Iniciando conexão P2P com {ip_dono}:{porta_dono}...")
    try:
        reader_peer, writer_peer = await asyncio.open_connection(ip_dono, porta_dono)
    except Exception as e:
        print(f"Não foi possível conectar ao peer: {e}")
        return

    try:
        msg_req = mensagens.cria_requisicao_download_peer(nome_arquivo)
        writer_peer.write(msg_req.encode('utf-8') + b'\n')
        await writer_peer.drain()

        resposta_peer = await reader_peer.readuntil(b'\n')
        
        if resposta_peer == b"ERROR_NOT_FOUND\n":
            print(f"O peer {ip_dono} não encontrou o arquivo.")
            return
        
        if resposta_peer != b"OK\n":
            print(f"Peer {ip_dono} respondeu de forma inesperada.")
            return
            
        print(f"Peer aceitou. Iniciando download de '{nome_arquivo}'...")
        
        os.makedirs(PASTA_ARQUIVOS, exist_ok=True)
        caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
        
        total_bytes = 0
        with open(caminho_arquivo, 'wb') as f:
            while True:
                try:
                    bloco = await reader_peer.read(4096)
                    if not bloco:
                        break
                    total_bytes += len(bloco)
                    # Escrita não bloqueante
                    await asyncio.to_thread(f.write, bloco)
                except asyncio.IncompleteReadError:
                    break
        
        print(f"\nDownload de '{nome_arquivo}' concluído! ({total_bytes} bytes recebidos).")
        print(f"Arquivo salvo em: {caminho_arquivo}")
        
    except Exception as e:
        print(f"Erro durante o download: {e}")
    finally:
        writer_peer.close()
        await writer_peer.wait_closed()

# Envia a notificação de saída e fecha a conexão.
async def sair_da_rede():
    global writer_sn, chave_identificadora
    if writer_sn and chave_identificadora:
        print("Notificando o supernó sobre a saída...")
        try:
            # Envia a mensagem de saída
            msg_saida = mensagens.cria_mensagem_saida_cliente(str(chave_identificadora))
            writer_sn.write(msg_saida.encode('utf-8') + b'\n')
            # timeout para garantir que a mensagem seja enviada
            await asyncio.wait_for(writer_sn.drain(), timeout=2.0)
            print("Notificação de saída enviada.")
        except Exception as e:
            print(f"Falha ao notificar supernó sobre saída: {e}")
        finally:
            writer_sn.close()
            await writer_sn.wait_closed()
            writer_sn = None # Limpa a variável global
            print("Conexão fechada.")
    elif writer_sn:
        # Se conectou mas não se registrou
        writer_sn.close()
        await writer_sn.wait_closed()
    
    print("Cliente encerrado.")


async def menu_loop():
    """O loop principal do menu do usuário."""
    try:
        while True:
            print("\n=== MENU CLIENTE P2P ===")
            print(f"(Conectado a {ipSuperno}:{portaSuperno} | Escutando em {minhaPortaPeer})")
            print("1 - Enviar arquivo que possuo (Indexar)")
            print("2 - Buscar arquivo específico (Download)")
            print("3 - Sair")
            
            opcao = await asyncio.to_thread(input, "Escolha uma opção: ")

            if opcao == "1":
                # Cria a pasta se não existir
                os.makedirs(PASTA_ARQUIVOS, exist_ok=True)
                nome = await asyncio.to_thread(input, f"Nome do arquivo (deve estar em ./{PASTA_ARQUIVOS}/): ")
                await enviar_arquivo_possuido(nome)
            elif opcao == "2":
                nome = await asyncio.to_thread(input, "Nome do arquivo que deseja buscar: ")
                await buscar_arquivo(nome)
            elif opcao == "3":
                print("Saindo...")
                break # Sai do loop
            else:
                print("❌ Opção inválida.")
    except (ConnectionResetError, asyncio.IncompleteReadError) as e:
        print(f"\nConexão com o supernó perdida: {e}")
    except asyncio.CancelledError:
        print("\nRecebido sinal de encerramento...")

async def main():
    """Função principal que inicia a descoberta, registro e as tarefas paralelas."""
    global ipSuperno, portaSuperno
    
    servidor_peer_task = None
    menu_task = None
    ouvinte_sn_task = None
    
    try:
        static_ip = os.environ.get("SUPERNODE_IP")
        
        if static_ip:
            print(f"IP do Supernó fornecido estaticamente: {ipSuperno}:{portaSuperno}")
        else:
            print("Nenhum IP de supernó fornecido. Iniciando descoberta dinâmica...")
            lista_sn = await obter_lista_supernos()
            if not lista_sn:
                return
            
            print("Medindo latência...")
            tasks = [medir_latencia(sn['ip'], sn['porta']) for sn in lista_sn]
            latencias = await asyncio.gather(*tasks)
            
            melhor_latencia = min(latencias)
            if melhor_latencia == float('inf'):
                print("Nenhum supernó respondeu.")
                return
                
            melhor_sn = lista_sn[latencias.index(melhor_latencia)]
            ipSuperno = melhor_sn['ip']
            portaSuperno = melhor_sn['porta']
            print(f"Supernó mais próximo selecionado: {ipSuperno}:{portaSuperno}")

        # Tenta se registrar no Supernó
        if not await registro():
            print("Falha no registro. Encerrando.")
            return

        # Inicia o servidor P2P para escutar outros clientes
        servidor_peer = await asyncio.start_server(
            handle_download_request, "0.0.0.0", minhaPortaPeer
        )
        print(f"Servidor P2P iniciado. Escutando em 0.0.0.0:{minhaPortaPeer}")
        
        # Cria as tarefas paralelas
        servidor_peer_task = asyncio.create_task(servidor_peer.serve_forever())
        ouvinte_sn_task = asyncio.create_task(ouvir_superno_loop())
        menu_task = asyncio.create_task(menu_loop())
        
        # Roda o menu e o servidor P2P ao mesmo tempo
        tasks = {menu_task, servidor_peer_task, ouvinte_sn_task}
        done, pending = await asyncio.wait(
            tasks, 
            return_when=asyncio.FIRST_COMPLETED
        )

    except KeyboardInterrupt:
        print("\nCtrl+C pressionado...")
    except asyncio.CancelledError:
        pass 
    finally:
        # Cancela as tarefas
        if menu_task:
            menu_task.cancel()
        if servidor_peer_task:
            servidor_peer_task.cancel()
        if ouvinte_sn_task:
            ouvinte_sn_task.cancel()
        
        # Espera as tarefas serem canceladas
        await asyncio.sleep(0.1) 
        
        # Fecha a conexão com o Supernó
        await sair_da_rede()

if __name__ == "__main__":
    asyncio.run(main())