#!/usr/bin/env python3
"""Decode observed GC world strips; preserve baked TRN positions and UVs.

World draw formats 1 (float32 positions) and 32 (S16/256 positions) use
position/color/UV indices. This differs from the car's four/five-index layout.
Unresolved models are rejected with reasons, never silently repaired.
"""
import math
import struct
from nfs_rockport import chunks


def decode_model(data, start, end, *, allow_triangle_statistic_mismatch=False):
    """Decode source draw packets; optionally validate draws despite a differing header statistic.

    Original draw-loop evidence (8011773C..801181C0) does not consume the
    header triangle statistic. LOD does consume it, so its original bits are
    preserved in declared_triangles. Opt-in never bypasses descriptor, attribute,
    finite-position or stored-bounds checks and never changes source bytes.
    """
    def children(s, e):
        for k, a, b in chunks(data[s:e]):
            yield k, a + s, b + s
    parts = {k: (a, b) for k, a, b in children(start, end)}
    def need(kind):
        if kind not in parts:
            raise ValueError(f'Missing model chunk {kind:08x}')
        return parts[kind]
    hs, he = need(0x134011)
    h = (hs + 15) & ~15
    if h + 161 > he:
        raise ValueError('Short aligned model header')
    name = data[h + 160:he].split(b'\0')[0].decode('ascii')
    bounds = [struct.unpack_from('<3f', data, h + a) for a in (32, 48)]
    expected = struct.unpack_from('<H', data, h + 20)[0]
    ts, te = need(0x134012)
    if (te - ts) % 8:
        raise ValueError('Malformed texture references')
    textures = [struct.unpack_from('<I', data, at)[0] for at in range(ts, te, 8)]
    gs, ge = need(0x80134100)
    leaves = {k: (a, b) for k, a, b in children(gs, ge)}
    if not {0x134800, 0x134801, 0x134802} <= leaves.keys():
        raise ValueError('Missing geometry leaves')
    meta = (leaves[0x134800][0] + 15) & ~15
    table = (leaves[0x134801][0] + 15) & ~15
    blob = (leaves[0x134802][0] + 31) & ~31
    if meta + 28 > leaves[0x134800][1]:
        raise ValueError('Short geometry metadata')
    version, _, count = struct.unpack_from('>3H', data, meta)
    size, po, unused, co, uv = struct.unpack_from('>5I', data, meta + 8)
    if version != 22 or not count or table + count * 16 > leaves[0x134801][1] or blob + size > leaves[0x134802][1]:
        raise ValueError('Invalid geometry metadata/bounds')
    strips = []
    faces = []
    formats = set()
    for i in range(count):
        at = table + i * 16
        offset = struct.unpack_from('>I', data, at)[0]
        n, tex, flags, fmt = data[at + 8], data[at + 10], data[at + 12], data[at + 13]
        length = struct.unpack_from('>H', data, at + 14)[0]
        if fmt not in (1, 32) or flags & ~0x96 or n < 3 or tex >= len(textures):
            raise ValueError('Unsupported world draw descriptor')
        widths = [2 if flags & bit else 1 for bit in (16, 4, 2)]
        prefix = 3 if flags & 128 else 0
        if offset + length > size or prefix + n * sum(widths) > length:
            raise ValueError('Strip exceeds geometry data')
        p = blob + offset
        if prefix and (data[p] & 0xf8 != 0x98 or struct.unpack_from('>H', data, p + 1)[0] != n):
            raise ValueError('Unsupported display-list primitive/count')
        p += prefix
        corners = []
        for j in range(n):
            corner = []
            for width in widths:
                corner.append(int.from_bytes(data[p:p + width], 'big'))
                p += width
            corners.append(corner)
        formats.add(fmt)
        for j in range(n - 2):
            a, b, c = corners[j:j + 3]
            if j % 2:
                a, b = b, a
            if len({a[0], b[0], c[0]}) == 3:
                faces.append(dict(corners=[a, b, c], texture=f'{textures[tex]:08x}'))
        strips.append(corners)
    if len(formats) != 1:
        raise ValueError('Mixed position representations')
    if len(faces) != expected and not allow_triangle_statistic_mismatch:
        raise ValueError(f'Triangle count mismatch: decoded {len(faces)}, header {expected}')
    npos = max(c[0] for strip in strips for c in strip) + 1
    ncolor = max(c[1] for strip in strips for c in strip) + 1
    nuv = max(c[2] for strip in strips for c in strip) + 1
    floating = formats == {1}
    stride = 12 if floating else 6
    if not po + npos * stride <= co or not co + ncolor * 4 <= uv or uv + nuv * 4 > size:
        raise ValueError('Attribute arrays overlap/exceed blob')
    positions = [struct.unpack_from('>3f' if floating else '>3h', data, blob + po + i * stride) for i in range(npos)]
    if not floating:
        positions = [tuple(v / 256 for v in p) for p in positions]
    if not all(math.isfinite(v) and abs(v) < 1e7 for p in positions for v in p):
        raise ValueError('Invalid decoded position')
    if not all(bounds[0][a] - .05 <= p[a] <= bounds[1][a] + .05 for p in positions for a in range(3)):
        raise ValueError('Decoded positions exceed stored bounds')
    texcoords = [tuple(v / 4096 for v in struct.unpack_from('>2h', data, blob + uv + i * 4)) for i in range(nuv)]
    # The fourth source byte also carries material/night-light information;
    # it is not used as transparency without that material system.
    colors = [tuple(v / 255 for v in data[blob + co + i * 4:blob + co + i * 4 + 3]) + (1.0,)
              for i in range(ncolor)]
    return dict(declared_triangles=expected, emitted_position_index_triangles=len(faces),
                triangle_statistic_mismatch=len(faces)!=expected, name=name, hash=f'{struct.unpack_from("<I", data, h + 16)[0]:08x}',
                positions=positions, texcoords=texcoords, colors=colors, faces=faces, bounds=bounds,
                matrix=struct.unpack_from('<16f', data, h + 64))


def decode(data, select=lambda name: name.startswith('TRN_'), *, allow_triangle_statistic_mismatch=False):
    models, rejected = [], []
    for kind, start, end in chunks(data):
        if kind != 0x80134000:
            continue
        for k, a, b in chunks(data[start:end]):
            if k != 0x80134010:
                continue
            a, b = a + start, b + start
            parts = {k: (a + s, a + e) for k, s, e in chunks(data[a:b])}
            if 0x134011 not in parts:
                raise ValueError('Model lacks header')
            hs, he = parts[0x134011]
            h = (hs + 15) & ~15
            if h + 161 > he:
                raise ValueError('Short aligned model header')
            name = data[h + 160:he].split(b'\0')[0].decode('ascii')
            if not select(name):
                continue
            try:
                models.append(decode_model(data, a, b, allow_triangle_statistic_mismatch=allow_triangle_statistic_mismatch))
            except ValueError as error:
                rejected.append(dict(name=name, offset=a, reason=str(error)))
    return models, rejected
