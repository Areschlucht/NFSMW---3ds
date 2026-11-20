#!/usr/bin/env python3
"""Inventory original audio bindings and resolve/extract exact ZDIR assets.

All extracted banks and decoded audio are private. Candidate archive names are
admitted only by exact original filename hash matches; their semantic call sites
are retained separately from native playback policy.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from audit_whole_game import directory_records,name_hash,ZDIR_SHA,ATTR_SHA
from extract_music_streams import extract
from mw_debug_info import DebugInfo
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash

ELF_SHA='6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7'
EXTENSIONS=('.abk','.gin','.gin3','.gin34','.big','.csi','.idx','.evt','.mpf','.mus')
PREFIXES=('','SOUND\\','SOUND\\Engine\\','SOUND\\evt_sys\\','SOUND\\FE\\','SOUND\\Global\\','SOUND\\IG_Global\\','SOUND\\NOS\\','SOUND\\PFData\\','SOUND\\Skids\\','SOUND\\Speech\\','SOUND\\Turbo\\','SOUND\\Shifting\\','SOUND\\FXEdit\\')

def digest(data):return hashlib.sha256(data).hexdigest()
def strings(value):
 if isinstance(value,dict):
  if isinstance(value.get('text'),str):yield value['text']
  for v in value.values():yield from strings(v)
 elif isinstance(value,list):
  for v in value:yield from strings(v)
def checked(path,wanted):
 data=path.read_bytes()
 if digest(data)!=wanted:raise ValueError('Original source hash differs: '+str(path))
 return data

def inventory(args):
 raw=checked(args.attributes,ATTR_SHA);zdir=checked(args.zdir,ZDIR_SHA)
 checked(args.elf,ELF_SHA)
 labels=set();layouts={}
 with DebugInfo(args.elf) as debug:
  for typ in ['engineaudio','audiosystem','acceltrans','audioimpact','audioscrape','turbosfx']:
   entries=[c for e in debug.find(typ,tags={2,19}) for c in debug.children(e) if c.name=='_LayoutStruct']
   if not entries:continue
   members=max((debug.members(e) for e in entries),key=len)
   layouts[typ]={m['name']:m['offset'] for m in members};labels.update(m['name'] for m in members)
 db=VehicleAttributes(raw,labels)
 engine=[];bindings=[];audio_fields=[];errors=[];filenames=set()
 for (class_key,key),row in db.collections.items():
  typ=db.label(class_key);fields={}
  # Read independent known definitions; a malformed optional field does not
  # suppress valid source banks or hide the exact rejected field.
  for field_key in db.classes[class_key]['fields']:
   try:field=db.field_value(row,field_key)
   except KeyError:continue
   except (ValueError,struct.error) as exc:
    errors.append({'class':typ,'collection':db.label(key),'field':db.label(field_key),'error':str(exc)});continue
   fields[db.label(field_key)]=field
   for text in strings(field['value']):
    if text.lower().endswith(EXTENSIONS):filenames.add(text)
  if typ=='engineaudio':engine.append({'key':f'{key:08x}','name':db.label(key),'fields':fields})
  if typ=='pvehicle':
   f=fields.get('engineaudio')
   if f:bindings.append({'physical_key':f'{key:08x}','physical_profile':db.label(key),'model':fields.get('MODEL',{}).get('value'),'engineaudio':f})
  if any(t in typ.lower() for t in ('audio','sound','speech','sfx')):audio_fields.append({'class':typ,'name':db.label(key),'key':f'{key:08x}','fields':fields})
 # Original compiled defaults supplement actual vault strings, but do not
 # establish that every compiled debug/default filename is shipped.
 dol=args.dol.read_bytes()
 for text in re.findall(rb'[ -~]{4,}\x00',dol):
  s=text[:-1].decode('ascii')
  if s.lower().endswith(EXTENSIONS):filenames.add(s)
 records=directory_records(zdir);bykey={};resolved=[];missing=[]
 for record in records:bykey.setdefault(record['hash'],[]).append(record)
 for leaf in sorted(filenames):
  candidates={leaf} if '\\' in leaf else {prefix+leaf for prefix in PREFIXES}
  hits=[]
  for name in sorted(candidates):
   records_for_name=bykey.get(f'{name_hash(name):08x}',[])
   if len(records_for_name)>1:raise ValueError('Ambiguous original audio archive hash: '+name)
   if records_for_name:hits.append({'candidate_name':name,'name_evidence':'original attribute/compiled filename with exact archive hash',**records_for_name[0]})
  if hits:resolved.extend(hits)
  else:missing.append(leaf)
 unique={r['hash']:r for r in resolved};header_inventory=[]
 # Complete top-level sound-bank coverage: unreferenced banks remain explicitly
 # unnamed and are never assigned an invented vehicle or event identity.
 magic_extensions={b'ABKC':'.abk',b'Gnsu':'.gin',b'Octn':'.gin',b'MOIR':'.csi'}
 for archive in range(4):
  with (args.archives/f'ZZDATA{archive}.BIN').open('rb') as f:
   for record in records:
    if record['archive']!=archive or record['bytes']<4:continue
    f.seek(record['offset_bytes']);magic=f.read(4)
    if magic not in magic_extensions:continue
    header_inventory.append({**record,'magic':magic.decode('ascii'),'named':record['hash'] in unique})
    if record['hash'] in unique:continue
    if len(bykey[record['hash']])!=1:raise ValueError('Ambiguous header-admitted audio record')
    unique[record['hash']]={'candidate_name':'@UNNAMED/'+record['hash']+magic_extensions[magic], 'name_evidence':'original bank header only; original path unresolved',**record}
 args.output.mkdir(parents=True,exist_ok=True);bankdir=args.output/'original';bankdir.mkdir(exist_ok=True)
 for r in unique.values():
  ext=Path(r['candidate_name']).suffix.lower();target=bankdir/(r['hash']+ext)
  r['sha256']=extract(args.archives/f'ZZDATA{r["archive"]}.BIN',r,target);r['file']=str(target.relative_to(args.output))
 report={'schema':1,'sources':{'attributes':ATTR_SHA,'zdir':ZDIR_SHA,'elf':ELF_SHA,'dol':digest(dol)},'debug_layouts':layouts,'engineaudio':engine,'vehicle_bindings':bindings,'audio_collections':audio_fields,'header_inventory':header_inventory,'resolved':sorted(unique.values(),key=lambda r:r['candidate_name']),'missing_candidates':missing,'rejected_fields':errors,'counts':{'engineaudio':len(engine),'vehicles_with_engineaudio':len(bindings),'resolved_files':len(unique),'resolved_bytes':sum(r['bytes'] for r in unique.values()),'extension_counts':dict(Counter(Path(r['candidate_name']).suffix.lower() for r in unique.values()))},'limits':['Archive hash match is path evidence, not proof that an event is admitted at runtime','Ginsu RPM grain synthesis/mix and ABK event identities require their own source consumers','Rejected optional fields are retained, never silently coerced to defaults']}
 (args.output/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['attributes','zdir','dol','elf','archives','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();r=inventory(a);print(json.dumps(r['counts'],indent=2))
