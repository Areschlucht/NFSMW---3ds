#!/usr/bin/env python3
"""Check extracted car geometry with the existing supported GC mesh decoder.

Candidate names and decodable parts do not establish the playable GC roster,
vehicle attachment setup, material fidelity or gameplay integration.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from decode_brakes import decode


def inspect(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    results=[]
    for entry in manifest['entries']:
        if not entry['candidate_name'].endswith('\\GEOMETRY.BIN'):
            continue
        raw=(directory/entry['file']).read_bytes()
        if len(raw)!=entry['bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('Extracted payload differs from manifest')
        result={'candidate_name':entry['candidate_name'],'directory_record_offset':entry['directory_record_offset'],
                'bytes':len(raw),'sha256':entry['sha256']}
        if not raw:
            result['status']='empty directory entry'
        else:
            try:
                models=decode(raw,lod='B')
            except (ValueError,KeyError,IndexError,UnicodeError,struct.error) as e:
                result.update(status='unsupported or rejected',reason=str(e))
            else:
                result.update(status='decoded' if models else 'no supported B parts selected',
                    part_count=len(models),triangles=sum(len(m['faces']) for m in models),
                    lamp_parts=[{'name':m['name'],'triangles':len(m['faces'])} for m in models
                                if any(n in m['name'] for n in ('HEADLIGHT','BRAKELIGHT'))])
        results.append(result)
    return {'schema':1,'records':results,'status_counts':dict(Counter(r['status'] for r in results)),
            'limits':['No additional cars are integrated into the playable build by this tool',
                      'LOD B decoding does not establish the original playable roster or complete mesh/attachment/material support']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=inspect(a.directory);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['status_counts']))
