#!/usr/bin/env python3
"""Read original MW GC preset records (chunk 00030220), retaining unknowns.

Schema anchors: loader 802DB494, record stride290, model string+8,
preset string+28, 139 part keys+60; consumer802DB684. File payload words are
little-endian, then swapped by the original GC loader. This does not label
part slots or reconstruct paint. Optional bounded PPC verification needs DOL.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from material_recovery_vehicle import DOL_SHA256
from vehicle_dol import DolImage
from nfs_rockport import chunks

KIND = 0x00030220
STRIDE = 0x290
PARTS = 139


def bounded_name(raw):
    end = raw.find(b'\0')
    if end < 0:
        raise ValueError('Unterminated fixed-width preset name')
    try:
        return raw[:end].decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('Non-ASCII preset name') from error


def preset_payload(payload, *, file_offset=0):
    if len(payload) % STRIDE:
        raise ValueError('Preset payload does not contain complete 0x290-byte records')
    if len(payload) // STRIDE > 16384:
        raise ValueError('Preset record budget exceeded')
    result = []
    for at in range(0, len(payload), STRIDE):
        record = payload[at:at+STRIDE]
        result.append(dict(file_offset=file_offset+at,
                           model_name=bounded_name(record[8:0x28]),
                           preset_name=bounded_name(record[0x28:0x48]),
                           unknown_48=record[0x48:0x60].hex(),
                           part_keys=[f'{x:08x}' for x in struct.unpack_from('<139I', record, 0x60)],
                           unknown_28c=record[0x28c:0x290].hex(),
                           record_sha256=hashlib.sha256(record).hexdigest()))
    return result


def part_slot_labels(image):
    """Read the pinned executable's enum/string table, without guessed labels."""
    if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:
        raise ValueError('Part slot names require pinned USA executable')
    labels=[]
    for index in range(PARTS):
        enum,pointer=struct.unpack('>II',image.read(0x80438484+index*8,8))
        if enum!=index:
            raise ValueError('Original part enum table is not sequential')
        label=image.c_string(pointer)
        if not label or not label.isprintable():
            raise ValueError('Invalid original part slot name')
        labels.append(label)
    return labels


def report(data, image=None):
    result = []
    for kind, start, end in chunks(data):
        if kind == KIND:
            result.extend(preset_payload(data[start:end], file_offset=start))
    return dict(source_sha256=hashlib.sha256(data).hexdigest(),
                chunk_kind=f'{KIND:08x}', records=result,
                part_slots=part_slot_labels(image) if image is not None else None,
                scope='Top-level original chunk30220 only; opaque containers are not guessed or recursively interpreted')


def verify_loader(image, payload):
    """Compare endian transformations against the exact pinned original loader.

    Input is synthetic or original preset payload, <=32 records. The original
    loader's linked-list writes are excluded from comparison; every remaining
    byte is compared, including names, untouched padding and swapped fields.
    """
    if hashlib.sha256(image.data).hexdigest() != DOL_SHA256:
        raise ValueError('Original loader requires pinned USA executable')
    preset_payload(payload)
    if not payload or len(payload) > STRIDE*32:
        raise ValueError('Original reference requires 1..32 bounded records')
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_PC
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    obj, stack, stop, head = 0x90000000, 0x91000000, 0xa0000000, 0x804a6f80
    for va, size in ((0x802db000,0x1000),(0x8005c000,0x1000),(obj,0x6000),
                     (stack,0x2000),(stop,0x1000),(0x804a6000,0x1000)):
        uc.mem_map(va,size)
    for va, size in ((0x802db494,0xec),(0x8005caa0,0x94)):
        image.file_offset(va,size,executable=True)
        uc.mem_write(va,image.read(va,size))
    uc.mem_write(obj,struct.pack('>II',KIND,len(payload))+bytes(payload))
    uc.mem_write(head,struct.pack('>II',head,head))
    uc.reg_write(UC_PPC_REG_1,stack+0x1000);uc.reg_write(UC_PPC_REG_3,obj)
    uc.reg_write(UC_PPC_REG_LR,stop)
    uc.emu_start(0x802db494,stop,timeout=200000,count=200000)
    if uc.reg_read(UC_PPC_REG_PC)!=stop or uc.reg_read(UC_PPC_REG_3)!=1:
        raise ValueError('Original preset loader did not return successfully')
    actual=bytes(uc.mem_read(obj+8,len(payload)))
    expected=bytearray(payload)
    for at in range(0,len(payload),STRIDE):
        for field,size in ((0x48,8),(0x50,8),(0x58,4),(0x5c,4),
                           *((0x60+i*4,4) for i in range(PARTS))):
            expected[at+field:at+field+size]=payload[at+field:at+field+size][::-1]
        if actual[at+8:at+STRIDE]!=expected[at+8:at+STRIDE]:
            raise ValueError('Original loader disagrees with recovered field byte order')
    return dict(records=len(payload)//STRIDE, matched=True,
                compared_bytes=len(payload)-8*(len(payload)//STRIDE))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--dol',type=Path,help='Pinned original executable supplies verified part enum names')
    args=p.parse_args();r=report(args.source.read_bytes(),DolImage(args.dol.read_bytes()) if args.dol else None)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(f'{len(r["records"])} original preset records')
