import asyncio
import json
import uuid
from src.shared import mensagens

HOST = "127.0.0.1"
PORTA = 8000

TOTAL_SUPERNOS = 2
supernos = []

# Evento para sinalizar quando os nós estão prontos
lock_supernos = asyncio.Lock()

#def handle_requisicoes_superno(msg):

async def broadcast_lista_supernos():
    """
    Função para realizar o broadcast da lista de super nós
    ativos aos super nós.
    """
    async with lock_supernos:
        if not supernos:
            return
        
        print(f'Lista dos supernós ativos atualizada contendo {len(supernos)} super nós ativos.')
        print('Preparando para realizar o broadcast...')

        supernos_para_enviar = [
            {
                "addr": sn["addr"],
                "chave": sn["chave"],
                "ip": sn["ip"],
                "porta": sn["porta"]
            } for sn in supernos
        ]

        msg_broadcast = mensagens.cria_broadcast_lista_supernos(supernos_para_enviar)

        tasks = []
        for sn in supernos:
            try:
                sn["writer"].write(msg_broadcast.encode('utf-8'))
                tasks.append(sn["writer"].drain())
            except Exception as e:
                print(f"Falha ao adicionar mensagem na fila para {sn["addr"]}: {e}")

        if tasks:
            await asyncio.gather(*tasks)
            print("Broadcast da lista de super nós realizada com sucesso.")

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

            if len(supernos) == TOTAL_SUPERNOS:
                # create_task para executar o broadcast e não bloquear esta função
                asyncio.create_task(broadcast_lista_supernos())
                asyncio.create_task(broadcast_registros_concluidos())

        while True:
            dados = await reader.read(4096)

            if not dados:
                print(f"Super nó {addr} se desconectou.")
                break

            msg_recebida = mensagens.decodifica_mensagem(dados)

            if msg_recebida and msg_recebida.get("comando") == mensagens.CMD_SN2COORD_FINISH:
                print(f"Super nó {addr} finalizou o registro dos clientes: {msg_recebida.get("mensagem")}.")
                return
            else:
                print("IMPLEMENTAR")
                # Recebe demais requisições do super nó
                #handle_requisicoes_superno(msg_recebida)

    except (ConnectionResetError, asyncio.IncompleteReadError) as error:
        print(f"Conexão com {addr} perdida. Erro: {error}")
    except Exception as error:
        print(f"Erro inesperado com {addr}. Erro: {error}")
    finally:
        async with lock_supernos:
            if is_registrado:
                supernos[:] = [sn for sn in supernos if sn["addr"] != addr]
                print(f"Super nó {addr} removido da lista")

            asyncio.create_task(broadcast_lista_supernos())

        writer.close()
        await writer.wait_closed()

async def broadcast_registros_concluidos():
    """
    Realiza o broadcast para todos os super nós da rede após todos serem registrados
    """

    print("Todos os super nós foram registrados. Preparando para realizar o broadcast...")
    msg_broadcast = mensagens.cria_confirmacao_registro()

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