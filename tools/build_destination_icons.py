#!/usr/bin/env python3
"""Extract authentic GC mini-map art into a bounded native RGBA sidecar.

Does not claim original mini-map actor bindings or 3D FX animation recovered.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image
from nfs_tpk import parse
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

SOURCE_SHA='0e3543f534cb94b113168a1b5f6b7a7224b32d12986fb18253b937f16c293d79'
ROWS=((1,-1,'2cfd5273','MINIMAP_ICON_SAFE_HOUSE',16),
      (2,-1,'1ce551d4','MINIMAP_ICON_CHOP_SHOP',16),
      (3,-1,'12bb8395','MINIMAP_ICON_CAR_LOT',16),
      (4,0,'571cd206','MINIMAP_ICON_POINT_TO_POINT',8),
      (4,1,'25559384','MINIMAP_ICON_CIRCUIT',16))

def bhash(name):
    key=0xffffffff
    for b in name.upper().encode('ascii'):key=(key*33+b)&0xffffffff
    return key

def build(ingamea,dol,output):
    source=ingamea.read_bytes();raw=dol.read_bytes()
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA or hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA source')
    if output.exists():raise ValueError('Use a fresh output directory')
    textures={r['hash']:r for r in parse(source)};records=[];pixels=bytearray();evidence=[]
    for kind,event,key,name,side in ROWS:
        if f'{bhash(name):08x}'!=key:raise ValueError('Original full-name/hash mismatch')
        r=textures[key]
        if (r['width'],r['height'])!=(side,side) or r['name']!=name[:23]:raise ValueError('Unexpected texture descriptor')
        rgba=r['rgba']
        if len(rgba)!=side*side*4:raise ValueError('Decoded pixel length mismatch')
        records.append(struct.pack('<8I',kind,event&0xffffffff,int(key,16),side,side,256+len(pixels),len(rgba),0));pixels.extend(rgba)
        evidence.append({'kind':kind,'original_event_type':event,'source_hash':key,'full_source_name':name,'source_record_name':r['name'],
            'width':side,'height':side,'rgba_sha256':hashlib.sha256(rgba).hexdigest(),
            'nonzero_alpha_pixels':sum(a!=0 for a in rgba[3::4]),'partial_alpha_pixels':sum(0<a<255 for a in rgba[3::4]),
            'source_texture_descriptor':{k:v for k,v in r.items() if k!='rgba'}})
    data=bytearray(96)+b''.join(records)+pixels
    if len(data)!=4608:raise ValueError('Native sidecar length differs')
    struct.pack_into('<4s7I',data,0,b'NFI1',1,len(data),0,5,96,256,32);data[32:64]=bytes.fromhex(DOL_SHA256);data[64:96]=bytes.fromhex(SOURCE_SHA)
    struct.pack_into('<I',data,12,zlib.crc32(data[96:]));output.mkdir(parents=True)
    for row,r in zip(ROWS,evidence):
        key=row[2];Image.frombytes('RGBA',(r['width'],r['height']),textures[key]['rgba']).save(output/(key+'.png'))
    (output/'destination-icons.nfi').write_bytes(data)
    im=DolImage(raw)
    report={'schema':1,'source_sha256':{'ingamea':SOURCE_SHA,'dol':DOL_SHA256},'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
      'icons':evidence,'original_consumer_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(im.read(a,b-a)).hexdigest()} for a,b in [(0x80162a78,0x80162b14),(0x80162b14,0x80162bac)]],
      'limits':['Authentic original mini-map pixels; role assignment is a documented 3DS overlay binding',
                'Original location selector directly binds WORLD_*32x32 icons; race selector binds MODE_ICON_*64x64 icons',
                'Original mini-map-specific consumer and 3D FX producer are not recovered by name/hash matching',
                'No native game assets are removed or race availability inferred','Unknown race types return no icon']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('ingamea','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=build(a.ingamea,a.dol,a.output);print(json.dumps({'icons':len(r['icons']),'bytes':r['bytes'],'sha256':r['sha256']}))
