#!/usr/bin/env python3
"""Inspect a DOL without executing it or modifying the input (Python 3 only)."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def inspect(path):
    data = path.read_bytes()
    if len(data) < 0x100:
        raise ValueError('File is too short for a DOL header')
    offsets = struct.unpack_from('>18I', data, 0)
    addresses = struct.unpack_from('>18I', data, 0x48)
    sizes = struct.unpack_from('>18I', data, 0x90)
    sections = []
    for i, (offset, address, size) in enumerate(zip(offsets, addresses, sizes)):
        if not size:
            continue
        if offset < 0x100 or offset + size > len(data):
            raise ValueError(f'Section {i} exceeds file bounds')
        sections.append(dict(name=f'text{i}' if i < 7 else f'data{i-7}',
                             offset=offset, address=address, size=size))
    for i, first in enumerate(sections):
        for second in sections[i+1:]:
            for key in ('offset', 'address'):
                if max(first[key], second[key]) < min(first[key]+first['size'], second[key]+second['size']):
                    raise ValueError(f'Overlapping {key} ranges')
    bss, bss_size, entry = struct.unpack_from('>3I', data, 0xd8)
    if not any(s['name'].startswith('text') and s['address'] <= entry < s['address'] + s['size'] for s in sections):
        raise ValueError('Entry point is outside text sections')
    strings = [(m.start(), m.group().decode('ascii'))
               for m in re.finditer(rb'[ -~]{8,}', data)]
    paths = sorted(set(s for _, s in strings if re.search(r'[a-z]:[/\\].*\.(?:cpp|hpp|c|h)$', s, re.I)))
    assets = sorted(set(s for _, s in strings if re.search(r'\.(?:bin|bun|big|viv|thp|ast|abk|mus)(?:$|\W)', s, re.I)))
    return dict(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                sections=sections, bss_address=bss, bss_size=bss_size, entry=entry,
                printable_string_count=len(strings), source_paths=paths,
                asset_string_candidates=assets)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dol', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.dol), indent=2))
