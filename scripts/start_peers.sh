#!/bin/bash

# Prepara pastas
rm -rf files/blocks/* files/downloads logs/*
mkdir -p files/blocks files/downloads logs

# Divide o arquivo original
python3 -c "from file_utils import split_file; import config; config.TOTAL_BLOCKS = split_file('files/original.txt', 'files/blocks', config.BLOCK_SIZE)"

# Conta blocos
TOTAL_BLOCKS=$(ls files/blocks | wc -l)
PEERS=10
BLOCKS_PER_PEER=$((TOTAL_BLOCKS / PEERS))
EXTRA_BLOCKS=$((TOTAL_BLOCKS % PEERS))
ALL_BLOCKS=$(seq 0 $((TOTAL_BLOCKS - 1)))

# Distribui blocos garantindo cobertura total
i=0
for b in $ALL_BLOCKS; do
    echo $b >> temp_peer_$((i % PEERS)).txt
    i=$((i + 1))
done

for i in $(seq 0 $((PEERS - 1))); do
    BLOCKS=$(shuf temp_peer_$i.txt | xargs)
    echo "Iniciando peer $i com blocos: $BLOCKS"
    python3 peer.py $i $TOTAL_BLOCKS $BLOCKS &
    rm temp_peer_$i.txt
done
