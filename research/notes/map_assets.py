#!/usr/bin/env python3
"""Match executable path strings against ZDIR hashes; no game code is executed."""
import argparse
import csv
import re
import sys
from pathlib import Path
from inspect_zdir import read_records


def name_hash(name):
    value = 0xffffffff
    for byte in name.upper().encode('ascii'):
        value = (33 * value + byte) & 0xffffffff
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dol', type=Path)
    parser.add_argument('zdir', type=Path)
    args = parser.parse_args()
    rows = read_records(args.zdir)
    names = sorted(set(m.group().decode('ascii').upper()
                       for m in re.finditer(rb'[ -~]{5,}', args.dol.read_bytes())
                       if b'\\' in m.group() and b'.' in m.group()))
    output = csv.writer(sys.stdout)
    output.writerow(['name_candidate', 'hash', 'archive', 'offset_bytes', 'size_bytes'])
    for name in names:
        key = name_hash(name)
        for row in rows:
            if row[0] == key:
                output.writerow([name, f'{key:08x}', row[1], row[2]*2048, row[4]])
