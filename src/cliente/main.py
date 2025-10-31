import asyncio
import sys
import uuid
from src.shared import mensagens


ipLocal = "127.0.0.1"
ipSuperno = "127.0.0.1"
porta = 8001


async def registro():
    global porta
    porta = int(sys.argv[1])

    #conectar ao superno
    reader, writer = await asyncio.open_connection(ipSuperno, porta)
    print(f"Conectado ao superno em {ipSuperno}:{porta}")

    # Gera a chave única e devolve para o super nó
    chave_identificadora = uuid.uuid4().hex #para simular uma chave unica gerada
    #chave_identificadora = uuid.uuid5(uuid.NAMESPACE_DNS, ipLocal) #quando testarmos com ip no lab
    print(f"Chave identificadora gerada")

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