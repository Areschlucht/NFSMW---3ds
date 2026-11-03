"""Export compact, bounded original region/index metadata for the native loader.

This file contains no converted meshes. It selects exact original source sections
and supplies source ranges to a separate streaming asset loader.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from nfs_rockport import decode as decode_index
from world_streaming_regions import decode as decode_regions


def export(index, stream_bytes):
    sections=sorted(decode_index(index,stream_bytes)['sections'],key=lambda s:s['id'])
    regions=decode_regions(index)
    polygons=regions['polygons']
    dependencies=regions['dependencies']
    if len(sections)>1024 or len(polygons)>768 or len(dependencies)>512:
        raise ValueError('Original data exceeds explicit runtime metadata budgets')
    polygon_index={p['id']:i for i,p in enumerate(polygons)}
    if len(polygon_index)!=len(polygons):
        raise ValueError('Ambiguous original polygon identifier')
    section_data=b''.join(struct.pack('<HHII',s['id'],0,s['offset'],s['bytes']) for s in sections)
    points=[]
    polygon_data=bytearray()
    for polygon in polygons:
        polygon_data.extend(struct.pack('<HHI4f2fI',polygon['id'],len(polygon['points']),len(points),
                                        *polygon['bounds'],*polygon['center'],polygon['flags']))
        points.extend(polygon['points'])
    refs=[]
    dependency_data=bytearray()
    for dependency in dependencies:
        dependency_data.extend(struct.pack('<HHIHH',dependency['id'],polygon_index[dependency['id']],
                                           len(refs),len(dependency['section_ids']),0))
        refs.extend(dependency['section_ids'])
    point_data=b''.join(struct.pack('<2f',*p) for p in points)
    ref_data=struct.pack(f'<{len(refs)}h',*refs)
    chunks=[section_data,polygon_data,dependency_data,point_data,ref_data]
    offsets=[]
    cursor=128
    for chunk in chunks:
        offsets.append(cursor)
        cursor+=len(chunk)
    header=struct.pack('<4sHH14I32s32s',b'WST1',1,128,cursor,len(sections),len(polygons),
                       len(dependencies),len(points),len(refs),regions['section_span'],
                       *offsets,stream_bytes,0,bytes(32),hashlib.sha256(index).digest())
    return bytearray(header+b''.join(chunks))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--stream',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=export(args.index.read_bytes(),args.stream.stat().st_size)
    with args.stream.open('rb') as file:
        output[64:96]=hashlib.file_digest(file,'sha256').digest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(output)
    print(json.dumps(dict(bytes=len(output),sha256=hashlib.sha256(output).hexdigest(),
                          source_sha256=output[64:96].hex())))
