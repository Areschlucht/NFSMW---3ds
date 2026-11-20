#!/usr/bin/env python3
"""Decode inventory-admitted EA banks once, retaining original loop metadata.

Uses the pinned workspace vgmstream CLI; no original sounds are authored or
synthesized. Raw GIN ramps are not mislabeled as looped engine playback.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,subprocess,wave
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def metadata(cli,path,index):
 result=subprocess.run([str(cli),'-m','-s',str(index),str(path)],capture_output=True,text=True,timeout=20)
 if result.returncode:raise ValueError(result.stderr.strip() or result.stdout.strip())
 text=result.stdout
 def number(label,required=True):
  m=re.search(r'^'+re.escape(label)+r': (\d+)',text,re.M)
  if m:return int(m.group(1))
  if required:raise ValueError('Missing decoder '+label)
  return None
 count=number('stream count',False) or 1;frames=number('stream total samples')
 if count>1024 or frames>44100*600:raise ValueError('Unbounded stream count/duration')
 return dict(rate=number('sample rate'),channels=number('channels'),frames=frames,streams=count,loop_start=number('loop start',False),loop_end=number('loop end',False),decoder_metadata=text)
def decode_one(args,row):
 source=args.root/row['file'];out=args.root/'decoded';out.mkdir(exist_ok=True)
 if sha(source.read_bytes())!=row['sha256']:raise ValueError('Original bank changed')
 summary={'source':row,'streams':[]};errors=[]
 try:first=metadata(args.decoder,source,1)
 except (ValueError,subprocess.TimeoutExpired) as exc:return {'source':row,'error':str(exc)}
 for i in range(1,first['streams']+1):
  try:
   m=first if i==1 else metadata(args.decoder,source,i)
   path=out/f'{row["hash"]}_{i:03d}.wav'
   if not path.exists():
    result=subprocess.run([str(args.decoder),'-i','-s',str(i),'-o',str(path),str(source)],capture_output=True,text=True,timeout=40)
    if result.returncode:raise ValueError(result.stderr.strip() or result.stdout.strip())
   with wave.open(str(path),'rb') as w:
    if (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())!=(m['rate'],m['channels'],2,m['frames']):raise ValueError('Decoded PCM parameters differ')
    pcm=w.readframes(w.getnframes())
   m.update(index=i,file=str(path.relative_to(args.root)),sha256=sha(path.read_bytes()),pcm_sha256=sha(pcm),bytes=path.stat().st_size)
   if source.suffix=='.gin':m['limitation']='Full original RPM ramp only; grain/RPM playback tables are separate, never invent a loop'
   summary['streams'].append(m)
  except (ValueError,subprocess.TimeoutExpired,wave.Error) as exc:errors.append({'stream':i,'error':str(exc)})
 if errors:summary['errors']=errors
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--decoder',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
 report=json.loads((a.root/'inventory.json').read_text());rows=[r for r in report['resolved'] if Path(r['file']).suffix in ('.abk','.gin')]
 with ThreadPoolExecutor(max_workers=max(1,min(a.jobs,8))) as pool:results=list(pool.map(lambda row:decode_one(a,row),rows))
 out={'schema':1,'sources':report['sources'],'decoder':str(a.decoder),'decode_policy':'Original signed16LE PCM once; preserve loop metadata separately, no trimming/resampling/synthetic audio','banks':results,'counts':{'banks':len(rows),'decoded_streams':sum(len(r.get('streams',[])) for r in results),'decoded_bytes':sum(s['bytes'] for r in results for s in r.get('streams',[])),'failed_banks':sum('error'in r for r in results),'failed_streams':sum(len(r.get('errors',[])) for r in results)}}
 (a.root/'decoded-manifest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['counts'],indent=2))
