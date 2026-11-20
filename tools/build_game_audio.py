#!/usr/bin/env python3
"""Lossless native PCM packet writer; original audio remains private."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import wave
import zlib

def encode(wav, output, source_sha256, *, loop_start=None, loop_end=None, reference_rpm=0, native_loop=False):
    source=bytes.fromhex(source_sha256)
    if len(source)!=32 or not any(source):raise ValueError('Original source SHA256 required')
    with wave.open(str(wav),'rb') as f:
        channels,rate,frames=f.getnchannels(),f.getframerate(),f.getnframes()
        if f.getsampwidth()!=2 or channels not in (1,2) or not 8000<=rate<=48000 or not 0<frames<=0x10000000:raise ValueError('Unsupported source PCM')
        pcm=f.readframes(frames)
    if len(pcm)!=frames*channels*2:raise ValueError('Truncated PCM')
    if channels==1:pcm=b''.join(pcm[i:i+2]*2 for i in range(0,len(pcm),2))
    flags=0
    if loop_start is not None or loop_end is not None:
        if loop_start is None or loop_end is None or not 0<=loop_start<loop_end<=frames:raise ValueError('Invalid loop')
        flags=3 if native_loop else 1
    elif native_loop:raise ValueError('Native loop requires explicit bounds')
    blocks=(frames+4095)//4096
    table=b''.join(struct.pack('<I',zlib.crc32(pcm[i*16384:(i+1)*16384])) for i in range(blocks))
    at=(128+len(table)+31)//32*32
    header=bytearray(128)
    struct.pack_into('<4s13IfI',header,0,b'NAG1',1,at+len(pcm),0,rate,2,frames,4096,blocks,128,at,loop_start or 0,loop_end or 0,flags,reference_rpm,channels)
    header[64:96]=source;struct.pack_into('<I',header,96,zlib.crc32(table));struct.pack_into('<I',header,12,zlib.crc32(header[16:]))
    data=bytes(header)+table+bytes(at-128-len(table))+pcm
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() and output.read_bytes()!=data:raise ValueError('Existing native output differs; refusing overwrite')
    if not output.exists():output.write_bytes(data)
    return {'file':output.name,'bytes':len(data),'frames':frames,'sample_rate':rate,'original_channels':channels,'channels':2,'source_sha256':source_sha256,'wav_sha256':hashlib.sha256(Path(wav).read_bytes()).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),'loop_start':loop_start,'loop_end':loop_end,'loop_policy':'native preview' if native_loop else 'original metadata' if flags else 'none','reference_rpm':reference_rpm}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);p.add_argument('--source-sha256',required=True);p.add_argument('--loop-start',type=int);p.add_argument('--loop-end',type=int);p.add_argument('--native-loop',action='store_true');p.add_argument('--reference-rpm',type=float,default=0);a=p.parse_args()
    print(json.dumps(encode(a.wav,a.output,a.source_sha256,loop_start=a.loop_start,loop_end=a.loop_end,native_loop=a.native_loop,reference_rpm=a.reference_rpm),indent=2))
if __name__=='__main__':main()
