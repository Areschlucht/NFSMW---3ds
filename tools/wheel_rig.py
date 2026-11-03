"""Portable wheel animation metadata tied to one converted car scene by CRC."""
import math
import struct
import zlib


def inspect_rig(data, batch_count, body_crc):
    if len(data)<32:
        raise ValueError('Short wheel rig header')
    magic,version,count,batches,size,crc,source,reserved=struct.unpack_from('<4s7I',data)
    if magic!=b'NWA1' or version!=1 or count!=4 or batches!=batch_count or not 1<=batches<=2048 or reserved or source!=body_crc:
        raise ValueError('Wheel rig does not match car scene')
    if size!=96+batches*4 or len(data)!=32+size or zlib.crc32(data[32:])!=crc:
        raise ValueError('Wheel rig length/CRC mismatch')
    wheels=[]
    for i in range(4):
        x,y,z,radius,front,reserved=struct.unpack_from('<4f2I',data,32+i*24)
        if not all(math.isfinite(v) and abs(v)<=1.01 for v in (x,y,z)) or not math.isfinite(radius) or not .1<radius<1 or front>1 or reserved:
            raise ValueError('Invalid wheel pivot/radius/flags')
        wheels.append(dict(pivot=[x,y,z],radius=radius,front=bool(front)))
    groups=struct.unpack_from('<'+str(batches)+'I',data,128)
    if set(groups)!={0,1,2,3,4} or sum(w['front'] for w in wheels)!=2:
        raise ValueError('Incomplete wheel groups/front axle flags')
    return wheels,list(groups)


def encode_rig(wheels,groups,body_crc):
    payload=b''.join(struct.pack('<4f2I',*w['pivot'],w['radius'],int(w['front']),0) for w in wheels)
    payload+=struct.pack('<'+str(len(groups))+'I',*groups)
    raw=struct.pack('<4s7I',b'NWA1',1,len(wheels),len(groups),len(payload),zlib.crc32(payload),body_crc,0)+payload
    inspect_rig(raw,len(groups),body_crc)
    return raw
