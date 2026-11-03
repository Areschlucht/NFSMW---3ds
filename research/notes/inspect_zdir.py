#!/usr/bin/env python3
"""Export candidate ZDIR records; column meanings remain hypotheses.

Usage: python3 inspect_zdir.py ZDIR.BIN > zdir-records.csv
No archive extraction or decompression is attempted.
"""
import argparse
import csv
import struct
import sys
from pathlib import Path


def read_records(path):
    data = path.read_bytes()
    if not data or len(data) % 24:
        raise ValueError('Expected a nonempty multiple of 24 bytes')
    rows = list(struct.iter_unpack('<6I', data))
    if any(a[0] > b[0] for a, b in zip(rows, rows[1:])):
        raise ValueError('First field is not sorted as in the inspected sample')
    if any(r[1] > 3 for r in rows):
        raise ValueError('Archive selector outside inspected range 0..3')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    writer = csv.writer(sys.stdout)
    writer.writerow(['candidate_name_hash_hex', 'candidate_archive_index',
                     'raw_word2', 'raw_word3', 'candidate_size_bytes',
                     'raw_word5_hex'])
    for key, archive, word2, word3, size, word5 in read_records(args.directory):
        writer.writerow([f'{key:08x}', archive, word2, word3, size, f'{word5:08x}'])
