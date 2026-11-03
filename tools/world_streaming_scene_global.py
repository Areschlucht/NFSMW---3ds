"""Import verified boot-global texture providers into an explicit export namespace.

sections/0.wsi is NOT an original track section. Its provenance lists exact
original global banks and packet ranges. Renderer use is separately opt-in.
Only requested original hashes are imported; no substitutes or aliases invented.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from nfs_rockport import chunks
from nfs_tpk import parse
from world_streaming_scene_export import section_asset,texture_asset


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--hash',dest='hashes',action='append',required=True)
    parser.add_argument('--extend',action='store_true',help='Explicitly add providers to an existing boot bank; conflicting identities still rejected')
    parser.add_argument('banks',type=Path,nargs='+')
    args=parser.parse_args();wanted={f'{int(key,16):08x}' for key in args.hashes}
    manifest_path=args.assets/'manifest.json';manifest=json.loads(manifest_path.read_text())
    existing=manifest.get('global_banks',[])
    if (existing or (args.assets/'sections/0.wsi').exists()) and not args.extend:
        raise ValueError('Global bank already exists; refusing silent provider replacement')
    providers=[];sources=[];records={}
    if args.extend:
        if len(existing)!=1 or existing[0]['id']!=0:raise ValueError('Expected one explicit existing boot bank')
        old=(args.assets/existing[0]['path']).read_bytes()
        if hashlib.sha256(old).hexdigest()!=existing[0]['sha256']:raise ValueError('Existing boot bank differs from manifest')
        count=struct.unpack_from('<I',old,20)[0];offset=struct.unpack_from('<I',old,32)[0]
        providers=[(f'{struct.unpack_from("<I",old,offset+i*40)[0]:08x}',old[offset+i*40+4:offset+i*40+36].hex()) for i in range(count)]
        sources=list(existing[0]['sources'])
    resolved=set()
    for bank in args.banks:
        data=bank.read_bytes();sha=hashlib.sha256(data).hexdigest()
        packet_ranges={}
        for kind,a,b in chunks(data):
            if kind!=0xB3300000:continue
            parts={k:(a+c,a+d) for k,c,d in chunks(data[a:b])};h,he=parts[0xB3310000]
            headers={k:(h+c,h+d) for k,c,d in chunks(data[h:he])};ks,ke=headers[0x33310002]
            for at in range(ks,ke,8):
                key=f'{struct.unpack_from("<I",data,at)[0]:08x}'
                packet_ranges.setdefault(key,[]).append(dict(offset=a-8,bytes=b-a+8))
        decoded=parse(data,wanted_hashes=wanted)
        for texture in decoded:
            payload,identity,record=texture_asset(texture,0)
            key=texture['hash'];resolved.add(key)
            if any(old_key==key and old_identity!=identity for old_key,old_identity in providers):
                raise ValueError('Conflicting boot provider identities require original priority proof')
            if (key,identity) not in providers:providers.append((key,identity))
            path=args.assets/'textures'/(key+'-'+identity+'.wtx')
            if path.exists() and path.read_bytes()!=payload:
                raise ValueError('Existing content identity has different bytes')
            path.write_bytes(payload)
            records[identity]=dict(record,identity=identity,path=str(path.relative_to(args.assets)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
            sources.append(dict(texture_hash=key,texture_identity=identity,source_file=str(bank),source_sha256=sha,
                                source_bytes=len(data),packet_ranges=packet_ranges[key],source_rgba_sha256=hashlib.sha256(texture['rgba']).hexdigest()))
    if resolved!=wanted:
        raise ValueError('Some requested original providers are absent: '+','.join(sorted(wanted-resolved)))
    payload=section_asset(dict(id=0,offset=0,bytes=0),[],[],providers)
    path=args.assets/'sections/0.wsi';path.write_bytes(payload)
    manifest['textures'].update(records)
    manifest['global_banks']=[dict(id=0,namespace='boot-global-provider-bank-not-track-section',path='sections/0.wsi',bytes=len(payload),
                                  model_bindings=0,texture_bindings=len(providers),instances=0,sha256=hashlib.sha256(payload).hexdigest(),sources=sources)]
    manifest_path.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    summary_path=args.assets/'summary.json';summary=json.loads(summary_path.read_text())
    summary.update(texture_payloads=len(manifest['textures']),texture_bytes=sum(t['bytes'] for t in manifest['textures'].values()),global_provider_banks=1,global_texture_bindings=len(providers))
    summary_path.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(resolved=sorted(resolved),provider_bank='sections/0.wsi',manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest()),indent=2))
