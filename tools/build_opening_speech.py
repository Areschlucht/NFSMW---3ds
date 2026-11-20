#!/usr/bin/env python3
"""Package the verified original SMS10 mono PCM as CRC-bounded stereo NVS1."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
PCM_SHA='91bdfd4259961d80a73ebc83498dfb4042e9708098fd49fab787d56c106ba458'
STREAM_SHA='a11bf14413e8d8aa3560df81f0932be090e4237523f030a94b7f2e55c860810a'
def build(pcm,output):
 mono=pcm.read_bytes()
 if len(mono)!=491606 or hashlib.sha256(mono).hexdigest()!=PCM_SHA:raise ValueError('verified original SMS10 PCM differs')
 stereo=bytearray(len(mono)*2)
 for i in range(0,len(mono),2):stereo[i*2:i*2+4]=mono[i:i+2]*2
 frames=len(mono)//2;blocks=(frames+4095)//4096
 table=b''.join(struct.pack('<I',zlib.crc32(stereo[i*16384:(i+1)*16384])) for i in range(blocks))
 audio_at=(96+len(table)+15)&~15;packet=bytearray(audio_at)+stereo
 struct.pack_into('<4s11I',packet,0,b'NVS1',1,len(packet),0,10,22050,frames,2,4096,blocks,96,audio_at)
 packet[96:96+len(table)]=table
 packet[48:80]=bytes.fromhex(STREAM_SHA);struct.pack_into('<4I',packet,80,zlib.crc32(table),65536,1,0)
 struct.pack_into('<I',packet,12,zlib.crc32(packet[16:96]))
 if output.exists() and output.read_bytes()!=packet:raise ValueError('existing speech packet differs')
 output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(packet)
 report=dict(schema=1,sms_id=10,rate=22050,frames=frames,channels=2,blocks=blocks,audio_at=audio_at,bytes=len(packet),sha256=hashlib.sha256(packet).hexdigest(),source_pcm_sha256=PCM_SHA,source_stream_sha256=STREAM_SHA,conversion='Each original signed16LE mono sample duplicated to left and right; no resampling, trimming or synthesized audio')
 output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pcm',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.pcm,a.output)))
