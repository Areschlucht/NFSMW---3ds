#!/usr/bin/env python3
"""Decode GameCube tiled RGB5A3 textures; extract a BNR menu banner to PNG.

Standard-library only. This does not parse NFS texture packages or compressed
assets. More pixel formats should be added when actual package headers identify
which formats the game uses.
"""
import argparse
import struct
import zlib
from pathlib import Path


def rgb5a3(value):
    if not 0 <= value <= 65535:
        raise ValueError('RGB5A3 pixel must fit 16 bits')
    if value & 0x8000:
        channels = ((value >> 10) & 31, (value >> 5) & 31, value & 31)
        return tuple((x << 3) | (x >> 2) for x in channels) + (255,)
    alpha = (value >> 12) & 7
    return (((value >> 8) & 15) * 17, ((value >> 4) & 15) * 17,
            (value & 15) * 17, (alpha << 5) | (alpha << 2) | (alpha >> 1))


def tiled_rgb5a3(data, width, height):
    if width <= 0 or height <= 0 or width % 4 or height % 4:
        raise ValueError('Expected positive dimensions in multiples of four')
    if len(data) != width * height * 2:
        raise ValueError('Texture byte length does not match dimensions')
    output = bytearray(width * height * 4)
    offset = 0
    for tile_y in range(0, height, 4):
        for tile_x in range(0, width, 4):
            for y in range(4):
                for x in range(4):
                    value = (data[offset] << 8) | data[offset + 1]
                    destination = ((tile_y + y) * width + tile_x + x) * 4
                    output[destination:destination + 4] = bytes(rgb5a3(value))
                    offset += 2
    return bytes(output)


def banner_rgba(data):
    sizes = {b'BNR1': 0x1960, b'BNR2': 0x1fa0}
    if data[:4] not in sizes or len(data) != sizes[data[:4]]:
        raise ValueError('Unsupported or truncated BNR banner')
    return tiled_rgb5a3(data[0x20:0x1820], 96, 32)


def indexed(data, width, height, palette, bits):
    """GameCube C4 (8x8 tiles) or C8 (8x4 tiles), RGB5A3 palette."""
    tile_height=8 if bits==4 else 4
    if bits not in (4,8) or width<=0 or height<=0 or width%8 or height%tile_height:
        raise ValueError('Unsupported indexed texture dimensions')
    if len(data)!=width*height*bits//8 or len(palette)%2:
        raise ValueError('Invalid indexed texture size')
    colors=[rgb5a3((palette[i]<<8)|palette[i+1]) for i in range(0,len(palette),2)]
    out=bytearray(width*height*4);position=0
    for ty in range(0,height,tile_height):
        for tx in range(0,width,8):
            for y in range(tile_height):
                for x in range(8):
                    if bits==8:
                        index=data[position];position+=1
                    else:
                        index=(data[position]>>4) if x%2==0 else (data[position]&15)
                        if x%2:position+=1
                    if index>=len(colors):raise ValueError('Palette index out of bounds')
                    offset=((ty+y)*width+tx+x)*4
                    out[offset:offset+4]=bytes(colors[index])
    return bytes(out)


def rgb565(value):
    r,g,b=(value>>11)&31,(value>>5)&63,value&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2),255)


def tiled_rgb565(data,width,height):
    """GX_RGB565(format4): 4x4 tiles, big-endian5R/6G/5B, opaque alpha."""
    if width<=0 or height<=0 or width%4 or height%4 or len(data)!=width*height*2:
        raise ValueError('Invalid RGB565 dimensions or size')
    output=bytearray(width*height*4)
    offset=0
    for ty in range(0,height,4):
        for tx in range(0,width,4):
            for y in range(4):
                for x in range(4):
                    value=(data[offset]<<8)|data[offset+1]
                    at=((ty+y)*width+tx+x)*4
                    output[at:at+4]=bytes(rgb565(value));offset+=2
    return bytes(output)


def rgba8(data,width,height):
    """GX RGBA8: 4x4 tiles, 32-byte AR plane followed by GB plane."""
    if width<=0 or height<=0 or width%4 or height%4 or len(data)!=width*height*4:
        raise ValueError('Invalid RGBA8 dimensions or size')
    out=bytearray(len(data));at=0
    for ty in range(0,height,4):
        for tx in range(0,width,4):
            for i in range(16):
                dst=((ty+i//4)*width+tx+i%4)*4
                out[dst:dst+4]=bytes((data[at+i*2+1],data[at+32+i*2],data[at+33+i*2],data[at+i*2]))
            at+=64
    return bytes(out)


def cmpr(data,width,height):
    """GameCube CMPR: 8x8 macrotiles containing four big-endian DXT1 blocks."""
    if width<=0 or height<=0 or width%8 or height%8 or len(data)!=width*height//2:
        raise ValueError('Invalid CMPR dimensions or size')
    out=bytearray(width*height*4);position=0
    for ty in range(0,height,8):
        for tx in range(0,width,8):
            for bx,by in ((0,0),(4,0),(0,4),(4,4)):
                a,b=struct.unpack_from('>HH',data,position)
                colors=[rgb565(a),rgb565(b)]
                if a>b:
                    colors += [tuple((2*colors[0][i]+colors[1][i])//3 for i in range(3))+(255,),
                               tuple((colors[0][i]+2*colors[1][i])//3 for i in range(3))+(255,)]
                else:
                    colors += [tuple((colors[0][i]+colors[1][i])//2 for i in range(3))+(255,),(0,0,0,0)]
                for y in range(4):
                    selectors=data[position+4+y]
                    for x in range(4):
                        color=colors[(selectors>>(6-2*x))&3]
                        offset=((ty+by+y)*width+tx+bx+x)*4
                        out[offset:offset+4]=bytes(color)
                position+=8
    return bytes(out)


def png_rgba(rgba, width, height):
    if width <= 0 or height <= 0 or len(rgba) != width * height * 4:
        raise ValueError('Invalid RGBA dimensions/byte length')
    def chunk(kind, payload):
        return (struct.pack('>I', len(payload)) + kind + payload +
                struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff))
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('banner', type=Path)
    parser.add_argument('output_png', type=Path)
    args = parser.parse_args()
    rgba = banner_rgba(args.banner.read_bytes())
    # Exclusive creation protects existing results and input files.
    with args.output_png.open('xb') as output:
        output.write(png_rgba(rgba, 96, 32))
    print(f'Decoded 96x32 RGB5A3 banner: {args.output_png}')
