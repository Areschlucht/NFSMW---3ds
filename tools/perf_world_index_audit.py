#!/usr/bin/env python3
"""Audit exact indexed-world reuse; report cache models without hardware claims.

The native bridge runs the same reset camera and conservative visibility code as
the renderer. Cache simulations are assumptions (FIFO/LRU, reset on each actual
merged draw run), not a statement about PICA200 cache size or behavior.
"""
import argparse
import ctypes
import hashlib
import json
import math
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def read_scene(path):
    data = Path(path).read_bytes()
    if len(data) < 32:
        raise ValueError('Truncated NFM header')
    magic, version, nv, nb, nt, size, crc, reserved = struct.unpack_from('<4s7I', data)
    if magic != b'NFM1' or version not in (1, 2) or reserved:
        raise ValueError('Unsupported scene header')
    stride = 32 if version == 1 else 48
    if not 0 < nv <= 200000 or nv % 3 or not 0 < nb <= 2048 or not 0 < nt <= 128:
        raise ValueError('Invalid scene counts')
    if size != nv*stride + (nb+nt)*16 or len(data) != size+32 or zlib.crc32(data[32:]) != crc:
        raise ValueError('Invalid scene size/CRC')
    textures = list(struct.iter_unpack('<4I', data[32:32+nt*16]))
    for _, width, height, flags in textures:
        if not 8 <= width <= 1024 or width & (width-1) or not 8 <= height <= 1024 or height & (height-1) or flags > 7 or flags & 4 and not flags & 1:
            raise ValueError('Invalid texture record')
    start = 32+nt*16
    batches = list(struct.iter_unpack('<4I', data[start:start+nb*16]))
    expected = 0
    for first, count, texture, flags in batches:
        if first != expected or not count or count % 3 or first+count > nv or texture >= nt or flags:
            raise ValueError('Invalid batch coverage/material')
        expected += count
    if expected != nv:
        raise ValueError('Incomplete batch coverage')
    start += nb*16
    packed, positions = [], []
    for i in range(nv):
        raw = data[start+i*stride:start+(i+1)*stride]
        values = struct.unpack('<' + ('8f' if version == 1 else '12f'), raw)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Nonfinite vertex')
        if any(abs(v) > 1.01 for v in values[:3]) or not .98 <= sum(v*v for v in values[3:6]) <= 1.02 or any(abs(v) > 16 for v in values[6:8]):
            raise ValueError('Invalid vertex bounds/normal/UV')
        colors = values[8:] if version == 2 else (1., 1., 1., 1.)
        if any(not 0 <= v <= 1 for v in colors):
            raise ValueError('Invalid vertex colour')
        color_bytes = raw[32:] if version == 2 else struct.pack('<4f', *colors)
        packed.append(raw[:12] + struct.pack('<2f', values[6], f32(1-values[7])) + color_bytes)
        positions.append(values[:3])
    return dict(raw=data, textures=textures, batches=batches, vertices=packed, positions=positions)


def encode(vertices):
    if not vertices or len(vertices) % 3 or any(len(v) != 36 for v in vertices):
        raise ValueError('Expected a complete packed world triangle stream')
    lookup, unique, indices = {}, [], []
    for vertex in vertices:
        if vertex not in lookup:
            if len(unique) == 65536:
                raise ValueError('More than 65536 exact world vertices: retain DrawArrays fallback')
            lookup[vertex] = len(unique)
            unique.append(vertex)
        indices.append(lookup[vertex])
    if any(unique[index] != vertex for index, vertex in zip(indices, vertices)):
        raise AssertionError('Indexed decode-back mismatch')
    return unique, indices


def native_attribute_opportunity(vertices):
    """Check lossless CPU reconstruction from original-like byte/short data.

    This does not prove that a shader's FP24 conversion/multiply yields the same
    fragment colours. A future packed format needs pixel/hardware validation.
    """
    colors_ok = uv_ok = 0
    compact = []
    for raw in vertices:
        values = struct.unpack('<9f', raw)
        rgba = bytes(max(0, min(255, round(c*255))) for c in values[5:])
        color_matches = struct.pack('<4f', *(c/255 for c in rgba)) == raw[20:]
        u, v = round(values[3]*4096), round((1-values[4])*4096)
        uv_matches = (-32768 <= u <= 32767 and -32768 <= v <= 32767 and
                      struct.pack('<2f', u/4096, 1-v/4096) == raw[12:20])
        colors_ok += color_matches
        uv_ok += uv_matches
        if color_matches and uv_matches:
            compact.append(raw[:12]+struct.pack('<2h', u, v)+rgba)
    valid = len(compact) == len(vertices)
    return dict(corners=len(vertices), exact_rgba8_reconstructable=colors_ok,
                exact_original_s16_q12_uv_reconstructable=uv_ok,
                proposed_stride=20, unique_compact_records=len(set(compact)) if valid else None,
                proposed_gpu_bytes_with_u16=len(set(compact))*20+len(vertices)*2 if valid else None,
                status='Source-equivalent CPU representation only; shader conversion/pixel/hardware equivalence untested.')


def merged_runs(batches, textures, visible):
    runs = []
    for pass_id in (0, 1):
        current = None
        for i, (first, count, texture, _) in enumerate(batches):
            if bool(textures[texture][3] & 1) != bool(pass_id) or not visible[i]:
                continue
            if current and current[2] == texture and current[0]+current[1] == first:
                current[1] += count
            else:
                if current:
                    runs.append(tuple(current))
                current = [first, count, texture]
        if current:
            runs.append(tuple(current))
    return runs


def cache_misses(indices, runs, capacity, policy):
    misses = 0
    for first, count, _ in runs:
        cache = []
        for index in indices[first:first+count]:
            if index not in cache:
                misses += 1
                cache.append(index)
                if len(cache) > capacity:
                    cache.pop(0)
            elif policy == 'lru':
                cache.remove(index)
                cache.append(index)
    return misses


class Bounds(ctypes.Structure):
    _fields_ = [('center', ctypes.c_float*3), ('extent', ctypes.c_float*3)]


def scene_bounds(scene):
    result = (Bounds*len(scene['batches']))()
    for i, (first, count, _, _) in enumerate(scene['batches']):
        points = scene['positions'][first:first+count]
        for a in range(3):
            low, high = min(p[a] for p in points), max(p[a] for p in points)
            result[i].center[a] = f32(f32(low+high)*.5)
            result[i].extent[a] = f32(f32(high-low)*.5)
    return result


def road_pose(path):
    data = Path(path).read_bytes()
    if len(data) < 64 or data[:4] != b'NRD1':
        raise ValueError('Invalid NRD header')
    version, count, crc = struct.unpack_from('<3I', data, 4)
    if version != 1 or not count or len(data) != 64+count*36 or zlib.crc32(data[64:]) != crc:
        raise ValueError('Invalid NRD size/CRC')
    if any(struct.unpack_from('<3I', data, 52)):
        raise ValueError('Invalid NRD reserved fields')
    scale = struct.unpack_from('<f', data, 16)[0]
    spawn = struct.unpack_from('<4f', data, 36)
    if not all(math.isfinite(v) for v in (*spawn, scale)) or not .00001 <= scale <= 1:
        raise ValueError('Invalid NRD camera configuration')
    return scale, spawn


def view_report(scene, indices, poses, cc):
    project = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='nfsmw-index-audit-') as temporary:
        library = Path(temporary)/'visibility.so'
        subprocess.run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC', '-I'+str(project/'include'),
                        str(project/'tools/perf_visibility_bridge.c'), str(project/'source_bmw/world_visibility.c'),
                        str(project/'source_bmw/chase_camera.c'), '-lm', '-o', str(library)], check=True)
        native = ctypes.CDLL(str(library))
        native.perf_visible_pose.argtypes = [ctypes.POINTER(Bounds), ctypes.c_size_t, ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.POINTER(ctypes.c_uint8)]
        native.perf_visible_pose.restype = ctypes.c_bool
        bounds = scene_bounds(scene)
        visible = (ctypes.c_uint8*len(bounds))()
        result = []
        for name, path in poses:
            scale, spawn = road_pose(path)
            for angle in range(0, 360, 30):
                camera = (ctypes.c_float*4)(*spawn[:3], spawn[3]+math.radians(angle))
                if not native.perf_visible_pose(bounds, len(bounds), camera, scale, visible):
                    raise ValueError('Native visibility setup failed')
                runs = merged_runs(scene['batches'], scene['textures'], visible)
                references = sum(count for _, count, _ in runs)
                entry = dict(location=name, heading_offset_deg=angle, world_triangles=references//3,
                             visible_batches=sum(visible), merged_draw_calls=len(runs), index_references=references)
                for policy in ('fifo', 'lru'):
                    for capacity in (8, 16, 32):
                        entry[f'{policy}{capacity}_modeled_transform_misses'] = cache_misses(indices, runs, capacity, policy)
                result.append(entry)
        return result


def audit(scene_path, poses=(), cc='cc'):
    scene = read_scene(scene_path)
    unique, indices = encode(scene['vertices'])
    expanded_bytes = len(indices)*36
    indexed_bytes = len(unique)*36 + len(indices)*2
    report = dict(scene_sha256=hashlib.sha256(scene['raw']).hexdigest(),
                  expanded_vertices=len(indices), unique_vertices=len(unique), world_vertex_stride=36,
                  expanded_gpu_bytes=expanded_bytes, indexed_gpu_bytes=indexed_bytes,
                  allocation_reduction_percent=100*(1-indexed_bytes/expanded_bytes), u16_fits=True,
                  batch_count=len(scene['batches']), triangle_material_order_preserved=True,
                  packed_stream_sha256=hashlib.sha256(b''.join(scene['vertices'])).hexdigest(),
                  decoded_index_stream_sha256=hashlib.sha256(b''.join(unique[i] for i in indices)).hexdigest(),
                  native_attribute_opportunity=native_attribute_opportunity(scene['vertices']),
                  cache_model='Hypothetical FIFO/LRU caches of 8/16/32 entries, reset per actual merged visible run. No PICA cache or FPS claim.',
                  views=view_report(scene, indices, poses, cc) if poses else [])
    return report, unique, indices


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--pose', nargs=2, action='append', default=[], metavar=('NAME', 'NRD_FILE'))
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--output', type=Path, required=True, help='Research-only output directory, not an app installation')
    args = parser.parse_args()
    report, vertices, indices = audit(args.scene, args.pose, args.cc)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output/'vertices-float36.bin').write_bytes(b''.join(vertices))
    (args.output/'indices-u16.bin').write_bytes(struct.pack('<'+'H'*len(indices), *indices))
    print(json.dumps({k:v for k,v in report.items() if k != 'views'}, indent=2))
    print('Sampled views:', len(report['views']))
