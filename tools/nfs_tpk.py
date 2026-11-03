#!/usr/bin/env python3
"""Inspect/export observed Most Wanted GameCube texture packages to PNG.

Supports observed 124-byte texture records and 60-byte GC platform records,
C4/C8 with RGB5A3 palettes, CMPR, RGB5A3 and RGBA8. Does not execute game code.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from gc_texture import indexed,cmpr,png_rgba,rgba8,tiled_rgb5a3,tiled_rgb565
from nfs_jdlz import decompress


def chunks(data,start,end):
    while start<end:
        if end-start<8:raise ValueError('Short chunk header')
        kind,size=struct.unpack_from('<II',data,start)
        stop=start+8+size
        if stop>end:raise ValueError('Chunk exceeds parent')
        yield kind,start,stop
        start=stop


def parse(data,huff_decoder=None,wanted_hashes=None):
    if data[:4]==b'JDLZ':data=decompress(data)
    result=[]
    for kind,start,end in chunks(data,0,len(data)):
        if kind!=0xb3300000:continue
        parts={k:(s,e) for k,s,e in chunks(data,start+8,end)}
        h,he=parts[0xb3310000];d,de=parts[0xb3320000]
        header={k:(s,e) for k,s,e in chunks(data,h+8,he)}
        pixels={k:(s,e) for k,s,e in chunks(data,d+8,de)}
        keys_start,keys_end=header[0x33310002]
        if (keys_end-keys_start-8)%8:raise ValueError('Malformed hash table')
        count=(keys_end-keys_start-8)//8
        compressed=0x33310003 in header
        if compressed:
            table,table_end=header[0x33310003]
            if table_end-table-8!=count*24:raise ValueError('Unsupported compressed texture table')
        else:
            table,table_end=header[0x33310004];platform,platform_end=header[0x33310005]
            if table_end-table-8!=count*124 or platform_end-platform-8!=count*60:
                raise ValueError('Unsupported texture record size')
        p,pe=pixels[0x33320002];base=(p+0x87)&~127
        if base>pe:raise ValueError('Pixel alignment exceeds chunk')
        pack_name=data[header[0x33310001][0]+12:header[0x33310001][0]+40].split(b'\0')[0].decode('ascii')
        for i in range(count):
            source=data;local_base=base;limit=pe;compression=None
            if compressed:
                key,offset,packed,unpacked,_,_=struct.unpack_from('<6I',data,table+8+i*24)
                first=start+offset
                if first<base or first>pe or packed>pe-first or unpacked<184 or unpacked>32*1024*1024:
                    raise ValueError('Invalid compressed texture bounds')
                packet=data[first:first+packed]
                compression=packet[:4].decode('ascii')
                if packet[:4]==b'JDLZ':source=decompress(packet)
                elif packet[:4]==b'HUFF' and huff_decoder:source=huff_decoder(packet,unpacked)
                else:raise ValueError(f'Unsupported or unavailable compression reader: {packet[:4]!r}')
                if len(source)!=unpacked:raise ValueError('Decompressed texture length mismatch')
                entry=unpacked-184;native=unpacked-60;limit=entry
                if key!=struct.unpack_from('<I',source,entry+36)[0]:raise ValueError('Compressed texture hash mismatch')
                local_base=-struct.unpack_from('<I',source,entry+48)[0]
            else:
                entry=table+8+i*124;native=platform+8+i*60
            name=source[entry+12:entry+36].split(b'\0')[0].decode('ascii')
            key=struct.unpack_from('<I',source,entry+36)[0]
            if key!=struct.unpack_from('<I',data,keys_start+8+i*8)[0]:raise ValueError('Hash table disagrees with record')
            if wanted_hashes is not None and f'{key:08x}' not in wanted_hashes:continue
            offset,pal_offset,size,pal_size=struct.unpack_from('<4I',source,entry+48)
            width,height=struct.unpack_from('<2H',source,entry+68)
            native_format=struct.unpack_from('>I',source,native+56)[0]
            fmt=native_format&0x7fffffff
            if not width or not height or width>4096 or height>4096:raise ValueError('Invalid dimensions')
            if offset+local_base<0 or offset>limit-local_base or size>limit-local_base-offset:raise ValueError('Image data outside chunk')
            raw=source[local_base+offset:local_base+offset+size]
            if fmt in (8,9):
                if pal_offset+local_base<0 or pal_offset>limit-local_base or pal_size>limit-local_base-pal_offset:raise ValueError('Palette outside chunk')
                rgba=indexed(raw,width,height,source[local_base+pal_offset:local_base+pal_offset+pal_size],4 if fmt==8 else 8)
            elif fmt==14:rgba=cmpr(raw,width,height)
            elif fmt==6:rgba=rgba8(raw,width,height)
            elif fmt==5:rgba=tiled_rgb5a3(raw,width,height)
            elif fmt==4:rgba=tiled_rgb565(raw,width,height)
            else:raise ValueError(f'Unsupported GX texture format {native_format:x}')
            result.append(dict(package=pack_name,name=name,hash=f'{key:08x}',width=width,height=height,
                               native_format=f'{native_format:08x}',pixel_offset=local_base+offset,compression=compression,
                               alpha_test_mode=source[entry+85],blend_mode=source[entry+86],
                               image_bytes=size,palette_bytes=pal_size,rgba=rgba))
    if not result:raise ValueError('No supported texture package found')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--huff-reference',action='store_true',help='Use the pinned, emulated offline HUFF reference (requires Unicorn)')
    args=parser.parse_args()
    huff=None
    if args.huff_reference:
        from nfs_huff_reference import decode as huff
    textures=parse(args.bundle.read_bytes(),huff)
    args.output.mkdir(parents=True,exist_ok=True);manifest=[]
    for index,t in enumerate(textures):
        safe=re.sub(r'[^A-Za-z0-9_.-]','_',t['name'])
        filename=f'{index:03d}_{safe}.png'
        rgba=t.pop('rgba')
        (args.output/filename).write_bytes(png_rgba(rgba,t['width'],t['height']))
        manifest.append(dict(t,png=filename,rgba_sha256=hashlib.sha256(rgba).hexdigest()))
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Exported {len(textures)} images to {args.output}')
