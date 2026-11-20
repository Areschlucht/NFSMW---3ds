#!/usr/bin/env python3
"""Wrap exact original GIN banks and authoritative pvehicle engineaudio bindings."""
import argparse,hashlib,json,math,struct,zlib
from pathlib import Path
ATTR='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
DOL='33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
def text(value,n):
 raw=value.encode('ascii')
 if len(raw)>=n or any(x<32 or x>126 for x in raw):raise ValueError('Invalid bounded source text')
 return raw+bytes(n-len(raw))
def build(source,output):
 inv=json.loads((source/'inventory.json').read_text())
 if inv['sources']['attributes']!=ATTR or inv['sources']['dol']!=DOL:raise ValueError('Unexpected source identity')
 output.mkdir(parents=True,exist_ok=True);banks={};records=[];by_file={}
 for row in inv['resolved']:
  if not row['file'].lower().endswith('.gin'):continue
  raw=(source/row['file']).read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if sha!=row['sha256'] or raw[:8]!=b'Gnsu20\0\0':raise ValueError('Original GIN changed')
  header=bytearray(96);struct.pack_into('<4s7I',header,0,b'NGI1',1,96+len(raw),0,len(raw),zlib.crc32(raw),struct.unpack_from('<I',raw,28)[0],struct.unpack_from('<I',raw,24)[0]);header[32:64]=bytes.fromhex(sha);struct.pack_into('<I',header,12,zlib.crc32(header[16:]));data=bytes(header)+raw
  name=Path(row['file']).stem+'.ngi';target=output/name;target.write_bytes(data);banks[row['candidate_name'].rsplit('\\',1)[-1].lower()]=name
  if name in by_file:
   if by_file[name]['sha256']!=hashlib.sha256(data).hexdigest():raise ValueError('Conflicting source bank alias')
   by_file[name]['source_aliases'].append(row)
  else:
   record={'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_aliases':[row],'sample_rate':struct.unpack_from('<I',raw,28)[0]};by_file[name]=record;records.append(record)
 engines={e['key']:e for e in inv['engineaudio']};rows=[];bindings=[]
 for vehicle in sorted(inv['vehicle_bindings'],key=lambda v:v['physical_profile']):
  ref=vehicle['engineaudio']['value']['values'][0];e=engines[f"{ref['collection_key']:08x}"];f=e['fields']
  val=lambda key,default=0:f.get(key,{}).get('value',default)
  filename=lambda key:banks.get(val(key,{}).get('text','').lower(),'') if isinstance(val(key,{}),dict) else ''
  accel,decel=filename('Filename_GinsuAccel'),filename('Filename_GinsuDecel');minimum,maximum=float(val('MinRPM')),float(val('MaxRPM'));flags=int(bool(accel))+2*int(bool(decel))+4*int(minimum>0 and maximum>minimum)
  row=bytearray(192);row[:32]=text(vehicle['model']['text'],32);row[32:80]=text(vehicle['physical_profile'],48);row[80:96]=text(accel,16);row[96:112]=text(decel,16);row[112:144]=text(e['name'],32)
  struct.pack_into('<IIffIIIIffII',row,144,int(vehicle['physical_key'],16),int(e['key'],16),minimum,maximum,int(val('CarID')),int(val('Master_Vol')),int(val('GINSUAccelVol')),int(val('GinsuDecelVol')),float(val('GINSU_Decel_MinRPM')),float(val('GINSU_Decel_MaxRPM')),flags,0);rows.append(bytes(row));bindings.append(dict(profile=vehicle['physical_profile'],model=vehicle['model']['text'],engineaudio=e['name'],accel=accel,decel=decel,minimum_rpm=minimum,maximum_rpm=maximum,flags=flags,source_engineaudio=e,source_vehicle=vehicle))
 data=bytearray(96)+b''.join(rows);struct.pack_into('<4s7I',data,0,b'NGB1',1,len(data),0,len(rows),96,192,0);data[32:64]=bytes.fromhex(ATTR);data[64:96]=bytes.fromhex(DOL);struct.pack_into('<I',data,12,zlib.crc32(data[16:]));(output/'bindings.ngb').write_bytes(data)
 result={'schema':1,'sources':inv['sources'],'banks':records,'bindings':bindings,'bank_count':len(records),'binding_count':len(rows),'limits':['Original Ginsu numeric core and bank identity; complete HybridMotor gain/load/Doppler/shift/noise layers remain separate','Audio input is engine controllerRPM calibrated1000..10000→engineaudioMin/Max, not vehicle speed-derived guesses','Physical profile must be selected explicitly; visual car name alone can have multiple original sound variants']};(output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build(a.source,a.output);print(json.dumps({'banks':r['bank_count'],'bindings':r['binding_count']}))
