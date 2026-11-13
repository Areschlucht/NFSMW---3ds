#!/usr/bin/env python3
"""Pack source-verified absolute race snapshots, including exact0x400 mirrors."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


def pack(plan, summary, stream, source_digest):
    key = int(plan['event_key'], 16)
    groups = bytearray(512)
    for group in plan['active_group_ids']:
        if not 0 < group < 4096:
            raise ValueError('Group index outside bounded original table')
        groups[group // 8] |= 1 << (group % 8)
    records = []
    mirrors = {r['source_instance_offset']: r for r in plan['reflections']}
    previous = -1
    with stream.open('rb') as f:
        for row in plan['overrides']:
            at, old, effective = (row[n] for n in ('source_instance_offset', 'expected_source_flags', 'effective_flags'))
            changed = old ^ effective
            if at <= previous or not changed or changed & ~0x410:
                raise ValueError('Unordered or unsupported source state transition')
            f.seek(at)
            raw = f.read(64)
            if len(raw) != 64 or struct.unpack_from('<I', raw, 24)[0] != old:
                raise ValueError('Source instance flags differ')
            reflected = bool(old & 0x00800000 and changed & 0x400)
            if reflected != (at in mirrors):
                raise ValueError('Reflection ownership differs')
            if reflected:
                wrapped = [(-x) & 65535 for x in struct.unpack_from('<3H', raw, 44)]
                actual = struct.unpack('<3h', struct.pack('<3H', *wrapped))
                if list(actual) != mirrors[at]['q13_first_row']:
                    raise ValueError('Original Q13 reflected row differs')
            records.append(struct.pack('<3I', at, old, effective))
            previous = at
    if len(mirrors) != plan['transform_mutation_count']:
        raise ValueError('Reflection count differs')
    data = bytearray(128) + groups + b''.join(records)
    struct.pack_into('<4s9I', data, 0, b'NWS1', 2, len(data), 0,
                     plan['base_bin_index'], 16, len(records), 128, 640, key)
    data[64:96] = source_digest
    data[96:128] = bytes.fromhex(summary['source_sha256']['gameplay'])
    struct.pack_into('<I', data, 12, zlib.crc32(data[16:]))
    return bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plans', 'stream', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    summary = json.loads((a.plans / 'summary.json').read_text())
    with a.stream.open('rb') as f:
        source_digest = hashlib.file_digest(f, 'sha256').digest()
    a.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in summary['event_plans']:
        original = a.plans / item['path']
        if hashlib.sha256(original.read_bytes()).hexdigest() != item['plan_sha256']:
            raise ValueError('Verified source plan differs')
        plan = json.loads(original.read_text())
        data = pack(plan, summary, a.stream, source_digest)
        output = a.output / (plan['event_key'] + '.nws')
        if output.exists() and output.read_bytes() != data:
            raise ValueError('Existing native snapshot differs')
        output.write_bytes(data)
        rows.append({'event': plan['event_key'], 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest(), 'mirrors': plan['transform_mutation_count']})
    (a.output / 'manifest.json').write_text(json.dumps({'version': 2, 'states': rows}, indent=2) + '\n')
    print(json.dumps({'states': len(rows), 'bytes': sum(r['bytes'] for r in rows)}))
