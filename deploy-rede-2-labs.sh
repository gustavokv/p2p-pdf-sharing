#!/bin/bash

# ==========================================================
# SCRIPT DE DEPLOY PARA REDE P2P DISTRIBUÍDA (17 NÓS EM 2 LABS)
# (Com monitoramento em 17 terminais)
# ==========================================================
#
# Pré-requisitos:
# 1. Este script deve ser rodado da MÁQUINA DO COORDENADOR.
# 2. Acesso SSH sem senha (via chave) deve estar configurado
#    da máquina coordenadora para TODAS as 16 máquinas remotas.
# 3. O projeto (com o 'iniciar-no.sh') deve estar no mesmo
#    caminho em TODAS as 17 máquinas.
# 4. 'gnome-terminal' (ou 'konsole', etc.) deve estar instalado
#    na máquina coordenadora.
#
# ==========================================================

clear

# --- CONFIGURAÇÃO DA REDE (PREENCHA AQUI) ---

# Usuário SSH para conectar às máquinas remotas
SSH_USER="rgm47006"

# Caminho absoluto para a pasta do projeto
PROJECT_PATH="/home/local/rgm47006/p2p-pdf-sharing"

# Terminal a ser usado para abrir novas janelas
TERMINAL_CMD="gnome-terminal"

# --- MAPA DA REDE ---
IP_COORD="l1m11u.lab1" # IP desta máquina (Coordenador)

# Supernós (Hostnames e Portas)
IP_SN1="l1m12u.lab1"; PORT_SN1="8001"
IP_SN2="l1m03u.lab1"; PORT_SN2="8002"
IP_SN3="l4m08u.lab4"; PORT_SN3="8003"
IP_SN4="l4m07u.lab4"; PORT_SN4="8004"

# Clientes (Hostnames)
CLIENTES_SN1=("l1m14u.lab1" "l1m06u.lab1" "l1m05u.lab1")
CLIENTES_SN2=("l1m04u.lab1" "l1m21u.lab1" "l1m20u.lab1")
CLIENTES_SN3=("l4m20u.lab4" "l4m06u.lab4" "l4m05u.lab4")
CLIENTES_SN4=("l4m24u.lab4" "l4m02u.lab4" "l4m04u.lab4")
# --- FIM DO MAPA ---


# --- INÍCIO DA EXECUÇÃO ---
echo "AVISO: Este script irá iniciar 17 processos."
echo "O Coordenador (local) e 16 processos remotos (via SSH)."
echo "17 novas janelas de terminal serão abertas para monitorar todos os nós."
echo "Pressupõe SSH sem senha para '$SSH_USER' em todas as 16 máquinas."
read -p "Pressione [Enter] para continuar ou [Ctrl+C] para cancelar..."

# 1. Iniciar o Coordenador (Localmente, em novo terminal)
echo -e "\n[FASE 1/3] Iniciando Coordenador localmente em $IP_COORD (monitorado)..."
CMD_COORD="bash -c \"
    echo '--- INICIANDO COORDENADOR LOCAL ($IP_COORD) ---';
    cd $PROJECT_PATH;
    chmod +x iniciar-no.sh;
    ./iniciar-no.sh coordenador;
    echo;
    echo '--- PROCESSO DO COORDENADOR FINALIZADO. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_COORD" &
echo "Comando do Coordenador enviado. Aguardando 5 segundos para iniciar..."
sleep 5

# 2. Iniciar os Supernós (Remotamente, em terminais locais)
echo -e "\n[FASE 2/3] Iniciando 4 Supernós remotamente (monitorados)..."

# --- Supernó 1 ---
echo "  -> Abrindo terminal SSH para Supernó 1 ($IP_SN1)..."
CMD_REMOTO_SN1="./iniciar-no.sh superno $IP_SN1 $PORT_SN1 $IP_COORD"
CMD_SN1="bash -c \"
    echo '--- CONECTANDO AO SUPERNÓ 1 ($IP_SN1) ---';
    ssh $SSH_USER@$IP_SN1 '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_REMOTO_SN1 ---;
        $CMD_REMOTO_SN1;
    ';
    echo;
    echo '--- SESSÃO SSH (SUPERNÓ 1) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN1" &
sleep 20 # Pausa para o terminal abrir

# --- Supernó 2 ---
echo "  -> Abrindo terminal SSH para Supernó 2 ($IP_SN2)..."
CMD_REMOTO_SN2="./iniciar-no.sh superno $IP_SN2 $PORT_SN2 $IP_COORD"
CMD_SN2="bash -c \"
    echo '--- CONECTANDO AO SUPERNÓ 2 ($IP_SN2) ---';
    ssh $SSH_USER@$IP_SN2 '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_REMOTO_SN2 ---;
        $CMD_REMOTO_SN2;
    ';
    echo;
    echo '--- SESSÃO SSH (SUPERNÓ 2) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN2" &
sleep 20

# --- Supernó 3 ---
echo "  -> Abrindo terminal SSH para Supernó 3 ($IP_SN3)..."
CMD_REMOTO_SN3="./iniciar-no.sh superno $IP_SN3 $PORT_SN3 $IP_COORD"
CMD_SN3="bash -c \"
    echo '--- CONECTANDO AO SUPERNÓ 3 ($IP_SN3) ---';
    ssh $SSH_USER@$IP_SN3 '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_REMOTO_SN3 ---;
        $CMD_REMOTO_SN3;
    ';
    echo;
    echo '--- SESSÃO SSH (SUPERNÓ 3) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN3" &
sleep 20

# --- Supernó 4 ---
echo "  -> Abrindo terminal SSH para Supernó 4 ($IP_SN4)..."
CMD_REMOTO_SN4="./iniciar-no.sh superno $IP_SN4 $PORT_SN4 $IP_COORD"
CMD_SN4="bash -c \"
    echo '--- CONECTANDO AO SUPERNÓ 4 ($IP_SN4) ---';
    ssh $SSH_USER@$IP_SN4 '
        echo --- CONEXÃO SSH ESTABELECIDA ---;
        cd $PROJECT_PATH;
        chmod +x iniciar-no.sh;
        echo --- INICIANDO SCRIPT: $CMD_REMOTO_SN4 ---;
        $CMD_REMOTO_SN4;
    ';
    echo;
    echo '--- SESSÃO SSH (SUPERNÓ 4) FINALIZADA. Pressione [Enter] para fechar. ---';
    read
\""
$TERMINAL_CMD -- bash -c "$CMD_SN4" &

echo "Comandos dos supernós enviados. Aguardando 10 segundos para se registrarem..."
sleep 20

# 3. Iniciar os Clientes (Remotamente, em terminais locais)
echo -e "\n[FASE 3/3] Iniciando 12 Clientes remotamente (monitorados)..."
i=1
BASE_PEER_PORT=9000

echo "  Iniciando clientes do Supernó 1 ($IP_SN1)..."
for ip in "${CLIENTES_SN1[@]}"; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # (9001, 9002, 9003)
    echo "  -> Abrindo terminal SSH para Cliente ($ip) (Porta P2P: $CLIENT_PEER_PORT)..."
    
    # Define o comando que será executado remotamente
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $ip $IP_SN1 $PORT_SN1"
    
    CMD_TO_RUN="bash -c \"
        echo '--- CONECTANDO AO CLIENTE (IP: $ip) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN1 ---';
        ssh $SSH_USER@$ip '
            echo --- CONEXÃO SSH ESTABELECIDA ---;
            cd $PROJECT_PATH;
            chmod +x iniciar-no.sh;
            
            echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
            $CMD_LOCAL_CLIENTE;
        ';
        echo;
        echo '--- SESSÃO SSH (CLIENTE $ip) (P2P: $CLIENT_PEER_PORT) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    let "i=i+1" 
    sleep 10 # Pequena pausa para os terminais abrirem
done

echo "  Iniciando clientes do Supernó 2 ($IP_SN2)..."
for ip in "${CLIENTES_SN2[@]}"; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # (9004, 9005, 9006)
    echo "  -> Abrindo terminal SSH para Cliente ($ip) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $ip $IP_SN2 $PORT_SN2"

    CMD_TO_RUN="bash -c \"
        echo '--- CONECTANDO AO CLIENTE (IP: $ip) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN2 ---';
        ssh $SSH_USER@$ip '
            echo --- CONEXÃO SSH ESTABELECIDA ---;
            cd $PROJECT_PATH;
            chmod +x iniciar-no.sh;
            
            echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
            $CMD_LOCAL_CLIENTE;
        ';
        echo;
        echo '--- SESSÃO SSH (CLIENTE $ip) (P2P: $CLIENT_PEER_PORT) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    let "i=i+1" 
    sleep 10
done

echo "  Iniciando clientes do Supernó 3 ($IP_SN3)..."
for ip in "${CLIENTES_SN3[@]}"; do
    let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # (9007, 9008, 9009)
    echo "  -> Abrindo terminal SSH para Cliente ($ip) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $ip $IP_SN3 $PORT_SN3"

    CMD_TO_RUN="bash -c \"
        echo '--- CONECTANDO AO CLIENTE (IP: $ip) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN3 ---';
        ssh $SSH_USER@$ip '
            echo --- CONEXÃO SSH ESTABELECIDA ---;
            cd $PROJECT_PATH;
            chmod +x iniciar-no.sh;
            
            echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
            $CMD_LOCAL_CLIENTE;
        ';
        echo;
        echo '--- SESSÃO SSH (CLIENTE $ip) (P2P: $CLIENT_PEER_PORT) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    let "i=i+1" 
    sleep 10
done

echo "  Iniciando clientes do Supernó 4 ($IP_SN4)..."
for ip in "${CLIENTES_SN4[@]}"; do
     let "CLIENT_PEER_PORT = BASE_PEER_PORT + i" # (9010, 9011, 9012)
    echo "  -> Abrindo terminal SSH para Cliente ($ip) (Porta P2P: $CLIENT_PEER_PORT)..."
    CMD_LOCAL_CLIENTE="export PEER_PORT=$CLIENT_PEER_PORT; ./iniciar-no.sh cliente $ip $IP_SN4 $PORT_SN4"

    CMD_TO_RUN="bash -c \"
        echo '--- CONECTANDO AO CLIENTE (IP: $ip) (P2P: $CLIENT_PEER_PORT) PARA SUPERNÓ $IP_SN4 ---';
        ssh $SSH_USER@$ip '
            echo --- CONEXÃO SSH ESTABELECIDA ---;
            cd $PROJECT_PATH;
            chmod +x iniciar-no.sh;
            
            echo --- INICIANDO SCRIPT: $CMD_LOCAL_CLIENTE ---;
            $CMD_LOCAL_CLIENTE;
        ';
        echo;
        echo '--- SESSÃO SSH (CLIENTE $ip) (P2P: $CLIENT_PEER_PORT) FINALIZADA. Pressione [Enter] para fechar. ---';
        read
    \""
    $TERMINAL_CMD -- bash -c "$CMD_TO_RUN" &
    let "i=i+1" 
    sleep 10
done

echo -e "\n============================================="
echo "DEPLOY CONCLUÍDO!"
echo "Todos os 17 nós receberam o comando de início."
echo "17 terminais devem estar abertos monitorando os nós."
echo "============================================="