#!/usr/bin/env python3
"""Pack proven destination centers/actions; no invented shop purchases or warp."""
import argparse,json,math,struct,zlib,hashlib
from pathlib import Path
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=json.loads(a.catalog.read_text());rows=[];kinds={'safehouse':1,'customshop':2,'carlot':3,'race_entry':4}
 for d in sorted(r['destinations']+r['race_entries'],key=lambda d:int(d['key'],16)):
  kind=kinds[d['kind']];respawn=d.get('respawn');pos=d['position_source'];radius=d['radius_source']
  if len(pos)!=3 or not all(math.isfinite(x) for x in (*pos,radius)) or radius<=0:raise ValueError('Invalid source hotspot')
  for name,values in [('position_provenance',pos),('radius_provenance',[radius])]:
   if struct.pack('>'+str(len(values))+'f',*values).hex()!=d[name]['original_bytes']:raise ValueError('Source float mismatch')
  rows.append(struct.pack('<II4fIII4fIII',int(d['key'],16),kind,*pos,radius,d['bin_index'],int(d.get('event_key','0'),16),int(respawn['key'],16) if respawn else 0,*(respawn['position_source'] if respawn else [0,0,0]),respawn['rotation_source_degrees'] if respawn else 0,d.get('original_frontend_mode',0),0,0))
 data=bytearray(96)+b''.join(rows);struct.pack_into('<4s7I',data,0,b'NFD1',1,len(data),0,len(rows),96,64,0)
 data[32:64]=bytes.fromhex(r['source_sha256']['gameplay']);data[64:96]=bytes.fromhex(r['source_sha256']['dol']);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
 if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('Existing output differs')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if not a.output.exists():a.output.write_bytes(data)
 print(json.dumps({'records':len(rows),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
