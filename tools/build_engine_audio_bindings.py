#!/usr/bin/env python3
"""Join original MODEL/ecar and upgrade-indexed engineaudio references.

Physical collection names are never guessed from the displayed/visual car ID.
The actual pvehicle MODEL field joins case-insensitively to actual ecar original
CollectionName text, and each sound upgrade preserves its RefSpec array index.
"""
import argparse,hashlib,json
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
from audit_whole_game import ATTR_SHA
CALIBRATION=('MinRPM','MaxRPM','Master_Vol','AEMSVol','GINSUAccelVol','GinsuDecelVol','GINSUMix_S_RPM','GINSUMix_L_RPM','DECEL_GINSUMix_S_RPM','DECEL_GINSUMix_L_RPM','GINSU_Decel_MinRPM','GINSU_Decel_MaxRPM','GINSU_DECEL_FADE_IN','GINSU_DECEL_FADE_OUT','Ginsu_ACL_Neg_L_RPM','AccelDeltaRPMThreshold','DecelDeltaRPMThreshold','CarID','EngType')
def build(args):
 inv=json.loads((args.root/'inventory.json').read_text());raw=args.attributes.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Original attributes changed')
 db=VehicleAttributes(raw);ecars={}
 for (kind,key),row in db.collections.items():
  if kind!=vlt_hash('ecar'):continue
  try:name=db.field_value(row,'CollectionName')['value']
  except KeyError:continue
  if not isinstance(name,str):raise ValueError('ecarCollectionName is not text')
  ecars.setdefault(name.casefold(),[]).append({'key':f'{key:08x}','collection_name':name})
 audio={e['key']:e for e in inv['engineaudio']};resolved=inv['resolved'];bindings=[];errors=[]
 def asset(field,extension):
  text=field.get('value',{}).get('text','') if field else ''
  if not text:return None
  matches=[r for r in resolved if r['candidate_name'].replace('\\','/').split('/')[-1].casefold()==text.replace('\\','/').split('/')[-1].casefold() and r['candidate_name'].lower().endswith(extension)]
  if len(matches)>1:raise ValueError('Ambiguous source audio filename: '+text)
  if not matches:return {'original_filename':text,'present':False,'field_provenance':field}
  r=matches[0];return {'original_filename':text,'present':True,'archive_key':r['hash'],'source_sha256':r['sha256'],'original_file':r['file'],'candidate_name':r['candidate_name'],'field_provenance':field}
 for row in inv['vehicle_bindings']:
  model=row.get('model',{}).get('text');visual=ecars.get((model or '').casefold(),[])
  if len(visual)!=1:
   errors.append({'physical_key':row['physical_key'],'model':model,'error':'No unique original ecarCollectionName match'});continue
  refs=row['engineaudio']['value'];refs=refs.get('values',[refs]);slots=[]
  for index,ref in enumerate(refs):
   key=f'{ref["collection_key"]:08x}';e=audio.get(key)
   if not e:raise ValueError('Original engineaudio RefSpec target absent')
   f=e['fields'];slots.append({'upgrade_index':index,'engineaudio_key':key,'engineaudio_name':e['name'],'accel':asset(f.get('Filename_GinsuAccel'),'.gin'),'decel':asset(f.get('Filename_GinsuDecel'),'.gin'),'main_bank':asset(f.get('BankName_mainRAM'),'.abk'),'calibration':{k:f[k] for k in CALIBRATION if k in f}})
  bindings.append({**row,'visual_model':model,'ecar_key':visual[0]['key'],'ecar_collection_name':visual[0]['collection_name'],'sound_upgrades':slots})
 report={'schema':1,'source_attributes_sha256':ATTR_SHA,'source_inventory_sha256':hashlib.sha256((args.root/'inventory.json').read_bytes()).hexdigest(),'mapping_policy':'Original pvehicle.MODEL text joins unique actual ecar.CollectionName case-insensitively; physical-key and upgrade-slot are authoritative, not display names','bindings':bindings,'unbound':errors,'counts':{'physical_bindings':len(bindings),'ecars':len({b['ecar_key'] for b in bindings}),'sound_upgrade_slots':sum(len(b['sound_upgrades']) for b in bindings),'missing_accel':sum(not s['accel'] or not s['accel']['present'] for b in bindings for s in b['sound_upgrades'])},'limits':['Presence in the parameter bank is not a roster/unlock claim','Original grain/AEMS mix policy remains separate','Missing original decel filenames remain explicit; no invented replacement asset']}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['root','attributes','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=build(a);print(json.dumps(r['counts'],indent=2));print('unbound',len(r['unbound']))
