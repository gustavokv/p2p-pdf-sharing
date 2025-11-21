# 🌐 Trabalho de Sistemas Distribuídos - Rede P2P Híbrida

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Concluído-success.svg?style=for-the-badge)

**Universidade Estadual de Mato Grosso do Sul (UEMS)**
Curso de Ciência da Computação | Disciplina: Programação Distribuída
**Professor:** Prof. Dr. Rubens Barbosa Filho | **Data:** 21/11/2025

</div>

---

## 👥 Autores

* **Gustavo Kermaunar Volobueff**
* **Victor Manoel Fernandes de Souza**

---

## 📘 1. Descrição do Projeto

Este projeto implementa um sistema de compartilhamento de arquivos PDF utilizando uma arquitetura **Peer-to-Peer (P2P) Híbrida** com Supernós. O sistema foi desenvolvido em Python utilizando a biblioteca `asyncio` para garantir alta concorrência e desempenho na comunicação de rede.

### Funcionalidades Implementadas:

* 🏛️ **Arquitetura Híbrida:** Coordenador centralizado para registro + Supernós para busca descentralizada.
* ⚡ **Comunicação Assíncrona:** Uso de Sockets TCP não bloqueantes.
* 🌊 **Busca por Inundação (Flooding):** Supernós consultam vizinhos para encontrar arquivos.
* 🔄 **Transferência P2P:** Download direto entre clientes (Peer-to-Peer).
* 🛡️ **Tolerância a Falhas (Eleição):** Algoritmo do Valentão (Bully) para eleger novo Coordenador.
* 🤝 **Consistência (Consenso):** Protocolo 2PC (Two-Phase Commit) para replicação de dados e promoção de nós.
* 📈 **Gestão Dinâmica:** Entrada e saída de nós com atualização automática da topologia.

---

## 📂 2. Estrutura de Diretórios

O código-fonte deve ser mantido na seguinte estrutura para execução correta:

```text
p2p-pdf-sharing/
├── deploy-rede-2-labs.sh  # Script de automação para iniciar a rede completa 
├── iniciar-no.sh          # Script auxiliar wrapper para iniciar cada nó individualmente
├── indice_replicado.json  # (Gerado automaticamente) Persistência temporária durante promoção
├── shared_pdfs/           # Pasta padrão para armazenar os arquivos PDF a serem compartilhados
│
└── src/                   # Código-fonte Python
    ├── __init__.py
    ├── coordenador/
    │   ├── __init__.py
    │   └── main.py        # Código do Coordenador Central
    │
    ├── superno/
    │   ├── __init__.py
    │   └── main.py        # Código dos Supernós (Líderes de Grupo)
    │
    ├── cliente/
    │   ├── __init__.py
    │   └── main.py        # Código dos Clientes (Peers)
    │
    └── shared/
        ├── __init__.py
        └── mensagens.py   # Protocolo de comunicação (JSON) e constantes
```

---

## ⚙️ 3. Pré-requisitos de Execução

1.  **Ambiente:** Linux.
2.  **Interpretador:** Python 3.8 ou superior.
3.  **Terminal:** `gnome-terminal` instalado (necessário para os scripts de deploy automático).
4.  **Rede:**
    * As portas **8000-8004** (Supernós/Coord) e **9000-9016** (Clientes) devem estar livres.
    * Para execução distribuída (Laboratório), o SSH sem senha deve estar configurado.

---

## 🚀 4. Roteiro de Execução (Como Rodar)

O projeto inclui scripts de automação para facilitar o deploy. Você pode rodar de duas formas:

### OPÇÃO A: Execução Automatizada (Recomendada)

Esta opção sobe a rede completa (1 Coordenador, 4 Supernós e 12 Clientes) automaticamente.

1.  Abra o terminal na raiz do projeto (`p2p-pdf-sharing/`).
2.  Dê permissão de execução aos scripts:
    ```bash
    chmod +x deploy-rede-2-labs.sh iniciar-no.sh
    ```
3.  *(Opcional)* Se for rodar apenas em uma máquina local, utilize o script correspondente (se houver). O script entregue já está configurado para o ambiente de laboratório alvo.
4.  Execute o script de deploy:
    ```bash
    ./deploy-rede-2-labs.sh
    ```
5.  O script abrirá **17 janelas de terminal**, cada uma representando um nó da rede:
    * Janela 1: Coordenador (Porta 8000)
    * Janelas 2-5: Supernós (Portas 8001-8004)
    * Janelas 6-17: Clientes (Portas 9001-9012)

### OPÇÃO B: Execução Manual (Passo a Passo)

Caso deseje subir os nós individualmente para testes específicos:

**1. Inicie o Coordenador:**
```bash
./iniciar-no.sh coordenador
```

**2. Inicie os Supernós (em outros terminais):**
```bash
./iniciar-no.sh superno <IP_LOCAL> <PORTA_SN> <IP_COORDENADOR>
# Exemplo: ./iniciar-no.sh superno 127.0.0.1 8001 127.0.0.1
```

**3. Inicie os Clientes (em outros terminais):**

```bash
export PEER_PORT=9001  # Defina uma porta única para cada cliente
./iniciar-no.sh cliente <IP_LOCAL> <IP_SUPERNODE> <PORTA_SUPERNODE>
# Exemplo: ./iniciar-no.sh cliente 127.0.0.1 127.0.0.1 8001
```

## 🧪 5. Roteiro de Testes (Demonstração)

### TESTE 1: Transferência de Arquivo (P2P)

1.  No terminal de um Cliente (ex: Cliente A), escolha a opção `1 - Enviar arquivo que possuo (Indexar)`.
2.  Digite o nome de um arquivo PDF existente na pasta `shared_pdfs_<PORTA>`.
3.  No terminal de outro Cliente (ex: Cliente B), escolha `2 - Buscar arquivo específico (Download)`.
4.  Digite o nome do arquivo indexado anteriormente.
5.  O sistema localizará o arquivo e perguntará se deseja baixar. Confirme com `s`.
6.  Verifique se o arquivo apareceu na pasta do Cliente B.

### TESTE 2: Tolerância a Falhas (Eleição + Consenso)

1.  Vá até a janela do **COORDENADOR** e pressione `Ctrl+C` para encerrá-lo abruptamente.
2.  Observe os terminais dos Supernós.
3.  Eles detectarão a falha (`"O LÍDER MORREU"`) e iniciarão a Eleição (**Algoritmo do Valentão**).
4.  O Supernó com maior ID vencerá e iniciará o Consenso (**2PC**).
5.  O novo Coordenador promoverá um de seus Clientes a novo Supernó.
    * O Cliente escolhido reiniciará automaticamente como Supernó.
    * Os outros Clientes migrarão automaticamente para o novo Supernó.
    * Os Supernós vizinhos atualizarão suas rotas.
6.  Após a estabilização, tente realizar uma nova busca de arquivo para confirmar que a rede continua operante.

---

## 📝 6. Observações Técnicas

* **IDs do Algoritmo Valentão:**
    * Em ambiente de laboratório (distribuído), o ID é baseado no endereço IP.
    * Em ambiente local (localhost), o ID é baseado na porta.
    * *Isso garante que sempre haja um critério de desempate único.*
