#!/usr/bin/env python3
"""Strictly decode observed MW GC original collision CARP assets/instances.

This recovers source geometry/metadata, not the complete original collision
response. Raw masks, orientation bits, instance transforms and material hashes
are retained. It does not synthesize collision from rendered bounding boxes.
See map-collision research for executable addresses and unresolved semantics.
"""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from nfs_rockport import chunks


def _finite(values, label):
    if not all(math.isfinite(v) for v in values):
        raise ValueError(f'Nonfinite {label}')


def decode_asset(data, start, end, local_index):
    if end - start < 16:
        raise ValueError('Short collision asset header')
    nodes, mesh_bytes, walls, wall_bytes, fixed, material_count, material_bytes, token = struct.unpack_from('>4H2BHI', data, start)
    used = 16 + mesh_bytes + wall_bytes + material_bytes
    if fixed or wall_bytes != walls * 32 or material_bytes != material_count * 4 or ((used + 63) & ~63) != end - start:
        raise ValueError('Unsupported collision asset layout/fixup state')
    if nodes * 16 > mesh_bytes:
        raise ValueError('Collision node table exceeds mesh bank')
    materials = list(struct.unpack_from(f'>{material_count}I', data, start + 16 + mesh_bytes + wall_bytes))
    parts = []
    for index in range(nodes):
        at = start + 16 + index * 16
        center = struct.unpack_from('>3f', data, at)
        radius_raw, relative = struct.unpack_from('>2H', data, at + 12)
        _finite(center, 'collision node center')
        if relative < nodes * 16 or relative + 24 > mesh_bytes:
            raise ValueError('Collision strip pointer exceeds mesh bank')
        strip = start + 16 + relative
        count = struct.unpack_from('>H', data, strip + 6)[0]
        flags = struct.unpack_from('>H', data, strip + 14)[0]
        if count < 3 or relative + count * 8 > mesh_bytes or flags & ~3:
            raise ValueError('Unsupported collision strip count/flags')
        vertices = []
        triangles = []
        for vertex in range(count):
            q = strip + vertex * 8
            packed = struct.unpack_from('>3h', data, q)
            point = [center[a] + packed[a] / 128 for a in range(3)]
            # The original broad-phase radius is rounded down in 1/16 units.
            if math.hypot(packed[0], packed[2]) / 128 > (radius_raw + 1) / 16 + .0001:
                raise ValueError('Collision vertex exceeds encoded radius quantum')
            vertices.append(point)
            if vertex >= 2:
                material_index, attributes = data[q + 6:q + 8]
                if material_index >= material_count:
                    raise ValueError('Collision triangle material outside local table')
                triangles.append(dict(corners=[vertex - 2, vertex - 1, vertex],
                                      material_index=material_index, attributes=attributes))
        parts.append(dict(center=list(center), radius_raw=radius_raw, radius=radius_raw / 16,
                          strip_offset=relative, flags=flags, vertices=vertices, triangles=triangles))
    wall_records = []
    for index in range(walls):
        at = start + 16 + mesh_bytes + index * 32
        a = struct.unpack_from('>3f', data, at)
        b = struct.unpack_from('>3f', data, at + 16)
        inverse = struct.unpack_from('>f', data, at + 28)[0]
        material_index, flags, unknown = struct.unpack_from('>2BH', data, at + 12)
        _finite((*a, *b, inverse), 'collision wall')
        length = math.hypot(b[0] - a[0], b[2] - a[2])
        if length <= 0 or inverse <= 0 or abs(inverse - 1 / length) > max(1e-5, inverse * 1e-5):
            raise ValueError('Collision wall inverse-length mismatch')
        if material_index >= material_count:
            raise ValueError('Collision wall material outside local table')
        wall_records.append(dict(endpoint_a=list(a), endpoint_b=list(b),
                                 inverse_horizontal_length=inverse, material_index=material_index,
                                 flags=flags, unknown_u16=unknown))
    return dict(index=local_index, source_offset=start, source_bytes=end - start,
                source_sha256=hashlib.sha256(data[start:end]).hexdigest(), raw_token=token,
                materials=materials, parts=parts, walls=wall_records)


def decode_package(data, start, end):
    aligned = (start + 15) & ~15
    if aligned + 48 > end or any(v != 0x11 for v in data[start:aligned]):
        raise ValueError('Invalid collision package alignment/header')
    root_bytes, identifier, fixed, runtime_pointer = struct.unpack_from('<4I', data, aligned)
    root = aligned + 16
    if fixed or runtime_pointer or identifier >= 2700 or root + root_bytes != end:
        raise ValueError('Unsupported collision package wrapper')
    if data[root:root + 16] != b'CARPP\0\0\1' + struct.pack('>II', 0, 1):
        raise ValueError('Unsupported collision CARP version')
    if data[root + 16:root + 24] != b'ArtiH\0\0\0':
        raise ValueError('Missing collision Arti directory')
    count, one = struct.unpack_from('>2I', data, root + 24)
    directory_end = root + 32 + count * 16
    if not count or count > 1024 or one != 1 or directory_end > end:
        raise ValueError('Invalid collision directory count')
    entries = {}
    ranges = []
    for i in range(count):
        at = root + 32 + i * 16
        tag, packed_size, items, relative = struct.unpack_from('>4sIII', data, at)
        if tag in entries or not packed_size & 0x40000000:
            raise ValueError('Duplicate/nonrelative collision directory entry')
        size = packed_size & 0xffffff
        first = at + relative
        if first < directory_end or first > end or size > end - first:
            raise ValueError('Collision directory data outside package')
        entries[tag] = (first, first + size, items)
        if size:
            ranges.append((first, first + size))
    ranges.sort()
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError('Overlapping collision resources')
    assets = {}
    instances = []
    for tag, (first, stop, items) in entries.items():
        if tag == b'Name':
            continue
        if tag[:2] == b'ca':
            if items != 1:
                raise ValueError('Unsupported multi-item collision asset')
            index = int.from_bytes(tag[2:], 'big')
            assets[index] = decode_asset(data, first, stop, index)
        elif tag[:2] == b'ci':
            if stop - first != items * 64:
                raise ValueError('Invalid collision instance stride/count')
            for i in range(items):
                at = first + i * 64
                x = struct.unpack_from('>3f', data, at)
                z = struct.unpack_from('>3f', data, at + 32)
                translation = struct.unpack_from('>3f', data, at + 48)
                extents = [struct.unpack_from('>f', data, at + q)[0] for q in (12, 20, 44)]
                metric = struct.unpack_from('>f', data, at + 60)[0]
                _finite((*x, *z, *translation, *extents, metric), 'collision instance')
                if any(e < 0 for e in extents):
                    raise ValueError('Negative collision instance extent')
                asset = struct.unpack_from('>H', data, at + 26)[0]
                instances.append(dict(source_offset=at, basis_x=list(x), basis_z=list(z),
                                      world_to_local_translation=list(translation),
                                      extents=extents, metric_3c=metric, asset_index=asset,
                                      raw_10=struct.unpack_from('>I', data, at + 16)[0],
                                      raw_18=struct.unpack_from('>H', data, at + 24)[0],
                                      raw_pointer_1c=struct.unpack_from('>I', data, at + 28)[0]))
        else:
            raise ValueError(f'Unsupported collision resource tag {tag!r}')
    if any(i['asset_index'] not in assets for i in instances):
        raise ValueError('Collision instance refers to missing local asset')
    return dict(id=identifier, source_offset=start - 8, source_bytes=end - start + 8,
                assets=assets, instances=instances)


def packages(data):
    for kind, start, end in chunks(data):
        if kind == 0x3b801:
            yield decode_package(data, start, end)


def inventory(data):
    totals = Counter()
    rows = []
    materials = Counter()
    for package in packages(data):
        parts = sum(len(a['parts']) for a in package['assets'].values())
        walls = sum(len(a['walls']) for a in package['assets'].values())
        triangles = sum(len(p['triangles']) for a in package['assets'].values() for p in a['parts'])
        for a in package['assets'].values():
            materials.update(f'{key:08x}' for key in a['materials'])
        totals.update(packs=1, assets=len(package['assets']), instances=len(package['instances']),
                      quantized_parts=parts, triangle_candidates=triangles, wall_records=walls)
        rows.append(dict(id=package['id'], source_offset=package['source_offset'],
                         source_bytes=package['source_bytes'], assets=len(package['assets']),
                         instances=len(package['instances']), quantized_parts=parts,
                         triangle_candidates=triangles, wall_records=walls))
    return dict(source_sha256=hashlib.sha256(data).hexdigest(), totals=dict(totals),
                material_keys=dict(sorted(materials.items())), packages=rows,
                limitations='Original collision geometry/metadata only; query flags, full transform/reference and collision response are not yet implemented in the 3DS app.')




def instance_matrix(instance):
    """Original row-vector world→local matrix for the observed CI flag case.

    Original 0x802EDF84 constructs this matrix; 0x80193498 applies it.
    Unobserved low orientation flags take an original cross-product branch and
    are rejected here until that path is independently referenced.
    """
    if instance['raw_10'] & 3:
        raise ValueError('Unreferenced collision instance orientation flags')
    x, z, t = (instance[k] for k in ('basis_x', 'basis_z', 'world_to_local_translation'))
    values = [*x, 0.0, 0.0, 1.0, 0.0, 0.0, *z, 0.0, *t, 1.0]
    _finite(values, 'collision instance matrix')
    return values


def transform_point(point, matrix):
    """Apply row-vector affine matrix; this is world→local for CI matrices."""
    if len(point) != 3 or len(matrix) != 16 or list(matrix[3::4]) != [0, 0, 0, 1]:
        raise ValueError('Invalid affine transform')
    _finite((*point, *matrix), 'affine transform input')
    return [sum(point[k] * matrix[k * 4 + axis] for k in range(3)) + matrix[12 + axis]
            for axis in range(3)]


def inverse_affine(matrix):
    """Invert an affine row matrix, including scale/reflection; never negate T alone."""
    transform_point([0, 0, 0], matrix)
    a, b, c = matrix[0:3]
    d, e, f = matrix[4:7]
    g, h, i = matrix[8:11]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if not math.isfinite(determinant) or determinant == 0:
        raise ValueError('Singular collision instance transform')
    inverse = [(e*i-f*h)/determinant, (c*h-b*i)/determinant, (b*f-c*e)/determinant, 0,
               (f*g-d*i)/determinant, (a*i-c*g)/determinant, (c*d-a*f)/determinant, 0,
               (d*h-e*g)/determinant, (b*g-a*h)/determinant, (a*e-b*d)/determinant, 0,
               0, 0, 0, 1]
    inverse[12:15] = [-sum(matrix[12+k] * inverse[k*4+axis] for k in range(3)) for axis in range(3)]
    _finite(inverse, 'inverse collision matrix')
    return inverse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        report = inventory(args.stream.read_bytes())
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    except (OSError, ValueError, struct.error) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(report['totals'], sort_keys=True))
