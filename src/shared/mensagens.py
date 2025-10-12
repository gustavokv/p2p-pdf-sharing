import json

""" Comandos para comunicação do coordenador com o super nó """
CMD_SN2COORD_REQUISICAO_REGISTRO = "SN2COORD_REQUISICAO_REGISTRO"
CMD_COORD2SN_RESPOSTA_REGISTRO = "COORD2SN_RESPOSTA_REGISTRO"
CMD_SN2COORD_ACK_REGISTRO = "SN2COORD_ACK_REGISTRO"
CMD_COORD2SN_CONFIRMACAO_REGISTRO = "COORD2SN_CONFIRMACAO_REGISTRO"
CMD_COORD2SN_LISTA_SUPERNOS = "COORD2SN_LISTA_SUPERNOS"

# <--- Padroniza a forma de troca de mensagem entre nós --->

def criar_mensagem(comando, **payload):
    mensagem = {
        "comando": comando,
        "payload": payload
    }

    return json.dumps(mensagem)

def decodifica_mensagem(dados_em_bytes):
    """
    Decodifica uma cadeia de bytes para JSON e devolve um dict
    """

    if not dados_em_bytes:
        return None
    
    try:
        dados_json = dados_em_bytes.decode('utf-8')
        return json.loads(dados_json)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"[ERROR] Erro ao DECODIFICAR mensagem: {error}")
        return None

# <--- Funções do Coordenador --->

def cria_resposta_coordenador(status, chave_unica):
    """ Devolve ao super nó uma chave única """
    return criar_mensagem(CMD_COORD2SN_RESPOSTA_REGISTRO, status=status, chave_unica=chave_unica)

def criar_confirmacao_registro():
    """ Broadcast para todos os super nós indicando que todos foram registrados """
    return criar_mensagem(CMD_COORD2SN_CONFIRMACAO_REGISTRO, mensagem="Todos os supernós foram registrados com sucesso.")


# <--- Funções do Super nó --->

def cria_requisicao_registro_superno(ip, porta=8000):
    return criar_mensagem(CMD_SN2COORD_REQUISICAO_REGISTRO, endereco_ip=ip, porta=porta)