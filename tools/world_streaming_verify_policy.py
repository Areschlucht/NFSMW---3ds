"""Compare isolated original streaming policy stages with host translations."""
import argparse
import itertools
import json
from pathlib import Path
import random
import struct

from world_streaming_policy import bind_lod_hashes, section_fallback
from world_streaming_policy_reference import reference, polygon_reference, ContainingSelectorReference
from world_streaming_regions import decode, polygon_contains, ContainingRegionSelector, NoContainingRegion


def verify(dol, manifest, index):
    binding = 0
    for slots in itertools.product((0,1,2,0xBE43EDBB,0x90F70174), repeat=4):
        got, allocations = reference(dol, slots=slots)
        if got != bind_lod_hashes(slots):
            raise ValueError('Original LOD binding mismatch')
        if allocations != len(set(slots)-{0,0xBE43EDBB,0x90F70174}):
            raise ValueError('Original same-hash handle-sharing mismatch')
        binding += 1
    rows = [o for s in manifest['sections'] for o in s['objects']]
    random.Random(0).shuffle(rows)
    for row in rows[:64]:
        slots = struct.unpack_from('<4I', bytes.fromhex(row['raw']), 24)
        got,_ = reference(dol, slots=slots)
        if got != bind_lod_hashes(slots):
            raise ValueError('Original object-record binding mismatch')
    regions = decode(index)
    ids = [s['id'] for s in manifest['sections']]
    fallback = []
    for span in (3,10,regions['section_span']):
        for available in ([],[111,119,141,2019],ids):
            for identifier in (-101,0,99,100,101,102,103,109,110,111,119,139,140,141,199,
                               2000,2001,2009,2019,2099,2100,2101):
                actual = reference(dol, identifier=identifier, available_ids=available, section_span=span)
                if actual != section_fallback(identifier, available, span):
                    raise ValueError('Original section fallback mismatch')
                fallback.append(dict(id=identifier,span=span,available_count=len(available),result=actual))
    polygon_cases = 0
    for polygon in regions['polygons']:
        points = polygon['points']
        center = [sum(p[a] for p in points)/len(points) for a in range(2)]
        samples = [center, points[0], [(points[0][a]+points[1][a])*.5 for a in range(2)]]
        for point in samples:
            got = polygon_reference(dol, point, points)
            if got != polygon_contains(point, points):
                raise ValueError(f"Original polygon containment mismatch: {polygon['offset']}, {point}")
            polygon_cases += 1
    original_selector=ContainingSelectorReference(dol,regions)
    host_selector=ContainingRegionSelector(regions)
    polygon_by_id={p['id']:p for p in regions['polygons']}
    sequence=[d['id'] for d in regions['dependencies']]
    sequence+=list(reversed(sequence[:64]))+sequence[:64]
    selector_cases=0
    outside=[]
    for identifier in sequence:
        point=polygon_by_id[identifier]['center']
        try:
            selected=host_selector.select(point)
        except NoContainingRegion:
            outside.append(identifier)
            continue
        actual=original_selector.select(point)
        if actual!=selected['id']:
            raise ValueError('Original stateful containing-region selector mismatch')
        selector_cases+=1
    return dict(binding_exhaustive_cases=binding,binding_original_object_samples=min(64,len(rows)),
                section_fallback_cases=len(fallback),section_fallback=fallback,
                polygon_cases=polygon_cases,original_region_polygons=len(regions['polygons']),
                stateful_containing_selector_cases=selector_cases,
                region_centers_requiring_nearest_fallback=outside,
                configured_section_span=regions['section_span'],
                verified_entries=['802BDBE0..802BDCE4','802B9184..802B9244','802BFF3C..802BFFF4','802C1094 contained branch'],
                limitations='Binding, missing-ID fallback, polygon containment and contained-region selection only; '
                            'nearest-region fallback, prediction, '
                            'asynchronous readiness and callbacks are not claimed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','manifest','index','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.dol.read_bytes(),json.loads(args.manifest.read_text()),args.index.read_bytes())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='section_fallback'},indent=2))
