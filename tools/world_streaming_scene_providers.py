"""Audit exact normal-mode source-bank texture identity bindings per region."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--regions',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();manifest=json.loads((args.assets/'manifest.json').read_text());regions=json.loads(args.regions.read_text())
    sections={}
    for section in manifest['sections']:
        data=(args.assets/section['path']).read_bytes();count=struct.unpack_from('<I',data,20)[0];offset=struct.unpack_from('<I',data,32)[0]
        sections[section['id']]=[(struct.unpack_from('<I',data,offset+i*40)[0],data[offset+i*40+4:offset+i*40+36].hex()) for i in range(count)]
    rows=[];all_providers=defaultdict(set)
    for dependency in regions['dependencies']:
        ids=list(dict.fromkeys(i for i in [2500,2400,2600]+dependency['section_ids'] if i in sections))
        providers=defaultdict(set)
        for sid in ids:
            for key,identity in sections[sid]:providers[key].add(identity);all_providers[key].add(identity)
        ambiguous={f'{key:08x}':sorted(values) for key,values in providers.items() if len(values)>1}
        rows.append(dict(region=dependency['id'],source_sections=ids,texture_hashes=len(providers),ambiguities=ambiguous))
    result=dict(regions=len(rows),regions_with_ambiguous_texture_providers=sum(bool(row['ambiguities']) for row in rows),
                max_active_texture_hashes=max(row['texture_hashes'] for row in rows),
                union_all_normal_regions_texture_hashes=len(all_providers),
                union_all_normal_regions_ambiguous_hashes={f'{key:08x}':sorted(values) for key,values in all_providers.items() if len(values)>1},
                region_results=rows,
                limits='Source provider identities for current normal-mode static region requests; dynamic groups and optional source remap modes are separate')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('region_results','union_all_normal_regions_ambiguous_hashes')},indent=2))
