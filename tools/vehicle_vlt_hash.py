"""Original Attrib string hash: Jenkins lookup2, 32-bit wrap, seed ABCDEF00.

ASCII bytes are assembled little-endian by the hash algorithm even on PPC.
Case is preserved. Empty strings return zero in the original wrapper at
0x801956E8. Unlike editor convenience APIs, hexadecimal-looking strings are
hashed as strings rather than interpreted as literal hash values.
"""
import struct

MASK = 0xffffffff


def _mix(a, b, c):
    a = ((a-b-c) & MASK) ^ (c >> 13)
    b = ((b-c-a) & MASK) ^ ((a << 8) & MASK)
    c = ((c-a-b) & MASK) ^ (b >> 13)
    a = ((a-b-c) & MASK) ^ (c >> 12)
    b = ((b-c-a) & MASK) ^ ((a << 16) & MASK)
    c = ((c-a-b) & MASK) ^ (b >> 5)
    a = ((a-b-c) & MASK) ^ (c >> 3)
    b = ((b-c-a) & MASK) ^ ((a << 10) & MASK)
    c = ((c-a-b) & MASK) ^ (b >> 15)
    return a, b, c


def vlt_hash(name):
    data = name.encode('ascii') if isinstance(name, str) else bytes(name)
    if b'\0' in data:
        raise ValueError('Attribute name contains a NUL byte')
    if not data:
        return 0
    a = b = 0x9e3779b9
    c = 0xabcdef00
    offset = 0
    while len(data)-offset >= 12:
        x, y, z = struct.unpack_from('<3I', data, offset)
        a, b, c = _mix((a+x) & MASK, (b+y) & MASK, (c+z) & MASK)
        offset += 12
    c = (c+len(data)) & MASK
    tail = data[offset:]
    for i, value in enumerate(tail):
        if i < 4:
            a = (a+(value << (i*8))) & MASK
        elif i < 8:
            b = (b+(value << ((i-4)*8))) & MASK
        else:
            c = (c+(value << ((i-7)*8))) & MASK
    return _mix(a, b, c)[2]
