import asyncio
import sys
import uuid
import os      
from src.shared import mensagens

#USAR NO LAB
#ipLocal = os.environ.get("HOST_IP", "127.0.0.1")         
#ipSuperno = os.environ.get("SUPERNODE_IP", "127.0.0.1") 
#porta = int(os.environ.get("SUPERNODE_PORT", 8001))   

ipLocal = "127.0.0.1"
ipSuperno = "127.0.0.1"
porta = 8001

reader = None
writer = None
chave_identificadora = None

async def registro():
    global chave_identificadora, reader, writer, ipLocal, ipSuperno, porta

    try:
        reader, writer = await asyncio.open_connection(ipSuperno, porta)
        print(f"Conectado ao superno em {ipSuperno}:{porta}")
    except ConnectionRefusedError:
        print(f"[ERRO] Conexão recusada. O supernó {ipSuperno}:{porta} está offline?")
        return False # Indica falha no registro

    # Gera a chave única usando hash (SHA-1) do IP
    chave_identificadora = uuid.uuid5(uuid.NAMESPACE_DNS, ipLocal)
    print(f"Chave identificadora gerada (SHA-1): {chave_identificadora}")

    # Envia a requisição de registro
    msgDeregistro = mensagens.cria_requisicao_registro_cliente(ipLocal, porta, str(chave_identificadora))
    writer.write(msgDeregistro.encode('utf-8'))
    await writer.drain()

    #espera ack
    dados = await reader.read(4096)
    requisicao_registro = mensagens.decodifica_mensagem(dados)
    print("ACK recebido do supernó:", requisicao_registro)

    return True # Indica sucesso no registro 


async def enviar_arquivo_possuido(nome_arquivo):
    """Envia ao supernó o nome de um arquivo que este cliente possui."""

    if not writer:
        print("Não está conectado. Tente reiniciar.")
        return

    msg = mensagens.cria_requisicao_indexar_arquivo(nome_arquivo)
    writer.write(msg.encode('utf-8'))
    await writer.drain()

    dados = await reader.read(4096)
    resposta = mensagens.decodifica_mensagem(dados)
    print(f"[Supernó]: {resposta}")



async def buscar_arquivo(nome_arquivo):
    """Solicita ao supernó onde encontrar um arquivo específico."""

    if not writer:
        print("Não está conectado. Tente reiniciar.")
        return

    msg = mensagens.cria_requisicao_busca_cliente(nome_arquivo)
    writer.write(msg.encode('utf-8'))
    await writer.drain()

    dados = await reader.read(4096)
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
            writer.write(msg_saida.encode('utf-8'))
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
    try:
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