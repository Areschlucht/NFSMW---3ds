"""Resolve inventoried world references against explicitly supplied original banks."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from nfs_rockport import chunks


def scan(data):
    models,textures=[],[]
    for kind,a,b in chunks(data):
        if kind==0xB3300000:
            parts={k:(a+c,a+d) for k,c,d in chunks(data[a:b])}
            c,d=parts[0xB3310000]
            leaves={k:(c+e,c+f) for k,e,f in chunks(data[c:d])}
            keys,ke=leaves[0x33310002]
            if (ke-keys)%8:
                raise ValueError('Incomplete texture hash table')
            for at in range(keys,ke,8):
                textures.append(dict(hash=f'{struct.unpack_from("<I",data,at)[0]:08x}',
                                     package_offset=a-8,package_bytes=b-a+8))
        elif kind==0x80134000:
            for model_kind,c,d in chunks(data[a:b]):
                if model_kind!=0x80134010:
                    continue
                c+=a
                d+=a
                leaves={k:(c+e,c+f) for k,e,f in chunks(data[c:d])}
                if 0x134011 not in leaves:
                    raise ValueError('Model lacks original header')
                hs,he=leaves[0x134011]
                header=(hs+15)&~15
                if header+161>he:
                    raise ValueError('Truncated model header')
                models.append(dict(hash=f'{struct.unpack_from("<I",data,header+16)[0]:08x}',
                                   name=data[header+160:he].split(b'\0')[0].decode('ascii'),
                                   offset=c,bytes=d-c,raw_sha256=hashlib.sha256(data[c:d]).hexdigest()))
    return dict(models=models,textures=textures)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('banks',type=Path,nargs='+')
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    banks=[]
    for path in args.banks:
        data=path.read_bytes()
        banks.append(dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),**scan(data)))
    model_keys={m['hash'] for bank in banks for m in bank['models']}
    texture_keys={t['hash'] for bank in banks for t in bank['textures']}
    missing_models=set(manifest['summary']['missing_model_hashes'])
    missing_textures=set(manifest['summary']['missing_texture_hashes'])
    missing_consumed=set(manifest['summary'].get('missing_consumed_texture_hashes', missing_textures))
    result=dict(banks=banks,resolved_model_hashes=sorted(missing_models&model_keys),
                resolved_texture_hashes=sorted(missing_textures&texture_keys),
                unresolved_model_hashes=sorted(missing_models-model_keys),
                unresolved_texture_hashes=sorted(missing_textures-texture_keys),
                unresolved_consumed_texture_hashes=sorted(missing_consumed-texture_keys),
                limitations='Reference availability only; source geometry/material decoding and activation are separate checks')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:len(v) for k,v in result.items() if k.endswith('_hashes')}))
