#!/bin/bash

# --- Script para iniciar um nó da rede P2P ---

# Limpa o terminal para uma visualização limpa
clear

# Define o caminho para a raiz do seu projeto.
# Este script assume que você o está executando de dentro da pasta do projeto.
PROJECT_DIR=$(pwd)
PYTHON_CMD="python3"

# --- Validação Inicial ---
if [ -z "$1" ]; then
    echo "ERRO: Você deve especificar um papel para este nó."
    echo "Uso: ./iniciar-no.sh [coordenador|superno|cliente]"
    exit 1
fi

ROLE=$1

# --- LÓGICA DO COORDENADOR ---
if [ "$ROLE" == "coordenador" ]; then
    echo "================================="
    echo "Iniciando Nó: COORDENADOR"
    echo "================================="
    
    cd "$PROJECT_DIR"
    $PYTHON_CMD src/coordenador/main.py

# --- LÓGICA DO SUPERNÓ ---
elif [ "$ROLE" == "superno" ]; then
    if [ $# -ne 4 ]; then
        echo "ERRO: O papel 'superno' requer 3 argumentos."
        echo "Uso: ./iniciar-no.sh superno <IP_DESTA_MAQUINA> <PORTA_PARA_ESCUTAR> <IP_DO_COORDENADOR>"
        echo "Exemplo: ./iniciar-no.sh superno 192.168.1.101 8001 192.168.1.100"
        exit 1
    fi

    # Define as variáveis de ambiente para o script Python
    export HOST_IP=$2
    export COORDINATOR_PORT="8000"
    export COORDINATOR_IP=$4
    
    MY_PORT=$3

    echo "================================="
    echo "Iniciando Nó: SUPERNÓ"
    echo "================================="
    echo "  -> Meu IP (Host):   $HOST_IP"
    echo "  -> Minha Porta:     $MY_PORT"
    echo "  -> IP Coordenador: $COORDINATOR_IP"
    echo "---------------------------------"
    
    cd "$PROJECT_DIR"
    $PYTHON_CMD src/supernode/main.py $MY_PORT

# --- LÓGICA DO CLIENTE ---
elif [ "$ROLE" == "cliente" ]; then
    if [ $# -ne 4 ]; then
        echo "ERRO: O papel 'cliente' requer 3 argumentos."
        echo "Uso: ./iniciar-no.sh cliente <IP_DESTA_MAQUINA> <IP_DO_SUPERNODE> <PORTA_DO_SUPERNODE>"
        echo "Exemplo: ./iniciar-no.sh cliente 192.168.1.150 192.168.1.101 8001"
        exit 1
    fi

    # Define as variáveis de ambiente para o script Python
    export HOST_IP=$2
    export SUPERNODE_IP=$3
    export SUPERNODE_PORT=$4

    echo "================================="
    echo "Iniciando Nó: CLIENTE"
    echo "================================="
    echo "  -> Meu IP (Host):   $HOST_IP"
    echo "  -> IP Supernó:     $SUPERNODE_IP"
    echo "  -> Porta Supernó:  $SUPERNODE_PORT"
    echo "---------------------------------"
    
    cd "$PROJECT_DIR"
    $PYTHON_CMD src/client/main.py

else
    echo "ERRO: Papel '$ROLE' desconhecido."
    echo "Use: [coordenador|superno|cliente]"
    exit 1
fi