#!/usr/bin/env python3
"""Audit original section/dependency sizes without claiming converted residency.

Logical IDs absent from the physical index are skipped, matching recovered
normal gather semantics. No render/collision ID arithmetic is inferred.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def audit(root):
    paths = {name: root/name for name in (
        'world-streaming/initial-render-inventory.json',
        'world-streaming/render-availability-manifest.json',
        'world-streaming/original-regions-and-dependencies.json',
        'world-streaming/original-render-collision-containment.json',
        'map-collision/collision-streaming-manifest.json')}
    inv, avail, policy, containment, collision = [json.loads(p.read_text()) for p in paths.values()]
    sections = {s['id']: s for s in avail['sections']}
    models = defaultdict(dict)
    for m in inv['models']:
        models[m['section']][m['raw_sha256']] = m
    packs = defaultdict(dict)
    for c in containment['relations']:
        packs[c['section_id']][c['sha256']] = c

    def content_class(section):
        # Describe observed content, not an unverified original allocator's
        # category predicate or a guessed numeric-ID range.
        if section['available_textures'] and not section['available_models']:
            return 'texture_content'
        if section['available_models'] and not section['instance_count']:
            return 'model_bank_content'
        return 'regular_or_mixed_content'

    def budget(ids):
        requested = list(dict.fromkeys(ids))
        present = [sid for sid in requested if sid in sections]
        unique_models = {}
        unique_packs = {}
        textures = set()
        for sid in present:
            unique_models.update(models[sid])
            unique_packs.update(packs[sid])
            textures.update(sections[sid]['available_textures'])
        validated = [m for m in unique_models.values() if m['validated']]
        tri = sum(m['validated_triangles'] for m in validated)
        # A conservative candidate allocation upper bound only for validated
        # stored model corners, not instances or unresolved/rejected geometry.
        # 36-byte vertices +2-byte indices, both128 aligned per model.
        gpu_upper = sum(((m['validated_triangles']*3*36+127)//128*128 +
                         m['validated_triangles']*3*2+127)//128*128 for m in validated)
        return dict(section_ids=present, skipped_absent_ids=[i for i in requested if i not in sections],
                    raw_section_bytes=sum(sections[i]['bytes'] for i in present),
                    max_single_section_bytes=max((sections[i]['bytes'] for i in present), default=0),
                    raw_section_classes={kind: sum(sections[i]['bytes'] for i in present if
                        content_class(sections[i]) == kind)
                        for kind in ('texture_content','model_bank_content','regular_or_mixed_content')},
                    raw_model_variants=len(unique_models), validated_model_variants=len(validated),
                    rejected_model_variants=len(unique_models)-len(validated),
                    validated_stored_model_triangles=tri,
                    model_corner_gpu36_with_u16_upper_estimate=gpu_upper,
                    object_instances=sum(sections[i]['instance_count'] for i in present),
                    available_texture_hashes=len(textures),
                    converted_texture_gpu_bytes=None,
                    embedded_unique_collision_packs=len(unique_packs),
                    embedded_collision_raw_bytes=sum(c['bytes'] for c in unique_packs.values()),
                    converted_collision_runtime_bytes=None)

    regions = [dict(region_id=d['id'], **budget([2500,2400,2600]+d['section_ids']))
               for d in policy['dependencies']]
    return dict(schema=1, kind='source-budget-audit-not-runtime-admission',
                provenance={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths.values()},
                limitations=[
                    'Raw section bytes overlap embedded collision/model/texture bytes; do not add them twice.',
                    'GPU estimate covers each validated stored model variant once, not transformed instance copies or selected LOD policy.',
                    'Available texture hash counts are not validated material dependencies or converted texture memory.',
                    'Texture dimensions/formats/mip allocation and collision runtime structure sizes unresolved: admission must reject unknown cost.',
                    'Category labels describe observed source content, not proven original allocator classes or lifetime rules.',
                    'Each region plus mandatory banks is audited independently; two viewpoints and retained previous region require set-union costing.'],
                mandatory=budget([2500,2400,2600]),
                all_sections=budget(list(sections)),
                per_section=[dict(id=sid, **budget([sid])) for sid in sections], regions=regions,
                worst_region_raw=max(regions,key=lambda r:r['raw_section_bytes']),
                worst_region_stored_model_gpu_estimate=max(regions,key=lambda r:r['model_corner_gpu36_with_u16_upper_estimate']),
                collision_source_totals=collision['totals'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research',type=Path,default=Path('/workspace/port-research'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.research)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('mandatory','all_sections','worst_region_raw','worst_region_stored_model_gpu_estimate')},indent=2))
