#!/bin/bash

# ==========================================================
# SCRIPT DE DEPLOY PARA REDE P2P LOCAL (17 NÓS EM 1 MÁQUINA)
# (Com monitoramento em 17 terminais)
# ==========================================================
#
# Pré-requisitos:
# 1. O projeto (com o 'iniciar-no.sh') deve estar no
#    caminho definido em PROJECT_PATH.
# 2. 'gnome-terminal' (ou 'konsole', etc.) deve estar instalado.
#
# ==========================================================

clear

# --- CONFIGURAÇÃO DA REDE (AGORA LOCAL) ---

# Caminho absoluto para a pasta do projeto
PROJECT_PATH="CAMINHO_PROJETO"

# Terminal a ser usado para abrir novas janelas
TERMINAL_CMD="gnome-terminal"

# --- MAPA DA REDE (TUDO LOCAL) ---
IP_COORD="127.0.0.1" # IP desta máquina (Coordenador)

# Supernós (Hostnames e Portas)
IP_SN1="127.0.0.1"; PORT_SN1="8001"
IP_SN2="127.0.0.1"; PORT_SN2="8002"
IP_SN3="127.0.0.1"; PORT_SN3="8003"
IP_SN4="127.0.0.1"; PORT_SN4="8004"

BASE_PEER_PORT=9000


# --- INÍCIO DA EXECUÇÃO ---
echo "AVISO: Este script irá iniciar 17 processos, TODOS LOCALMENTE."
echo "9 novas janelas de terminal serão abertas para monitorar todos os nós."
read -p "Pressione [Enter] para continuar ou [Ctrl+C] para cancelar..."

# 1. Iniciar o Coordenador (Localmente, em novo terminal)
echo -e "\n[FASE 1/3] Iniciando Coordenador localmente em $IP_COORD:8000 (monitorado)..."
CMD_COORD="bash -c \"
    echo '--- INICIANDO COORDENADOR LOCAL ($IP_COORD:8000) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    ./iniciar-no.sh coordenador;
    echo;
    echo '--- PROCESSO DO COORDENADOR FINALIZADO. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_COORD" &
echo "Comando do Coordenador enviado. Aguardando 3 segundos para iniciar..."
sleep 3

# 2. Iniciar os Supernós (Localmente, em terminais locais)
echo -e "\n[FASE 2/3] Iniciando 2 Supernós localmente (monitorados)..."

# --- Supernó 1 ---
echo "  -> Abrindo terminal local para Supernó 1 ($IP_SN1:$PORT_SN1)..."
CMD_LOCAL_SN1="./iniciar-no.sh superno $IP_SN1 $PORT_SN1 $IP_COORD"
CMD_SN1="bash -c \"
    echo '--- INICIANDO SUPERNÓ 1 LOCAL ($IP_SN1:$PORT_SN1) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    echo --- INICIANDO SCRIPT: $CMD_LOCAL_SN1 ---;
    $CMD_LOCAL_SN1;
    echo;
    echo '--- SESSÃO (SUPERNÓ 1) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN1" &
sleep 1 # Pausa para o terminal abrir

# --- Supernó 2 ---
echo "  -> Abrindo terminal local para Supernó 2 ($IP_SN2:$PORT_SN2)..."
CMD_LOCAL_SN2="./iniciar-no.sh superno $IP_SN2 $PORT_SN2 $IP_COORD"
CMD_SN2="bash -c \"
    echo '--- INICIANDO SUPERNÓ 2 LOCAL ($IP_SN2:$PORT_SN2) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    echo --- INICIANDO SCRIPT: $CMD_LOCAL_SN2 ---;
    $CMD_LOCAL_SN2;
    echo;
    echo '--- SESSÃO (SUPERNÓ 2) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN2" &

# --- Supernó 3 ---
echo "  -> Abrindo terminal local para Supernó 3 ($IP_SN3:$PORT_SN3)..."
CMD_LOCAL_SN3="./iniciar-no.sh superno $IP_SN3 $PORT_SN3 $IP_COORD"
CMD_SN3="bash -c \"
    echo '--- INICIANDO SUPERNÓ 3 LOCAL ($IP_SN3:$PORT_SN3) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    echo --- INICIANDO SCRIPT: $CMD_LOCAL_SN3 ---;
    $CMD_LOCAL_SN3;
    echo;
    echo '--- SESSÃO (SUPERNÓ 3) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN3" &
sleep 1 # Pausa para o terminal abrir

# --- Supernó 4 ---
echo "  -> Abrindo terminal local para Supernó 4 ($IP_SN4:$PORT_SN4)..."
CMD_LOCAL_SN4="./iniciar-no.sh superno $IP_SN4 $PORT_SN4 $IP_COORD"
CMD_SN4="bash -c \"
    echo '--- INICIANDO SUPERNÓ 4 LOCAL ($IP_SN4:$PORT_SN4) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    echo --- INICIANDO SCRIPT: $CMD_LOCAL_SN4 ---;
    $CMD_LOCAL_SN4;
    echo;
    echo '--- SESSÃO (SUPERNÓ 4) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN4" &
sleep 1 # Pausa para o terminal abrir

echo "Comandos dos supernós enviados. Aguardando 5 segundos para se registrarem..."
sleep 5

# 3. Iniciar os Clientes (Localmente, em terminais locais)
echo -e "\n[FASE 3/3] Iniciando 6 Clientes localmente (monitorados)..."

echo "  Iniciando 3 clientes para o Supernó 1 ($IP_SN1:$PORT_SN1)..."
for i in {1..3}; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # (9001, 9002, 9003)
    echo "  -> Abrindo terminal local para Cliente $i (SN1) (Porta P2P: $CLIENT_PEER_PORT)..."
    # O IP "desta máquina" do cliente pode ser 127.0.0.1
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente 127.0.0.1 $IP_SN1 $PORT_SN1"
    
    CMD_TO_RUN="bash -c \"
        echo '--- INICIANDO CLIENTE $i (P2P: $CLIENT_PEER_PORT) (para SUPERNÓ $IP_SN1:$PORT_SN1) ---';
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
        $CMD_LOCAL_CLIENTE;
        echo;
        echo '--- SESSÃO (CLIENTE $i) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    sleep 1 # Pequena pausa para os terminais abrirem
done

echo "  Iniciando 3 clientes para o Supernó 2 ($IP_SN2:$PORT_SN2)..."
for i in {1..3}; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + 3 + i" # (9004, 9005, 9006)
    echo "  -> Abrindo terminal local para Cliente $i (SN2) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente 127.0.0.1 $IP_SN2 $PORT_SN2"

    CMD_TO_RUN="bash -c \"
        echo '--- INICIANDO CLIENTE $i (P2P: $CLIENT_PEER_PORT) (para SUPERNÓ $IP_SN2:$PORT_SN2) ---';
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
        $CMD_LOCAL_CLIENTE;
        echo;
        echo '--- SESSÃO (CLIENTE $i) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    sleep 1
done

echo "  Iniciando 3 clientes para o Supernó 3 ($IP_SN3:$PORT_SN3)..."
for i in {1..3}; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + 6 + i" # (9004, 9005, 9006)
    echo "  -> Abrindo terminal local para Cliente $i (SN3) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente 127.0.0.1 $IP_SN3 $PORT_SN3"

    CMD_TO_RUN="bash -c \"
        echo '--- INICIANDO CLIENTE $i (P2P: $CLIENT_PEER_PORT) (para SUPERNÓ $IP_SN3:$PORT_SN3) ---';
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
        $CMD_LOCAL_CLIENTE;
        echo;
        echo '--- SESSÃO (CLIENTE $i) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    sleep 1
done

echo "  Iniciando 3 clientes para o Supernó 4 ($IP_SN4:$PORT_SN4)..."
for i in {1..3}; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + 9 + i" # (9004, 9005, 9006)
    echo "  -> Abrindo terminal local para Cliente $i (SN4) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente 127.0.0.1 $IP_SN4 $PORT_SN4"

    CMD_TO_RUN="bash -c \"
        echo '--- INICIANDO CLIENTE $i (P2P: $CLIENT_PEER_PORT) (para SUPERNÓ $IP_SN4:$PORT_SN4) ---';
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
        $CMD_LOCAL_CLIENTE;
        echo;
        echo '--- SESSÃO (CLIENTE $i) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    sleep 1
done

echo -e "\n============================================="
echo "DEPLOY LOCAL CONCLUÍDO!"
echo "Todos os 17 nós receberam o comando de início."
echo "17 terminais devem estar abertos monitorando os nós."
echo "============================================="