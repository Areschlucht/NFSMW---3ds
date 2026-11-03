"""Native runtime vectors against original-verified policy and source gather."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from nfs_rockport import decode as decode_index
from world_streaming_regions import decode,ContainingRegionSelector
from world_streaming_policy_reference import gather_reference


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('index','metadata','dol','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    raw=args.index.read_bytes();regions=decode(raw);sections=decode_index(raw)['sections']
    byid={s['id']:s for s in sections};polygons={p['id']:p for p in regions['polygons']}
    selector=ContainingRegionSelector(regions)
    sequence=[d['id'] for d in regions['dependencies']]
    sequence+=list(reversed(sequence[:64]))+sequence[:64]
    vectors=bytearray(b'WSQ1'+struct.pack('<I',len(sequence)))
    expected=[]
    for identifier in sequence:
        point=polygons[identifier]['center'];selected=selector.select(point)
        requested=[2500,2400,2600]+selected['section_ids']
        ids=list(dict.fromkeys(i for i in requested if i in byid))
        vectors.extend(struct.pack('<2fHH',*point,selected['id'],len(ids)))
        vectors.extend(struct.pack(f'<{len(ids)}H',*ids))
        expected.append((requested,ids))
    dol=args.dol.read_bytes();gather_cases=0
    for index in (0,63,217,len(expected)-1):
        requested,wanted=expected[index]
        if gather_reference(dol,requested,sections)!=wanted:
            raise ValueError('Original source request-gather mismatch')
        gather_cases+=1
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='world-streaming-runtime-') as temporary:
        folder=Path(temporary);vector_path=folder/'vectors.bin';vector_path.write_bytes(vectors)
        binary=folder/'test'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic',
                        '-fno-fast-math','-ffp-contract=off','-fsanitize=undefined,address',
                        '-I'+str(root/'include'),str(root/'source_bmw/world_streaming.c'),
                        str(root/'tests/test_world_streaming_runtime.c'),'-lm','-o',str(binary)],check=True)
        result=json.loads(subprocess.check_output([str(binary),str(args.metadata),str(vector_path)],text=True))
    result.update(original_request_gather_cases=gather_cases,vector_sha256=hashlib.sha256(vectors).hexdigest(),
                  metadata_sha256=hashlib.sha256(args.metadata.read_bytes()).hexdigest(),
                  limits='Contained-region normal-mode planning only; no async IO, geometry upload, nearest fallback or automatic eviction')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
