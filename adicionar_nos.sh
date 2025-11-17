#!/bin/bash

# ==========================================================
# SCRIPT PARA ADICIONAR NÓS EXTRAS À REDE
# (Executar enquanto o deploy já estiver rodando)
# ==========================================================

clear

SSH_USER="rgm47006"
PROJECT_PATH="/home/AD/rgm47006/Documentos/p2p-pdf-sharing"
TERMINAL_CMD="gnome-terminal"
IP_COORD="l4m03u.lab4"
BASE_PEER_PORT=9000

# --- Contador de porta P2P ---
i=13 

# --- NÓS A ADICIONAR ---
IP_SN5="l1m09u.lab1"
PORT_SN5="8005"

IP_CLIENTE_A="l1m09u.lab1"
IP_CLIENTE_B="l1m09u.lab1"
IP_CLIENTE_C="l1m09u.lab1"

echo "--- ADICIONANDO NOVOS NÓS À REDE EXISTENTE ---"

# 1. Iniciar o Novo Supernó (SN5)
echo "-> Lançando Supernó 5 ($IP_SN5:$PORT_SN5) via SSH..."

CMD_REMOTO_SN5="./iniciar-no.sh superno $IP_SN5 $PORT_SN5 $IP_COORD"
CMD_SN5_RUN="bash -c \"
    echo '--- CONECTANDO AO SUPERNÓ 5 ($IP_SN5) ---';
    ssh $SSH_USER@$IP_SN5 '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_REMOTO_SN5 ---;
        $CMD_REMOTO_SN5;
    ';
    echo;
    echo '--- SESSÃO SSH (SUPERNÓ 5) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN5_RUN" &

echo "Aguardando 20 segundos para o Supernó 5 se registrar e iniciar..."
sleep 20

# 2. Iniciar Cliente Estático A (Conectado ao SN5)
let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # Porta 9013
echo "-> Lançando Cliente Estático A ($IP_CLIENTE_A) (P2P: $CLIENT_PEER_PORT) -> (SN5)..."
CMD_CLIENTE_A="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $IP_CLIENTE_A $IP_SN5 $PORT_SN5"

CMD_CLIENTE_A_RUN="bash -c \"
    echo '--- CONECTANDO AO CLIENTE A (IP: $IP_CLIENTE_A) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN5 ---';
    ssh $SSH_USER@$IP_CLIENTE_A '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_CLIENTE_A ---;
        $CMD_CLIENTE_A;
    ';
    echo;
    echo '--- SESSÃO SSH (CLIENTE A) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_CLIENTE_A_RUN" &
let "i=i+1" # i agora é 14
sleep 10

# 3. Iniciar Cliente Estático B (Conectado ao SN5)
let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # Porta 9014
echo "-> Lançando Cliente Estático B ($IP_CLIENTE_B) (P2P: $CLIENT_PEER_PORT) -> (SN5)..."
CMD_CLIENTE_B="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $IP_CLIENTE_B $IP_SN5 $PORT_SN5"

CMD_CLIENTE_B_RUN="bash -c \"
    echo '--- CONECTANDO AO CLIENTE B (IP: $IP_CLIENTE_B) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN5 ---';
    ssh $SSH_USER@$IP_CLIENTE_B '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_CLIENTE_B ---;
        $CMD_CLIENTE_B;
    ';
    echo;
    echo '--- SESSÃO SSH (CLIENTE B) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_CLIENTE_B_RUN" &
let "i=i+1" # i agora é 15
sleep 10

# 4. Iniciar um Cliente em modo DINÂMICO
let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # Porta 9015
echo "-> Lançando Cliente Dinâmico C ($IP_CLIENTE_C) (P2P: $CLIENT_PEER_PORT)..."
# Args Dinâmico: cliente <IP_CLIENTE> <IP_COORDENADOR>
CMD_CLIENTE_C="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $IP_CLIENTE_C $IP_COORD"

CMD_CLIENTE_C_RUN="bash -c \"
    echo '--- CONECTANDO AO CLIENTE C (IP: $IP_CLIENTE_C) (P2P: $CLIENT_PEER_PORT) (DINÂMICO) ---';
    ssh $SSH_USER@$IP_CLIENTE_C '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_CLIENTE_C ---;
        $CMD_CLIENTE_C;
    ';
    echo;
    echo '--- SESSÃO SSH (CLIENTE C) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_CLIENTE_C_RUN" &
let "i=i+1" # i agora é 16

echo "Concluído! Verifique as novas 4 janelas."