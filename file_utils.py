# file_utils.py

import os

def split_file(filepath, block_dir, block_size):
    """Divide o arquivo em blocos de tamanho fixo."""
    os.makedirs(block_dir, exist_ok=True)
    with open(filepath, 'rb') as f:
        index = 0
        while chunk := f.read(block_size):
            with open(f'{block_dir}/block_{index}', 'wb') as bf:
                bf.write(chunk)
            index += 1
    return index  # Retorna o total de blocos

def reconstruct_file(block_ids, block_dir, output_path):
    """Reconstrói o arquivo a partir dos blocos."""
    with open(output_path, 'wb') as out:
        for i in sorted(block_ids):
            with open(f'{block_dir}/block_{i}', 'rb') as bf:
                out.write(bf.read())
