#!/usr/bin/env python3
"""Prepare true opening opponent model assets with source palette provenance.

This preserves original KIT00 model geometry and real texture pixels. It does
not claim the original customized preset's kit/hood/rim/vinyl compositor is
implemented: missing generated skin uses that preset's actual BASE_PAINT RGB
as an explicitly flat native diffuse adapter, never a fabricated white livery.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from build_starter_cars import (ATTR_SHA, PAINT_SOURCE_SHA, CarParts,
    VehicleAttributes, build_car, existing_pixels, native_textures, pack_catalog,
    sha, texture_hash)
from material_recovery_presets import report, verify_loader
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

PRESETS = {
    'MUSTANGGT': 'RAZORMUSTANG',
    'SUPRA': 'DDAYSUPRA',
    'SLR': 'BL2',
    'GTO': 'OPM_MUSTANG_BOSS',
    'IMPREZAWRX': 'OPM_WRX_VERSION2',
    'RX8': 'OPM_RX8_Version3',
}


def verify_host(directory):
    """Use the actual native readers/indexer, not a second Python NFM decoder."""
    root = Path(__file__).resolve().parents[1]
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-fsanitize=address,undefined', '-no-pie', '-I'+str(root/'include')]
    with tempfile.TemporaryDirectory(prefix='opening-opponents-') as temporary:
        work = Path(temporary)
        index = work/'index-test'
        subprocess.run(['cc', *flags, str(root/'tests/test_vehicle_index.c'),
                        *(str(root/'source_bmw'/n) for n in
                          ('vehicle_index.c', 'nfs_scene.c', 'wheel_motion.c')),
                        '-lm', '-o', str(index)], check=True)
        result = subprocess.run([str(index), *(str(directory/car) for car in PRESETS)],
                                check=True, capture_output=True, text=True)
        rows = [json.loads(s) for s in result.stdout.splitlines() if s.startswith('{')]
        if len(rows) != 6:
            raise ValueError('Native reconstruction tests did not cover all six models')
        catalog_source = work/'catalog-test.c'
        catalog_source.write_text('''#include "mw_vehicle_catalog.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f&&!fseek(f,0,SEEK_END));
 long n=ftell(f);assert(n>0);rewind(f);void*p=malloc((size_t)n);
 assert(p&&fread(p,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));
 MwVehicleCatalog c;assert(mw_vehicle_catalog_open(&c,p,(size_t)n)&&c.count==6);
 for(unsigned i=0;i<c.count;i++){
  MwVehicleSpec s,found;assert(mw_vehicle_catalog_get(&c,i,&s));
  assert(!s.frontend_key&&s.ecar_key&&s.body_crc&&s.wheel_crc);
  assert(mw_vehicle_catalog_find_id(&c,s.id,&found)&&found.body_crc==s.body_crc);
 }
 free(p);puts("Six original NPC model catalog entries accepted");return 0;
}
''')
        catalog = work/'catalog-test'
        subprocess.run(['cc', *flags, str(catalog_source),
                        str(root/'source_bmw/mw_vehicle_catalog.c'), '-lm', '-o', str(catalog)], check=True)
        subprocess.run([str(catalog), str(directory/'catalog.nvc')],
                       check=True, capture_output=True, text=True)
    return {'actual_nfm_nwa_and_catalog_readers': True, 'asan_ubsan': True,
            'all_source_vertex_attributes_and_post_vflip_reconstructed': True,
            'all_batch_ranges_and_wheel_groups_preserved': True,
            'cars': rows,
            'saved_geometry_bytes': sum(r['saved_bytes'] for r in rows)}


def build(a):
    if a.output.exists():
        raise ValueError('Use a new output directory; no assets overwritten')
    attributes = a.attributes.read_bytes()
    original_parts = a.carparts.read_bytes()
    dol = a.dol.read_bytes()
    if sha(attributes) != ATTR_SHA or sha(original_parts) != PAINT_SOURCE_SHA or sha(dol) != DOL_SHA256:
        raise ValueError('Expected pinned original USA attributes/carparts/DOL')
    db = VehicleAttributes(attributes)
    parts = CarParts(original_parts)
    source_presets = report(original_parts, DolImage(dol))
    if source_presets['part_slots'][76] != 'BASE_PAINT':
        raise ValueError('Actual original preset enum no longer names BASE_PAINT')
    shared = existing_pixels(a.shared_textures)
    built, selected_raw = [], bytearray()
    for model, name in PRESETS.items():
        matches = [r for r in source_presets['records'] if r['preset_name'] == name]
        if len(matches) != 1 or matches[0]['model_name'] != model:
            raise ValueError('Opening preset has ambiguous/different original model')
        preset = matches[0]
        at = preset['file_offset']
        raw = original_parts[at:at+0x290]
        if len(raw) != 0x290 or sha(raw) != preset['record_sha256']:
            raise ValueError('Original preset provenance mismatch')
        selected_raw.extend(raw)
        base = parts.part(int(preset['part_keys'][76], 16))
        values = [parts.value(base, n) for n in ('RED', 'GREEN', 'BLUE', 'GLOSS')]
        if not all(isinstance(v, int) and 0 <= v <= 255 for v in values):
            raise ValueError('Unsupported original base paint components')
        paint = {'name': base['name'], 'key': base['key'], 'source_sha256': parts.sha256,
                 'rgba': values[:3]+[255], 'gloss': values[3],
                 'preset': name, 'preset_offset': at,
                 'preset_record_sha256': preset['record_sha256'],
                 'base_paint_enum': 76, 'base_paint_label': 'BASE_PAINT',
                 'original_part': base}
        car = build_car(a, model, db, shared, paint)
        car['frontend_collection_key'] = '00000000'
        car['opening_preset'] = preset
        car['source_base_paint'] = paint
        car['preset_rendering_complete'] = False
        car['limitations'] = [
            'True source model identity and original KIT00 geometry; source preset custom body kit/hood/spoiler/rim assembly is not recovered here',
            'Source preset BASE_PAINT enum/part RGB retained; missing generated skin is a flat native diffuse adapter, not original paint/reflection rendering',
            'Original preset vinyl/unique livery references are preserved as provenance, not composited or replaced by invented art',
            'Exact typed TireOffsets mount original front tire four times; full original hub/body-height/rim transform remains separate',
            'Intact default light selector and common untinted window binding are inherited documented adapters',
        ]
        (a.output/model/'scene.json').write_text(json.dumps(car, indent=2)+'\n')
        built.append(car)
    parity = verify_loader(DolImage(dol), bytes(selected_raw)) if a.verify_original_loader else None
    pixels = native_textures(a.output) if a.native_textures else 0
    summary = {'schema': 1, 'attributes_sha256': ATTR_SHA,
               'preset_source_sha256': parts.sha256,
               'preset_slot_label_source_sha256': DOL_SHA256,
               'cars': [{k: r[k] for k in ('id', 'display_name', 'frontend_collection_key',
                         'ecar_collection_key', 'half_extent', 'vertices', 'triangles',
                         'body_sha256', 'wheel_rig_sha256', 'limitations')}
                        for r in built],
               'textures_native': bool(pixels),
               'source_rgba_to_native_textures_compared': pixels,
               'original_preset_loader_verification': parity,
               'preset_rendering_complete': False}
    summary['native_catalog'] = pack_catalog(a.output, summary, parts.sha256)
    (a.output/'catalog.json').write_text(json.dumps(summary, indent=2)+'\n')
    if a.verify_host:
        (a.output/'verification.json').write_text(json.dumps(verify_host(a.output), indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ('meshes', 'candidates', 'attributes', 'carparts', 'dol', 'output'):
        parser.add_argument('--'+n, type=Path, required=True)
    parser.add_argument('--shared-textures', type=Path, action='append', required=True)
    parser.add_argument('--native-textures', action='store_true')
    parser.add_argument('--verify-original-loader', action='store_true')
    parser.add_argument('--verify-host', action='store_true')
    args = parser.parse_args()
    result = build(args)
    print(json.dumps({'cars': len(result['cars']),
                      'textures_compared': result['source_rgba_to_native_textures_compared'],
                      'catalog': result['native_catalog'],
                      'preset_rendering_complete': False}, indent=2))
