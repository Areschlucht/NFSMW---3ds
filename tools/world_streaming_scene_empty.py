"""Incrementally preserve independently proved original empty/no-draw models.

No nonempty geometry or texture is decoded or rewritten. Original empty bounds,
160-byte headers and source aliases remain intact; animation population is not
invented. Requires the separate complete empty-model equivalence audit.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import struct

from nfs_rockport import chunks
from world_streaming_scene_export import asset_crc,section_asset


def run(args):
    manifest=json.loads((args.assets/'manifest.json').read_text())
    inventory=json.loads(args.inventory.read_text());proof=json.loads(args.proof.read_text())
    if proof['source_sha256']!=manifest['source_sha256'] or inventory['source_sha256']!=manifest['source_sha256']:
        raise ValueError('Empty audit and existing assets have different source streams')
    if 'empty_catalog_sha256' in manifest:
        raise ValueError('Empty catalog already imported; refusing duplicate source aliases')
    original_sections={s['id']:s for s in inventory['sections']};additions=defaultdict(list);all_aliases=[]
    with args.stream.open('rb') as file:
        with mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as original:
            if hashlib.sha256(original).hexdigest()!=manifest['source_sha256']:
                raise ValueError('Original stream differs from empty audit')
            for key,group in proof['groups'].items():
                if not group['empty'] or not group['full_guard_equivalent'] or key in manifest['models']:
                    raise ValueError('Empty source group is unproved or already exported')
                aliases=group['aliases'];first=aliases[0];guard=first['catalog_key']
                for alias in aliases:
                    start,length=alias['offset'],alias['bytes']
                    if alias['catalog_key']!=guard or hashlib.sha256(original[start:start+length]).hexdigest()!=alias['raw_sha256']:
                        raise ValueError('Empty source alias differs from audited input')
                start,length=first['offset'],first['bytes']
                leaves={k:(start+a,start+b) for k,a,b in chunks(original[start:start+length])}
                h=(leaves[0x134011][0]+15)&~15;header=bytes(original[h:h+160])
                if hashlib.sha256(header).hexdigest()!=first['header_sha256']:
                    raise ValueError('Empty source header differs from audit')
                if struct.unpack_from('<H',header,20)[0]:
                    raise ValueError('Unexpected nonzero empty source triangle statistic')
                payload=bytearray(416);payload[:4]=b'WSM1'
                struct.pack_into('<15I',payload,4,1,len(payload),int(key,16),0,0,0,0,0,256,256,256,256,0,0,1)
                payload[64:76]=header[32:44];payload[76:88]=header[48:60];payload[88:152]=header[64:128]
                payload[152:184]=bytes.fromhex(first['raw_sha256']);payload[184:216]=bytes.fromhex(guard.split(':')[-1])
                struct.pack_into('<8I',payload,216,first['section'],start,length,0,len(payload),0,256,160)
                payload[256:416]=header;struct.pack_into('<I',payload,56,asset_crc(payload,56))
                path=args.assets/'models'/(key+'.wsm')
                if path.exists():raise ValueError('Refusing to overwrite model asset')
                path.write_bytes(payload)
                manifest['models'][key]=dict(hash=key,name=first['name'],vertices=0,indices=0,batches=0,linear_bytes=0,
                    source_declared_triangles=0,emitted_triangles=0,texture_hashes=[],empty_source=True,
                    catalog_key=guard,path=str(path.relative_to(args.assets)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
                for alias in aliases:
                    additions[alias['section']].append((key,guard))
                    row={k:alias[k] for k in ('hash','catalog_key','section','offset','raw_sha256')};row['empty_source']=True
                    all_aliases.append(row)
    for sid,extra in additions.items():
        record=next(s for s in manifest['sections'] if s['id']==sid);path=args.assets/record['path'];old=path.read_bytes()
        if hashlib.sha256(old).hexdigest()!=record['sha256']:raise ValueError('Existing section differs from manifest')
        nm,nt,ni,mo,to,io=struct.unpack_from('<6I',old,16)
        models=[(f'{struct.unpack_from("<I",old,mo+i*40)[0]:08x}',old[mo+i*40+4:mo+i*40+36].hex()) for i in range(nm)]
        textures=[(f'{struct.unpack_from("<I",old,to+i*40)[0]:08x}',old[to+i*40+4:to+i*40+36].hex()) for i in range(nt)]
        instances=[old[io+i*144:io+(i+1)*144] for i in range(ni)]
        payload=section_asset(original_sections[sid],instances,models+extra,textures);path.write_bytes(payload)
        record.update(bytes=len(payload),model_bindings=len(models)+len(extra),sha256=hashlib.sha256(payload).hexdigest())
    accepted={(a['section'],a['offset']) for a in all_aliases}
    manifest['rejected']=[r for r in manifest['rejected'] if (r.get('section'),r.get('offset')) not in accepted]
    manifest['model_aliases'].extend(all_aliases);manifest['empty_catalog_sha256']=hashlib.sha256(args.proof.read_bytes()).hexdigest()
    manifest['empty_source_note']='Exact authored zero-draw records retained; animation/runtime population remains a separate gate'
    (args.assets/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    summary=json.loads((args.assets/'summary.json').read_text());summary.update(models=len(manifest['models']),model_bytes=sum(m['bytes'] for m in manifest['models'].values()),
        empty_models=len(proof['groups']),empty_aliases=len(all_aliases),rejected=len(manifest['rejected']))
    (args.assets/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','inventory','stream','proof'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
