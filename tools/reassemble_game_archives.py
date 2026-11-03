#!/usr/bin/env python3
"""Reassemble privately supplied 28-MiB pieces without overwriting existing data."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SIZES = (315254784, 340240384, 330981376, 346253312)
ZDIR_SHA = 'd5726a00d086edb5f8a47ff4bffa4715f84b44441987fd323141a6dfaf1ba333'
PART_BYTES = 28 * 1048576


def plan(directory, archive):
    source = f'ZZDATA{archive}.BIN'
    raw = (directory / (source + '.parts.json')).read_text(encoding='utf-8-sig')
    m = json.loads(raw)
    if (m['Schema'], m['Source'], m['Bytes'], m['ZdirSHA256'], m['PartBytes']) != (1, source, SIZES[archive], ZDIR_SHA, PART_BYTES):
        raise ValueError('Unexpected manifest source/size/schema')
    if not isinstance(m['SHA256'], str) or not re.fullmatch('[0-9a-f]{64}', m['SHA256']):
        raise ValueError('Invalid whole-archive SHA256')
    expected_count = (SIZES[archive] + PART_BYTES - 1) // PART_BYTES
    if not isinstance(m['Parts'], list) or len(m['Parts']) != expected_count:
        raise ValueError('Unexpected piece count')
    for i, part in enumerate(m['Parts']):
        size = min(PART_BYTES, SIZES[archive] - i * PART_BYTES)
        if (part['File'], part['Offset'], part['Bytes']) != (f'{source}.part{i:02d}.bin', i * PART_BYTES, size):
            raise ValueError('Unexpected piece name/offset/size')
        if not isinstance(part['SHA256'], str) or not re.fullmatch('[0-9a-f]{64}', part['SHA256']):
            raise ValueError('Invalid piece SHA256')
        path = directory / part['File']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError('Missing or invalid piece: ' + part['File'])
    return m


def assemble(directory, destination, archive):
    m = plan(directory, archive)
    target = destination / m['Source']
    if target.exists():
        raise ValueError('Destination already exists; no overwrite: ' + str(target))
    destination.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.partial')
    whole = hashlib.sha256()
    with partial.open('xb') as output:
        for part in m['Parts']:
            h = hashlib.sha256()
            with (directory / part['File']).open('rb') as source:
                while block := source.read(1048576):
                    h.update(block)
                    whole.update(block)
                    output.write(block)
            if h.hexdigest() != part['SHA256']:
                raise ValueError('Piece hash mismatch; retained partial: ' + part['File'])
    if partial.stat().st_size != m['Bytes'] or whole.hexdigest() != m['SHA256']:
        raise ValueError('Reconstructed archive hash mismatch; retained partial')
    # Link creation refuses an existing target atomically; retain the partial as
    # a recovery copy. No source pieces or previous outputs are deleted.
    target.hardlink_to(partial)
    return {'source': m['Source'], 'bytes': m['Bytes'], 'sha256': whole.hexdigest(),
            'pieces_verified': len(m['Parts'])}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--archives', type=int, nargs='+', choices=range(4), default=[1, 0, 2, 3])
    a = p.parse_args()
    if len(set(a.archives)) != len(a.archives):
        raise ValueError('Duplicate archive selector')
    for index in a.archives:
        print(json.dumps(assemble(a.directory, a.destination, index)))
