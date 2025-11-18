import json

# Comandos para comunicação do coordenador com o super nó 
CMD_COORD2SN_RESPOSTA_REGISTRO = "COORD2SN_RESPOSTA_REGISTRO"
CMD_COORD2SN_CONFIRMACAO_REGISTRO = "COORD2SN_CONFIRMACAO_REGISTRO"
CMD_COORD2SN_LISTA_SUPERNOS = "COORD2SN_LISTA_SUPERNOS"
CMD_COORD2SN_RESPOSTA_ESTOU_VIVO = "CMD_COORD2SN_RESPOSTA_ESTOU_VIVO"

# Comandos para comunicação do super nó com o coordenador 
CMD_SN2COORD_REQUISICAO_REGISTRO = "SN2COORD_REQUISICAO_REGISTRO"
CMD_SN2COORD_ACK_REGISTRO = "SN2COORD_ACK_REGISTRO"
CMD_SN2COORD_FINISH = "SN2COORD_FINISH"
CMD_SN2COORD_SAIDA = "SN2COORD_SAIDA"
CMD_SN2COORD_PERGUNTA_ESTOU_VIVO = "CMD_SN2COORD_PERGUNTA_ESTOU_VIVO"


#SUPERNO PARA CLIENTE
CMD_SN2CLIENTE_RESPOSTA_REGISTRO = "CMD_SN2CLIENTE_REQUISICAO_REGISTRO"
CMD_SN2CLIENTE_CONFIRMACAO_REGISTRO = "CMD_SN2CLIENTE_CONFIRMACAO_REGISTRO"
CMD_SN2CLIENTE_LISTA_CLIENTE = "CMD_SN2CLIENTE_LISTA_CLIENTE"
CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU = "CMD_SN2CLIENTE_RESPOSTA_BUSCA_ACHOU"
CMD_SN2CLIENTE_RESPOSTA_BUSCA_NAO_ACHOU = "CMD_SN2CLIENTE_RESPOSTA_BUSCA_NAO_ACHOU"
CMD_SN2CLIENTE_ACK_INDEXACAO = "SN2CLIENTE_ACK_INDEXACAO"

#CLIENTE PARA SUPERNO
CMD_CLIENTESN2_REQUISICAO_REGISTRO = "CMD_CLIENTESN2_REQUISICAO_REGISTRO_E_ENVIO_DE_CHAVE_UNICA"
CMD_CLIENTESN2_ACK_REGISTRO = "CMD_CLIENTESN2_ACK_REGISTRO"
CMD_CLIENTESN2_FINISH = "CMD_CLIENTESN2_FINISH"
CMD_CLIENTE2SN_BUSCA_ARQUIVO = "CLIENTE2SN_BUSCA_ARQUIVO"
CMD_CLIENTE2SN_INDEXAR_ARQUIVO = "CLIENTE2SN_INDEXAR_ARQUIVO"
CMD_CLIENTE2SN_SAIDA = "CLIENTE2SN_SAIDA"

# SUPER NO PARA SUPER NO
CMD_SN2SN_QUERY_ARQUIVO = "SN2SN_QUERY_ARQUIVO"
CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU = "SN2SN_RESPOSTA_ARQUIVO_ACHOU"
CMD_SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU = "SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU"
CMD_SN2SN_INICIAR_ELEICAO = "SN2SN_INICIAR_ELEICAO"
CMD_SN2SN_ELEICAO_INICIADO = "CMD_SN2SN_ELEICAO_INICIADO"
CMD_SN2SN_NOVO_COORDENADOR = "SN2SN_NOVO_COORDENADOR"


# <--- Padroniza a forma de troca de mensagem entre nós --->

def criar_mensagem(comando, **payload):
    mensagem = {
        "comando": comando,
        "payload": payload
    }

    return json.dumps(mensagem)

# Decodifica uma cadeia de bytes para JSON e devolve um dict
def decodifica_mensagem(dados_em_bytes):

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
    #Devolve ao super nó uma chave única 
    return criar_mensagem(CMD_COORD2SN_RESPOSTA_REGISTRO, status=status, chave_unica=chave_unica)

def cria_confirmacao_registro():
    # Broadcast para todos os super nós indicando que todos foram registrados 
    return criar_mensagem(CMD_COORD2SN_CONFIRMACAO_REGISTRO, mensagem="Todos os supernós foram registrados com sucesso.")

def cria_broadcast_lista_supernos(supernos_ativos):
    return criar_mensagem(CMD_COORD2SN_LISTA_SUPERNOS, supernos=supernos_ativos)

def cria_resposta_estou_vivo():
    return criar_mensagem(CMD_COORD2SN_RESPOSTA_ESTOU_VIVO, mensagem = "Tô vivasso jão")


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

def cria_resposta_arquivo_sn(comando, nome_arquivo, chave_identificadora, info_dono):
    return criar_mensagem(comando, nome_arquivo=nome_arquivo, chave_identificadora=chave_identificadora, info_dono=info_dono)

def cria_resposta_local_arquivo(comando, nome_arquivo, info_dono):
    return criar_mensagem(comando, nome_arquivo=nome_arquivo, info_dono=info_dono)

def cria_mensagem_eleicao(minha_chave):
    return criar_mensagem(CMD_SN2SN_INICIAR_ELEICAO, chave_remetente=minha_chave)

def cria_mensagem_resposta_eleicao():
    return criar_mensagem(CMD_SN2SN_ELEICAO_INICIADO, mensagem = "eleição foi iniciado, pode desistir")

def cria_mensagem_vitoria(ip, porta):
    return criar_mensagem(CMD_SN2SN_NOVO_COORDENADOR, ip=ip, porta=porta)

def cria_mensagem_alive():
    return criar_mensagem(CMD_SN2COORD_PERGUNTA_ESTOU_VIVO, mensagem ="Iae, tu ta vivo??")

def cria_ack_indexacao_arquivo(nome_arquivo, status):
    return criar_mensagem(CMD_SN2CLIENTE_ACK_INDEXACAO, nome_arquivo=nome_arquivo, status=status)

def cria_mensagem_saida_superno(chave_superno):
    return criar_mensagem(CMD_SN2COORD_SAIDA, chave_superno=chave_superno)

# <--- Funções do cliente --->

def cria_requisicao_registro_cliente(ip, porta, chave_unica):
    return criar_mensagem(CMD_CLIENTESN2_REQUISICAO_REGISTRO, endereco_ip = ip, porta=porta, chave_unica = chave_unica)

def cria_requisicao_busca_cliente(nome_arquivo):
    return criar_mensagem(CMD_CLIENTE2SN_BUSCA_ARQUIVO, nome_arquivo=nome_arquivo)

def cria_requisicao_indexar_arquivo(nome_arquivo):
    return criar_mensagem(CMD_CLIENTE2SN_INDEXAR_ARQUIVO, nome_arquivo=nome_arquivo)

def cria_mensagem_saida_cliente(chave_cliente):
    return criar_mensagem(CMD_CLIENTE2SN_SAIDA, chave_cliente=chave_cliente)
