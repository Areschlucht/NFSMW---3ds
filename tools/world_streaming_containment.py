"""Locate original collision packets inside indexed stream source ranges."""
import argparse
import bisect
from collections import Counter
import json
from pathlib import Path


def relate(render, collision):
    if render['source_sha256'] != collision['source_sha256']:
        raise ValueError('Render and collision manifests refer to different streams')
    sections=sorted(render['sections'],key=lambda s:s['offset'])
    starts=[s['offset'] for s in sections]
    result=[]
    for pack in collision['physical_packages']:
        index=bisect.bisect_right(starts,pack['offset'])-1
        if index<0:
            raise ValueError('Collision package precedes original index ranges')
        section=sections[index]
        if pack['offset']+pack['bytes']>section['offset']+section['bytes']:
            raise ValueError('Collision package crosses indexed section boundary')
        result.append(dict(section_id=section['id'],section_offset=section['offset'],
                           collision_id=pack['id'],collision_offset=pack['offset'],
                           bytes=pack['bytes'],sha256=pack['sha256']))
    return dict(source_sha256=render['source_sha256'],relations=result,
                summary=dict(physical_packs=len(result),containing_sections=len({r['section_id'] for r in result}),
                             id_differences=dict(Counter(str(r['section_id']-r['collision_id']) for r in result))),
                limitations='Original physical containment only; activation and query policy are separate evidence')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('render','collision','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=relate(json.loads(args.render.read_text()),json.loads(args.collision.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary']))
