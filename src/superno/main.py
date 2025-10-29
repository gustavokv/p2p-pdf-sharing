import asyncio
from src.shared import mensagens

ipServidor = "127.0.0.1"
ipLocal = "127.0.0.1"
listaDeSupernos = None
listaDeClientes = []
portaCoordenador = 8000
portaSuperno = 8001
nunClinteMax = 1
lock = asyncio.Lock()
readWriterCoord = {}

async def registro():
    reader, writer = await asyncio.open_connection(ipServidor, portaCoordenador)
    print(f"Conectado ao coordenador em {ipServidor}:{portaCoordenador}")

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
    global listaDeSupernos
    listaDeSupernos = confirmacao["payload"]["supernos"]
    print(f"Lista de supernos recebida: {listaDeSupernos}")

    dados = await reader.read(4096)
    confirmacao = mensagens.decodifica_mensagem(dados)
    print(f"Mensagem do coordenador: {confirmacao}")

    readerWriter = {"reader": reader, "writer": writer}
    async with lock:
        readWriterCoord[ipLocal] = readerWriter

    print("Registro finalizado. Conexão ativa.")


async def servidorSuperNo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Cliente {addr} conectado.")

    try:
        dados = await reader.read(4096)
        requisicao_registro = mensagens.decodifica_mensagem(dados)

        novo_cliente = {
            "writer": writer,
            "chave": requisicao_registro["payload"]["chave_unica"],
            "ip": requisicao_registro["payload"]["endereco_ip"],
            "porta": requisicao_registro["payload"]["porta"]
        }

        async with lock:
            listaDeClientes.append(novo_cliente)
            if len(listaDeClientes) == nunClinteMax:
                print("manda pacote finish")

        msgACK = mensagens.cria_ack_resposta_para_cliente(novo_cliente["chave"])
        writer.write(msgACK.encode('utf-8'))
        await writer.drain()

    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}")

async def main():
    await registro()
    servidor = await asyncio.start_server(servidorSuperNo, ipLocal, portaSuperno)
    print(f"Super nó escutando em {ipLocal}:{portaSuperno}")

    async with servidor:
        await servidor.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
