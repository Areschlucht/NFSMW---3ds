"""Build a source-preserving availability manifest, not an invented load policy.

Meshes are never materialized. Only one indexed section is copied at a time.
Object-table records preserve the three original LOD slots (including zeros),
and raw unknown fields. An ID or model hash is never used to discard variants.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import struct

from nfs_rockport import chunks
from world_streaming_policy import bind_lod_hashes


def ordered_ranges(sections, source_bytes):
    ranges = sorted((s['offset'], s['offset'] + s['bytes']) for s in sections)
    if any(a < 0 or a >= b or b > source_bytes for a, b in ranges):
        raise ValueError('Invalid section range')
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError('Overlapping section ranges')
    return ranges


def build(inventory_path, stream_path, index_path):
    inventory = json.loads(Path(inventory_path).read_text())
    index = Path(index_path).read_bytes()
    index_payloads = [index[a:b] for k, a, b in chunks(index) if k == 0x34110]
    if len(index_payloads) != 1 or len(index_payloads[0]) % 92:
        raise ValueError('Invalid original streaming table')
    raw_index = {struct.unpack_from('<I', row, 8)[0]: row.hex()
                 for row in (index_payloads[0][a:a+92]
                             for a in range(0, len(index_payloads[0]), 92))}
    if len(raw_index) * 92 != len(index_payloads[0]):
        raise ValueError('Duplicate index identifier')
    if set(raw_index) != {s['id'] for s in inventory['sections']}:
        raise ValueError('Index and inventory section sets differ')
    variants, hashes = {}, defaultdict(set)
    for model in inventory['models']:
        sha = model['raw_sha256']
        hashes[model['hash']].add(sha)
        if sha not in variants:
            variants[sha] = {k: model[k] for k in
                             ('hash', 'name', 'bytes', 'bounds', 'matrix', 'textures',
                              'expected_triangles', 'validated')}
            if not model['validated']:
                variants[sha]['rejection'] = model['reason']
            variants[sha]['consumed_textures'] = model.get('consumed_textures', model['textures'])
            variants[sha]['sources'] = []
        variants[sha]['sources'].append([model['section'], model['offset']])
    sections = []
    missing = set()
    with Path(stream_path).open('rb') as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as full:
            ordered_ranges(inventory['sections'], len(full))
            if hashlib.sha256(full).hexdigest() != inventory['source_sha256']:
                raise ValueError('Stream SHA does not match inventory')
            for source in inventory['sections']:
                offset, length = source['offset'], source['bytes']
                original_record = bytes.fromhex(raw_index[source['id']])
                if struct.unpack_from('<2I', original_record, 20) != (offset, length):
                    raise ValueError('Index and inventory source ranges differ')
                data = full[offset:offset+length]
                section = dict(id=source['id'], offset=offset, bytes=length,
                               sha256=hashlib.sha256(data).hexdigest(),
                               raw_index_record=raw_index[source['id']],
                               bounds=source['instance_bounds'],
                               instance_count=source['instances'],
                               available_models=sorted(set(source['model_hashes'])),
                               available_textures=sorted(set(source['texture_hashes'])),
                               required_lod_hashes=source['instance_model_keys'],
                               objects=[], instance_tables=[])
                for key in section['required_lod_hashes']:
                    if key not in hashes:
                        missing.add(key)
                for kind, a, b in chunks(data):
                    if kind != 0x80034100:
                        continue
                    for leaf, c, d in chunks(data[a:b]):
                        c += a
                        d += a
                        if leaf == 0x34102:
                            if (d-c) % 72:
                                raise ValueError('Incomplete object table')
                            for at in range(c, d, 72):
                                record = data[at:at+72]
                                section['objects'].append(dict(
                                    offset=offset+at, raw=record.hex(),
                                    name=record[:28].split(b'\0')[0].decode('ascii'),
                                    lod_slots=[f'{v:08x}' for v in struct.unpack_from('<4I', record, 24)],
                                    bound_lod_slots=[f'{v:08x}' if v is not None else None
                                                     for v in bind_lod_hashes(struct.unpack_from('<4I', record, 24))]))
                        elif leaf == 0x34103:
                            c = (c+15) & ~15
                            if (d-c) % 64:
                                raise ValueError('Incomplete instance table')
                            section['instance_tables'].append(dict(offset=offset+c,
                                                                   bytes=d-c, count=(d-c)//64))
                sections.append(section)
    missing_textures = sorted({key for v in variants.values() for key in v['textures']}
                              - inventory['texture_sources'].keys())
    missing_consumed = sorted({key for v in variants.values() for key in v['consumed_textures']}
                              - inventory['texture_sources'].keys())
    return dict(schema=1, kind='original-source-availability-only',
                source_sha256=inventory['source_sha256'],
                index_sha256=hashlib.sha256(index).hexdigest(),
                policy=dict(activation='unrecovered', lod_selection='unrecovered',
                            collisions='external collision manifest; no render-ID mapping inferred',
                            variants='retain every distinct raw model; hash alone is insufficient',
                            decode='legacy strict acceptance retained; rejected packets not auto-enabled'),
                summary=dict(sections=len(sections), models=len(inventory['models']),
                             distinct_model_hashes=len(hashes), raw_model_variants=len(variants),
                             ambiguous_hashes=sum(len(v)>1 for v in hashes.values()),
                             instances=sum(s['instance_count'] for s in sections),
                             max_section_bytes=max(s['bytes'] for s in sections),
                             missing_model_hashes=sorted(missing),
                             missing_texture_hashes=missing_textures,
                             missing_consumed_texture_hashes=missing_consumed),
                sections=sections, models=variants,
                model_hash_variants={k: sorted(v) for k, v in hashes.items()},
                texture_sources=inventory['texture_sources'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'stream', 'index', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    manifest = build(args.inventory, args.stream, args.index)
    Path(args.output).write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
    print(json.dumps(manifest['summary'], indent=2))
