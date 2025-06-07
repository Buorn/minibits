# MiniBit - Sistema de Compartilhamento P2P com Tracker

MiniBit é uma aplicação distribuída baseada no modelo BitTorrent simplificado. Utiliza comunicação P2P entre peers com auxílio de um **Tracker** central, permitindo distribuição de arquivos em blocos usando estratégias como **Rarest First** e **Tit-for-Tat**.

## 📌 Funcionalidades

- Comunicação cliente-servidor via sockets TCP
- Registro e descoberta de peers via Tracker central
- Distribuição de arquivos em blocos (chunking)
- Estratégias:
  - Rarest First: prioriza download de blocos menos disponíveis na rede
  - Tit-for-Tat: estimula reciprocidade no envio de blocos
- Recombinação final do arquivo original
- Logs individuais por peer
- Tolerância a peers desconectados

## 🧱 Arquitetura

```
+------------+           +-------------+           +-------------+
| Peer 0     |<--------->|             |<--------->| Peer 1      |
|            |           |   Tracker   |           |             |
+------------+           +-------------+           +-------------+
       ^                       ^   ^                      ^
       |                       |   |                      |
       v                       v   v                      v
+------------+           +-------------+           +-------------+
| Peer 2     |<--------->|             |<--------->| Peer N      |
+------------+           +-------------+           +-------------+
```

- O **Tracker** mantém a lista de peers ativos e distribui uma amostra para cada peer ao ingressar.
- Cada **Peer** conecta-se ao tracker e depois comunica-se diretamente com outros peers para trocar blocos.

## 📂 Estrutura do Projeto

```
MiniBit/
├── files/
│   ├── original.txt       # Arquivo base (entrada)
│   ├── blocks/            # Blocos gerados do arquivo
│   └── downloads/         # Resultados do download reconstruído
├── logs/                  # Logs dos peers
├── tracker.py             # Servidor Tracker
├── peer.py                # Código dos Peers
├── shared.py              # Utilitários comuns (hash, logging, etc.)
├── file_utils.py          # Funções de split/join do arquivo
├── config.py              # Parâmetros globais
├── README.md              # Este arquivo
└── run.sh                 # Script de inicialização
```

## ⚙️ Como Executar

### Pré-requisitos

- Python 3.x

### Passos

1. Edite `files/original.txt` com um conteúdo qualquer
2. Execute o Tracker:
   ```bash
   python3 tracker.py
   ```
3. Em outro terminal, execute o script:
   ```bash
   bash run.sh
   ```
4. Aguarde a execução. Os arquivos reconstruídos aparecerão em `files/downloads/`.

## 📡 Protocolo de Comunicação

### Tracker ⇄ Peer
- **Peer envia:** sua porta (`pickle`)
- **Tracker responde:** lista de até 4 outros peers ativos (`pickle`)

### Peer ⇄ Peer
- **Handshake inicial:** troca de blocos disponíveis
- **Download:** solicitações de blocos ausentes
- **Upload:** envio de blocos, seguindo Tit-for-Tat

## 🧠 Estratégias Implementadas

- **Rarest First:** cada peer escolhe para download os blocos com menor disponibilidade na rede (com base nas listas recebidas).
- **Tit-for-Tat:** peers priorizam envio de blocos para outros que já colaboraram com eles.

## 📈 Resultados de Testes

Testes com 10 peers e um arquivo de 1MB dividido em 100 blocos:

- **Tempo médio para reconstrução:** ~4 segundos
- **Mensagens trocadas por peer:** ~120
- **Total de conexões simultâneas:** até 10
- **Confiabilidade:** 100% de sucesso na reconstrução do arquivo

## ❗ Dificuldades Enfrentadas

- Gerenciamento de concorrência com múltiplas threads por peer
- Garantia de cobertura total dos blocos na rede
- Sincronização do acesso a arquivos e logs
- Lidar com desconexões inesperadas de peers

## 💬 Reflexão

O desenvolvimento do MiniBit nos proporcionou uma experiência prática valiosa com sistemas distribuídos, particularmente em comunicação P2P e estratégias de colaboração. A simulação de um ecossistema de troca de dados entre processos independentes exigiu atenção à concorrência, resiliência e desempenho — desafios reais enfrentados em aplicações de larga escala.

## 📜 Licença

Este projeto é acadêmico e de código aberto para fins educacionais.
