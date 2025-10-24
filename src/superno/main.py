import asyncio
from src.shared import mensagens

ipServidor = "127.0.0.1"
ipLocal = "127.0.0.1"
porta = 8000
chave = None

async def registro():
    reader, writer = await asyncio.open_connection(ipServidor, porta)
    print(f"Conectado ao coordenador em {ipServidor}:{porta}")

    # Envia solicitação de registro
    msg_registro = mensagens.cria_requisicao_registro_superno(ipLocal, porta)
    writer.write(msg_registro.encode('utf-8'))
    await writer.drain()
    print("Solicitação de registro enviada ao coordenador.")

    # Aguarda resposta com a chave única
    dados = await reader.read(4096)
    resposta = mensagens.decodifica_mensagem(dados)
    chave = resposta.get("payload", {}).get("chave_unica")
    print(f"Chave recebida: {chave}")

    # Envia ACK de confirmação
    msg_ack = mensagens.cria_ack_resposta(chave)
    writer.write(msg_ack.encode('utf-8'))
    await writer.drain()
    print("ACK enviado ao coordenador.")

    # Aguarda mensagem final de confirmação de registro (broadcast)
    dados = await reader.read(4096)
    confirmacao = mensagens.decodifica_mensagem(dados)
    print(f"Mensagem do coordenador: {confirmacao}")

    # Mantém a conexão aberta (depende do protocolo)
    print("Registro finalizado. Conexão ativa.")
    # await asyncio.sleep(9999)  # se quiser manter vivo

    while True:
        n =1

async def main():
    await registro()

if __name__ == "__main__":
    asyncio.run(main())
