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

reader = None
writer = None

chave_identificadora = None

async def registro():
    global porta #REMOVER NO LAB
    global chave_identificadora
    global reader
    global writer
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


async def enviar_arquivo_possuido(nome_arquivo):
    """Envia ao supernó o nome de um arquivo que este cliente possui."""

    if chave_identificadora is None:
        print("Registre-se primeiro antes de anunciar arquivos.")
        return

    msg = mensagens.cria_requisicao_indexar_arquivo(nome_arquivo)
    writer.write(msg.encode('utf-8'))
    await writer.drain()

    dados = await reader.read(4096)
    resposta = mensagens.decodifica_mensagem(dados)
    print(f"[Supernó]: {resposta}")



async def buscar_arquivo(nome_arquivo):
    """Solicita ao supernó onde encontrar um arquivo específico."""

    msg = mensagens.cria_requisicao_busca_cliente(nome_arquivo)
    writer.write(msg.encode('utf-8'))
    await writer.drain()

    dados = await reader.read(4096)
    resposta = mensagens.decodifica_mensagem(dados)
    print(f"[Supernó]: {resposta}")



async def menu():

    await registro()

    """Menu interativo do cliente."""
    while True:
        print("\n=== MENU CLIENTE P2P ===")
        print("1 - Enviar arquivo que possuo")
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
            break
        else:
            print("❌ Opção inválida.")



if __name__ == "__main__":
    asyncio.run(menu())