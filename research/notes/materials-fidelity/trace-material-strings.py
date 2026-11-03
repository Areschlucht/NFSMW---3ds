from pathlib import Path
import sys,struct,re,json
sys.path.insert(0,'/workspace/port-research')
from inspect_dol import inspect
p=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol');d=p.read_bytes();sections=inspect(p)['sections']
def address(off):
 for s in sections:
  if s['offset']<=off<s['offset']+s['size']:return s['address']+off-s['offset']
 raise ValueError(off)
strings={address(m.start()):m.group().decode() for m in re.finditer(rb'[\x20-\x7e]{4,}',d) if 0x408300<=m.start()<0x409c00}
xrefs=[]
for s in sections:
 if not s['name'].startswith('text'):continue
 high={}
 for off in range(s['offset'],s['offset']+s['size'],4):
  word=struct.unpack_from('>I',d,off)[0];op=word>>26;rt=(word>>21)&31;ra=(word>>16)&31;imm=word&65535;signed=imm-65536 if imm&32768 else imm
  if op==15 and ra==0:high[rt]=(imm<<16,off)
  elif op==14 and ra in high:
   value,hi=high[ra];target=(value+signed)&0xffffffff
   if off-hi<=40 and target in strings:xrefs.append(dict(instruction=hex(address(off)),high_instruction=hex(address(hi)),target=hex(target),text=strings[target]))
  if op in (18,19):high={}
Path('/workspace/port-research/materials-fidelity/string-xrefs.json').write_text(json.dumps(xrefs,indent=2)+'\n')
for x in xrefs:
 if any(q in x['text'] for q in ['SKIN','HEADLIGHT','BRAKELIGHT','VINYL','PREVINYL','_ON','_OFF']):print(x)
