#!/usr/bin/env python3
"""Pack exact opening SpawnCop poses and Width triggers for two-cop native AI.

The Lua call ordering/ownership is recovered by build_opening_career.py. This
tool independently matches every exported spatial scalar against pinned bytes.
It creates no road points, replacement police cars or guessed spherical triggers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from vehicle_attributes import VehicleAttributes,vlt_hash
from vehicle_ppc_reference import DOL_SHA256

GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'
ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
PLANS=[{'event':0x6ddd8383,'spawns':['993840ea','0a54490f'],'triggers':[('8760f956',1),('04045a5c',2),('c55b4cba',4)]},
       {'event':0xf7e4440a,'spawns':['52d38e96','5d691cb3'],'triggers':[('b14f35ba',1),('a2568789',2)]}]


def sha(b):return hashlib.sha256(b).hexdigest()
def checked_field(row,key,value,raw):
    f=row['source_fields'][str(key)];original=bytes.fromhex(f['original_bytes']);at=f['file_offset']
    values=value if isinstance(value,list) else [value]
    expected=struct.pack('>'+str(len(values))+'f',*values)
    if f['source_sha256']!=GAMEPLAY_SHA or f['value']!=value or raw[at:at+len(original)]!=original or expected!=original:raise ValueError('Original pursuit spatial field mismatch')
    return f


def build(a):
    evidence=json.loads(a.evidence.read_text());gameplay=a.gameplay.read_bytes();attributes=a.attributes.read_bytes();dol=a.dol.read_bytes()
    if sha(gameplay)!=GAMEPLAY_SHA or sha(attributes)!=ATTR_SHA or sha(dol)!=DOL_SHA256:raise ValueError('Unexpected original pursuit sources')
    nodes={n['key']:n for n in evidence['opening_police_nodes']}
    db=VehicleAttributes(attributes,labels=['TopSpeedMultiplier','AccelerationMultiplier']);cls=vlt_hash('pvehicle');key=vlt_hash('copmidsize');vehicle=db.fields(db.collections[cls,key]);model=vehicle['MODEL']['value']['text']
    if model!='COPMIDSIZE':raise ValueError('Original SpawnCop model differs')
    ref=vehicle['aivehicle']['value'];ai=db.fields(db.collections[ref['class_key'],ref['collection_key']])
    top=ai['TopSpeedMultiplier']['value'];accel=ai['AccelerationMultiplier']['value'];unknown=ai['0x7ca3d0a5']['value'];events=[];spawns=[];triggers=[];provenance=[]
    for plan in PLANS:
        first_spawn=len(spawns);first_trigger=len(triggers)
        for node_key in plan['spawns']:
            n=nodes[node_key]
            if n['present']!=3 or n['width'] or n['radius'] or any(n['dimensions']):raise ValueError('Original cop spawn must be a pose')
            pf=checked_field(n,vlt_hash('Position'),n['position'],gameplay);rf=checked_field(n,vlt_hash('Rotation'),n['rotation'],gameplay)
            spawns.append(struct.pack('<II4fII',int(node_key,16),key,*n['position'],n['rotation'],0,0))
            provenance.append({'event':f'{plan["event"]:08x}','role':'spawn','key':node_key,'position':pf,'rotation':rf})
        for node_key,action in plan['triggers']:
            n=nodes[node_key]
            if n['present']!=19 or n['radius'] or any(n['dimensions']) or n['width']<=0:raise ValueError('Original pursuit trigger must be Width-only')
            pf=checked_field(n,vlt_hash('Position'),n['position'],gameplay);rf=checked_field(n,vlt_hash('Rotation'),n['rotation'],gameplay);wf=checked_field(n,vlt_hash('Width'),n['width'],gameplay)
            triggers.append(struct.pack('<II5fI',int(node_key,16),action,*n['position'],n['rotation'],n['width'],0))
            provenance.append({'event':f'{plan["event"]:08x}','role':'trigger','key':node_key,'action':action,'position':pf,'rotation':rf,'width':wf})
        events.append(struct.pack('<8I',plan['event'],first_spawn,2,first_trigger,len(plan['triggers']),0,0,0))
    data=bytearray(160)+b''.join(events+spawns+triggers)
    if len(data)!=512:raise ValueError('Unexpected native pursuit shape')
    struct.pack_into('<4s10I',data,0,b'NPP1',1,len(data),0,2,160,224,4,352,5,key)
    struct.pack_into('<3f',data,48,top,accel,unknown);data[64:96]=bytes.fromhex(GAMEPLAY_SHA);data[96:128]=bytes.fromhex(ATTR_SHA);data[128:160]=bytes.fromhex(DOL_SHA256);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    a.output.mkdir(parents=True,exist_ok=True);path=a.output/'opening-pursuit.npp'
    if path.exists() and path.read_bytes()!=data:raise ValueError('Existing pursuit packet differs')
    if not path.exists():path.write_bytes(data)
    report={'schema':1,'sha256':sha(data),'bytes':len(data),'source_sha256':{'gameplay':GAMEPLAY_SHA,'attributes':ATTR_SHA,'dol':DOL_SHA256},'plans':PLANS,'model':model,'model_key':f'{key:08x}','source_vehicle_fields':vehicle,'source_ai_fields':ai,'spatial_provenance':provenance,'limits':['Native two-cop chase is a port policy, not original steering/tactics','Source AI multipliers retained separately; unresolved speed field280 has no invented units','Original SpawnCop flags are false,false; actor physics uses existing provisional native controller','Width boxes use shared native swept actor proxy, not original actor OBB','911 is an emitted source action; original audio/call progression remains caller-owned','No new pursuit/spawn after source bail action; released cars coast as a native policy']}
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'bytes':len(data),'sha256':sha(data),'cop_model':model,'source_top_speed_multiplier':top,'source_acceleration_multiplier':accel}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('evidence','gameplay','attributes','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    build(p.parse_args())
