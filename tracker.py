# tracker.py

import socket
import threading
import pickle
import random
import time
from config import TRACKER_HOST, TRACKER_PORT, TRACKER_TIMEOUT

# Dicionário para armazenar peers e o timestamp do último contato
# {peer_port: last_seen_timestamp}
peers = {}
peers_lock = threading.Lock()

def clean_inactive_peers():
    """Thread que remove peers inativos periodicamente."""
    while True:
        time.sleep(TRACKER_TIMEOUT / 2)
        with peers_lock:
            now = time.time()
            inactive_peers = [
                port for port, last_seen in peers.items()
                if now - last_seen > TRACKER_TIMEOUT
            ]
            for port in inactive_peers:
                del peers[port]
                print(f'[Tracker] Peer inativo removido: {port}')

def handle_client(conn):
    """Lida com uma nova conexão de um peer."""
    try:
        # 1. Recebe a porta do peer e registra seu contato
        port = pickle.loads(conn.recv(1024))
        with peers_lock:
            peers[port] = time.time()

        # 2. Obtém uma lista de outros peers ativos
        with peers_lock:
            # Garante que não vamos incluir o próprio peer na lista
            other_peers = list(peers.keys() - {port})

        # 3. Seleciona um subconjunto para enviar de volta
        # Req 2.4.2: Se a rede tiver menos de 5 peers, retorna todos os outros
        # A lógica `min(4, len(other_peers))` já cobre isso.
        # Por exemplo, se há 4 peers na rede, other_peers terá 3. min(4,3)=3.
        num_to_return = min(MAX_UNCHOKED, len(other_peers))
        selected = random.sample(other_peers, num_to_return)

        # 4. Envia a lista para o peer
        conn.send(pickle.dumps(selected))

    except Exception as e:
        # Não precisa printar erros de conexão/desconexão comuns
        pass
    finally:
        conn.close()

def start_tracker():
    """Inicia o servidor do tracker."""
    # Inicia a thread de limpeza de peers inativos
    threading.Thread(target=clean_inactive_peers, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((TRACKER_HOST, TRACKER_PORT))
        s.listen()
        print(f'[Tracker] Online e aguardando peers em {TRACKER_HOST}:{TRACKER_PORT}...')
        while True:
            conn, _ = s.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    from config import MAX_UNCHOKED
    start_tracker()