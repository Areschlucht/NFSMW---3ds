"""Bounded reference for the USA DOL's original GX strip descriptor emitter.

This does not emulate the game or infer triangles from the model's advisory
triangle statistic. It executes the original descriptor loop, intercepting only
GXBegin and GXCallDisplayList, and records the index bytes written to the FIFO.
Requires Unicorn and the separately supplied original executable.
"""
import hashlib
import struct

from map_recovery_dol import DolImage

DOL_SHA256 = '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
ENTRY, STOP = 0x8011773C, 0x801181C0
GX_BEGIN, GX_LIST = 0x8033D2A8, 0x803408CC


def emit_original(dol_bytes, descriptor, packet):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN
    from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn import ppc_const as reg

    if hashlib.sha256(dol_bytes).hexdigest() != DOL_SHA256:
        raise ValueError('Reference requires the verified USA Speed.dol')
    if len(descriptor) != 16 or not packet or len(packet) > 65535:
        raise ValueError('Invalid bounded descriptor packet')
    if descriptor[13] not in (1, 32):
        raise ValueError('Only observed three-index formats are verified')
    flags = descriptor[12]
    if flags & 0x3f not in (0, 2, 4, 6, 16, 18, 20, 22, 28, 30):
        raise ValueError('Unsupported index flags')
    widths = (2 if flags & 16 else 1, 2 if flags & 4 else 1,
              2 if flags & 2 else 1)
    compiled = bool(flags & 128 and struct.unpack_from('>H', descriptor, 14)[0])
    required = (struct.unpack_from('>H', descriptor, 14)[0] if compiled
                else descriptor[8] * sum(widths))
    if required > len(packet) or descriptor[8] < 3:
        raise ValueError('Truncated or empty strip')
    image = DolImage(dol_bytes)
    machine = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    machine.mem_map(0x80117000, 0x2000)
    machine.mem_write(ENTRY, image.read(ENTRY, STOP - ENTRY + 4))
    for address in (GX_BEGIN, GX_LIST):
        machine.mem_map(address & ~4095, 4096)
    machine.mem_map(0x10000000, 0x20000)
    machine.mem_map(0xCC008000, 4096)
    descriptor_address, data_address = 0x10001000, 0x10002000
    stack, context = 0x10018000, 0x10019000
    machine.mem_write(descriptor_address, struct.pack('>I', data_address) + descriptor[4:])
    machine.mem_write(data_address, packet)
    machine.mem_write(stack + 0x80, struct.pack('>I', 0))
    for number, value in ((1, stack), (26, context), (27, 0), (28, descriptor_address)):
        machine.reg_write(getattr(reg, f'UC_PPC_REG_{number}'), value)
    result = {'fifo': bytearray(), 'begin': [], 'display_lists': [], 'stopped': False}

    def code_hook(uc, address, size, _):
        if address == STOP:
            result['stopped'] = True
            uc.emu_stop()
        elif address in (GX_BEGIN, GX_LIST):
            args = [uc.reg_read(getattr(reg, f'UC_PPC_REG_{i}')) for i in (3, 4, 5)]
            if address == GX_BEGIN:
                result['begin'].append(args)
            else:
                if args[0] != data_address or args[1] != required:
                    raise ValueError('Original display-list call exceeds packet')
                result['display_lists'].append(bytes(uc.mem_read(args[0], args[1])))
            uc.reg_write(reg.UC_PPC_REG_PC, uc.reg_read(reg.UC_PPC_REG_LR))
        elif not ENTRY <= address < STOP:
            raise ValueError(f'Unexpected executable address {address:08x}')

    def write_hook(uc, access, address, size, value, _):
        if address == 0xCC008000:
            if size not in (1, 2):
                raise ValueError('Unexpected FIFO write width')
            result['fifo'].extend(value.to_bytes(size, 'big'))

    machine.hook_add(UC_HOOK_CODE, code_hook)
    machine.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    machine.emu_start(ENTRY, STOP + 4, count=10000)
    if not result.pop('stopped'):
        raise ValueError('Original emitter instruction budget exceeded')
    result['fifo'] = bytes(result['fifo'])
    return result
