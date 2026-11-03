"""Read mapped DOL bytes using its section table, never a global VA offset."""
import hashlib
import struct


class DolImage:
    def __init__(self, data):
        if len(data) < 0x100:
            raise ValueError('Short DOL header')
        self.data = data
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.sections = []
        for i in range(18):
            offset = struct.unpack_from('>I', data, i * 4)[0]
            address = struct.unpack_from('>I', data, 0x48 + i * 4)[0]
            size = struct.unpack_from('>I', data, 0x90 + i * 4)[0]
            if not size:
                continue
            if offset < 0x100 or offset + size > len(data) or address + size > 2**32:
                raise ValueError('Invalid DOL section range')
            self.sections.append(dict(index=i, kind='text' if i < 7 else 'data',
                                      offset=offset, address=address, size=size))
        if not self.sections:
            raise ValueError('DOL contains no mapped sections')
        for field in ('offset', 'address'):
            ordered = sorted(self.sections, key=lambda s: s[field])
            if any(a[field] + a['size'] > b[field] for a, b in zip(ordered, ordered[1:])):
                raise ValueError(f'Overlapping DOL {field} ranges')

    def read(self, address, size):
        if size < 0:
            raise ValueError('Negative DOL read size')
        for section in self.sections:
            if section['address'] <= address and address + size <= section['address'] + section['size']:
                offset = section['offset'] + address - section['address']
                return self.data[offset:offset + size]
        raise ValueError('DOL address is not within one mapped section')

    def f32(self, address):
        return struct.unpack('>f', self.read(address, 4))[0]
