#!/usr/bin/env python3
"""Read original frontend camera records and execute their original static pose.

Private original ELF/DOL/VPAK and external pinned estimate reference are inputs.
No native replacement camera, guessed scene placement, or game assets are emitted.
The JSON is research evidence, not an executable runtime asset pack.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
from mw_debug_info import DebugInfo

LABELS = ('cam_angle', 'cam_damping', 'cam_anim_speed', 'cam_fov',
          'cam_lookat_x', 'cam_lookat_y', 'cam_lookat_z', 'cam_orbit_vertical',
          'cam_orbit_horizontal', 'cam_orbit_radius', 'cam_roll_angle', 'cam_periods')
SCREENS = ('mainmenu', 'career_master', 'quickrace_master', 'challengeseries',
           'option_master', 'mc_master', 'mycarsmanager', 'career_manager',
           'career_car_select', 'carlot_car_select', 'carlot_showcase')
GARAGES = ('main_fe', 'career_safehouse', 'customization_shop', 'backroom', 'car_lot')
PINNED = {
    'dol': '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166',
    'elf': '6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7',
    'attributes': '5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c',
    'frontend': 'adbb364d58f348ee95d2b59e99d0312b1bd8079d77be7bc76bd40461ee2cc9c2',
}


def checked(path, kind):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != PINNED[kind]:
        raise ValueError('Wrong original ' + kind)
    return data


def source_record(db, key):
    row = db.collections[(vlt_hash('frontend'), key)]
    return {name: db.field_value(row, name) for name in LABELS}


def extract(args):
    from drive_camera_reference import DriveReference
    from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
    from unicorn import UC_HOOK_CODE, ppc_const as r
    raw = checked(args.dol, 'dol')
    checked(args.elf, 'elf')
    base = VehicleAttributes(checked(args.attributes, 'attributes'))
    db = VehicleAttributes(checked(args.frontend, 'frontend'), LABELS, dependency=base)
    with DebugInfo(args.elf) as debug, DolphinFrsqrteReference(args.dolphin_reference) as oracle:
        source_layout = next(c for e in debug.find('frontend', tags={2, 19})
                             for c in debug.children(e) if c.name == '_LayoutStruct')
        layout = {m['name']: m['offset'] for m in debug.members(source_layout)}
        for name in LABELS:
            definition = db.classes[vlt_hash('frontend')]['fields'][vlt_hash(name)]
            if definition['offset'] != layout[name]:
                raise ValueError('Debug/schema layout disagrees for ' + name)
        ref = DriveReference(raw, oracle, args.elf)
        functions = ('CreateCameraMatrix__20SelectCarCameraMoverP8bMatrix4P19SelectCarCameraData',
                     'ComputeBankedUpVector__11CameraMoverP8bVector3N21Us',
                     'bSinCos__FPfT0Us', 'bSin__FUs', 'bCos__FUs',
                     'GetGarageType__9FEManager',
                     'GetCarRotationX__16GarageMainScreen',
                     'GetCarRotationY__16GarageMainScreen',
                     'GetCarRotationZ__16GarageMainScreen',
                     'GetGeometryZAngle__16GarageMainScreen',
                     'GetGeometryXPos__16GarageMainScreen',
                     'GetGeometryYPos__16GarageMainScreen',
                     'GetGeometryZPos__16GarageMainScreen')
        symbols = {name: debug.symbols(name)[0] for name in functions}
        ref.extra_allowed += tuple((s['address'], s['address']+s['size']) for s in symbols.values())
        ref.extra_allowed += ((0x8010ab28, 0x8010b704), (0x80329e28, 0x80329e5c))
        u = ref.u
        captures = []

        def hook(u, address, size, data):
            if address == 0x8010af38:  # Actual eCreateLookAtMatrix inputs.
                captures.append([list(struct.unpack('>3f', bytes(u.mem_read(
                    u.reg_read(r.UC_PPC_REG_0+i), 12)))) for i in (4, 5, 6)])

        u.hook_add(UC_HOOK_CODE, hook)
        def call(address, gprs):
            ref.provider_calls.clear()
            u.reg_write(r.UC_PPC_REG_1, 0x7000ff00)
            u.reg_write(r.UC_PPC_REG_LR, 0x6000fff0)
            for n, value in enumerate(gprs):
                u.reg_write(r.UC_PPC_REG_3+n, value)
            u.emu_start(address, 0x6000fff0, count=50000)
            if u.reg_read(r.UC_PPC_REG_PC) != 0x6000fff0 or ref.provider_calls:
                raise ValueError('Original FE matrix escaped static numeric path')

        names = set()
        screen_refs = {}
        for name in SCREENS:
            values = source_record(db, vlt_hash(name))
            key = values['cam_angle']['value']['collection_key']
            screen_refs[name] = {'camera': db.label(key), 'camera_key': f'{key:08x}',
                                 'reference': values['cam_angle']}
            if key:
                names.add(db.label(key))
        for garage in GARAGES:
            for phase in ('entry', 'final'):
                names.add('angle_'+phase+'_'+garage)
        cameras = {}
        for name in sorted(names):
            fields = source_record(db, vlt_hash(name))
            v = {name: field['value'] for name, field in fields.items()}
            packet = [v['cam_orbit_vertical'], v['cam_orbit_horizontal'],
                      v['cam_orbit_radius'], v['cam_roll_angle'], v['cam_fov'],
                      v['cam_lookat_x'], v['cam_lookat_y'], v['cam_lookat_z']]
            u.mem_write(0x60001000, struct.pack('>8f', *packet))
            captures.clear()
            call(0x800787ac, [0x60000000, 0x60001000])
            if len(captures) != 1:
                raise ValueError('Expected exactly one original look-at construction')
            eye, target, up = captures[0]
            cameras[name] = {
                'collection_key': f'{vlt_hash(name):08x}', 'fields': fields,
                'eye_source': eye, 'target_source': target, 'up_source': up,
                'eye_viewer': [eye[0], eye[2], -eye[1]],
                'target_viewer': [target[0], target[2], -target[1]],
                'up_viewer': [up[0], up[2], -up[1]],
                'fov_degrees': v['cam_fov'],
                'original_view_matrix': list(struct.unpack('>16f', bytes(u.mem_read(0x60000000, 64)))),
            }
        # The small original getters are direct source constants selected by
        # original eGarageType. Read their exact constant pools and publish the
        # recovered branch mapping, separate from camera numerical execution.
        def number(address):
            return struct.unpack('>f', ref.dol.read(address, 4))[0]
        placement = {}
        for index, garage in enumerate(GARAGES, 1):
            special = index == 5
            placement[garage] = {
                'garage_type': index,
                'geometry_rotation_z_degrees': number(0x803c7078 if index == 2 else
                    0x803c707c if index in (3,5) else 0x803c7080),
                'geometry_position_source': [number(0x803c7084),
                    number(0x803c708c if special else 0x803c7088), number(0x803c7090)],
                'car_rotation_xyz_degrees': [
                    number(0x803c7064 if special else 0x803c7060),
                    number(0x803c706c if special else 0x803c7068),
                    number(0x803c7074 if special else 0x803c7070)],
                'car_position_source': {'x': number(0x804390e4), 'y': number(0x804390e8),
                    'z_formula': 'fma(sum(tire_radius),0.25,-mean(wheel_mount_z))-0.02500000037252903'},
                'body_height_bias': number(0x803c70a4),
            }
        return {
            'schema': 1, 'source_sha256': PINNED,
            'evidence': 'Original static CreateCameraMatrix including rotation, banked up and look-at ran unmodified; no camera providers substituted',
            'functions': {name: {'address': f'{s["address"]:08x}', 'bytes': s['size']} for name,s in symbols.items()},
            'frontend_debug_layout': layout, 'screen_references': screen_refs,
            'camera_cases': len(cameras), 'cameras': cameras, 'placement': placement,
            'limits': ['Original animated transition/period/damping update not ported by this research tool',
                       'Car tire mount/radius providers must bind actual currently selected vehicle',
                       'Geometry header matrices and scene pass admission remain separate consumers',
                       'These are original full-screen GameCube camera records; two-screen UI adaptation is caller-owned'],
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dol', 'elf', 'attributes', 'frontend', 'dolphin-reference', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    report = extract(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'camera_cases': report['camera_cases'], 'screens':len(report['screen_references']),
                      'placement':report['placement'], 'output':str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
