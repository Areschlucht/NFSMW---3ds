"""Strict original L2RA region polygons and section dependency records.

Layouts follow 802C0A08's leaf loaders. Coordinates retain native two-axis order;
mapping a 3D camera to these axes and stateful selection remain separate work.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from nfs_rockport import chunks


def decode(data):
    outer = [(a,b) for k,a,b in chunks(data) if k == 0x80034150]
    if len(outer) != 1:
        raise ValueError('Expected one original region package')
    a,b = outer[0]
    leaf_records=list(chunks(data[a:b]))
    leaves = {k:(a+c,a+d) for k,c,d in leaf_records}
    if len(leaves)!=len(leaf_records):
        raise ValueError('Duplicate original region leaf')
    if set(leaves) != {0x34151,0x34152,0x34153,0x34155}:
        raise ValueError('Unsupported original region leaves')
    c,d = leaves[0x34151]
    span,count = struct.unpack_from('<2I',data,c)
    if count*2+8 > d-c or not 1 <= span < 100:
        raise ValueError('Invalid section-span configuration')
    config_ids = list(struct.unpack_from(f'<{count}h',data,c+8))
    config_raw=data[c:d].hex()
    polygons=[]
    c,d=leaves[0x34152]
    while c<d:
        if c+36>d:
            raise ValueError('Truncated polygon record')
        identifier,n,flags=struct.unpack_from('<hBB',data,c+8)
        size=36+n*8
        if not 3<=n<=16 or c+size>d:
            raise ValueError('Invalid polygon vertex count/range')
        bbox=struct.unpack_from('<4f',data,c+12)
        center=struct.unpack_from('<2f',data,c+28)
        points=[list(struct.unpack_from('<2f',data,c+36+i*8)) for i in range(n)]
        if not all(math.isfinite(v) for v in (*bbox,*center,*(v for p in points for v in p))):
            raise ValueError('Nonfinite region point')
        if any(bbox[i]>bbox[i+2] for i in (0,1)):
            raise ValueError('Inverted polygon bounds')
        if any(not bbox[i]<=point[i]<=bbox[i+2] for point in points for i in (0,1)):
            raise ValueError('Polygon point exceeds original bounds')
        polygons.append(dict(id=identifier,offset=c,bytes=size,flags=flags,
                             bounds=list(bbox),center=list(center),points=points,
                             raw=data[c:c+size].hex()))
        c+=size
    dependencies=[]
    c,d=leaves[0x34153]
    while c<d:
        if c+18>d:
            raise ValueError('Truncated dependency record')
        identifier,initial,capacity,count=struct.unpack_from('<hBBh',data,c+12)
        size=20+capacity*2
        if not 0<=count<=capacity<=72 or c+size>d:
            raise ValueError('Invalid dependency record count/range')
        ids=list(struct.unpack_from(f'<{count}h',data,c+18))
        dependencies.append(dict(id=identifier,offset=c,bytes=size,initial_count=initial,
                                 capacity=capacity,section_ids=ids,raw=data[c:c+size].hex()))
        c+=size
    groups=[]
    c,d=leaves[0x34155]
    if (d-c)%76:
        raise ValueError('Truncated fixed section group')
    for at in range(c,d,76):
        n=struct.unpack_from('<h',data,at+24)[0]
        m=struct.unpack_from('<h',data,at+58)[0]
        if not 0<=n<=16 or not 0<=m<=8:
            raise ValueError('Invalid section group counts')
        groups.append(dict(name=data[at+8:at+24].split(b'\0')[0].decode('ascii'),
                           offset=at,raw=data[at:at+76].hex(),
                           region_ids=list(struct.unpack_from(f'<{n}h',data,at+26)),
                           extra_section_ids=list(struct.unpack_from(f'<{m}h',data,at+60))))
    return dict(source_sha256=hashlib.sha256(data).hexdigest(),section_span=span,
                configured_ids=config_ids,config_raw=config_raw,
                polygons=polygons,dependencies=dependencies,groups=groups,
                limitations='Original polygons and ordered section lists; not full stateful camera/prediction/load policy')


def f32(value):
    return struct.unpack('>f',struct.pack('>f',value))[0]


def polygon_contains(point, points):
    """Original 802BFF3C odd/even test with each single-precision rounding."""
    if len(points)<3 or not all(math.isfinite(v) for p in (point,*points) for v in p):
        raise ValueError('Invalid polygon containment input')
    x,y=map(f32,point)
    hit=False
    previous=points[-1]
    for current in points:
        xi,yi=map(f32,current)
        xp,yp=map(f32,previous)
        if yi<=y<yp or yp<=y<yi:
            crossing=f32(f32(f32(f32(xp-xi)*f32(y-yi))/f32(yp-yi))+xi)
            if x<crossing:
                hit=not hit
        previous=current
    return hit


class NoContainingRegion(ValueError):
    pass


class ContainingRegionSelector:
    """Contained-point branch of 802C1094, including move-to-front order.

    Outside every dependency region, the original calls its nearest-polygon
    fallback. That separate stage is deliberately surfaced as an exception here;
    returning an arbitrary region would invent original behavior.
    """
    def __init__(self, region_data):
        polygons={p['id']:p for p in region_data['polygons']}
        self.order=list(region_data['dependencies'])
        self.polygons=polygons

    def select(self, point):
        x,y=map(f32,point)
        for index,dependency in enumerate(self.order):
            polygon=self.polygons[dependency['id']]
            a,b,c,d=polygon['bounds']
            if a<=x<=c and b<=y<=d and polygon_contains((x,y),polygon['points']):
                self.order.insert(0,self.order.pop(index))
                return dependency
        raise NoContainingRegion('Original nearest-region fallback required')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('index',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=decode(args.index.read_bytes())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(section_span=result['section_span'],polygons=len(result['polygons']),
                          dependencies=len(result['dependencies']),groups=len(result['groups']))))
