"""Bounded JDLZ decoding. Algorithm reference: NI240SX/UCGT's Java reader,
which credits MWisBest/OpenNFSTools. No external implementation is executed.
"""
import struct


def decompress(data, max_output=32*1024*1024):
    if len(data)<16 or data[:8]!=b'JDLZ\x02\x10\0\0':
        raise ValueError('Unsupported JDLZ header')
    size,packed=struct.unpack_from('<II',data,8)
    if not size or size>max_output or packed!=len(data):
        raise ValueError('Invalid JDLZ size')
    flags1=flags2=1
    position=16
    output=bytearray()
    def byte():
        nonlocal position
        if position>=len(data): raise ValueError('Truncated JDLZ stream')
        value=data[position];position+=1
        return value
    while len(output)<size:
        if flags1==1:flags1=byte()|256
        if flags2==1:flags2=byte()|256
        if flags1&1:
            a,b=byte(),byte()
            if flags2&1:
                length=(((a&0xf0)<<4)|b)+3
                distance=(a&15)+1
            else:
                length=(a&31)+3
                distance=(((a&0xe0)<<3)|b)+17
            if distance>len(output) or length>size-len(output):
                raise ValueError('Invalid JDLZ back-reference')
            for _ in range(length):output.append(output[-distance])
            flags2>>=1
        else:output.append(byte())
        flags1>>=1
    # Texture packets may end with two reserved, unused flag bytes (nonzero).
    # Standalone streams also contain up to three zero alignment bytes.
    if len(data)-position>3 or (len(data)-position>2 and any(data[position:])):
        raise ValueError(f'Unexpected JDLZ trailing data: {len(data)-position} bytes {data[position:].hex()}')
    return bytes(output)
