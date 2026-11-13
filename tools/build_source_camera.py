#!/usr/bin/env python3
"""Pack original per-ecar camera profiles and authored chase tuning privately."""
import argparse,hashlib,json,math,struct,zlib
from pathlib import Path
from camera_recovery_verify import ATTR_SHA,LABELS
from camera_recovery_export import FIELDS
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

VEHICLES=('bmwm3gtre46','cobaltss','gti','is300','punto')

def build(attributes,dol,output):
    attrs=attributes.read_bytes();raw=dol.read_bytes()
    if hashlib.sha256(attrs).hexdigest()!=ATTR_SHA or hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA sources')
    db=VehicleAttributes(attrs,LABELS);im=DolImage(raw);cars=[];rows=[];provenance=[]
    for name in VEHICLES:
        vehicle=db.find('ecar',name);profiles=[];evidence=[]
        for mode,key in enumerate(FIELDS):
            ref=db.field_value(vehicle,key);p=ref['value'];row=db.find(p['class_key'],p['collection_key']);fields=db.fields(row);values=[];sources=[]
            for field in ('ANGLE','LAG','HEIGHT','LATOFFSET','FOV','STIFFNESS','TILTING'):
                source=fields[field];items=source['value']['values']
                if len(items)!=2 or not all(math.isfinite(x) for x in items):raise ValueError('Bad source profile array')
                if field=='TILTING':values.extend(int(x) for x in items)
                else:values.extend(items)
                sources.append(source)
            profiles.append(struct.pack('<12f2I',*values));evidence.append({'mode':mode,'profile_key':f'{row["key"]:08x}','reference':ref,'fields':sources})
        rows.append((vehicle['key'],name,b''.join(profiles)));provenance.append({'ecar_key':f'{vehicle["key"]:08x}','name':name,'profiles':evidence})
    rows.sort();profile_at=128+len(rows)*48;tuning_at=profile_at+len(rows)*7*56;profiles=b''.join(r[2] for r in rows);tunings=bytearray();samples=[]
    for mode in range(7):
        at=0x80416578+mode*0x160;data=im.read(at,352);values=struct.unpack('>88f',data)
        if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite original tuning')
        tunings.extend(struct.pack('<88f',*values));samples.append({'mode':mode,'address':f'{at:08x}','source_sha256':hashlib.sha256(data).hexdigest()})
    for i,(key,name,data) in enumerate(rows):cars.append(struct.pack('<4I32s',key,profile_at+i*7*56,7,0,name.encode('ascii')))
    data=bytearray(128)+b''.join(cars)+profiles+tunings;struct.pack_into('<4s11I',data,0,b'NCP1',1,len(data),0,len(rows),128,48,profile_at,tuning_at,56,7,176)
    data[64:96]=bytes.fromhex(DOL_SHA256);data[96:128]=bytes.fromhex(ATTR_SHA);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    output.mkdir(parents=True,exist_ok=True);target=output/'camera.ncp'
    if target.exists() and target.read_bytes()!=data:raise ValueError('Existing output differs')
    if not target.exists():target.write_bytes(data)
    report={'format':'NCP1','vehicles':len(rows),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':{'attributes':ATTR_SHA,'dol':DOL_SHA256},'profiles':provenance,'tuning':samples,'limits':['Original numerical components; not complete original chase camera','Native flat controller supplies speed/velocity/basis; original controller producers, timer attenuation, camera collision and complete placement remain separate','No source asset bytes embedded in authored C']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('attributes','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=build(a.attributes,a.dol,a.output);print(json.dumps({k:r[k] for k in ('format','vehicles','bytes','sha256')}))
