#!/usr/bin/env python3
"""Pack original static frontend camera/placement outputs, without executable data."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

HASHES = {
    'dol': '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166',
    'elf': '6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7',
    'attributes': '5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c',
    'frontend': 'adbb364d58f348ee95d2b59e99d0312b1bd8079d77be7bc76bd40461ee2cc9c2',
}


def build_frontend_scene(report):
    if report['schema'] != 1 or report['source_sha256'] != HASHES:
        raise ValueError('Frontend reference source identity differs')
    cameras = report['cameras']
    placements = sorted(report['placement'].values(), key=lambda x: x['garage_type'])
    if len(cameras) != 18 or [p['garage_type'] for p in placements] != list(range(1, 6)):
        raise ValueError('Unexpected source frontend coverage')
    out = bytearray(2240)
    struct.pack_into('<4s9I', out, 0, b'NFP1', 1, len(out), 0, 18, 192, 96, 5, 1920, 64)
    for i, value in enumerate(HASHES.values()):
        out[40+i*32:72+i*32] = bytes.fromhex(value)
    keys = set()
    for i, (name, c) in enumerate(sorted(cameras.items())):
        encoded = name.encode('ascii')
        if not encoded or len(encoded) >= 48 or any(not (chr(v).islower() or chr(v).isdigit() or v == 95) for v in encoded):
            raise ValueError('Invalid source camera name')
        key = int(c['collection_key'], 16)
        values = c['eye_source']+c['target_source']+c['up_source']+[c['fov_degrees']]
        if len(values) != 10 or not all(math.isfinite(x) for x in values) or not 1 < values[-1] < 179 or not key or key in keys:
            raise ValueError('Invalid source camera values')
        keys.add(key)
        struct.pack_into('<48s10fII', out, 192+i*96, encoded, *values, key, 0)
    for i, p in enumerate(placements):
        rotation = p.get('car_rotation_xyz_degrees', p.get('car_relative_rotation_xyz_degrees'))
        values = p['geometry_position_source']+[p['geometry_rotation_z_degrees']]+rotation+[p['body_height_bias']]
        if len(values) != 8 or not all(math.isfinite(x) for x in values):
            raise ValueError('Invalid source placement values')
        if p['car_position_source']['x'] or p['car_position_source']['y']:
            raise ValueError('Nonzero carXY provider needs separate representation')
        struct.pack_into('<I8f', out, 1920+i*64, i+1, *values)
    struct.pack_into('<I', out, 12, zlib.crc32(out[16:]))
    return bytes(out)


def build_frontend_stances(attributes, models):
    """Original stock FE providers: ecar TireOffsets and FECompressions.

    LookupWheelRadius802c7a24 reads TireOffsets.w; LookupWheelPosition802c7964
    copies XYZ and adds FECompressions[wheel>>1] to Z. This deliberately does
    not substitute the distinct physical TIRES/chassis dimensions.
    """
    from vehicle_attributes import VehicleAttributes
    from vehicle_vlt_hash import vlt_hash
    if hashlib.sha256(attributes).hexdigest() != HASHES['attributes']:
        raise ValueError('Frontend stance source identity differs')
    db = VehicleAttributes(attributes, ('TireOffsets', 'FECompressions'))
    def f32(x):
        return struct.unpack('<f', struct.pack('<f', x))[0]
    results, provenance = {}, {}
    for model, key in models.items():
        row = db.collections[(vlt_hash('ecar'), key)]
        tire_field = db.field_value(row, 'TireOffsets')
        compression_field = db.field_value(row, 'FECompressions')
        tires = tire_field['value']['values']
        compressions = compression_field['value']['values']
        if len(tires) != 4 or len(compressions) != 2:
            raise ValueError('Incomplete actual frontend wheel providers ' + model)
        radius_sum, mount_sum = 0.0, 0.0
        for i, wheel in enumerate(tires):
            if len(wheel) != 4 or not all(math.isfinite(v) for v in wheel) or wheel[3] <= 0:
                raise ValueError('Invalid actual frontend wheel provider ' + model)
            mount_z = f32(wheel[2]+compressions[i>>1])
            radius_sum = f32(radius_sum+wheel[3])
            mount_sum = f32(mount_sum+mount_z)
        # Original fmsubs uses a power-of-two multiplier. Binary64 computes
        # this exact finite-f32 subtraction before the one f32 rounding.
        height = f32(f32(radius_sum*.25-f32(mount_sum*.25)) + f32(-.025))
        data = struct.pack('<4sfI', b'NFG1', height, key)
        results[model] = data+struct.pack('<I', zlib.crc32(data))
        provenance[model] = {'ecar_key': f'{key:08x}', 'height': height,
                             'stock_fields': {'TireOffsets': tire_field,
                                              'FECompressions': compression_field},
                             'limit': 'Actual stock ecar providers; custom ride/part substitutions remain external'}
    return results, provenance


def verify_stances_original(attributes, dol, models):
    """Compare the final original FE reduction fragment, without patching code.

    The caller-owned TireOffsets/FECompressions producers are decoded above.
    Their ordered sums are the explicit entry state of803a5af8..803a5b34.
    This is not a whole FrontEndRenderingCar lifecycle comparison.
    """
    from map_recovery_contact_reference import OriginalContactReference
    from unicorn import ppc_const as r
    if hashlib.sha256(dol).hexdigest() != HASHES['dol']:
        raise ValueError('Frontend stance executable differs')
    results, provenance = build_frontend_stances(attributes, models)
    reference = OriginalContactReference(dol, None)
    reference.extra_allowed = ((0x803a5af8, 0x803a5b34),)
    def f32(x):
        return struct.unpack('<f', struct.pack('<f', x))[0]
    for name, record in provenance.items():
        tires = record['stock_fields']['TireOffsets']['value']['values']
        compressions = record['stock_fields']['FECompressions']['value']['values']
        radius_sum, mount_sum = 0.0, 0.0
        for i, wheel in enumerate(tires):
            radius_sum = f32(radius_sum+wheel[3])
            mount_sum = f32(mount_sum+f32(wheel[2]+compressions[i>>1]))
        reference.putfloating(29, radius_sum)
        reference.putfloating(30, mount_sum)
        reference.u.reg_write(r.UC_PPC_REG_1, 0x7000ff00)
        reference.u.reg_write(r.UC_PPC_REG_27, 0x60000000)
        reference.u.emu_start(0x803a5af8, 0x803a5b34, count=100)
        actual = bytes(reference.u.mem_read(0x7000ff60, 4))
        expected = results[name][4:8][::-1]
        if actual != expected:
            raise AssertionError((name, actual.hex(), expected.hex()))
    return {'source_fragment': '803a5af8..803a5b34', 'cases': len(models),
            'bit_mismatches': 0, 'limits': 'Final reduction with actual decoded stock FE wheel sums; not full rendering-car lifecycle'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    result = build_frontend_scene(json.loads(a.reference.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(result)
    print(json.dumps({'bytes': len(result), 'sha256': hashlib.sha256(result).hexdigest(), 'cameras': 18, 'placements': 5}))


if __name__ == '__main__':
    main()
