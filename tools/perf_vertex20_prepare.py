#!/usr/bin/env python3
"""Prepare isolated component ablations from the frozen float36 baseline.
Never edits the working renderer. Each compact codec rejects nonrepresentable
data rather than silently quantizing it.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path('/workspace/port-research/hardware-optimization/vertex20')
PROJECT = Path(__file__).resolve().parent.parent


def ignored(directory, names):
    return [name for name in names if name in ('.git', 'dist', '__pycache__') or
            (name.startswith('build') and (Path(directory)/name).is_dir()) or
            Path(name).suffix in ('.3dsx', '.elf', '.smdh', '.map')]


def prepare(mode):
    destination = ROOT/(mode+'-project')
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(ROOT/'baseline-project', destination, ignore=ignored)
    shutil.copyfile(PROJECT/'tools/perf_vertex20_components.h', destination/'include/perf_vertex20_components.h')
    shutil.copyfile(PROJECT/'tools/perf_vertex20_components.c', destination/'source_bmw/perf_vertex20_components.c')
    vertex, function = ('PerfVertexUV32', 'perf_vertex20_uv32_pack') if mode == 'uv32' else ('PerfVertexColor24', 'perf_vertex20_color24_pack')
    path = destination/'source_rockport/rockport_main.c'
    text = path.read_text().replace('#include "world_vertex.h"', '#include "world_vertex.h"\n#include "perf_vertex20_components.h"')
    text = text.replace('size_t stride=is_world?sizeof(WorldVertex):sizeof(NfsVertex);', f'size_t stride=is_world?sizeof({vertex}):sizeof(NfsVertex);')
    text = text.replace('memcpy(mesh->gpu_vertices,indexed.vertices,vertex_bytes);', f'if (!{function}(mesh->gpu_vertices,indexed.vertices,indexed.vertex_count)) {{ world_index_free(&indexed);return false; }}')
    text = text.replace('if (is_world) world_vertex_pack(mesh->gpu_vertices,mesh->scene.vertices,mesh->scene.vertex_count);',
                        f'if (is_world) {{ for (unsigned i=0;i<mesh->scene.vertex_count;++i) {{ WorldVertex one;world_vertex_pack(&one,&mesh->scene.vertices[i],1);if (!{function}(({vertex} *)mesh->gpu_vertices+i,&one,1)) return false; }} }}')
    if mode == 'uv32':
        text = text.replace('AttrInfo_AddLoader(&world_attributes,1,GPU_FLOAT,2);', 'AttrInfo_AddLoader(&world_attributes,1,GPU_SHORT,2);')
    else:
        text = text.replace('AttrInfo_AddLoader(&world_attributes,2,GPU_FLOAT,4);', 'AttrInfo_AddLoader(&world_attributes,2,GPU_UNSIGNED_BYTE,4);')
    path.write_text(text)
    path = destination/'tools/build_rockport.sh'
    path.write_text(path.read_text().replace('world_vertex.c world_index.c', 'world_vertex.c world_index.c perf_vertex20_components.c'))
    path = destination/'source_rockport/world_vshader.v.pica'
    text = path.read_text()
    if mode == 'uv32':
        text = text.replace('.alias ones constants.yyyy', '.constf uvscale(0.000244140625, -0.000244140625, 0.0, 0.0)\n.alias ones constants.yyyy')
        text = text.replace('mov outtc0, texcoord', 'mov r2, constants\n    mad outtc0, texcoord, uvscale, r2')
    else:
        text = text.replace('.constf constants(0.0, 1.0, 0.0, 0.0)', '.constf constants(0.0, 1.0, 0.00392156862745098039, 0.0)')
        text = text.replace('mov outclr, vertexcolor', 'mul outclr, constants.zzzz, vertexcolor')
    path.write_text(text)
    manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in destination.rglob('*') if p.is_file()}
    (ROOT/(mode+'-source-manifest.json')).write_text(json.dumps(manifest, indent=2)+'\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['uv32', 'color24'])
    prepare(parser.parse_args().mode)
