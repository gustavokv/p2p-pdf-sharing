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
CMD_SN2CLIENTE_PEDIDO_VOTACAO = "SN2CLIENTE_PEDIDO_VOTACAO"
CMD_SN2CLIENTE_GLOBAL_COMMIT = "SN2CLIENTE_GLOBAL_COMMIT"
CMD_SN2CLIENTE_GLOBAL_ABORT = "SN2CLIENTE_GLOBAL_ABORT"
CMD_SN_REPLICA_INDICE = "SN_REPLICA_INDICE" # Para enviar a um novo SN
CMD_SN2CLIENTE_PROMOCAO = "SN2CLIENTE_PROMOCAO"

#CLIENTE PARA SUPERNO
CMD_CLIENTESN2_REQUISICAO_REGISTRO = "CMD_CLIENTESN2_REQUISICAO_REGISTRO_E_ENVIO_DE_CHAVE_UNICA"
CMD_CLIENTESN2_ACK_REGISTRO = "CMD_CLIENTESN2_ACK_REGISTRO"
CMD_CLIENTESN2_FINISH = "CMD_CLIENTESN2_FINISH"
CMD_CLIENTE2SN_BUSCA_ARQUIVO = "CLIENTE2SN_BUSCA_ARQUIVO"
CMD_CLIENTE2SN_INDEXAR_ARQUIVO = "CLIENTE2SN_INDEXAR_ARQUIVO"
CMD_CLIENTE2SN_SAIDA = "CLIENTE2SN_SAIDA"
CMD_CLIENTE2SN_VOTO_SIM = "CLIENTE2SN_VOTO_SIM"
CMD_CLIENTE2SN_VOTO_NAO = "CLIENTE2SN_VOTO_NAO"

# SUPER NO PARA SUPER NO
CMD_SN2SN_QUERY_ARQUIVO = "SN2SN_QUERY_ARQUIVO"
CMD_SN2SN_RESPOSTA_ARQUIVO_ACHOU = "SN2SN_RESPOSTA_ARQUIVO_ACHOU"
CMD_SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU = "SN2SN_RESPOSTA_ARQUIVO_NAO_ACHOU"
CMD_SN2SN_INICIAR_ELEICAO = "SN2SN_INICIAR_ELEICAO"
CMD_SN2SN_NOVO_COORDENADOR = "SN2SN_NOVO_COORDENADOR"

# Cliente para cliente
CMD_PEER2PEER_REQUISICAO_DOWNLOAD = "P2P_REQUISICAO_DOWNLOAD"


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

def cria_mensagem_alive():
    return criar_mensagem(CMD_SN2COORD_PERGUNTA_ESTOU_VIVO, mensagem ="Iae, tu ta vivo??")

def cria_mensagem_coordenador(minha_chave):
    return criar_mensagem(CMD_SN2SN_NOVO_COORDENADOR, chave_lider=minha_chave)

def cria_ack_indexacao_arquivo(nome_arquivo, status):
    return criar_mensagem(CMD_SN2CLIENTE_ACK_INDEXACAO, nome_arquivo=nome_arquivo, status=status)

def cria_mensagem_saida_superno(chave_superno):
    return criar_mensagem(CMD_SN2COORD_SAIDA, chave_superno=chave_superno)

def cria_pedido_votacao(tid, indice_para_replicar, soma_mestre):
    return criar_mensagem(CMD_SN2CLIENTE_PEDIDO_VOTACAO, 
                          tid=tid, 
                          indice=indice_para_replicar, 
                          soma=soma_mestre)

def cria_msg_global_commit(tid):
    return criar_mensagem(CMD_SN2CLIENTE_GLOBAL_COMMIT, tid=tid)

def cria_msg_global_abort(tid):
    return criar_mensagem(CMD_SN2CLIENTE_GLOBAL_ABORT, tid=tid)

def cria_msg_replica_indice(indice):
    return criar_mensagem(CMD_SN_REPLICA_INDICE, indice=indice)

# <--- Funções do cliente --->

def cria_requisicao_registro_cliente(ip, porta, chave_unica):
    return criar_mensagem(CMD_CLIENTESN2_REQUISICAO_REGISTRO, endereco_ip = ip, porta=porta, chave_unica = chave_unica)

def cria_requisicao_busca_cliente(nome_arquivo):
    return criar_mensagem(CMD_CLIENTE2SN_BUSCA_ARQUIVO, nome_arquivo=nome_arquivo)

def cria_requisicao_indexar_arquivo(nome_arquivo, tamanho_arquivo):
    return criar_mensagem(CMD_CLIENTE2SN_INDEXAR_ARQUIVO, nome_arquivo=nome_arquivo,tamanho_arquivo=tamanho_arquivo)

def cria_mensagem_saida_cliente(chave_cliente):
    return criar_mensagem(CMD_CLIENTE2SN_SAIDA, chave_cliente=chave_cliente)

def cria_requisicao_download_peer(nome_arquivo):
    return criar_mensagem(CMD_PEER2PEER_REQUISICAO_DOWNLOAD, nome_arquivo=nome_arquivo)

def cria_voto_sim(tid):
    return criar_mensagem(CMD_CLIENTE2SN_VOTO_SIM, tid=tid)

def cria_voto_nao(tid):
    return criar_mensagem(CMD_CLIENTE2SN_VOTO_NAO, tid=tid)
