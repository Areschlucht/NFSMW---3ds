#!/usr/bin/env python3
"""Export verified BMW lamp alias bindings without modifying a runtime/scene.

The intact selector is recovered; original flag generation, window context,
source shader/alpha state and damage draw paths remain separate requirements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image
from material_recovery_vehicle import (DOL_SHA256, LIGHT_FIELDS, light_targets,
    original_targets, texture_hash)
from material_recovery_presets import report as preset_report, part_slot_labels
from vehicle_dol import DolImage

PRESETS_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'

def digest(raw):return hashlib.sha256(raw).hexdigest()

def scene_aliases(scene):
    raw=(scene/'body.nfm').read_bytes()
    if len(raw)<32:raise ValueError('Short NFM')
    magic,version,nv,nb,nt,size,crc,flags=struct.unpack_from('<4s7I',raw)
    if magic!=b'NFM1' or version!=1 or flags or size!=len(raw)-32 or size!=nt*16+nb*16+nv*32 or zlib.crc32(raw[32:])!=crc:
        raise ValueError('Invalid NFM schema/CRC')
    texture_keys=[struct.unpack_from('<I',raw,32+i*16)[0] for i in range(nt)]
    aliases={texture_hash(n):n for n in LIGHT_FIELDS}
    result=[]
    for i in range(nb):
        first,count,slot,reserved=struct.unpack_from('<4I',raw,32+nt*16+i*16)
        if first+count>nv or count%3 or slot>=nt or reserved:raise ValueError('Invalid NFM batch')
        if texture_keys[slot] in aliases:
            result.append(dict(nfm_batch=i,texture_slot=slot,alias=aliases[texture_keys[slot]],
                alias_hash=f'{texture_keys[slot]:08x}',first_vertex=first,vertex_count=count))
    return raw,result

def texture_inventory(directories):
    result={}
    for directory in directories:
        manifest=(directory/'manifest.json').read_bytes()
        for t in json.loads(manifest):
            path=directory/t['png']
            if path.resolve().parent!=directory.resolve():raise ValueError('Unexpected PNG path')
            key=int(t['hash'],16)
            rgba=Image.open(path).convert('RGBA')
            pixels=rgba.tobytes()
            if rgba.size!=(t['width'],t['height']) or digest(pixels)!=t['rgba_sha256']:
                raise ValueError('Source texture pixel/dimension mismatch')
            item=dict(hash=f'{key:08x}',source_name=t['name'],width=rgba.width,height=rgba.height,
                rgba_sha256=digest(pixels),png_sha256=digest(path.read_bytes()),
                manifest_sha256=digest(manifest),png=path.name,
                alpha_minmax=list(rgba.getchannel('A').getextrema()))
            if key in result and result[key]['rgba_sha256']!=item['rgba_sha256']:
                raise ValueError('Ambiguous texture source pixels')
            result[key]=item
    return result

def export(dol,presets,scene,texture_dirs,window_target,verify=False):
    image=DolImage(dol.read_bytes())
    if digest(image.data)!=DOL_SHA256:raise ValueError('Expected USA DOL')
    raw=presets.read_bytes()
    if digest(raw)!=PRESETS_SHA:raise ValueError('Expected verified original preset source')
    records=[x for x in preset_report(raw)['records'] if x['preset_name']=='M3GTRCAREERSTART']
    if len(records)!=1 or records[0]['model_name']!='BMWM3GTRE46':raise ValueError('Hero preset mismatch')
    record=records[0];slots=part_slot_labels(image)
    # No TEXTURE_NAME override is possible through an absent selected part.
    if any(record['part_keys'][i]!='00000000' for i in (0x40,0x41)):
        raise ValueError('Selected lamp parts require actual TEXTURE_NAME attribute resolution')
    nfm,batches=scene_aliases(scene);textures=texture_inventory(texture_dirs)
    aliases=sorted({x['alias'] for x in batches})
    if len(aliases)!=6:raise ValueError('Expected six BMW scene light aliases')
    states=[]
    for label,enabled,suppressed in [('intact_no_brake',0,0),('intact_both_side_brakes',24,0),
            ('intact_brakes_suppressed',24,24)]:
        args=dict(window_front_target=window_target,flags_1608=enabled,flags_160c=suppressed,force_side_lights=0)
        targets=light_targets('BMWM3GTRE46',**args)
        if verify and original_targets(image,'BMWM3GTRE46',**args)!=targets:
            raise ValueError('Original selector mismatch')
        selected=[]
        for alias in aliases:
            target=targets[alias]
            if target not in textures:raise ValueError(f'Source texture absent: {target:08x}')
            selected.append(dict(alias=alias,alias_hash=f'{texture_hash(alias):08x}',
                target_hash=f'{target:08x}',source_texture=textures[target]))
        states.append(dict(name=label,selector_inputs=args,bindings=selected))
    return dict(schema=1,car='BMWM3GTRE46',preset='M3GTRCAREERSTART',
        source_sha256=dict(dol=DOL_SHA256,presets=PRESETS_SHA,nfm=digest(nfm)),
        selected_lamp_slots=[dict(slot=i,name=slots[i],part_key=record['part_keys'][i]) for i in (0x40,0x41)],
        preset_record_sha256=record['record_sha256'],preset_file_offset=record['file_offset'],
        original_code_ranges=[dict(start=f'{start:08x}',end_exclusive=f'{end:08x}',
            sha256=digest(image.read(start,end-start))) for start,end in
            [(0x802d60c0,0x802d60d0),(0x802d6964,0x802d6ae0),(0x8027ebd0,0x8027ec20)]],
        nfm_alias_batches=batches,states=states,original_selector_cases_verified=len(states) if verify else 0,
        limits=['Read-only binding export; runtime assets/shaders are unchanged',
            'Flags are original selector inputs, not a recovered brake/damage state producer',
            'WINDOW_FRONT target is explicitly supplied; unmodified global source is not a verified live tint target',
            'Geometry merges source material runs; alpha/emissive/reflection state must be restored separately',
            'No halos/projected lights/reverse/emergency effect implementation is claimed'],
        integration_contract=['Keep six alias slots and switch resolved source texture handles at vehicle state update',
            'Use per-vehicle/preset/kit seeds; zero lamp slots justify defaults only for this verified preset',
            'Route the resolved current WINDOW_FRONT handle to both headlight glass aliases',
            'Preserve original material-run shader/alpha state and source UVs; do not use a global opaque override',
            'Feed original enable/suppress words through the recovered consumer; recover producers before claiming faithful state generation'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','presets','scene','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--texture-dir',type=Path,action='append',required=True)
    p.add_argument('--window-front-target',type=lambda x:int(x,16),required=True)
    p.add_argument('--verify-original',action='store_true')
    a=p.parse_args();r=export(a.dol,a.presets,a.scene,a.texture_dir,a.window_front_target,a.verify_original)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(alias_batches=len(r['nfm_alias_batches']),states=len(r['states']),
        verified_original_cases=r['original_selector_cases_verified'])))
