# peer.py

import socket
import threading
import pickle
import random
import time
import os
import sys
from collections import Counter
from config import *
from file_utils import reconstruct_file

class Peer:
    def __init__(self, peer_id, total_blocks, initial_blocks):
        self.peer_id = peer_id
        self.port = PEER_PORT_BASE + peer_id
        self.blocks = set(initial_blocks)
        self.total_blocks = total_blocks
        
        # Estado da rede e Estratégia
        self.known_peers = set()
        self.unchoked_peers = set()
        self.optimistic_unchoke = None
        self.choked_by = set() ### NOVO: Guarda quem nos bloqueou recentemente
        
        self.running = True
        self.lock = threading.Lock()

        # Configuração de Logs
        os.makedirs('logs', exist_ok=True)
        self.log_file = open(f'logs/peer_{self.peer_id}.log', 'w')
        self.log(f'Inicializado com {len(self.blocks)} blocos.')

    def log(self, msg):
        """Escreve uma mensagem no console e no arquivo de log."""
        percent = (100 * len(self.blocks)) // self.total_blocks
        status = f'[Peer {self.peer_id} ({percent:02d}%)] {msg}'
        print(status)
        self.log_file.write(status + '\n')
        self.log_file.flush()

    # --- LÓGICA DO SERVIDOR (RESPONDER A OUTROS PEERS) ---

    def start_server(self):
        """Inicia a thread do servidor para ouvir outros peers."""
        server_thread = threading.Thread(target=self._server_loop, daemon=True)
        server_thread.start()

    def _server_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((TRACKER_HOST, self.port))
            s.listen()
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_request, args=(conn, addr), daemon=True).start()
                except OSError:
                    break # Socket foi fechado

    def handle_request(self, conn, addr):
        """Lida com uma requisição de outro peer."""
        try:
            data = pickle.loads(conn.recv(4096))
            
            # Requisição da lista de blocos
            if data['type'] == 'list':
                conn.sendall(pickle.dumps(list(self.blocks)))
            
            # Requisição de um bloco específico
            elif data['type'] == 'block_request':
                requester_port = data['requester_port']
                block_id = data['block_id']
                
                # REQ 2.6.5: Só envia se o peer estiver desbloqueado
                with self.lock:
                    is_allowed = (requester_port in self.unchoked_peers) or \
                                 (requester_port == self.optimistic_unchoke)

                if is_allowed and block_id in self.blocks:
                    # Simula o envio a partir de um diretório central de blocos
                    with open(f'files/blocks/block_{block_id}', 'rb') as f:
                        conn.sendall(pickle.dumps(f.read()))
                else:
                    # Peer está "choked" (bloqueado), envia recusa
                    conn.sendall(pickle.dumps(b'CHOKED'))

        except (pickle.UnpicklingError, KeyError, EOFError, ConnectionResetError):
            pass # Ignora dados malformados ou conexões fechadas
        finally:
            conn.close()
            
    # --- LÓGICA DO CLIENTE (CONTATAR TRACKER E OUTROS PEERS) ---

    def _contact_peer(self, peer_port, message):
        """Função auxiliar para enviar uma mensagem a um peer e obter resposta."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2) # Timeout curto para não travar
                s.connect((TRACKER_HOST, peer_port))
                s.sendall(pickle.dumps(message))
                return pickle.loads(s.recv(65536))
        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

    def contact_tracker(self):
        """Contata o tracker para obter uma lista de peers."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((TRACKER_HOST, TRACKER_PORT))
                s.sendall(pickle.dumps(self.port))
                peers = pickle.loads(s.recv(4096))
                with self.lock:
                    self.known_peers.update(peers)
        except (socket.timeout, ConnectionRefusedError, OSError):
            self.log('Tracker offline ou inacessível.')

    # --- LÓGICA DE ESTRATÉGIA (RAREST FIRST & OLHO POR OLHO) ---
    
    def _get_network_block_info(self):
        """Consulta a rede para saber quem tem quais blocos."""
        block_counts = Counter()
        peer_haves = {} # {peer_port: set_of_blocks}
        
        with self.lock:
            peers_to_query = self.known_peers.copy()

        for peer_port in peers_to_query:
            if peer_port == self.port: continue
            
            blocks = self._contact_peer(peer_port, {'type': 'list'})
            if blocks is not None:
                peer_haves[peer_port] = set(blocks)
                block_counts.update(blocks)
            else: # Peer pode ter ficado offline
                with self.lock:
                    self.known_peers.discard(peer_port)

        return block_counts, peer_haves
        
    def rarest_first_selector(self, block_counts):
        """Seleciona o bloco mais raro que este peer não possui."""
        needed_blocks = set(range(self.total_blocks)) - self.blocks
        if not needed_blocks:
            return None
        
        candidate_rarity = {b: block_counts[b] for b in needed_blocks if b in block_counts}
        if not candidate_rarity:
            return None

        min_freq = min(candidate_rarity.values())
        rarest_blocks = [b for b, freq in candidate_rarity.items() if freq == min_freq]
        
        return random.choice(rarest_blocks)

    def update_unchoked_peers_loop(self):
        """REQ 2.6: Implementa a lógica "Olho por Olho" baseada em mérito e aprendizado."""
        while self.running:
            time.sleep(UNCHOKE_INTERVAL)

            if not self.known_peers:
                continue

            _, peer_haves = self._get_network_block_info()
            needed_blocks = set(range(self.total_blocks)) - self.blocks

            with self.lock:
                # ### NOVO: Limpa a lista de "não cooperativos" para dar uma segunda chance
                self.choked_by.clear()

                # Se não precisamos de blocos, desbloqueamos aleatoriamente para semear
                if not needed_blocks:
                    peers_to_unchoke = random.sample(
                        list(self.known_peers - {self.port}), 
                        min(MAX_UNCHOKED, len(self.known_peers - {self.port}))
                    )
                    self.unchoked_peers = set(peers_to_unchoke)
                    self.optimistic_unchoke = None
                    continue
            
            # Calcula a "pontuação" de cada peer
            scores = {}
            for port, haves in peer_haves.items():
                with self.lock:
                    # ### NOVO: Penaliza quem nos bloqueou na rodada anterior
                    if port in self.choked_by:
                        scores[port] = -1
                        continue
                scores[port] = len(needed_blocks.intersection(haves))
            
            sorted_peers = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)
            
            new_unchoked = set(sorted_peers[:MAX_UNCHOKED])
            choked_pool = [p for p in sorted_peers if p not in new_unchoked]
            new_optimistic = random.choice(choked_pool) if choked_pool else None

            with self.lock:
                self.unchoked_peers = new_unchoked
                self.optimistic_unchoke = new_optimistic
            
            unchoked_names = sorted([f'P{p-PEER_PORT_BASE}' for p in new_unchoked])
            optimistic_name = f'P{new_optimistic-PEER_PORT_BASE}' if new_optimistic else "Nenhum"
            self.log(f"Nova seleção Unchoked: {unchoked_names}, Otimista: {optimistic_name}")

    # --- LÓGICA PRINCIPAL DE DOWNLOAD E EXECUÇÃO ---

    def download_loop(self):
        """Loop principal que orquestra o download de blocos."""
        while len(self.blocks) < self.total_blocks:
            block_counts, peer_haves = self._get_network_block_info()
            
            target_block = self.rarest_first_selector(block_counts)
            if target_block is None:
                self.log("Nenhum bloco necessário ou disponível na rede conhecida.")
                time.sleep(5)
                continue
            
            with self.lock:
                potential_sources = list(self.unchoked_peers)
                if self.optimistic_unchoke:
                    potential_sources.append(self.optimistic_unchoke)
            
            random.shuffle(potential_sources)

            downloaded_this_cycle = False
            for peer_port in potential_sources:
                if peer_port in peer_haves and target_block in peer_haves[peer_port]:
                    message = {
                        'type': 'block_request',
                        'block_id': target_block,
                        'requester_port': self.port
                    }
                    block_data = self._contact_peer(peer_port, message)
                    
                    if block_data and block_data != b'CHOKED':
                        with open(f'files/blocks/block_{target_block}', 'wb') as f:
                            f.write(block_data)
                        with self.lock:
                            self.blocks.add(target_block)
                        self.log(f"BAIXOU bloco {target_block} de Peer {peer_port - PEER_PORT_BASE}")
                        downloaded_this_cycle = True
                        break 
                    elif block_data == b'CHOKED':
                        # ### NOVO: Aprende que este peer nos bloqueou
                        self.log(f"Bloqueado (choked) por Peer {peer_port - PEER_PORT_BASE}. Tentando outro...")
                        with self.lock:
                            self.choked_by.add(peer_port)

            if not downloaded_this_cycle:
                time.sleep(random.uniform(1.0, 2.0))

        # --- Conclusão ---
        self.log("ARQUIVO COMPLETO! Reconstruindo...")
        output_filename = f'files/downloads/peer_{self.peer_id}_arquivo_completo.txt'
        reconstruct_file(sorted(list(self.blocks)), 'files/blocks', output_filename)
        self.log(f'Arquivo salvo em {output_filename}.')
        self.log('Continuando a semear (seeding) para outros peers...')
        # O peer continua rodando para servir blocos para os outros.
        # A thread principal termina, mas as threads daemon continuarão a servir.

    def run(self):
        """Inicia todas as threads e lógicas do peer."""
        self.start_server()
        
        # Thread para contatar o tracker periodicamente
        def tracker_loop():
            while self.running:
                self.contact_tracker()
                time.sleep(TRACKER_UPDATE_INTERVAL)
        threading.Thread(target=tracker_loop, daemon=True).start()

        # Thread para a lógica de choking/unchoking
        threading.Thread(target=self.update_unchoked_peers_loop, daemon=True).start()
        
        # O loop de download roda na thread principal
        self.download_loop()
        
        # Mantém a thread principal viva para que as threads daemon (servidor) continuem
        while True:
            time.sleep(3600)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Uso: python3 peer.py <id> <total_blocos> <bloco1> <bloco2> ...")
        sys.exit(1)
        
    peer_id = int(sys.argv[1])
    total_blocks = int(sys.argv[2])
    initial_blocks = list(map(int, sys.argv[3:]))
    
    peer = Peer(peer_id, total_blocks, initial_blocks)
    peer.run()