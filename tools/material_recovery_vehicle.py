#!/usr/bin/env python3
"""Recover the observed MW USA GameCube intact-vehicle light alias selector.

The names in car geometry are runtime aliases. This reproduces the target-key
subset of original PPC routine 0x802CAA44, not vehicle state generation, damage
rendering, tint generation or the dynamic SKIN1 paint compositor. It deliberately
accepts the original flag words by field offset until their callers are mapped.
Optional reference checking runs only a checksum-pinned leaf routine in bounded
PowerPC emulation, never natively.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from vehicle_dol import DolImage

DOL_SHA256 = '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
HASH_VA = 0x80062ecc
SEEDED_HASH_VA = 0x80062efc
SELECTOR_VA = 0x802caa44
SELECTOR_BYTES = 0x802cae70 - SELECTOR_VA
LIGHT_FIELDS = {
    'HEADLIGHT_LEFT': 0x378, 'HEADLIGHT_RIGHT': 0x384,
    'BRAKELIGHT_LEFT': 0x390, 'BRAKELIGHT_RIGHT': 0x39c,
    'BRAKELIGHT_CENTRE': 0x3a8,
    'HEADLIGHT_GLASS_LEFT': 0x3b4, 'HEADLIGHT_GLASS_RIGHT': 0x3c0,
    'BRAKELIGHT_GLASS_LEFT': 0x3cc, 'BRAKELIGHT_GLASS_RIGHT': 0x3d8,
    'BRAKELIGHT_GLASS_CENTRE': 0x3e4,
}
SUFFIXES = ('_OFF', '_ON', '_DAMAGE0', '_GLASS_OFF', '_GLASS_ON', '_GLASS_DAMAGE0')


def uint32(value):
    if not isinstance(value, int) or not 0 <= value <= 0xffffffff:
        raise ValueError('Expected an unsigned 32-bit word')
    return value


def texture_hash(text, seed=0xffffffff):
    """Original 0x80062ECC/0x80062EFC: case-sensitive bytes, *33 + byte."""
    value = uint32(seed)
    try:
        raw = text.encode('ascii')
    except (AttributeError, UnicodeEncodeError) as error:
        raise ValueError('Texture name must be ASCII text') from error
    if b'\0' in raw:
        raise ValueError('Embedded NUL in texture name')
    for byte in raw:
        value = (value * 33 + byte) & 0xffffffff
    return value


def sources(car_name, headlight_seed=None, brakelight_seed=None):
    head = texture_hash(car_name + '_KIT00_HEADLIGHT')
    brake = texture_hash(car_name + '_KIT00_BRAKELIGHT')
    if headlight_seed is not None:
        head = uint32(headlight_seed) or head
    if brakelight_seed is not None:
        brake = uint32(brakelight_seed) or brake
    return ({suffix: texture_hash(suffix, head) for suffix in SUFFIXES},
            {suffix: texture_hash(suffix, brake) for suffix in SUFFIXES})


def light_targets(car_name, *, window_front_target, flags_1608=0, flags_160c=0,
                  force_side_lights=0, headlight_seed=None, brakelight_seed=None):
    """Target hashes written by the observed intact light-update routine.

    WINDOW_FRONT is its current resolved target, not necessarily the hash of
    that alias. Original code overrides headlight-glass targets with this value.
    TEXTURE_NAME part attributes can override either prefix seed.
    """
    uint32(window_front_target);uint32(flags_1608);uint32(flags_160c);uint32(force_side_lights)
    head, brake = sources(car_name, headlight_seed, brakelight_seed)
    result = {name: head['_ON'] for name in ('HEADLIGHT_LEFT', 'HEADLIGHT_RIGHT')}
    result.update({name: window_front_target for name in ('HEADLIGHT_GLASS_LEFT', 'HEADLIGHT_GLASS_RIGHT')})
    for side, bit in (('LEFT', 8), ('RIGHT', 16), ('CENTRE', 32)):
        active = bool(flags_1608 & bit) and not bool(flags_160c & bit)
        if force_side_lights and side != 'CENTRE':
            active = True
        suffix = '_ON' if active else '_OFF'
        result['BRAKELIGHT_' + side] = brake[suffix]
        result['BRAKELIGHT_GLASS_' + side] = brake['_GLASS' + suffix]
    return result


def vinyl_request_path(car_name, request_byte_7, force_previnyl=0):
    """Branch-only translation of 0x802DEFC4..0x802DF028.

    The producer and canonical per-car request mode remain unrecovered.
    A zero byte skips both alternatives even when force_previnyl is nonzero.
    """
    texture_hash(car_name)
    if not isinstance(request_byte_7, int) or not 0 <= request_byte_7 <= 255:
        raise ValueError('Expected the original request byte')
    uint32(force_previnyl)
    if request_byte_7 == 0:
        return None
    leaf = 'PREVINYL.BIN' if request_byte_7 == 2 or force_previnyl else 'VINYLS.BIN'
    return f'CARS\\{car_name}\\{leaf}'


def original_hash(image, text, seed=None):
    """Reference-check the exact pinned original byte-hash/seeded-hash code."""
    if hashlib.sha256(image.data).hexdigest() != DOL_SHA256:
        raise ValueError('Original reference DOL checksum mismatch')
    texture_hash(text, 0xffffffff if seed is None else seed)
    raw = text.encode('ascii')
    if len(raw) > 512:
        raise ValueError('Hash reference input exceeds its bounded buffer')
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR, UC_PPC_REG_PC
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    for address, size in ((0x80062000, 0x2000), (0x90000000, 0x1000), (0xa0000000, 0x1000)):
        uc.mem_map(address, size)
    image.file_offset(HASH_VA, 0x60, executable=True)
    uc.mem_write(HASH_VA, image.read(HASH_VA, 0x60));uc.mem_write(0x90000000, raw+b'\0')
    uc.reg_write(UC_PPC_REG_3, 0x90000000);uc.reg_write(UC_PPC_REG_LR, 0xa0000000)
    if seed is not None:
        uc.reg_write(UC_PPC_REG_4, seed)
    uc.emu_start(HASH_VA if seed is None else SEEDED_HASH_VA, 0xa0000000,
                 timeout=100000, count=4096)
    if uc.reg_read(UC_PPC_REG_PC) != 0xa0000000:
        raise ValueError('Original hash did not return within its bound')
    return uc.reg_read(UC_PPC_REG_3) & 0xffffffff


def original_targets(image, car_name, *, window_front_target, flags_1608=0,
                     flags_160c=0, force_side_lights=0,
                     headlight_seed=None, brakelight_seed=None):
    """Bounded reference execution of the pinned original integer leaf routine."""
    if hashlib.sha256(image.data).hexdigest() != DOL_SHA256:
        raise ValueError('Original reference DOL checksum mismatch')
    # Validate input words through the same public interface before emulation.
    light_targets(car_name, window_front_target=window_front_target, flags_1608=flags_1608,
                  flags_160c=flags_160c, force_side_lights=force_side_lights,
                  headlight_seed=headlight_seed, brakelight_seed=brakelight_seed)
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_PC
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    code, obj, stop, global_page = 0x802ca000, 0x90000000, 0xa0000000, 0x80437000
    for address, size in ((code, 0x2000), (obj, 0x2000), (stop, 0x1000), (global_page, 0x1000)):
        uc.mem_map(address, size)
    image.file_offset(SELECTOR_VA, SELECTOR_BYTES, executable=True)
    uc.mem_write(SELECTOR_VA, image.read(SELECTOR_VA, SELECTOR_BYTES))
    head, brake = sources(car_name, headlight_seed, brakelight_seed)
    def put(offset, value):
        uc.mem_write(obj + offset, struct.pack('>I', value))
    for at, table in ((0x15c8, head), (0x15e0, brake)):
        for i, suffix in enumerate(SUFFIXES):
            put(at + i*4, table[suffix])
    put(0x2d0, window_front_target);put(0x1608, flags_1608);put(0x160c, flags_160c)
    uc.mem_write(0x80437310, struct.pack('>I', force_side_lights))
    uc.reg_write(UC_PPC_REG_3, obj);uc.reg_write(UC_PPC_REG_LR, stop)
    uc.emu_start(SELECTOR_VA, stop, timeout=100000, count=8192)
    if uc.reg_read(UC_PPC_REG_PC) != stop:
        raise ValueError('Original material selector did not return within its bound')
    return {name: struct.unpack('>I', uc.mem_read(obj+offset, 4))[0] for name, offset in LIGHT_FIELDS.items()}


def report(image, car_name='BMWM3GTRE46', verify=False):
    if hashlib.sha256(image.data).hexdigest() != DOL_SHA256:
        raise ValueError('Material recovery addresses require the pinned USA executable')
    head, brake = sources(car_name)
    strings = image.strings(r'^(?:%s_SKIN[1-4]B?|%s_KIT00_(?:HEADLIGHT|BRAKELIGHT)|HEADLIGHT_(?:LEFT|RIGHT)|HEADLIGHT_GLASS_(?:LEFT|RIGHT)|BRAKELIGHT_(?:LEFT|RIGHT|CENTRE)|BRAKELIGHT_GLASS_(?:LEFT|RIGHT|CENTRE)|WINDOW_FRONT|_GLASS_(?:OFF|ON|DAMAGE0)|_(?:OFF|ON|DAMAGE0)|CARS\\%s\\(?:PREVINYL|VINYLS)\.BIN)$', minimum=3)
    refs = image.constant_xrefs(s['address'] for s in strings)
    output = dict(car_name=car_name, dol_sha256=hashlib.sha256(image.data).hexdigest(),
                  hash_function=f'{HASH_VA:08x}', seeded_hash_function=f'{SEEDED_HASH_VA:08x}',
                  selector_function=f'{SELECTOR_VA:08x}', selector_bytes_sha256=hashlib.sha256(image.read(SELECTOR_VA, SELECTOR_BYTES)).hexdigest(),
                  skin1=dict(name=car_name+'_SKIN1', key=f'{texture_hash(car_name+"_SKIN1"):08x}', status='runtime-generated paint output; compositor not recovered'),
                  source_headlights={s:f'{key:08x}' for s,key in head.items()},
                  source_brakelights={s:f'{key:08x}' for s,key in brake.items()},
                  aliases={name:f'{texture_hash(name):08x}' for name in LIGHT_FIELDS},
                  vinyl_loader=dict(branch_start='802defc4', existence_check='802df030', load='802df04c',
                                    request_byte_0='skip', request_byte_2=vinyl_request_path(car_name, 2),
                                    other_nonzero=vinyl_request_path(car_name, 1), global_force_previnyl='804388e4',
                                    mode_producer='unrecovered; canonical mode is not assumed'),
                  strings=strings, constant_xrefs=refs,
                  limitations=['Only the target-key subset of the light update is reproduced',
                               'Actual flag generation, damage rendering, live window/tint target and part selection remain separate systems',
                               'No guessed livery/paint output is generated',
                               'Duplicate DYNTEX archive entries have unresolved active-load precedence'])
    if verify:
        hash_cases = 0
        for text in [car_name+'_SKIN1', 'TEXTURE_NAME', 'WINDOW_FRONT', 'headlight_left', *LIGHT_FIELDS]:
            if texture_hash(text) != original_hash(image, text):
                raise ValueError(f'Original hash mismatch: {text}')
            hash_cases += 1
        for prefix in (car_name+'_KIT00_HEADLIGHT', car_name+'_KIT00_BRAKELIGHT'):
            for suffix in SUFFIXES:
                seed = texture_hash(prefix)
                if texture_hash(suffix, seed) != original_hash(image, suffix, seed):
                    raise ValueError(f'Original seeded hash mismatch: {prefix}{suffix}')
                hash_cases += 1
        output['original_hash_verification'] = dict(cases=hash_cases, matched=hash_cases)
        cases = 0
        for enabled in range(8):
            for suppressed in range(8):
                for force in (0, 1):
                    args = dict(window_front_target=0x12345678, flags_1608=enabled<<3,
                                flags_160c=suppressed<<3, force_side_lights=force)
                    expected = light_targets(car_name, **args)
                    observed = original_targets(image, car_name, **args)
                    if observed != expected:
                        raise ValueError(f'Original selector mismatch: {args}: {observed} != {expected}')
                    cases += 1
        output['original_selector_verification'] = dict(cases=cases, matched=cases,
                                                       scope='All 3-bit enable/suppress combinations with side override off/on')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dol', type=Path);parser.add_argument('output', type=Path)
    parser.add_argument('--car', default='BMWM3GTRE46')
    parser.add_argument('--verify-original', action='store_true')
    args = parser.parse_args()
    result = report(DolImage(args.dol.read_bytes()), args.car, args.verify_original)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(args.output)
    if 'original_selector_verification' in result:print(result['original_selector_verification'])
