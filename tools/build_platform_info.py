#!/usr/bin/env python3
"""Add source-scale/NFM binding sidecars to already validated platform exports."""
import argparse
import json
from pathlib import Path
import struct
import zlib

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
    for path in sorted(a.directory.glob('*/scene.json')):
        scene=json.loads(path.read_text());raw=(path.parent/'platform.nfm').read_bytes()
        crc=struct.unpack_from('<I',raw,24)[0]
        if zlib.crc32(raw[32:])!=crc:raise ValueError('NFM CRC differs')
        data=struct.pack('<4sIfI',b'NPS1',1,scene['normalization_scale_world'],crc)
        out=path.parent/'placement.bin'
        if out.exists() and out.read_bytes()!=data:raise ValueError('Existing placement differs')
        out.write_bytes(data)
    print('Platform source-scale sidecars verified')
