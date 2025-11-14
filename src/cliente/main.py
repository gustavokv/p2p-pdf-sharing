import asyncio
import sys
import uuid
import os      
from src.shared import mensagens

#USAR NO LAB
ipLocal = os.environ.get("HOST_IP", "127.0.0.1")         
ipSuperno = os.environ.get("SUPERNODE_IP", "127.0.0.1") 
porta = int(os.environ.get("SUPERNODE_PORT", 8001))  

ipCoordenador = os.environ.get("COORDINATOR_IP", "127.0.0.1")
portaCoordenador = int(os.environ.get("COORDINATOR_PORT", 8000)) - 1

#ipLocal = "127.0.0.1"
#ipSuperno = "127.0.0.1"
#porta = 8001

reader = None
writer = None
chave_identificadora = None

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
            print("[ERRO] Resposta inválida do Coordenador.")
            return None
            
    except Exception as e:
        print(f"[ERRO] Não foi possível contatar o Coordenador: {e}")
        return None

async def medir_latencia(ip, porta):
    """Mede o RTT de um handshake TCP para um supernó."""
    inicio = asyncio.get_event_loop().time()
    try:
        # Tenta conectar com um timeout curto (ex: 2 segundos)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, porta), 
            timeout=2.0
        )
        fim = asyncio.get_event_loop().time()
        
        # Fecha a conexão imediatamente
        writer.close()
        await writer.wait_closed()
        
        latencia = (fim - inicio) * 1000 # em milissegundos
        print(f"  -> {ip}:{porta} respondeu em {latencia:.2f} ms")
        return latencia
        
    except (asyncio.TimeoutError, ConnectionRefusedError):
        print(f"  -> {ip}:{porta} falhou (Timeout/Recusado)")
        return float('inf') # Retorna "infinito" se falhar

async def registro():
    global chave_identificadora, reader, writer, ipLocal, ipSuperno, porta
    porta = int(sys.argv[1])  # REMOVER NO LAB

    try:
        reader, writer = await asyncio.open_connection(ipSuperno, porta)
        print(f"Conectado ao superno em {ipSuperno}:{porta}")
    except ConnectionRefusedError:
        print(f"[ERRO] Conexão recusada. O supernó {ipSuperno}:{porta} está offline?")
        return False # Indica falha no registro

    # Gera a chave única usando hash (SHA-1) do IP
    #chave_identificadora = uuid.uuid5(uuid.NAMESPACE_DNS, ipLocal)
    chave_identificadora = uuid.uuid4()

    print(f"Chave identificadora gerada (SHA-1): {chave_identificadora}")

    # Envia a requisição de registro
    msgDeregistro = mensagens.cria_requisicao_registro_cliente(ipLocal, porta, str(chave_identificadora))
    writer.write(msgDeregistro.encode('utf-8') + b'\n')
    await writer.drain()

    #espera ack
    dados = await reader.readuntil(b'\n')
    requisicao_registro = mensagens.decodifica_mensagem(dados)
    print("ACK recebido do supernó:", requisicao_registro)

    return True # Indica sucesso no registro 


async def enviar_arquivo_possuido(nome_arquivo):
    """Envia ao supernó o nome de um arquivo que este cliente possui."""

    if not writer:
        print("Não está conectado. Tente reiniciar.")
        return

    msg = mensagens.cria_requisicao_indexar_arquivo(nome_arquivo)
    writer.write(msg.encode('utf-8') + b'\n')
    await writer.drain()

    dados = await reader.readuntil(b'\n')
    resposta = mensagens.decodifica_mensagem(dados)
    print(f"[Supernó]: {resposta}")



async def buscar_arquivo(nome_arquivo):
    """Solicita ao supernó onde encontrar um arquivo específico."""

    if not writer:
        print("Não está conectado. Tente reiniciar.")
        return

    msg = mensagens.cria_requisicao_busca_cliente(nome_arquivo)
    writer.write(msg.encode('utf-8') + b'\n')
    await writer.drain()

    dados = await reader.readuntil(b'\n')
    resposta = mensagens.decodifica_mensagem(dados)
    print(f"[Supernó]: {resposta}")

# Envia a notificação de saída e fecha a conexão.
async def sair_da_rede():
    global writer, chave_identificadora
    if writer and chave_identificadora:
        print("Notificando o supernó sobre a saída...")
        try:
            # Envia a mensagem de saída
            msg_saida = mensagens.cria_mensagem_saida_cliente(str(chave_identificadora))
            writer.write(msg_saida.encode('utf-8') + b'\n')
            # timeout para garantir que a mensagem seja enviada
            await asyncio.wait_for(writer.drain(), timeout=2.0)
            print("Notificação de saída enviada.")
        except Exception as e:
            print(f"Falha ao notificar supernó sobre saída: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            writer = None # Limpa a variável global
            print("Conexão fechada.")
    elif writer:
        # Se conectou mas não se registrou
        writer.close()
        await writer.wait_closed()
    
    print("Cliente encerrado.")


async def menu():
    global ipSuperno, porta

    try:
        static_ip = os.environ.get("SUPERNODE_IP")
        
        if static_ip:
            # Se foi fornecido, usa os valores globais (já definidos no topo)
            print(f"IP do Supernó fornecido estaticamente: {ipSuperno}:{porta}")
        else:
            # Se NENHUM IP foi fornecido, inicia a descoberta dinâmica
            print("Nenhum IP de supernó fornecido. Iniciando descoberta dinâmica...")
            
            lista_sn = await obter_lista_supernos()
            if not lista_sn:
                print("Não foi possível obter a lista de supernós. Encerrando.")
                return

            print("Medindo latência para encontrar o supernó mais próximo...")
            tasks = [medir_latencia(sn['ip'], sn['porta']) for sn in lista_sn]
            latencias = await asyncio.gather(*tasks)
            
            melhor_latencia = min(latencias)
            if melhor_latencia == float('inf'):
                print("Nenhum supernó respondeu. Encerrando.")
                return
                
            # Encontra o supernó correspondente à menor latência
            melhor_sn = lista_sn[latencias.index(melhor_latencia)]
            
            # Define os globais que 'registro()' usará
            ipSuperno = melhor_sn['ip']
            porta = melhor_sn['porta']
            
            print(f"Supernó mais próximo selecionado: {ipSuperno}:{porta} ({melhor_latencia:.2f} ms)")

        if not await registro():
            print("Falha no registro. Encerrando.")
            return

        while True:
            print("\n=== MENU CLIENTE P2P ===")
            print("1 - Enviar arquivo que possuo (Indexar)")
            print("2 - Buscar arquivo específico")
            print("3 - Sair")
            
            opcao = input("Escolha uma opção: ")

            if opcao == "1":
                nome = input("Nome do arquivo que você possui: ")
                await enviar_arquivo_possuido(nome)
            elif opcao == "2":
                nome = input("Nome do arquivo que deseja buscar: ")
                await buscar_arquivo(nome)
            elif opcao == "3":
                print("Saindo...")
                break # Sai do loop e vai para o 'finally'
            else:
                print("❌ Opção inválida.")
    
    except (ConnectionResetError, asyncio.IncompleteReadError) as e:
        print(f"Conexão com o supernó perdida: {e}")    
    except KeyboardInterrupt:
        print("Ctrl+C pressionado...")
    finally:
        # Este bloco é executado quando:
        # - Opção "3 - Sair"
        # - Ctrl+C (KeyboardInterrupt)
        # - Erro de conexão
        await sair_da_rede()



if __name__ == "__main__":
    asyncio.run(menu())