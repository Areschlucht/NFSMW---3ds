#!/usr/bin/env python3
"""Validate the language/chunk layouts observed in the supplied asset samples."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def chunks(data, start, end, depth=0):
    if depth > 32:
        raise ValueError('Excessive nesting')
    result = []
    while start < end:
        if end - start < 8:
            raise ValueError('Truncated chunk header')
        kind, size = struct.unpack_from('<II', data, start)
        stop = start + 8 + size
        if stop > end:
            raise ValueError('Chunk exceeds parent bounds')
        entry = dict(offset=start, id=f'{kind:08x}', payload_bytes=size)
        if kind & 0x80000000:
            entry['children'] = chunks(data, start+8, stop, depth+1)
        result.append(entry)
        start = stop
    return result


def language(data):
    kind, size = struct.unpack_from('<II', data)
    if kind != 0x39000 or size != len(data)-8:
        raise ValueError('Unexpected language chunk header')
    # The table and string offsets in this sample are relative to the payload.
    _, count, table_offset, strings_offset = struct.unpack_from('<4I', data, 8)
    table, strings = 8+table_offset, 8+strings_offset
    if not 24 <= table <= strings <= len(data) or table+count*8 != strings:
        raise ValueError('Unexpected language table bounds')
    entries = []
    for i in range(count):
        key, offset = struct.unpack_from('<II', data, table+i*8)
        position = strings+offset
        if position >= len(data) or (offset and data[position-1] != 0):
            raise ValueError('String offset is not at a string boundary')
        end = data.find(b'\0', position)
        if end < 0:
            raise ValueError('Unterminated string')
        # Keep raw string bytes out of the report; encoding is not established.
        entries.append(dict(hash=f'{key:08x}', offset=offset, bytes=end-position))
    if any(a['hash'] > b['hash'] for a,b in zip(entries, entries[1:])):
        raise ValueError('Language keys are not sorted')
    return dict(entries=count, table_file_offset=table,
                strings_file_offset=strings, string_boundaries_validated=count,
                unique_keys=len({e['hash'] for e in entries}))


def inspect(path):
    data = path.read_bytes()
    result = dict(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    result['chunks'] = chunks(data, 0, len(data))
    if struct.unpack_from('<I', data)[0] == 0x39000:
        result['language'] = language(data)
    else:
        result['object_name_candidates'] = sorted(set(
            m.group().decode('ascii') for m in re.finditer(rb'EBRAKE_[A-Z0-9_]+', data)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.asset), indent=2))
