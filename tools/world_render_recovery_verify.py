"""Verify rejected model packets against the original executable, not guesses."""
import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
import struct

from nfs_rockport import chunks
from world_render_recovery_reference import DOL_SHA256, emit_original
from world_render_recovery_geometry import diagnose_model


def verify(inventory_path, stream_path, dol_path):
    inventory = json.loads(Path(inventory_path).read_text())
    dol = Path(dol_path).read_bytes()
    cases, counts, geometry_checks = {}, Counter(), []
    with Path(stream_path).open('rb') as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as full:
            if hashlib.sha256(full).hexdigest() != inventory['source_sha256']:
                raise ValueError('Stream differs from inventoried input')
            for model in inventory['rejected']:
                if 'triangle' not in model['reason'].lower():
                    continue
                # Absolute source alignment matters for native aligned leaves.
                start, end = model['offset'], model['offset'] + model['bytes']
                # Preserve native 16/32-byte alignment without copying the stream.
                prefix = start % 32
                diagnostic_data = bytes(prefix) + bytes(full[start:end])
                check = dict(section=model['section'], offset=start, hash=model['hash'])
                try:
                    recovered, diagnostic = diagnose_model(diagnostic_data, prefix, len(diagnostic_data))
                    check.update(status='consumed_checks_pass', diagnostic=diagnostic,
                                 positions=len(recovered['positions']), faces=len(recovered['faces']))
                    zero_area = 0
                    for face in recovered['faces']:
                        a, b, c = [recovered['positions'][v[0]] for v in face['corners']]
                        u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
                        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                        zero_area += all(value == 0 for value in cross)
                    check['zero_area_faces_with_distinct_position_indices'] = zero_area
                except ValueError as error:
                    check.update(status='rejected', reason=str(error))
                geometry_checks.append(check)
                parts = {k: (start+a, start+b) for k, a, b in chunks(full[start:end])}
                a, b = parts[0x80134100]
                leaves = {k: (a+c, a+d) for k, c, d in chunks(full[a:b])}
                table = (leaves[0x134801][0] + 15) & ~15
                blob = (leaves[0x134802][0] + 31) & ~31
                for index, draw in enumerate(model['draws']):
                    descriptor = bytes(full[table+16*index:table+16*(index+1)])
                    flags, count = descriptor[12], descriptor[8]
                    width = 3 + bool(flags & 16) + bool(flags & 4) + bool(flags & 2)
                    compiled = bool(flags & 128 and draw['bytes'])
                    size = draw['bytes'] if compiled else count * width
                    packet_start = blob + draw['offset']
                    if packet_start + size > leaves[0x134802][1]:
                        raise ValueError('Packet exceeds original geometry leaf')
                    packet = bytes(full[packet_start:packet_start+size])
                    key = hashlib.sha256(descriptor[4:] + packet).hexdigest()
                    counts['draw_occurrences'] += 1
                    if key in cases:
                        continue
                    emitted = emit_original(dol, descriptor, packet)
                    if compiled:
                        if emitted['display_lists'] != [packet] or emitted['begin'] or emitted['fifo']:
                            raise ValueError('Compiled original emission mismatch')
                        if packet[0] & 0xF8 != 0x98 or struct.unpack_from('>H', packet, 1)[0] != count:
                            raise ValueError('Unexpected original compiled primitive')
                    elif emitted['fifo'] != packet or emitted['begin'] != [[0x98, 0, count]]:
                        raise ValueError('Raw original FIFO mismatch')
                    cases[key] = dict(flags=flags, format=descriptor[13], vertices=count,
                                      compiled=compiled, bytes=size)
                counts['model_occurrences'] += 1
    return dict(dol_sha256=DOL_SHA256, stream_sha256=inventory['source_sha256'],
                original_entry='8011773c', original_stop='801181c0',
                counts=dict(counts), unique_packet_cases=len(cases),
                geometry_checks=geometry_checks,
                geometry_summary=dict(Counter(c['status'] for c in geometry_checks)),
                case_classes=dict(Counter(f"{c['format']}:{c['flags']:02x}:{'list' if c['compiled'] else 'raw'}"
                                          for c in cases.values())),
                conclusion='Original index emission and listed consumed-geometry checks verified; '
                           'header triangle-count discrepancy retained. '
                           'This does not establish materials, LOD selection or placement.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'stream', 'dol', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = verify(args.inventory, args.stream, args.dol)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
