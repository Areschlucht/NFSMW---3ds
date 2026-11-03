#!/usr/bin/env python3
"""Clone a converted car scene with a source-derived diffuse preview.

Only one placeholder texture record changes. Geometry, UVs, draw order and wheel
rig payload are preserved. This does not implement original GX paint materials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib
from PIL import Image
from wheel_rig import inspect_rig


def apply(source, image_path, destination, provenance):
    if destination.exists():
        raise ValueError('Destination already exists; original scenes are never overwritten')
    evidence=json.loads(provenance.read_text())
    image=Image.open(image_path).convert('RGBA')
    if image.size!=(512,512) or image.getchannel('A').getextrema()!=(255,255):
        raise ValueError('Expected opaque 512x512 logical diffuse preview; GLOSS is separate')
    if evidence.get('target_hash')!='de3ad3c6' or evidence.get('width')!=512 or evidence.get('height')!=512 or hashlib.sha256(image.tobytes()).hexdigest()!=evidence.get('diffuse_rgba_sha256'):
        raise ValueError('Preview pixels do not match the canonical source manifest')
    raw=bytearray((source/'body.nfm').read_bytes())
    magic,version,nv,nb,nt,size,old_crc,reserved=struct.unpack_from('<4s7I',raw)
    stride={1:32,2:48}.get(version,0)
    if magic!=b'NFM1' or not stride or reserved or len(raw)!=size+32 or size!=nt*16+nb*16+nv*stride or zlib.crc32(raw[32:])!=old_crc:
        raise ValueError('Invalid source car scene')
    manifest=json.loads((source/'scene.json').read_text())
    if len(manifest['textures'])!=nt:
        raise ValueError('Texture manifest mismatch')
    key=0xde3ad3c6
    indices=[i for i in range(nt) if struct.unpack_from('<I',raw,32+i*16)[0]==key]
    if len(indices)!=1:
        raise ValueError('Expected exact original SKIN1 alias DE3AD3C6')
    i=indices[0];entry=manifest['textures'][i]
    if entry['hash']!='de3ad3c6' or not entry['missing']:
        raise ValueError('Only the original placeholder may be replaced')
    rig=(source/'wheels.nwa').read_bytes();inspect_rig(rig,nb,old_crc)
    old_geometry=bytes(raw[32+nt*16:])
    struct.pack_into('<4I',raw,32+i*16,key,512,512,0)
    new_crc=zlib.crc32(raw[32:]);struct.pack_into('<I',raw,24,new_crc)
    new_rig=bytearray(rig);struct.pack_into('<I',new_rig,24,new_crc)
    inspect_rig(new_rig,nb,new_crc)
    assert old_geometry==bytes(raw[32+nt*16:]) and new_rig[32:]==rig[32:]
    shutil.copytree(source,destination)
    (destination/'body.nfm').write_bytes(raw);(destination/'wheels.nwa').write_bytes(new_rig)
    entry.update(name='BMWM3GTRE46_SKIN1_LOGICAL_PREVIEW',missing=False,width=512,height=512,flags=0,
                 limitations='Native indexed-palette/quantization and full paint material remain unverified')
    manifest['unresolved']='Native paint palette/materials, remaining generated lights and fitted wheel placement'
    manifest['diffuse_preview']={'source_manifest':str(provenance),'source_manifest_sha256':hashlib.sha256(provenance.read_bytes()).hexdigest(),
        'source_image_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),'original_scene_crc':old_crc,
        'geometry_and_wheel_payload_unchanged':True,'native_palette_verified':False}
    (destination/'scene.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (destination/'paint-source-manifest.json').write_text(json.dumps(evidence,indent=2)+'\n')
    image.save(destination/'textures/de3ad3c6.png')
    (destination/'textures/de3ad3c6.t3x').unlink(missing_ok=True)
    print(destination)
    print('Convert textures/de3ad3c6.png to RGBA8 T3X before loading; geometry and wheel payload unchanged.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('image',type=Path)
    parser.add_argument('destination',type=Path);parser.add_argument('provenance',type=Path)
    args=parser.parse_args();apply(args.source,args.image,args.destination,args.provenance)
