#!/usr/bin/env python3
"""Stage privately converted opening-career inputs; never make a release ZIP.

Only known native formats are copied. Existing player save files and executables
are left untouched and excluded from the manifest. A stale executable from the
base preview is deliberately not copied. Run again after profile regeneration.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import zlib
from build_frontend_scene import build_frontend_scene, build_frontend_stances

MODELS = ('COBALTSS', 'GTI', 'IS300', 'PUNTO', 'TRAFHA', 'COPMIDSIZE',
          'MUSTANGGT', 'SUPRA', 'SLR', 'GTO', 'IMPREZAWRX', 'RX8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def catalog_rows(data):
    if len(data) < 256:
        raise ValueError('Truncated native vehicle catalog')
    magic, version, size, crc, count, at, stride, reserved = struct.unpack_from('<4s7I', data)
    if (magic, version, size, at, stride, reserved) != (b'NVC1', 1, len(data), 96, 160, 0):
        raise ValueError('Unsupported native vehicle catalog')
    if not 0 < count <= 128 or size != 96 + count * 160 or zlib.crc32(data[16:]) != crc:
        raise ValueError('Invalid native vehicle catalog extent/CRC')
    rows = {}
    for n in range(count):
        row = data[96+n*160:96+(n+1)*160]
        name = row[24:56].split(b'\0', 1)[0].decode('ascii')
        if not re.fullmatch(r'[A-Z0-9_]+', name) or name in rows:
            raise ValueError('Invalid/duplicate native vehicle ID')
        rows[name] = row
    return rows


def merge_catalogs(paths):
    rows = {}
    provenance = None
    for path in paths:
        data = path.read_bytes()
        current = catalog_rows(data)
        if provenance is not None and data[32:96] != provenance:
            raise ValueError('Vehicle attribute/part sources differ')
        provenance = data[32:96]
        for name, row in current.items():
            if name in rows and rows[name] != row:
                raise ValueError('Different catalog records for ' + name)
            rows[name] = row
    if set(rows) != set(MODELS):
        raise ValueError('Unexpected merged vehicle coverage: ' + repr(sorted(rows)))
    ecar = set()
    frontend = set()
    for row in rows.values():
        fe, ec = struct.unpack_from('<II', row)
        if not ec or ec in ecar or (fe and fe in frontend):
            raise ValueError('Ambiguous merged source collection key')
        ecar.add(ec)
        if fe:
            frontend.add(fe)
    output = bytearray(96) + b''.join(rows[n] for n in sorted(rows))
    struct.pack_into('<4s7I', output, 0, b'NVC1', 1, len(output), 0, len(rows), 96, 160, 0)
    output[32:96] = provenance
    struct.pack_into('<I', output, 12, zlib.crc32(output[16:]))
    return bytes(output), rows


def body_origin(body, scene, half):
    bounds = scene.get('source_bounds_viewer', scene.get('source_bounds'))
    if not bounds or len(bounds) != 2 or any(len(v) != 3 for v in bounds):
        raise ValueError('Missing source normalization bounds')
    center = [(bounds[0][a]+bounds[1][a])/2 for a in range(3)]
    actual_half = max(bounds[1][a]-bounds[0][a] for a in range(3))/2
    if not math.isclose(actual_half, half, rel_tol=1e-7, abs_tol=1e-7):
        raise ValueError('NFM normalization/profile extent differs')
    if 'center_viewer' in scene and any(abs(x-y)>1e-7 for x,y in zip(center,scene['center_viewer'])):
        raise ValueError('Source normalization center differs')
    magic,version,count,batches,textures,size,crc,reserved=struct.unpack_from('<4s7I',body)
    if magic!=b'NFM1' or version not in (1,2) or reserved or len(body)!=32+size or zlib.crc32(body[32:])!=crc:
        raise ValueError('Invalid normalized NFM source')
    stride=32 if version==1 else 48
    at=32+16*(batches+textures)
    if at+count*stride!=len(body):
        raise ValueError('Invalid normalized NFM extent')
    low=[float('inf')]*3;high=[-float('inf')]*3
    for n in range(count):
        xyz=struct.unpack_from('<3f',body,at+n*stride)
        for a in range(3):
            value=xyz[a]*half+center[a]
            low[a]=min(low[a],value);high[a]=max(high[a],value)
    if any(abs(low[a]-bounds[0][a])>1e-5 or abs(high[a]-bounds[1][a])>1e-5 for a in range(3)):
        raise ValueError('NFM source-bounds reconstruction differs')
    packet=struct.pack('<4sIIf3f',b'NVO1',1,crc,half,*center)
    return packet+struct.pack('<I',zlib.crc32(packet))


def stage(base, research, destination, attributes=None):
    planned = {}
    generated = {}
    generated['frontend-scene.nfp'] = build_frontend_scene(json.loads(
        (research/'menu-reference/frontend-source-placement.json').read_text()))

    def add(source, name):
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise ValueError('Missing/nonregular native asset: ' + str(source))
        if name in planned or name in generated:
            raise ValueError('Duplicate staging destination: ' + name)
        planned[name] = source

    def tree(source, target, pattern):
        files = sorted(source.glob(pattern))
        if not files:
            raise ValueError('No native assets matching ' + str(source / pattern))
        for p in files:
            add(p, target + '/' + p.name)

    for name in ('body.nfm', 'wheels.nwa', 'road.nrd', 'ui.nui',
                 'world-streaming.bin', 'world.mwp', 'world.nwc'):
        add(base/name, name)
    tree(base/'car-textures', 'car-textures', '*.t3x')
    origin_sources = {}
    bmw = research/'bmw/scene-v0.18-source-normals'
    if digest(base/'body.nfm') != digest(bmw/'body.nfm'):
        raise ValueError('BMW normalization metadata does not bind staged body')
    bmw_half = struct.unpack_from('<f', (base/'road.nrd').read_bytes(), 20)[0]
    generated['body.origin'] = body_origin((base/'body.nfm').read_bytes(),
        json.loads((bmw/'scene.json').read_text()), bmw_half)
    origin_sources['body.origin'] = {'source_scene_sha256': digest(bmw/'scene.json'),
                                   'source_body_sha256': digest(base/'body.nfm')}
    mapping = {
        'opening-career.nfc': 'opening-career/native-v3/opening-career.nfc',
        'events.nre': 'race-story/events-v3.nre',
        'free-roam.nfd': 'free-roam-destinations/free-roam.nfd',
        'destination-icons.nfi': 'free-roam-destinations/icons-v1/destination-icons.nfi',
        'menu-icons.nmi': 'menu-reference/icons-v1/menu-icons.nmi',
        'camera.ncp': 'menu-reference/source-camera-v1/camera.ncp',
        'frontend-top.nut': 'frontend-two-screen/native-v1/frontend-top.nut',
        'exploration.nws': 'free-roam-activation/exploration.nws',
        'career-bin15.nws': 'free-roam-activation/career-bin15.nws',
        'opening-nis.nni': 'opening-nis/native-camera-v2/opening-cameras.nis',
        'opening-nis-actors.nna': 'opening-nis/native-actors-v1/opening-nis-actors.nna',
        'opening-nis-actions.nac': 'opening-nis/native-actions-v1/opening-nis-actions.nac',
        'road-network.mwt': 'street-systems/native-v1/road-network.mwt',
        'opponents.nro': 'opening-opponents/native-v1/opening-opponents.nro',
        'pursuit.npp': 'opening-pursuit/native-v1/opening-pursuit.npp',
        'breakables.nbp': 'breakable-instances/native-v1/breakables.nbp',
        'speech/cellcall10.nvs': 'opening-story-services/cellcall10-v1.nvs',
    }
    for target, source in mapping.items():
        add(research/source, target)
    tree(research/'career-movies/native-v1', 'movies', '*.nvm')
    for base_name, source in [('intro', 'native-career-bin16'),
                              ('career', 'native-career-bin15'),
                              ('exploration', 'native-exploration')]:
        tree(research/'race-activation'/source, 'race-state/'+base_name, '*.nws')
    for scene in ('PLATFORMCRIB', 'CAREER_SAFEHOUSE', 'CAR_LOT',
                  'CUSTOMIZATION_SHOP', 'CUSTOMIZATION_SHOP_BACKROOM'):
        source = research/'menu-reference/platform-native-v1'/scene
        for name in ('platform.nfm', 'placement.bin'):
            add(source/name, 'platforms/'+scene+'/'+name)
        tree(source/'textures', 'platforms/'+scene+'/textures', '*.t3x')
    sources = [research/'starter-cars/native-v2',
               research/'opening-police-car/v1',
               research/'opening-opponent-assets/v1']
    catalog, rows = merge_catalogs([p/'catalog.nvc' for p in sources])
    generated['cars/catalog.nvc'] = catalog
    if attributes is None:
        attributes = Path('/workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN')
    stance_models = {name: struct.unpack_from('<I', row, 4)[0] for name, row in rows.items()}
    stance_models['BMWM3GTRE46'] = 0x4e085fb3
    stances, stance_provenance = build_frontend_stances(attributes.read_bytes(), stance_models)
    for name, data in stances.items():
        generated['body.stance' if name == 'BMWM3GTRE46' else 'cars/'+name+'/body.stance'] = data
        values = stance_provenance[name]['stock_fields']['FECompressions']['value']['values']
        tires = stance_provenance[name]['stock_fields']['TireOffsets']['value']['values']
        key = int(stance_provenance[name]['ecar_key'], 16)
        # Source LookupWheelPosition returns TireOffsetsXYZ with one fadds of
        # FECompressions[wheel>>1] to Z. Encode absolute desired stock mounts;
        # never add compression blindly to a legacy artwork-fitted NWA pivot.
        positions = []
        for i, tire in enumerate(tires):
            z = struct.unpack('<f', struct.pack('<f', tire[2]+values[i>>1]))[0]
            positions.extend((tire[0], tire[1], z))
        wheel_data = struct.pack('<4sI12fI', b'NFW2', key, *positions, 2)
        wheel_data += struct.pack('<I', zlib.crc32(wheel_data))
        generated['wheels.frontend' if name == 'BMWM3GTRE46' else 'cars/'+name+'/wheels.frontend'] = wheel_data
    for name in sorted(rows):
        parents = [p/name for p in sources if (p/name).is_dir()]
        if len(parents) != 1:
            raise ValueError('Ambiguous model source ' + name)
        source = parents[0]
        for asset in ('body.nfm', 'wheels.nwa'):
            add(source/asset, 'cars/'+name+'/'+asset)
        body_crc, wheel_crc = struct.unpack_from('<II', rows[name], 8)
        if struct.unpack_from('<I', (source/'body.nfm').read_bytes(), 24)[0] != body_crc:
            raise ValueError('Body CRC/catalog mismatch ' + name)
        if struct.unpack_from('<I', (source/'wheels.nwa').read_bytes(), 20)[0] != wheel_crc:
            raise ValueError('Wheel CRC/catalog mismatch ' + name)
        tree(source/'textures', 'cars/'+name+'/textures', '*.t3x')
        origin_name = 'cars/'+name+'/body.origin'
        generated[origin_name] = body_origin((source/'body.nfm').read_bytes(),
            json.loads((source/'scene.json').read_text()),struct.unpack_from('<f',rows[name],16)[0])
        origin_sources[origin_name] = {'source_scene_sha256': digest(source/'scene.json'),
                                     'source_body_sha256': digest(source/'body.nfm')}
    for suffix in ('ndp', 'mmp'):
        tree(research/'driving-runtime', 'physics', '*.'+suffix)
    tree(research/'driving-runtime-v2', 'physics', '*.nvr')
    tree(research/'vehicle-world', 'physics', '*.bnd')
    bindings = json.loads((research/'vehicle-world/manifest.json').read_text())
    profiles = {}
    for name, row in bindings['profiles'].items():
        if 'physics/'+row['file'] not in planned or 'physics/'+name+'.nvr' not in planned:
            raise ValueError('Missing complete native physics binding ' + name)
        profiles[name] = {'collision_file': row['file'],
                          'collision_model_key': row['model_key'],
                          'collision_sha256': row['sha256'],
                          'runtime_file': name+'.nvr'}
    generated['physics/vehicle-bindings.json'] = (json.dumps(
        {'schema': 1, 'profiles': profiles}, indent=2)+'\n').encode('ascii')

    # Validate the entire input plan before modifying the staging destination.
    manifest = []
    for name, source in sorted(planned.items()):
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Unsafe staging path ' + name)
        manifest.append({'path': name, 'bytes': source.stat().st_size,
                         'sha256': digest(source)})
    for name, data in sorted(generated.items()):
        manifest.append({'path': name, 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest()})
    destination.mkdir(parents=True, exist_ok=True)
    for name, source in sorted(planned.items()):
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and (target.is_symlink() or not target.is_file()):
            raise ValueError('Nonregular staging destination ' + str(target))
        expected = next(row for row in manifest if row['path'] == name)
        if target.exists() and target.stat().st_size == expected['bytes'] and digest(target) == expected['sha256']:
            continue
        pending = target.with_name(target.name+'.stage-pending')
        shutil.copyfile(source, pending)
        if digest(pending) != expected['sha256']:
            raise ValueError('Copy verification failed ' + name)
        pending.replace(target)
    for name, data in generated.items():
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        pending = target.with_name(target.name+'.stage-pending')
        pending.write_bytes(data)
        pending.replace(target)
    for row in manifest:
        if digest(destination/row['path']) != row['sha256']:
            raise ValueError('Staged validation failed ' + row['path'])
    result = {'schema': 1, 'purpose': 'private opening-career integration inputs; not a release',
              'files': sorted(manifest, key=lambda r: r['path']),
              'vehicle_ids': sorted(rows), 'normalization_provenance': origin_sources,
              'frontend_stance_provenance': stance_provenance,
              'file_count': len(manifest),
              'total_bytes': sum(row['bytes'] for row in manifest),
              'excluded': ['executables', 'player aliases and saves', 'original archives',
                           'original debug executable', 'PNG/source intermediates']}
    (destination/'integration-assets.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    project = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=project/'dist/v018-shipping-install/3ds/nfsmw-rockport')
    p.add_argument('--research', type=Path, default=Path('/workspace/port-research'))
    p.add_argument('--destination', type=Path,
                   default=project/'dist/career-integration-install/3ds/nfsmw-rockport')
    p.add_argument('--attributes', type=Path, help='Original USA ATTRIBUTES.BIN for actual stock frontend tire providers')
    args = p.parse_args()
    result = stage(args.base, args.research, args.destination, args.attributes)
    print(json.dumps({key: value for key, value in result.items() if key not in ('files', 'normalization_provenance', 'frontend_stance_provenance')}, indent=2))


if __name__ == '__main__':
    main()
