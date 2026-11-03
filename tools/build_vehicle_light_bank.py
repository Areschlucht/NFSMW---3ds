#!/usr/bin/env python3
"""Build a source-derived BMW brake-state texture bank; never edits input scenes.

Original selectors and source pixels are verified by vehicle_lights_recovery.
Native outputs use pinned tex3ds, with all tiled pixels independently compared.
The bank is an integration input, not recovered light producers/material shaders.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

from PIL import Image
from perf_tiling import IMAGE, tiled_rgba8
from vehicle_lights_recovery import export, scene_aliases
from wheel_rig import inspect_rig


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(dol, presets, scene, texture_dirs, window_target, output, verify=True):
    if output.exists():
        raise ValueError('Output must be a new directory; original scenes are never overwritten')
    if ',' in str(output.resolve()):
        raise ValueError('Output path cannot contain a comma (Docker mount syntax)')
    binding = export(dol, presets, scene, texture_dirs, window_target, verify)
    sources = {}
    for directory in texture_dirs:
        for item in json.loads((directory / 'manifest.json').read_text()):
            path = directory / item['png']
            if path.resolve().parent != directory.resolve():
                raise ValueError('Unexpected source PNG path')
            sources[item['hash']] = path
    targets = {item['target_hash']: item['source_texture']
               for state in binding['states'] for item in state['bindings']}
    output.mkdir(parents=True)
    native = output / 'targets'
    native.mkdir()
    for key in sorted(targets):
        image = Image.open(sources[key]).convert('RGBA')
        if sha(image.tobytes()) != targets[key]['rgba_sha256']:
            raise ValueError('Source changed after selector validation')
        image.save(native / (key + '.png'))
    env = os.environ.copy()
    for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    command = ['docker', '--host=unix:///var/run/docker.sock']
    subprocess.run(command + ['info', '--format', '{{.ServerVersion}}'], env=env, check=True,
                   stdout=subprocess.DEVNULL)
    # Only locally generated hexadecimal PNG names and a private output mount.
    script = ('set -e; for p in /bank/*.png; do '
              'tex3ds -f rgba8 -z none -r -o "${p%.png}.raw" "$p"; '
              'tex3ds -f rgba8 -z none -o "${p%.png}.t3x" "$p"; done')
    subprocess.run(command + ['run', '--rm', '--network', 'none', '--user',
                   f'{os.getuid()}:{os.getgid()}', '--mount',
                   f'type=bind,src={native.resolve()},dst=/bank', IMAGE,
                   'bash', '-lc', script], env=env, check=True)
    texture_rows = []
    for key, item in sorted(targets.items()):
        image = Image.open(native / (key + '.png')).convert('RGBA')
        raw = (native / (key + '.raw')).read_bytes()
        t3x = (native / (key + '.t3x')).read_bytes()
        expected = tiled_rgba8(image.tobytes(), image.width, image.height)
        if len(raw) != len(expected) + 4 or raw[0] != 0 or int.from_bytes(raw[1:4], 'little') != len(expected):
            raise ValueError('Unexpected uncompressed tex3ds payload envelope')
        if raw[4:] != expected or not t3x.endswith(raw):
            raise ValueError('Native texel order/channel mismatch')
        texture_rows.append(dict(target_hash=key, width=image.width, height=image.height,
            gpu_bytes=len(expected), gpu_sha256=sha(expected), t3x_sha256=sha(t3x),
            rgba_sha256=item['rgba_sha256'], native_file='targets/' + key + '.t3x'))
    # Keep original alias keys and batch order. The former placeholder sizes are
    # incompatible with actual original source textures, so change only dimensions.
    body = bytearray((scene / 'body.nfm').read_bytes())
    original_body = bytes(body)
    by_alias = {item['alias_hash']: item for item in binding['states'][0]['bindings']}
    patches = []
    count = struct.unpack_from('<I', body, 16)[0]
    for i in range(count):
        at = 32 + i * 16
        key, width, height, flags = struct.unpack_from('<4I', body, at)
        match = by_alias.get(f'{key:08x}')
        if not match:
            continue
        # All exported selector states must keep this alias's dimensions stable.
        dimensions = {(item['source_texture']['width'], item['source_texture']['height'])
                      for state in binding['states'] for item in state['bindings']
                      if item['alias_hash'] == f'{key:08x}'}
        if len(dimensions) != 1:
            raise ValueError('Alias requires dynamic dimension descriptors')
        new_width, new_height = next(iter(dimensions))
        struct.pack_into('<2I', body, at + 4, new_width, new_height)
        patches.append(dict(texture_slot=i, alias_hash=f'{key:08x}', old_size=[width, height],
                            new_size=[new_width, new_height], preserved_texture_flags=flags))
    if len(patches) != 6:
        raise ValueError('Expected exactly six alias descriptor patches')
    struct.pack_into('<I', body, 24, zlib.crc32(body[32:]))
    (output / 'body.nfm').write_bytes(body)
    before, batches_before = scene_aliases(scene)
    after, batches_after = scene_aliases(output)
    table_end = 32 + count * 16
    if before[table_end:] != after[table_end:] or batches_before != batches_after:
        raise ValueError('Geometry/batch data changed while patching dimensions')
    # NWA's geometry association is a body payload CRC, including texture table.
    # Rebind its header only; preserve wheel pivots/radii/groups byte-for-byte.
    rig = bytearray((scene / 'wheels.nwa').read_bytes())
    batch_count = struct.unpack_from('<I', before, 12)[0]
    old_crc = struct.unpack_from('<I', before, 24)[0]
    wheels, groups = inspect_rig(rig, batch_count, old_crc)
    original_rig = bytes(rig)
    struct.pack_into('<I', rig, 24, struct.unpack_from('<I', after, 24)[0])
    if inspect_rig(rig, batch_count, struct.unpack_from('<I', after, 24)[0]) != (wheels, groups):
        raise ValueError('Wheel rig changed unexpectedly')
    if rig[32:] != original_rig[32:]:
        raise ValueError('Wheel payload changed')
    (output / 'wheels.nwa').write_bytes(rig)
    default = output / 'default-alias-textures'
    default.mkdir()
    for item in binding['states'][0]['bindings']:
        shutil.copyfile(native / (item['target_hash'] + '.t3x'), default / (item['alias_hash'] + '.t3x'))
    states = [dict(name=s['name'], selector_inputs=s['selector_inputs'],
                   aliases={i['alias_hash']: i['target_hash'] for i in s['bindings']})
              for s in binding['states']]
    report = dict(schema=1, car=binding['car'], preset=binding['preset'],
        source_sha256=binding['source_sha256'], sdk_image=IMAGE,
        original_selector_cases_verified=binding['original_selector_cases_verified'],
        texture_bank=texture_rows, unique_gpu_texture_bytes=sum(r['gpu_bytes'] for r in texture_rows),
        states=states, alias_descriptor_patches=patches,
        body_sha256=sha(body), wheel_rig_sha256=sha(rig),
        geometry_and_batch_bytes_unchanged=True, wheel_payload_unchanged=True,
        native_texels_compared=sum(t['width'] * t['height'] for t in targets.values()),
        limits=['No runtime integration or new playable build',
                'State names describe explicit selector inputs, not recovered brake/damage producers',
                'WINDOW_FRONT is caller supplied; live window/tint selection remains separate',
                'Original material split/blend/emission semantics remain unfinished; no shader overrides added',
                'Preserved NFM flags describe the existing prototype, not recovered original lamp materials'],
        integration=['Overlay candidate body.nfm/wheels.nwa and six default-alias-textures into a cloned scene',
                     'Preserve all other source scene textures and metadata; update scene.json dimensions/hashes if packaging it',
                     'Preload the four unique bank textures once; map six alias slots to texture handles for state changes',
                     'Keep bank ownership separate from alias references to avoid duplicate C3D_TexDelete',
                     'Do not perform file reads, GPU allocation or texture upload per frame when braking'])
    (output / 'light-bank.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('dol', 'presets', 'scene', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--texture-dir', type=Path, action='append', required=True)
    p.add_argument('--window-front-target', type=lambda v: int(v, 16), required=True)
    p.add_argument('--skip-original-execution', action='store_true',
                   help='Keep source validation, but do not claim original selector execution')
    a = p.parse_args()
    r = build(a.dol, a.presets, a.scene, a.texture_dir, a.window_front_target,
              a.output, not a.skip_original_execution)
    print(json.dumps({k: r[k] for k in ('unique_gpu_texture_bytes', 'native_texels_compared',
                                      'original_selector_cases_verified', 'geometry_and_batch_bytes_unchanged')}))
