#!/usr/bin/env python3
"""Package the private exploration preview without saves or original archives."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile
import zlib

from package_rockport_v018 import validate_pack, sha
from wheel_rig import inspect_rig

ROOT = Path(__file__).resolve().parents[1]


def checked_sidecar(path, magic, crc_start):
    data = path.read_bytes()
    if (len(data) < crc_start or data[:4] != magic or
            struct.unpack_from('<I', data, 8)[0] != len(data) or
            struct.unpack_from('<I', data, 12)[0] != zlib.crc32(data[crc_start:])):
        raise ValueError(f'Invalid sidecar: {path.name}')
    return data


def package(a):
    base = a.install
    info = validate_pack(base / 'world.mwp')
    stream = bytes.fromhex(info['source_sha256'])
    metadata = (base / 'world-streaming.bin').read_bytes()
    collision = (base / 'world.nwc').read_bytes()
    state = checked_sidecar(a.assets / 'exploration.nws', b'NWS1', 16)
    destinations = checked_sidecar(a.assets / 'free-roam.nfd', b'NFD1', 16)
    checked_sidecar(a.assets / 'frontend-top.nut', b'NUT1', 96)
    checked_sidecar(a.assets / 'destination-icons.nfi', b'NFI1', 96)
    events = a.events.read_bytes()
    if (metadata[:4] != b'WST1' or collision[:4] != b'NWC1' or
            stream != metadata[64:96] or stream != collision[32:64] or
            stream != state[64:96] or state[96:128] != destinations[32:64] or
            events[:4] != b'NRE1' or events[64:96] != state[96:128]):
        raise ValueError('Source identity mismatch')
    road = (base / 'road.nrd').read_bytes()
    if (road[:4] != b'NRD1' or len(road) != 64 + struct.unpack_from('<I', road, 8)[0] * 36 or
            struct.unpack_from('<I', road, 12)[0] != zlib.crc32(road[64:])):
        raise ValueError('Road CRC/shape')
    body = (base / 'body.nfm').read_bytes()
    inspect_rig((base / 'wheels.nwa').read_bytes(), struct.unpack_from('<I', body, 12)[0],
                struct.unpack_from('<I', body, 24)[0])
    checked_sidecar(base / 'ui.nui', b'NUI2', 48)
    # Consume an installed runtime, which intentionally has no scene.json or
    # extraction-tool directory layout. The prior shipping manifest pins every
    # reused asset; NFM's own CRC/order selects the exact texture dependencies.
    magic, version, nv, nb, nt, size, crc, reserved = struct.unpack_from('<4s7I', body)
    stride = 32 if version == 1 else 48
    if (magic != b'NFM1' or version not in (1, 2) or reserved or not 0 < nt <= 128 or
            len(body) != size + 32 or size != nt * 16 + nb * 16 + nv * stride or
            zlib.crc32(body[32:]) != crc):
        raise ValueError('Invalid installed car scene')
    previous = json.loads((base / 'manifest.json').read_text())
    pinned = {row['path']: row for row in previous['files']}
    files = [(base / 'body.nfm', 'body.nfm')]
    for i in range(nt):
        key = struct.unpack_from('<I', body, 32 + i * 16)[0]
        name = f'car-textures/{key:08x}.t3x'
        files.append((base / name, name))
    files += [(base / n, n) for n in ('world.mwp', 'world-streaming.bin', 'world.nwc',
                                      'road.nrd', 'wheels.nwa', 'ui.nui')]
    for p, n in files:
        if n not in pinned or p.stat().st_size != pinned[n]['bytes'] or sha(p) != pinned[n]['sha256']:
            raise ValueError('Installed asset differs from its shipping manifest: ' + n)
    files += [(a.assets / n, n) for n in ('exploration.nws', 'free-roam.nfd',
                                         'frontend-top.nut', 'destination-icons.nfi')]
    files += [(a.events, 'events.nre'), (ROOT / 'EXPLORATION-PREVIEW.md', 'README.md')]
    for extension, magic in (('3dsx', b'3DSX'), ('smdh', b'SMDH')):
        p = a.binary.with_suffix('.' + extension)
        with p.open('rb') as f:
            if f.read(4) != magic:
                raise ValueError('Invalid application signature')
        files.append((p, 'nfsmw-rockport.' + extension))
    names = [n for _, n in files]
    if len(names) != len(set(names)) or any('alias' in n.lower() for n in names):
        raise ValueError('Duplicate path or test save')
    manifest = {
        'version': '0.18-exploration-preview', 'full_game': False,
        'whole_city_traversal_validated': False, 'playable_races': False,
        'shop_purchases': False, 'world': info,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'files': [{'path': n, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p, n in files],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p, n in files:
            z.write(p, '3ds/nfsmw-rockport/' + n)
        z.writestr('3ds/nfsmw-rockport/manifest.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(a.output) as z:
        if z.testzip():
            raise ValueError('ZIP CRC failure')
        for row in manifest['files']:
            with z.open('3ds/nfsmw-rockport/' + row['path']) as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() != row['sha256']:
                    raise ValueError('ZIP SHA mismatch')
    digest = sha(a.output)
    a.output.with_suffix('.zip.sha256').write_text(digest + '  ' + a.output.name + '\n')
    print(json.dumps({'zip': str(a.output), 'bytes': a.output.stat().st_size,
                      'sha256': digest, 'files': len(files) + 1}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('install', 'assets', 'events', 'binary', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    package(parser.parse_args())
