#!/usr/bin/env python3
"""Export five source-graph-verified original UI clips through NAG1 writer."""
import argparse,hashlib,json,wave,zlib
from pathlib import Path
from build_game_audio import encode
from game_audio_event_reference import BANK_SHA,DOL_SHA256
SELECTIONS={'accept':4,'back':5,'up':0,'left':2,'wrong':7}
def build(root,output):
 reference=root/'common-menu-reference.json';proof=json.loads(reference.read_text());decoded=json.loads((root/'decoded-manifest.json').read_text())
 if proof['source_bank_sha256']!=BANK_SHA or proof['dol_sha256']!=DOL_SHA256 or proof['count']!=69:raise ValueError('Original common sound graph reference differs')
 bank=next(r for r in decoded['banks'] if r['source']['sha256']==BANK_SHA);clips=[]
 for name,selector in SELECTIONS.items():
  selection=next(r for r in proof['selections'] if r['selector']==selector)
  cases=[r for r in proof['cases'] if r['selector']==selector]
  if len(cases)!=3 or any(r['bank_sample']!=selection['bank_sample'] for r in cases):raise ValueError('Incomplete source selection proof')
  stream=next(r for r in bank['streams'] if r['index']==selection['decoder_subsong']);wav=root/stream['file']
  if hashlib.sha256(wav.read_bytes()).hexdigest()!=stream['sha256']:raise ValueError('Original decoded clip changed')
  with wave.open(str(wav),'rb') as f:pcm=f.readframes(f.getnframes())
  clip=encode(wav,output/f'ui_{name}.nag',BANK_SHA)
  clip.update(name=name,source_selector=selector,source_bank_sample=selection['bank_sample'],source_decoder_subsong=stream['index'],original_pcm_sha256=hashlib.sha256(pcm).hexdigest(),original_pcm_crc32=f'{zlib.crc32(pcm):08x}',original_graph_reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest());clips.append(clip)
 report={'schema':1,'source':'Original USA GameCube FE_COMMON_MB bank; original common-menu sound graph verified offline','source_bank_sha256':BANK_SHA,'source_dol_sha256':DOL_SHA256,'original_reference_cases':69,'clips':clips,'limits':['No fabricated direction aliases; original down/right/pause selectors reach unmapped BNKsample0','Resident clip playback is a native port adapter; original full AEMS envelope/mix timing remains separate']}
 output.mkdir(parents=True,exist_ok=True);(output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build(a.root,a.output);print(json.dumps({'clips':len(r['clips']),'bytes':sum(c['bytes'] for c in r['clips'])}))
