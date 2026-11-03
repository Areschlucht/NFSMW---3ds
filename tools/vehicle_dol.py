#!/usr/bin/env python3
"""Validated DOL address mapping and conservative PowerPC constant xrefs.

This reads original bytes without executing them. Address translation always
uses the DOL section header; initialized small-data sections need not share
the text section's file/virtual-address delta. Xrefs identify materialized
addresses, not recovered function names or semantic units.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import re
import struct
from pathlib import Path


@dataclass(frozen=True)
class Section:
    name: str
    offset: int
    address: int
    size: int


class DolImage:
    def __init__(self, data):
        self.data = bytes(data)
        if len(data) < 0x100:
            raise ValueError('Truncated DOL header')
        sections = []
        for i in range(18):
            offset, address, size = (struct.unpack_from('>I', data, base+i*4)[0]
                                     for base in (0, 0x48, 0x90))
            if not size:
                continue
            if offset < 0x100 or offset+size > len(data) or address+size > 0x100000000:
                raise ValueError('DOL section exceeds file/address bounds')
            section = Section(f'text{i}' if i < 7 else f'data{i-7}', offset, address, size)
            for old in sections:
                for field in ('offset', 'address'):
                    a, b = getattr(old, field), getattr(section, field)
                    if max(a, b) < min(a+old.size, b+size):
                        raise ValueError(f'Overlapping DOL {field} ranges')
            sections.append(section)
        self.sections = tuple(sections)
        self.bss_address, self.bss_size, self.entry = struct.unpack_from('>3I', data, 0xd8)
        if self.bss_address+self.bss_size > 0x100000000:
            raise ValueError('BSS address overflow')
        if not any(s.name.startswith('text') and s.address <= self.entry < s.address+s.size
                   for s in sections) or self.entry % 4:
            raise ValueError('DOL entry is not aligned executable text')

    def file_offset(self, address, size=1, executable=False):
        if not isinstance(address, int) or not isinstance(size, int) or size <= 0 or address < 0:
            raise ValueError('Invalid address/read size')
        for section in self.sections:
            if executable and not section.name.startswith('text'):
                continue
            if section.address <= address and address+size <= section.address+section.size:
                return section.offset+address-section.address
        raise ValueError(f'Address 0x{address:08x}+{size} is outside a loaded section')

    def address(self, offset, size=1):
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0 or offset < 0:
            raise ValueError('Invalid file offset/read size')
        for section in self.sections:
            if section.offset <= offset and offset+size <= section.offset+section.size:
                return section.address+offset-section.offset
        raise ValueError('File range is outside a loaded section')

    def read(self, address, size):
        offset = self.file_offset(address, size)
        return self.data[offset:offset+size]

    def u32(self, address):
        return struct.unpack('>I', self.read(address, 4))[0]

    def f32(self, address):
        return struct.unpack('>f', self.read(address, 4))[0]

    def c_string(self, address, limit=256):
        if limit <= 0:
            raise ValueError('Invalid string limit')
        offset = self.file_offset(address)
        section = next(s for s in self.sections if s.offset <= offset < s.offset+s.size)
        raw = self.data[offset:min(offset+limit, section.offset+section.size)]
        stop = raw.find(b'\0')
        if stop < 0:
            raise ValueError('Unterminated bounded DOL string')
        return raw[:stop].decode('ascii')

    def strings(self, pattern=None, minimum=4):
        if minimum < 1:
            raise ValueError('Invalid minimum string length')
        result = []
        regex = re.compile(rb'[\x20-\x7e]{'+str(minimum).encode()+rb',}')
        for section in self.sections:
            for match in regex.finditer(self.data[section.offset:section.offset+section.size]):
                text = match.group().decode('ascii')
                if pattern is None or re.search(pattern, text):
                    result.append(dict(address=section.address+match.start(),
                                       offset=section.offset+match.start(), text=text))
        return result

    def constant_xrefs(self, targets):
        """Track lis/addi/ori/mr constants inside conservative straight-line blocks.

        Unknown GPR-writing instructions and control flow clear state. Calls
        clear volatile registers. This deliberately misses some valid xrefs
        instead of treating distant matching halfwords as proof.
        """
        targets = set(targets)
        result = []
        for section in self.sections:
            if not section.name.startswith('text'):
                continue
            registers = {}
            for at in range(section.offset, section.offset+section.size-3, 4):
                word = struct.unpack_from('>I', self.data, at)[0]
                op, rt, ra, rb = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
                immediate = word & 65535
                signed = immediate if immediate < 32768 else immediate-65536
                va = section.address+at-section.offset
                destination, value = None, None
                if op in (14, 15):
                    destination = rt
                    base = (0, va) if ra == 0 else registers.get(ra)
                    if base:
                        value = ((base[0]+(signed << 16 if op == 15 else signed)) & 0xffffffff, base[1])
                elif op == 24:
                    destination = ra
                    if rt in registers:
                        base = registers[rt]
                        value = (base[0] | immediate, base[1])
                elif op == 31 and ((word >> 1) & 1023) == 444:
                    destination = ra
                    if rt == rb:
                        value = registers.get(rt)
                elif op in (32, 33, 34, 35, 40, 41, 42, 43):
                    registers.pop(rt, None)
                    if op & 1:
                        registers.pop(ra, None)
                elif op in (36, 38, 44, 46, 47, 48, 50, 52, 54, 10, 11, 59, 63):
                    pass
                elif op in (37, 39, 45, 49, 51, 53, 55):
                    registers.pop(ra, None)
                elif op == 18 and word & 1:
                    for register in (0, *range(3, 13)):
                        registers.pop(register, None)
                else:
                    registers.clear()
                if destination is not None:
                    registers.pop(destination, None)
                    if value is not None:
                        registers[destination] = value
                        if value[0] in targets and op != 15:
                            result.append(dict(instruction=va, origin=value[1], target=value[0], register=destination))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dol', type=Path)
    parser.add_argument('--strings', default=r'^(?:Attrib::Gen::(?:engine|tires|chassis|brakes|transmission|rigidbodyspecs|nos)|Suspension\w*|EngineRacer|Physics|VehicleParams|EngineParams)$')
    args = parser.parse_args()
    image = DolImage(args.dol.read_bytes())
    strings = image.strings(args.strings)
    report = dict(sha256=hashlib.sha256(image.data).hexdigest(), sections=[s.__dict__ for s in image.sections],
                  entry=image.entry, strings=strings, xrefs=image.constant_xrefs(s['address'] for s in strings))
    print(json.dumps(report, indent=2))
