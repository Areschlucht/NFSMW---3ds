#!/usr/bin/env python3
"""Export actual stock source NVRs and BND bindings for every concrete pvehicle.

No generated physical values or fallback model mappings. Unsupported profiles are
reported with their exact rejection; original assets and native outputs stay private.
"""
import argparse
import hashlib
import json
from pathlib import Path

from build_vehicle_runtime import export as export_runtime
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
from vehicle_verify_original import ATTR_SHA
from world_collision_response_shapes import body_packages

BANK_SHA = 'da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'


def build(attributes, dol, bundle, output):
    source = attributes.read_bytes()
    bank = bundle.read_bytes()
    if hashlib.sha256(source).hexdigest() != ATTR_SHA or hashlib.sha256(bank).hexdigest() != BANK_SHA:
        raise ValueError('Unknown source attributes/collision bundle')
    db = VehicleAttributes(source)
    packages = {p['key']: p for p in body_packages(bank)}
    output.mkdir(parents=True, exist_ok=True)
    body_report = {'bundle': str(bundle), 'bundle_sha256': BANK_SHA, 'profiles': {}}
    manifest = {'schema': 1, 'attributes_sha256': ATTR_SHA, 'collision_bundle_sha256': BANK_SHA,
                'profiles': {}, 'rejected': [], 'model_defaults': {},
                'limits': ['Stock component upgrade index zero only',
                           'NVR presence does not activate source body/world/handling',
                           'Nonempty source RPM limiter is not implemented by engine driver']}
    rows = []
    for (kind, key), row in db.collections.items():
        if kind != vlt_hash('pvehicle'):
            continue
        name = db.label(key)
        fields = db.fields(row)
        model = fields.get('MODEL', {}).get('value', {}).get('text', '')
        if not model:
            continue
        usable = bool(fields.get('PlayerUsable', {}).get('value'))
        try:
            package = packages[vlt_hash(model)]
            bound = package['bounds'][0]
            binding = db.field_value(row, 'rigidbodyspecs')
            ref = binding['value']
            spec = db.collections[(ref['class_key'], ref['collection_key'])]
            entry = {'model_name': model, 'model_key': f'{package["key"]:08x}',
                     'physical_halfextent_mm': bound['half_extents_raw'],
                     'bound_package_offset': package['source_offset'],
                     'bound_package_sha256': package['source_sha256'],
                     'root_offset': bound['source_offset'],
                     'mass': db.field_value(row, 'MASS'), 'tensor_scale': db.field_value(row, 'TENSOR_SCALE'),
                     'rigidbodyspecs': binding, 'local_cg': db.field_value(spec, 'CG'),
                     'gravity': db.field_value(spec, 'GRAVITY'),
                     'collision_box_pad': db.field_value(spec, 'COLLISION_BOX_PAD')}
            body_report['profiles'][name] = entry
            rows.append((name, key, model, usable, package))
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            manifest['rejected'].append({'profile': name, 'physical_key': f'{key:08x}',
                'model': model, 'player_usable': usable, 'reason': f'{type(exc).__name__}: {exc}'})
    report_path = output/'body-parameters.json'
    report_path.write_text(json.dumps(body_report, indent=2)+'\n')
    levels = dict.fromkeys(('engine', 'transmission', 'induction', 'nos', 'tires', 'brakes', 'chassis'), 0)
    for name, key, model, usable, package in rows:
        try:
            data, report = export_runtime(attributes, dol, report_path, bundle, name, levels)
            (output/(name+'.nvr')).write_bytes(data)
            (output/(name+'.ndp')).write_bytes(data[128:464])
            (output/(name+'.mmp')).write_bytes(data[464:620])
            start, size = package['source_offset'], package['source_bytes']
            bnd = bank[start:start+size]
            (output/(model.lower()+'.bnd')).write_bytes(bnd)
            (output/(name+'.json')).write_text(json.dumps(report, indent=2)+'\n')
            limiter = report['fields']['engine/SPEED_LIMITER']['value']
            count = len(limiter.get('values', [])) if isinstance(limiter, dict) else len(limiter)
            manifest['profiles'][name] = {'model': model, 'physical_key': f'{key:08x}',
                'model_key': f'{package["key"]:08x}', 'player_usable': usable,
                'runtime_file': name+'.nvr', 'runtime_sha256': hashlib.sha256(data).hexdigest(),
                'collision_file': model.lower()+'.bnd', 'collision_sha256': hashlib.sha256(bnd).hexdigest(),
                'engine_audio_supported': count == 0, 'rpm_limiter_count': count}
            # Exact name==MODEL spelling is an actual base binding; no nearest or
            # "first matching vehicle" selection for challenge/profile variants.
            if name == model.lower():
                manifest['model_defaults'][model] = name
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            manifest['rejected'].append({'profile': name, 'physical_key': f'{key:08x}',
                'model': model, 'player_usable': usable, 'reason': f'{type(exc).__name__}: {exc}'})
    manifest['exported_profiles'] = len(manifest['profiles'])
    manifest['exported_player_usable'] = sum(r['player_usable'] for r in manifest['profiles'].values())
    manifest['rejected_count'] = len(manifest['rejected'])
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('attributes', 'dol', 'bundle', 'output'):
        parser.add_argument('--'+field, type=Path, required=True)
    args = parser.parse_args()
    result = build(args.attributes, args.dol, args.bundle, args.output)
    print(json.dumps({k: result[k] for k in ('exported_profiles', 'exported_player_usable', 'rejected_count')}))


if __name__ == '__main__':
    main()
