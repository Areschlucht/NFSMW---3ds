#!/usr/bin/env python3
"""Convert every supplied MW_MUSIC source segment, never a guessed song playlist."""
import argparse,hashlib,json,subprocess,wave
from pathlib import Path
from build_game_audio import encode

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--decoder',type=Path,required=True);a=p.parse_args();report=json.loads((a.source/'validation.json').read_text());bank=report['maps']['MW_MUSIC'];mus=a.source/'MW_MUSIC.MUS'
    if digest(mus)!=bank['sha256']['MUS']:raise ValueError('Original music stream changed')
    a.output.mkdir(parents=True,exist_ok=True);rawdir=a.output/'source-segments';wavdir=a.output/'decoded-vgmstream';native=a.output/'native-v1';rawdir.mkdir(exist_ok=True);wavdir.mkdir(exist_ok=True)
    rows=[]
    with mus.open('rb') as f:
        for row in bank['segments']:
            name=f"mw_music_{row['index']:03d}";f.seek(row['offset']);raw=f.read(row['bytes']);sha=hashlib.sha256(raw).hexdigest();clip=rawdir/(name+'.asf');wav=wavdir/(name+'.wav')
            if len(raw)!=row['bytes']:raise ValueError('Truncated source segment')
            if clip.exists() and clip.read_bytes()!=raw:raise ValueError('Existing source segment changed')
            if not clip.exists():clip.write_bytes(raw)
            if not wav.exists():subprocess.run([str(a.decoder),'-i','-o',str(wav),str(clip)],check=True,capture_output=True)
            with wave.open(str(wav),'rb') as w:
                if (w.getnframes(),w.getframerate(),w.getnchannels())!=(row['samples'],row['sample_rate'],row['channels']):raise ValueError('Decoded source count/rate/channel disagreement '+name)
            entry=encode(wav,native/(name+'.nag'),sha);entry.update(source_index=row['index'],source_offset=row['offset'],source_bytes=row['bytes'],source_mus_sha256=bank['sha256']['MUS'],declared_samples=row['samples']);rows.append(entry)
            print(name,entry['frames'],flush=True)
    out={'schema':1,'bank':'MW_MUSIC','source_mpf_sha256':bank['sha256']['MPF'],'source_mus_sha256':bank['sha256']['MUS'],'clips':rows,'segment_count':len(rows),'total_frames':sum(r['frames'] for r in rows),'limits':['Source descriptor order is a native sequential listening policy, not recovered PathFinder music state interpreter','Segments are not all complete songs; title/artist mapping remains unverified','No resampling or synthetic replacement audio; all decoded sample counts match sourceSCHl','Decoder vgmstream nativeEA-XA path; FFmpeg shorter outputs are not padded']}
    (native/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'clips':len(rows),'frames':out['total_frames'],'native_bytes':sum(r['bytes'] for r in rows)}))
if __name__=='__main__':main()
