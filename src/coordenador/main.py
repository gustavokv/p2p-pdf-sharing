import asyncio
import uuid
from src.shared import mensagens

HOST = "127.0.0.1"
PORTA = 8000

QUANT_SUPERNOS = 1
supernos = []

# Evento para sinalizar quando os nós estão prontos
lock_supernos = asyncio.Lock()

async def superno_handler(reader, writer):
    """ 
    Função assíncrona que irá gerenciar o supernó conectado
    reader e writer são objetos de stream para a comunicação não bloqueante
    """
    is_registrado = False
    addr = writer.get_extra_info('peername')
    print(f"Supernó {addr} conectado.")

    try:
        # Espera pela solicitação de registro no coordenador
        dados = await reader.read(4096)
        requisicao_registro = mensagens.decodifica_mensagem(dados)

        if not requisicao_registro or requisicao_registro.get("comando") != mensagens.CMD_SN2COORD_REQUISICAO_REGISTRO:
            print(f"Mensagem de registro inválida de {addr}.")
            return

        # Gera a chave única e devolve para o super nó
        chave_unica = uuid.uuid4().hex
        print(f"Registrando supernó {addr} com a chave única: {chave_unica}.")

        msg_resposta = mensagens.cria_resposta_coordenador("SUCESSO", chave_unica)
        writer.write(msg_resposta.encode('utf-8'))
        await writer.drain()
        
        # Aguarda ACK do super nó
        dados = await reader.read(4096)
        msg_ack = mensagens.decodifica_mensagem(dados)

        if not msg_ack or msg_ack.get("comando") != mensagens.CMD_SN2COORD_ACK_REGISTRO:
            print(f"ACK inválido de {addr}.")
            return

        if msg_ack.get("payload", {}).get("chave_unica") != chave_unica:
            print(f"Chave no ACK de {addr} está diferente.")
            return

        print(f"ACK recebido com sucesso de {addr}")

        async with lock_supernos:
            novo_superno = {
                "writer": writer,
                "addr": addr,
                "chave": chave_unica,
                "ip": requisicao_registro["payload"]["endereco_ip"],
                "porta": requisicao_registro["payload"]["porta"]
            } 

            supernos.append(novo_superno)
            is_registrado = True
            print(f"Novo super nó registrado. Total de super nós registrados: {len(supernos)}.")

            if len(supernos) == QUANT_SUPERNOS:
                # create_task para executar o broadcast e não bloquear esta função
                asyncio.create_task(broadcast_registros_concluidos())

        while True:
            dados = await reader.read(4096)
            if not dados:
                print(f"Super nó {addr} se deconectou")
                break

    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}")
    finally:
        async with lock_supernos:
            if is_registrado:
                supernos[:] = [sn for sn in supernos if sn["addr"] != addr]
                print(f"Super nó {addr} removido da lista")

        writer.close()
        await writer.wait_closed()

async def broadcast_registros_concluidos():
    """
    Realiza o broadcast para todos os super nós da rede após todos serem registrados
    """

    print("Todos os super nós foram registrados. Preparando para realizar o broadcast...")
    msg_broadcast = mensagens.criar_confirmacao_registro()

    async with lock_supernos:
        tasks = [] # Lista de tarefas para enviar a mensagem a todos os super nós
        for sn in supernos:
            sn["writer"].write(msg_broadcast.encode('utf-8'))
            tasks.append(sn["writer"].drain())
            print(f"Mensagem de broadcast adicionada para {sn["addr"]}")

        # Executa todas as tarefas de envio aos super nós concorrentemente
        await asyncio.gather(*tasks)
    print("Broadcast aos super nós concluído.")

async def main():
    print("Nó COORDENADOR está sendo iniciado...")
    servidor = await asyncio.start_server(superno_handler, HOST, PORTA)
    addr = servidor.sockets[0].getsockname()
    print(f"Coordenador escutando em: {addr[0]}:{addr[1]}")

    async with servidor:
        await servidor.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Coordenador encerrado pelo usuário.")