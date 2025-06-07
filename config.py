# config.py

# Configurações do tracker central
TRACKER_HOST = 'localhost'
TRACKER_PORT = 8000
TRACKER_TIMEOUT = 40  # Segundos para considerar um peer inativo

# Tamanho de cada bloco de arquivo em bytes
BLOCK_SIZE = 64

# Número total de blocos (definido dinamicamente após divisão do arquivo original)
TOTAL_BLOCKS = None

# Intervalo para reavaliar os peers desbloqueados (choking/unchoking)
UNCHOKE_INTERVAL = 10  # segundos

# Quantos peers podem ser desbloqueados simultaneamente (os "melhores")
MAX_UNCHOKED = 4

# Número de peers para desbloqueio otimista
OPTIMISTIC_UNCHOKE = 1

# Porta base para os peers (peer 0 = 9000, peer 1 = 9001, etc)
PEER_PORT_BASE = 9000

# Intervalo para o peer contatar o tracker e atualizar sua lista
TRACKER_UPDATE_INTERVAL = 15