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

    await asyncio.sleep(999.0)

async def main():
    await registro()

if __name__ == "__main__":
    asyncio.run(main())