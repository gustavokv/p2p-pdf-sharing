import asyncio
import sys
import uuid
import os      
from src.shared import mensagens

#USAR NO LAB
#ipLocal = os.environ.get("HOST_IP", "127.0.0.1")         # LÊ DO AMBIENTE
#ipSuperno = os.environ.get("SUPERNODE_IP", "127.0.0.1") # LÊ DO AMBIENTE
#porta = int(os.environ.get("SUPERNODE_PORT", 8001))   # LÊ DO AMBIENTE

ipLocal = "127.0.0.1"
ipSuperno = "127.0.0.1"
porta = 8001


async def registro():
    global porta #REMOVER NO LAB
    porta = int(sys.argv[1]) #REMOVER NO LAB

    #conectar ao superno
    reader, writer = await asyncio.open_connection(ipSuperno, porta)
    print(f"Conectado ao superno em {ipSuperno}:{porta}")

    # Gera a chave única e devolve para o super nó
    chave_identificadora = uuid.uuid4().hex #para simular uma chave unica gerada
    #chave_identificadora = uuid.uuid5(uuid.NAMESPACE_DNS, ipLocal) #USAR NO LAB
    print(f"Chave identificadora gerada: {chave_identificadora}")

    msgDeregistro = mensagens.cria_requisicao_registro_cliente(ipLocal, porta, chave_identificadora)
    writer.write(msgDeregistro.encode('utf-8'))
    await writer.drain()

    #espera ack
    dados = await reader.read(4096)
    requisicao_registro = mensagens.decodifica_mensagem(dados)
    print("ACK recebido do supernó:", requisicao_registro)

    return chave_identificadora

async def main():
    reader = None
    writer = None
    chave_identificadora = None

    try:
        try:
            reader, writer = await asyncio.open_connection(ipSuperno, porta)
            print(f"Conectado ao superno em {ipSuperno}:{porta}")
        except ConnectionRefusedError:
            print("Conexão recusada. Encerrando.")
            return

        chave_identificadora = await registro(reader, writer)
        
        if not chave_identificadora:
            print("Falha ao se registrar. Encerrando.")
            return

        print("Registro concluído do cliente.")
        
        # Loop para manter o cliente vivo e escutando
        while True:
            dados = await reader.read(4096)
            if not dados:
                print("Conexão com Supernó perdida.")
                break
            
            msg = mensagens.decodifica_mensagem(dados)
            if msg:
                print(f"Mensagem recebida do Supernó: {msg.get('comando')}")

    except (asyncio.CancelledError, KeyboardInterrupt):
        print("Sinal de desligamento recebido...")
    
    except (ConnectionResetError, asyncio.IncompleteReadError) as e:
        print(f"Conexão com Supernó perdida abruptamente: {e}")

    finally:
        # Lógica de Saída 
        if writer and chave_identificadora:
            print("Notificando o supernó sobre a saída")
            try:
                # Envia a mensagem de saída
                msg_saida = mensagens.cria_mensagem_saida_cliente(chave_identificadora)
                writer.write(msg_saida.encode('utf-8'))

                await asyncio.wait_for(writer.drain(), timeout=2.0)
                print("Notificação enviada.")
            except Exception as e:
                print(f"Falha ao notificar supernó: {e}")
            finally:
                writer.close()
                await writer.wait_closed()
        elif writer:
            # Se conectou mas não se registrou
            writer.close()
            await writer.wait_closed()
        
        print("Cliente encerrado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Encerrando...")