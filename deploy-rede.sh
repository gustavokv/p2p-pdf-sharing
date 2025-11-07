#!/bin/bash

# ==========================================================
# SCRIPT DE DEPLOY PARA REDE P2P DISTRIBUÍDA (17 NÓS)
# ==========================================================
#
# Pré-requisitos:
# 1. Este script deve ser rodado da MÁQUINA DO COORDENADOR.
# 2. Acesso SSH sem senha (via chave) deve estar configurado
#    da máquina coordenadora para todas as 16 outras máquinas.
# 3. O projeto (com o 'iniciar-no.sh') deve estar no mesmo
#    caminho em TODAS as 17 máquinas.
# 4. 'git' deve estar instalado em todas as máquinas.
#
# ==========================================================

clear

# --- CONFIGURAÇÃO DA REDE (PREENCHA AQUI) ---

# Usuário SSH para conectar às máquinas remotas
SSH_USER="aluno"

# Caminho absoluto para a pasta do projeto NAS MÁQUINAS REMOTAS
# Exemplo: /home/aluno/p2p-file-sharing
PROJECT_PATH="/home/aluno/p2p-file-sharing"

# --- MAPA DA REDE ---
# Preencha com os 17 IPs REAIS das suas máquinas
IP_COORD="192.168.1.100" # IP desta máquina (Coordenador)

# Supernós (IP e Porta que vão usar)
IP_SN1="192.168.1.101"; PORT_SN1="8001"
IP_SN2="192.168.1.102"; PORT_SN2="8002"
IP_SN3="192.168.5.101"; PORT_SN3="8003"
IP_SN4="192.168.5.102"; PORT_SN4="8004"

# Clientes (12 IPs)
CLIENTES_SN1=("192.168.1.150" "192.168.1.151" "192.168.1.152")
CLIENTES_SN2=("192.168.1.153" "192.168.1.154" "192.168.1.155")
CLIENTES_SN3=("192.168.5.150" "192.168.5.151" "192.168.5.152")
CLIENTES_SN4=("192.168.5.153" "192.168.5.154" "192.168.5.155")
# --- FIM DO MAPA ---


# --- FUNÇÃO DE AJUDA PARA DEPLOY ---
# $1 = Usuário SSH
# $2 = IP da Máquina Remota
# $3 = Comando a ser executado
remote_exec() {
    local user=$1
    local ip=$2
    local cmd=$3
    # Define um nome de log baseado no papel (coordenador, superno, cliente)
    local logfile="/tmp/p2p-$(echo $cmd | cut -d' ' -f2).log"

    echo "  -> Enviando comando para $ip..."
    
    # -n: Redireciona stdin de /dev/null (essencial para background)
    ssh -n "$user@$ip" "
        echo 'Conexão SSH recebida. Atualizando e iniciando nó...' > $logfile;
        cd $PROJECT_PATH;
        
        # Atualiza o código para a versão mais recente
        git pull origin main >> $logfile 2>&1;
        
        # Garante que o script é executável
        chmod +x iniciar-no.sh;
        
        # Inicia o nó em background usando nohup
        # nohup: Mantém o processo rodando mesmo após a sessão SSH fechar
        # &    : Roda em background
        nohup $cmd >> $logfile 2>&1 &
    "
    
    echo "     Comando enviado. Nó iniciado em background em $ip."
    echo "     Log disponível em: $ip:$logfile"
}


# --- INÍCIO DA EXECUÇÃO ---
echo "AVISO: Este script irá iniciar 17 processos em 17 máquinas."
echo "Pressupõe que você está rodando da máquina $IP_COORD."
echo "E que o acesso SSH sem senha está configurado para o usuário '$SSH_USER'."
read -p "Pressione [Enter] para continuar ou [Ctrl+C] para cancelar..."

# 1. Iniciar o Coordenador (Localmente)
echo -e "\n[FASE 1/3] Iniciando Coordenador localmente em $IP_COORD..."
cd $PROJECT_PATH
git pull origin main # Atualiza o código local
chmod +x iniciar-no.sh
# Inicia localmente, em background
nohup ./iniciar-no.sh coordenador > /tmp/p2p-coordenador.log 2>&1 &
echo "Coordenador iniciado. Log em /tmp/p2p-coordenador.log"
echo "Aguardando 5 segundos para o coordenador iniciar antes de conectar os supernós..."
sleep 5

# 2. Iniciar os Supernós (Remotamente)
echo -e "\n[FASE 2/3] Iniciando 4 Supernós remotamente..."
remote_exec $SSH_USER $IP_SN1 "./iniciar-no.sh superno $IP_SN1 $PORT_SN1 $IP_COORD"
remote_exec $SSH_USER $IP_SN2 "./iniciar-no.sh superno $IP_SN2 $PORT_SN2 $IP_COORD"
remote_exec $SSH_USER $IP_SN3 "./iniciar-no.sh superno $IP_SN3 $PORT_SN3 $IP_COORD"
remote_exec $SSH_USER $IP_SN4 "./iniciar-no.sh superno $IP_SN4 $PORT_SN4 $IP_COORD"
echo "Comandos dos supernós enviados. Aguardando 10 segundos para se registrarem..."
sleep 10

# 3. Iniciar os Clientes (Remotamente)
echo -e "\n[FASE 3/3] Iniciando 12 Clientes remotamente..."

echo "  Iniciando clientes do Supernó 1 ($IP_SN1)..."
for ip in "${CLIENTES_SN1[@]}"; do
    remote_exec $SSH_USER $ip "./iniciar-no.sh cliente $ip $IP_SN1 $PORT_SN1"
done

echo "  Iniciando clientes do Supernó 2 ($IP_SN2)..."
for ip in "${CLIENTES_SN2[@]}"; do
    remote_exec $SSH_USER $ip "./iniciar-no.sh cliente $ip $IP_SN2 $PORT_SN2"
done

echo "  Iniciando clientes do Supernó 3 ($IP_SN3)..."
for ip in "${CLIENTES_SN3[@]}"; do
    remote_exec $SSH_USER $ip "./iniciar-no.sh cliente $ip $IP_SN3 $PORT_SN3"
done

echo "  Iniciando clientes do Supernó 4 ($IP_SN4)..."
for ip in "${CLIENTES_SN4[@]}"; do
    remote_exec $SSH_USER $ip "./iniciar-no.sh cliente $ip $IP_SN4 $PORT_SN4"
done


echo -e "\n============================================="
echo "DEPLOY CONCLUÍDO!"
echo "Todos os 17 nós receberam o comando de início."
echo "============================================="
echo "Para verificar os logs em uma máquina, use:"
echo "ssh $SSH_USER@<ip_da_maquina> tail -f /tmp/p2p-*.log"