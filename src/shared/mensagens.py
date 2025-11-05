import json

""" Comandos para comunicação do coordenador com o super nó """
CMD_COORD2SN_RESPOSTA_REGISTRO = "COORD2SN_RESPOSTA_REGISTRO"
CMD_COORD2SN_CONFIRMACAO_REGISTRO = "COORD2SN_CONFIRMACAO_REGISTRO"
CMD_COORD2SN_LISTA_SUPERNOS = "COORD2SN_LISTA_SUPERNOS"

""" Comandos para comunicação do super nó com o coordenador """
CMD_SN2COORD_REQUISICAO_REGISTRO = "SN2COORD_REQUISICAO_REGISTRO"
CMD_SN2COORD_ACK_REGISTRO = "SN2COORD_ACK_REGISTRO"
CMD_SN2COORD_FINISH = "SN2COORD_FINISH"

#SUPERNO PARA CLIENTE
CMD_SN2CLIENTE_RESPOSTA_REGISTRO = "CMD_SN2CLIENTE_REQUISICAO_REGISTRO"
CMD_SN2CLIENTE_CONFIRMACAO_REGISTRO = "CMD_SN2CLIENTE_CONFIRMACAO_REGISTRO"
CMD_SN2CLIENTE_LISTA_CLIENTE = "CMD_SN2CLIENTE_LISTA_CLIENTE"
CMD_CLIENTE2SN_BUSCA_ARQUIVO = "CLIENTE2SN_BUSCA_ARQUIVO"

#CLIENTE PARA SUPERNO
CMD_CLIENTESN2_REQUISICAO_REGISTRO = "CMD_CLIENTESN2_REQUISICAO_REGISTRO_E_ENVIO_DE_CHAVE_UNICA"
CMD_CLIENTESN2_ACK_REGISTRO = "CMD_CLIENTESN2_ACK_REGISTRO"
CMD_CLIENTESN2_FINISH = "CMD_CLIENTESN2_FINISH"
CMD_SN2SN_QUERY_ARQUIVO = "SN2SN_QUERY_ARQUIVO"
CMD_SN2SN_RESPOSTA_ARQUIVO = "SN2SN_RESPOSTA_ARQUIVO"
CMD_SN2CLIENTE_RESPOSTA_BUSCA = "SN2CLIENTE_RESPOSTA_BUSCA"


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

def cria_confirmacao_registro():
    """ Broadcast para todos os super nós indicando que todos foram registrados """
    return criar_mensagem(CMD_COORD2SN_CONFIRMACAO_REGISTRO, mensagem="Todos os supernós foram registrados com sucesso.")

def cria_broadcast_lista_supernos(supernos_ativos):
    return criar_mensagem(CMD_COORD2SN_LISTA_SUPERNOS, supernos=supernos_ativos)


# <--- Funções do Super nó --->

def cria_requisicao_registro_superno(ip, porta=8000):
    return criar_mensagem(CMD_SN2COORD_REQUISICAO_REGISTRO, endereco_ip=ip, porta=porta)

def cria_ack_resposta_para_coord(chave_unica):
    return criar_mensagem(CMD_SN2COORD_ACK_REGISTRO, chave_unica=chave_unica)

def cria_pacote_finish():
    return criar_mensagem(CMD_SN2COORD_FINISH, mensagem="Super nó finalizou o registro dos clientes.")

def cria_ack_resposta_para_cliente(chave_unica):
    return criar_mensagem(CMD_SN2CLIENTE_RESPOSTA_REGISTRO, chave_unica = chave_unica)

def cria_query_arquivo_sn(nome_arquivo, chave_identificadora):
    return criar_mensagem(CMD_SN2SN_QUERY_ARQUIVO, nome_arquivo=nome_arquivo, chave_identificadora=chave_identificadora)

def cria_resposta_arquivo_sn(nome_arquivo, chave_identificadora, info_dono):
    return criar_mensagem(CMD_SN2SN_RESPOSTA_ARQUIVO, nome_arquivo=nome_arquivo, chave_identificadora=chave_identificadora, info_dono=info_dono)

def cria_resposta_local_arquivo(nome_arquivo, info_dono):
    return criar_mensagem(CMD_SN2CLIENTE_RESPOSTA_BUSCA, nome_arquivo=nome_arquivo, info_dono=info_dono)

# <--- Funções do cliente --->

def cria_requisicao_registro_cliente(ip, porta, chave_unica):
    return criar_mensagem(CMD_CLIENTESN2_REQUISICAO_REGISTRO, endereco_ip = ip, porta=porta, chave_unica = chave_unica)

def cria_requisicao_busca_cliente(nome_arquivo):
    return criar_mensagem(CMD_CLIENTE2SN_BUSCA_ARQUIVO, nome_arquivo=nome_arquivo)
