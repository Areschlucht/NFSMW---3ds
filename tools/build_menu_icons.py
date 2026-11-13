#!/usr/bin/env python3
"""Extract authentic USA GC frontend icons for the new handheld icon strip."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image
from nfs_tpk import parse
from vehicle_ppc_reference import DOL_SHA256

FRONT_SHA='bc3c7c33d8b2620deaa5506da8c43c7cecd6fa5ea3d3f369d8baf4bbee753920'
NAMES=('MAIN_ICON_CAREER','MAIN_ICON_QUICK_RACE','MAIN_ICON_CAR_SELECT',
       'MODE_ICON_CHALLENGE_SERIES','MAIN_ICON_PROFILE_MANAGER','MAIN_ICON_OPTIONS',
       'MAIN_ICON_RESUMECAREER','MAIN_ICON_NEWCAREER','INGAME_ICON_RESUME_RACE',
       'MARKER_ICON_PARTS','MARKER_ICON_PERFORMANCE','MARKER_ICON_VISUAL','ARROW')

def bhash(name):
    key=0xffffffff
    for b in name.upper().encode('ascii'):key=(key*33+b)&0xffffffff
    return key

def build(front,dol,output):
    raw=front.read_bytes();dol_raw=dol.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FRONT_SHA or hashlib.sha256(dol_raw).hexdigest()!=DOL_SHA256:
        raise ValueError('Unexpected USA sources')
    textures={t['hash']:t for t in parse(raw)};records=[];pixels=bytearray();evidence=[]
    for action,name in enumerate(NAMES,1):
        key=f'{bhash(name):08x}';t=textures[key];side=16 if action==13 else 64
        if t['name']!=name[:23] or (t['width'],t['height'])!=(side,side):raise ValueError('Source icon differs')
        rgba=t['rgba'];offset=128+len(NAMES)*32+len(pixels)
        records.append(struct.pack('<8I',action,int(key,16),side,side,offset,len(rgba),0,0));pixels.extend(rgba)
        evidence.append({'port_action':action,'source_hash':key,'full_source_name':name,
            'record_name':t['name'],'width':side,'height':side,'rgba_sha256':hashlib.sha256(rgba).hexdigest()})
    data=bytearray(128)+b''.join(records)+pixels
    struct.pack_into('<4s7I',data,0,b'NMI1',1,len(data),0,len(NAMES),128,128+len(NAMES)*32,32)
    data[32:64]=bytes.fromhex(FRONT_SHA);data[64:96]=bytes.fromhex(DOL_SHA256)
    struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    if len(data)!=198176:raise ValueError('Unexpected sidecar layout')
    output.mkdir(parents=True,exist_ok=True);target=output/'menu-icons.nmi'
    if target.exists() and target.read_bytes()!=data:raise ValueError('Existing output differs')
    if not target.exists():target.write_bytes(data)
    for row in evidence:
        t=textures[row['source_hash']];p=output/(row['source_hash']+'.png')
        if not p.exists():Image.frombytes('RGBA',(t['width'],t['height']),t['rgba']).save(p)
    report={'schema':1,'format':'NMI1','source_sha256':{'frontend':FRONT_SHA,'dol':DOL_SHA256},
        'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'icons':evidence,
        'limits':['Actual original frontend pixels; port enum/button roles are a new 3DS mapping',
            'Resume-free-roam reuses genuine INGAME_ICON_RESUME_RACE; main-menu uses original ARROW',
            'Original FEng positions, eligibility, animation and menu-camera curves are not reconstructed']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('front','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=build(a.front,a.dol,a.output);print(json.dumps({k:r[k] for k in ('format','bytes','sha256')}))
