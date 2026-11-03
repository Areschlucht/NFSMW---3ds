#!/usr/bin/env python3
"""Build content-addressed original collision ranges and source-point bounds.

Keeps every physical chunk occurrence. Bounds come only from original decoded
mesh vertices/wall endpoints transformed by referenced CI inverse; they are not
render extents, activation regions, collision volumes, or inferred blockers.
Decodes one physical package at a time and does not flatten the full world.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from world_collision import packages, instance_matrix, inverse_affine, transform_point


def manifest(data):
    unique = {}
    physical = []
    for package in packages(data):
        start, size = package['source_offset'], package['source_bytes']
        sha = hashlib.sha256(data[start:start+size]).hexdigest()
        physical.append(dict(id=package['id'], offset=start, bytes=size, sha256=sha))
        if sha in unique:
            unique[sha]['source_offsets'].append(start)
            continue
        low, high = [float('inf')]*3, [-float('inf')]*3
        materials = Counter()
        points = 0
        for instance in package['instances']:
            asset = package['assets'][instance['asset_index']]
            inverse = inverse_affine(instance_matrix(instance))
            for part in asset['parts']:
                for vertex in part['vertices']:
                    world = transform_point(vertex, inverse)
                    for a in range(3):low[a]=min(low[a],world[a]);high[a]=max(high[a],world[a])
                    points += 1
                for triangle in part['triangles']:
                    materials[f"{asset['materials'][triangle['material_index']]:08x}"] += 1
            for wall in asset['walls']:
                for key in ('endpoint_a', 'endpoint_b'):
                    world = transform_point(wall[key], inverse)
                    for a in range(3):low[a]=min(low[a],world[a]);high[a]=max(high[a],world[a])
                    points += 1
                materials[f"{asset['materials'][wall['material_index']]:08x}"] += 1
        native = [low,high] if points else None
        unique[sha] = dict(id=package['id'],sha256=sha,bytes=size,source_offsets=[start],
            native_source_point_bounds=native,
            viewer_source_point_bounds=[[v[2],v[1],v[0]] for v in native] if native else None,
            instances=len(package['instances']),assets=len(package['assets']),decoded_points=points,
            quantized_parts=sum(len(a['parts']) for a in package['assets'].values()),
            triangle_candidates=sum(len(p['triangles']) for a in package['assets'].values() for p in a['parts']),
            wall_records=sum(len(a['walls']) for a in package['assets'].values()),
            material_primitive_counts=dict(sorted(materials.items())))
    return dict(source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),
        physical_packages=physical,unique_packages=list(unique.values()),
        totals=dict(physical_packages=len(physical),unique_packages=len(unique),
            physical_collision_bytes=sum(p['bytes'] for p in physical),
            unique_collision_bytes=sum(p['bytes'] for p in unique.values()),
            **{key:sum(p[key] for p in unique.values()) for key in ('instances','assets','quantized_parts','triangle_candidates','wall_records')}),
        limitations='Original collision byte-range/source-point manifest only. Source point bounds are not activation volumes. Render/collision sector association, top-level query and response remain unresolved; never load all packages permanently into 3DS RAM.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stream',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    report=manifest(args.stream.read_bytes());args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['totals'],sort_keys=True))
