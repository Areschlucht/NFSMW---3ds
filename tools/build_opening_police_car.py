#!/usr/bin/env python3
"""Prepare the actual COPMIDSIZE Damage0 exterior and source police artwork.

Uses the strict starter-car texture/catalog helpers; never relabels a traffic
car or creates police paint. Geometry selection is an explicit native adapter.
"""
import argparse
from collections import OrderedDict
import gzip
import json
from pathlib import Path
import shutil
import struct
import tempfile
import zlib

from build_starter_cars import (ATTR_SHA, PAINT_SOURCE_SHA, CarParts,
    VehicleAttributes, decode_part, existing_pixels, inspect_rig, native_textures,
    original_texture_bank, pack_catalog, sha, texture_binding, texture_hash,
    encode_rig)

CAR = 'COPMIDSIZE'
GEOMETRY_SHA = '16404230013ae6d7a1178faadef35bb6f590ccdb59fcc60be90b47346cea6818'
TEXTURES_SHA = '4fa0f637769d1ef721057741b688a8f5133aa25e4b7e5ff499a3f39bb1b2f4ad'


def original_models(args):
    candidates = json.loads((args.candidates / 'manifest.json').read_text())['entries']
    source = [r for r in candidates if r['candidate_name'] == f'CARS\\{CAR}\\GEOMETRY.BIN']
    if len(source) != 1 or source[0]['sha256'] != GEOMETRY_SHA:
        raise ValueError('Expected original COPMIDSIZE geometry source')
    source = source[0]
    raw = (args.candidates / source['file']).read_bytes()
    if sha(raw) != GEOMETRY_SHA:
        raise ValueError('Police geometry SHA differs')
    manifest = json.loads((args.meshes / 'manifest.json').read_text())
    selected = [r for r in manifest['records'] if r['candidate_name'] == source['candidate_name']]
    if len(selected) != 1 or selected[0]['rejected'] or selected[0]['source_sha256'] != GEOMETRY_SHA or selected[0]['selected_offline_lod'] != 'B':
        raise ValueError('Expected complete strict police B-LOD export')
    directory = args.meshes / f"{source['hash']}-{source['directory_record_offset']}"
    models = []
    for path in sorted(directory.glob('*.mesh.json.gz')):
        row = json.loads(gzip.decompress(path.read_bytes()))
        if not (row['name'].startswith(CAR + '_KIT00_DAMAGE0_') and row['name'].endswith('_B') or row['name'] == CAR + '_KIT00_FRONT_TIRE_B'):
            continue
        class PacketCache:
            def __init__(self):
                self.index = 0
            def verify(self, descriptor, packet, widths):
                cached = row['descriptor_parity_checks'][self.index]
                self.index += 1
                if sha(packet) != cached['source_sha256']:
                    raise ValueError('Original police descriptor packet changed')
                return cached
        cache = PacketCache()
        decoded = decode_part(raw, row['source_model_offset'], row['source_model_offset'] + row['source_model_bytes'], cache)
        if cache.index != len(row['descriptor_parity_checks']) or any(json.dumps(decoded[k], sort_keys=True) != json.dumps(row[k], sort_keys=True) for k in decoded):
            raise ValueError('Police mesh export differs from original source')
        row['mesh_export_sha256'] = sha(path.read_bytes())
        models.append(row)
    expected = {CAR + '_KIT00_DAMAGE0_' + name + '_B' for name in (
        'BODY', 'COP_LIGHTS', 'FRONT_BUMPER', 'FRONT_WINDOW', 'HOOD',
        'LEFT_BRAKELIGHT', 'LEFT_DOOR', 'LEFT_HEADLIGHT', 'LEFT_REAR_DOOR',
        'REAR_BUMPER', 'RIGHT_BRAKELIGHT', 'RIGHT_DOOR', 'RIGHT_HEADLIGHT',
        'RIGHT_REAR_DOOR', 'TRUNK')}
    expected.add(CAR + '_KIT00_FRONT_TIRE_B')
    if {r['name'] for r in models} != expected or len(models) != len(expected):
        raise ValueError('Incomplete or ambiguous original police exterior')
    return dict(selected[0], original_directory_entry=source), models


def build_police(args, db, shared):
    source, models = original_models(args)
    texsource, bank = original_texture_bank(args.candidates, CAR, shared)
    if texsource['sha256'] != TEXTURES_SHA:
        raise ValueError('Expected actual police texture source')
    for name in ('COPMIDSIZE_SKIN1', 'COPMIDSIZE_BADGING'):
        key = f'{texture_hash(name):08x}'
        if key not in bank or bank[key][0].get('source_sha256') != TEXTURES_SHA:
            raise ValueError('No original police skin/badging; no paint substitute allowed')
    ecar = db.find('ecar', 'copmidsize')
    offsets = db.field_value(ecar, 'TireOffsets')
    mounts = offsets['value']['values']
    if len(mounts) != 4:
        raise ValueError('Four original police wheel offsets required')
    tires = [m for m in models if m['name'] == CAR + '_KIT00_FRONT_TIRE_B']
    groups, parts = OrderedDict(), []

    def append(model, wheel=0, mount=None):
        side = 1 if mount and mount[1] > 0 else -1
        parts.append({'name': model['name'], 'wheel_group': wheel,
            'source_model_offset': model['source_model_offset'],
            'mesh_export_sha256': model['mesh_export_sha256']})
        for triangle in model['triangles']:
            corners = triangle['corners']
            strip = model['strips'][triangle['strip']]
            positions = [model['positions'][c[0]] for c in corners]
            a = [positions[1][i] - positions[0][i] for i in range(3)]
            b = [positions[2][i] - positions[0][i] for i in range(3)]
            if not sum(x*x for x in (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])):
                continue
            vertices = groups.setdefault((strip['texture_hash'], wheel), [])
            for p, c in zip(positions, corners):
                normal, uv = model['normals_s8_64'][c[1]], model['uv'][c[4]]
                if mount:
                    p = (mount[0]-side*p[0], mount[1]-side*p[1], mount[2]+p[2])
                    normal = (-side*normal[0], -side*normal[1], normal[2])
                vertices.append([p[0], p[2], -p[1], normal[0], normal[2], -normal[1], *uv, 1., 1., 1., 1.])
    for model in models:
        if model is not tires[0]:
            append(model)
    for i, mount in enumerate(mounts):
        append(tires[0], i+1, mount)
    rows = [v for group in groups.values() for v in group]
    low = [min(v[a] for v in rows) for a in range(3)]
    high = [max(v[a] for v in rows) for a in range(3)]
    half = max(high[a]-low[a] for a in range(3))/2
    center = [(low[a]+high[a])/2 for a in range(3)]
    if not 1 < half < 4:
        raise ValueError('Unsupported native police extent')
    out = args.output / CAR
    textures = out / 'textures'
    textures.mkdir(parents=True)
    keys = sorted({key for key, _ in groups})
    texture_records, texture_manifest = [], []
    for key in keys:
        # None deliberately makes any generated-paint branch fail; this source
        # has actual skin/badging and only source bank/lamp/window bindings.
        (record, image), binding = texture_binding(CAR, key, bank, None)
        if image.width < 8 or image.height < 8:
            raise ValueError('Source texture below target minimum')
        hist = image.getchannel('A').histogram()
        flags = (1 if any(hist[1:255]) else 0) | (2 if sum(hist[:255]) else 0)
        image.save(textures / (key + '.png'))
        texture_records.append((int(key, 16), image.width, image.height, flags))
        texture_manifest.append({'hash': key, 'name': record['name'], 'missing': False,
            'width': image.width, 'height': image.height, 'flags': flags,
            'rgba_sha256': sha(image.tobytes()), 'source': record, 'binding': binding})
    lookup = {key: i for i, key in enumerate(keys)}
    batches, wheel_groups, flat = [], [], []
    for (key, group), vertices in groups.items():
        batches.append((len(flat), len(vertices), lookup[key], 0))
        wheel_groups.append(group)
        for vertex in vertices:
            vertex[:3] = [(vertex[a]-center[a])/half for a in range(3)]
            flat.append(vertex)
    payload = b''.join(struct.pack('<4I', *r) for r in texture_records + batches)
    payload += b''.join(struct.pack('<12f', *v) for v in flat)
    body_crc = zlib.crc32(payload)
    body = struct.pack('<4s7I', b'NFM1', 2, len(flat), len(batches), len(keys), len(payload), body_crc, 0) + payload
    rig = encode_rig([{'pivot': [(m[0]-center[0])/half, (m[2]-center[1])/half, (-m[1]-center[2])/half],
                       'radius': m[3], 'front': i < 2} for i, m in enumerate(mounts)], wheel_groups, body_crc)
    inspect_rig(rig, len(batches), body_crc)
    (out / 'body.nfm').write_bytes(body)
    (out / 'wheels.nwa').write_bytes(rig)
    record = {'id': CAR, 'display_name': 'Police Cruiser', 'frontend_collection_key': '00000000',
        'ecar_collection_key': f'{ecar["key"]:08x}', 'half_extent': half,
        'vertices': len(flat), 'triangles': len(flat)//3, 'batches': len(batches),
        'body_crc': f'{body_crc:08x}', 'body_sha256': sha(body), 'wheel_rig_sha256': sha(rig),
        'source_bounds_viewer': [low, high], 'center_viewer': center, 'parts': parts,
        'textures': texture_manifest, 'source_geometry': source, 'source_textures': texsource,
        'wheel_mounts': offsets, 'ecar_source_collection': ecar,
        'limitations': ['Explicit native KIT00 Damage0 B-LOD exterior selection, not original full part/damage scheduler',
            'Separate driver/interior part omitted; this is the exterior police model',
            'Original front tire mesh is mounted four times at exact typed TireOffsets; complete hub/body height/rim transforms remain separate',
            'Actual original skin/badging and source texture pixels retained; no constant paint or generated police livery',
            'Intact default lamp selector flags0 only; flashing emergency lights, siren and original police AI are not implemented by this asset converter',
            'Display text Police Cruiser is a native readable label, not a recovered language string']}
    (out / 'scene.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('meshes', 'candidates', 'attributes', 'carparts', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--shared-textures', type=Path, action='append', required=True)
    parser.add_argument('--native-textures', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a new police output directory')
    raw = args.attributes.read_bytes()
    if sha(raw) != ATTR_SHA:
        raise ValueError('Expected pinned original ATTRIBUTES')
    db = VehicleAttributes(raw)
    parts = CarParts(args.carparts.read_bytes())
    if parts.sha256 != PAINT_SOURCE_SHA:
        raise ValueError('Expected pinned original carparts')
    shared = existing_pixels(args.shared_textures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    target = args.output
    temporary = Path(tempfile.mkdtemp(prefix='.police-build-', dir=target.parent))
    try:
        args.output = temporary
        record = build_police(args, db, shared)
        count = native_textures(temporary) if args.native_textures else 0
        summary = {'schema': 1, 'attributes_sha256': ATTR_SHA,
            'cars': [{key: record[key] for key in ('id', 'display_name', 'frontend_collection_key',
                'ecar_collection_key', 'half_extent', 'vertices', 'triangles', 'batches', 'body_crc',
                'body_sha256', 'wheel_rig_sha256', 'limitations')}],
            'source_rgba_to_native_textures_compared': count, 'textures_native': bool(count)}
        summary['native_catalog'] = pack_catalog(temporary, summary, parts.sha256)
        (temporary / 'catalog.json').write_text(json.dumps(summary, indent=2) + '\n')
        temporary.rename(target)
        print(json.dumps(summary, indent=2))
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    main()
