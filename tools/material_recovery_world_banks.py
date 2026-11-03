#!/usr/bin/env python3
"""Audit exact original TPK keys in complete bundles and sparse MemoryFile banks.

Sparse banks contain original header/hash tables but may omit image payloads.
A matching sparse header establishes an original bank dependency, not a ready
image provider. No arbitrary strings, payloads or missing pixels are invented.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from nfs_jdlz import decompress


def spans(data,start,logical_end):
    at=start
    while at<logical_end:
        if at+8>len(data):break
        kind,size=struct.unpack_from('<2I',data,at);stop=at+8+size
        if stop>logical_end:raise ValueError('Chunk exceeds declared original parent')
        yield kind,at+8,stop
        if stop>len(data):break
        at=stop


def texture_keys(data,logical_size=None):
    logical_size=len(data) if logical_size is None else logical_size
    if logical_size<len(data):raise ValueError('Stored bytes exceed logical file')
    result=[]
    for kind,a,b in spans(data,0,logical_size):
        if kind!=0xb3300000:continue
        metadata=[(s,e) for k,s,e in spans(data,a,b) if k==0xb3310000]
        if len(metadata)!=1:raise ValueError('Texture package metadata missing or ambiguous')
        s,e=metadata[0];fields={k:(u,v) for k,u,v in spans(data,s,e)}
        if 0x33310002 not in fields:raise ValueError('Texture key table missing')
        u,v=fields[0x33310002]
        if v>len(data) or (v-u)%8:raise ValueError('Sparse texture key table is incomplete')
        name=None
        if 0x33310001 in fields:
            h,he=fields[0x33310001]
            if h+32<=min(he,len(data)):name=data[h+4:h+32].split(b'\0')[0].decode('ascii')
        for at in range(u,v,8):
            key,word1=struct.unpack_from('<2I',data,at)
            result.append(dict(hash=f'{key:08x}',reference_word1=f'{word1:08x}',package_name=name,
                key_file_offset=at,package_offset=a-8,package_bytes=b-a+8,
                package_complete=b<=len(data)))
    return result


def memory_entries(raw):
    if len(raw)<16 or struct.unpack_from('<3I',raw)!=(0,0,0x53219999):raise ValueError('Unsupported original MemoryFile header')
    count=struct.unpack_from('<I',raw,12)[0]
    if not 0<count<=1024 or 16+count*20>len(raw):raise ValueError('Invalid MemoryFile record count')
    result=[]
    for i in range(count):
        key,offset,logical,stored,address=struct.unpack_from('<5I',raw,16+i*20)
        if offset<16+20*count or stored>logical or offset+stored>len(raw):raise ValueError('MemoryFile entry exceeds source')
        payload=raw[offset:offset+stored]
        record=dict(key=f'{key:08x}',directory_offset=16+i*20,offset=offset,logical_bytes=logical,stored_bytes=stored,
            original_address=f'{address:08x}',sha256=hashlib.sha256(payload).hexdigest())
        if payload[:4]==b'JDLZ':
            unpacked=decompress(payload);record['jdlz_decoded_bytes']=len(unpacked);record['textures']=texture_keys(unpacked)
        elif payload[:4]==struct.pack('<I',0xb3300000):record['textures']=texture_keys(payload,logical)
        else:record['textures']=[]
        result.append(record)
    return result


def audit(path,wanted):
    data=path.read_bytes();result=dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    if len(data)>=12 and struct.unpack_from('<3I',data)==(0,0,0x53219999):
        result['memory_entries']=memory_entries(data)
        keys=[dict(t,memory_entry_key=e['key']) for e in result['memory_entries'] for t in e['textures']]
    else:
        if data[:4]==b'JDLZ':data=decompress(data);result['jdlz_decoded_bytes']=len(data)
        keys=texture_keys(data)
    result['texture_key_count']=len(keys);result['matched']=[t for t in keys if t['hash'] in wanted]
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wanted',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('banks',type=Path,nargs='+')
    a=p.parse_args();wanted=set(json.loads(a.wanted.read_text()));rows=[audit(path,wanted) for path in a.banks]
    a.output.write_text(json.dumps(dict(wanted=sorted(wanted),banks=rows,unresolved=sorted(wanted-{t['hash'] for r in rows for t in r['matched']})),indent=2)+'\n')
    print([(Path(r['path']).name,r['texture_key_count'],len(r['matched'])) for r in rows])
