#!/usr/bin/env python3
"""Read-only evidence inventory for the USA GameCube whole-game port.

Parameter collections, path-hash matches and strings are evidence categories,
not claims of complete feature recovery, roster membership or runtime use.
No game inputs, generated scene assets or application code are changed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

ZDIR_SHA='d5726a00d086edb5f8a47ff4bffa4715f84b44441987fd323141a6dfaf1ba333'
ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
ARCHIVE_BYTES=(315254784,340240384,330981376,346253312)
SECTOR_BASES=(0,153933,320066,481678)
GROUP_NAMES=('BARRIER_','BARRIERS_','PLAYER_BARRIERS_','SCENERY_GROUP_',
             'FREE_ROAM','EnableBinBarriers','DisableBarriers')
METADATA_ENTRIES=('GLOBAL\\GAMEPLAY.BIN',
    *(f'SOUND\\PFData\\MW_Mus_{i}.mpf' for i in range(1,5)),
    'SOUND\\PFData\\MW_Music.mpf','TRACKS\\PRECULLERBOOBOOSCRIPT.HOO')

def name_hash(name):
    value=0xffffffff
    for c in name.upper().encode('ascii'):value=(value*33+c)&0xffffffff
    return value

def read_pinned(path,expected):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Unexpected USA source: '+str(path))
    return raw

def directory_records(raw):
    if not raw or len(raw)%24:raise ValueError('Malformed ZDIR size')
    result=[];previous=0
    for at in range(0,len(raw),24):
        key,archive,sector,combined,size,unknown=struct.unpack_from('<6I',raw,at)
        if key<previous or archive>3:raise ValueError('ZDIR key/selector')
        offset=sector*2048
        if combined!=sector+SECTOR_BASES[archive] or offset+size>ARCHIVE_BYTES[archive]:raise ValueError('ZDIR source range')
        result.append({'hash':f'{key:08x}','archive':archive,'offset_bytes':offset,
            'bytes':size,'directory_record_offset':at})
        previous=key
    return result

def audit(dol,attributes,zdir,scene,project):
    image=DolImage(read_pinned(dol,DOL_SHA256));db=VehicleAttributes(read_pinned(attributes,ATTR_SHA))
    records=directory_records(read_pinned(zdir,ZDIR_SHA));by_key={}
    for r in records:by_key.setdefault(r['hash'],[]).append(r)
    classes=dict(sorted(Counter(db.label(c) for c,k in db.collections).items()))
    models=set();profiles=[]
    for (c,k),row in db.collections.items():
        if db.label(c)!='pvehicle':continue
        fields=db.fields(row);model=fields.get('MODEL',{}).get('value',{})
        text=model.get('text') if isinstance(model,dict) else None
        if text:models.add(text)
        profiles.append({'collection':db.label(k),'model':text,'player_usable_parameter':fields.get('PlayerUsable',{}).get('value')})
    candidates={'GLOBAL\\GAMEPLAY.BIN','FRONTEND\\PLATFORMS\\CAREER_SAFEHOUSE.BIN',
        'FRONTEND\\PLATFORMS\\CAR_LOT.BIN','FRONTEND\\PLATFORMS\\CUSTOMIZATION_SHOP.BIN',
        'TRACKS\\PRECULLERBOOBOOSCRIPT.HOO'}
    for model in models:
        for leaf in ('GEOMETRY.BIN','TEXTURES.BIN','PREVINYL.BIN','VINYLS.BIN'):
            candidates.add('CARS\\'+model+'\\'+leaf)
    for stem in ('MW_Music',*(f'MW_Mus_{i}' for i in range(1,5))):
        for suffix in ('.mpf','.mus'):
            candidates.add('SOUND\\PFData\\'+stem+suffix)
    matches=[]
    for name in sorted(candidates):
        key=f'{name_hash(name):08x}'
        for record in by_key.get(key,[]):matches.append({'candidate_name':name,**record})
    groups=[]
    for name in GROUP_NAMES:
        cursor=0
        while True:
            cursor=image.data.find(name.encode()+b'\0',cursor)
            if cursor<0:break
            groups.append({'text':name,'file_offset':cursor,'address':f'{image.address(cursor):08x}'})
            cursor+=1
    xrefs=image.constant_xrefs([int(r['address'],16) for r in groups])
    for r in xrefs:
        for key in ('instruction','origin','target'):r[key]=f'{r[key]:08x}'
    systems={}
    for category,pattern in {
        'movies':r'(?i)MOVIES\\',
        'audio':r'(?i)(sound\\|\.mus$|\.mpf$|\.abk$|\.gin$|EA_Trax)',
        'frontend':r'(?i)(PressStart\.fng|MainMenu\.fng|Loading.*\.fng|LS_.*\.fng|Main_GC\.fng)',
        'game_flow':r'(CStartNewCareer|CLoadCareer|CResumeCareer|MEnterFreeRoam|MNotifyMovieFinished|MPursuitBreaker)'
    }.items():
        systems[category]=[{**r,'address':f'{r["address"]:08x}'} for r in image.strings(pattern)]
    manifest=json.loads((scene/'manifest.json').read_text())
    barrier_models=[r for r in manifest['models'].values() if r['name'].startswith('XO_TRACKBARRIER')]
    barrier_keys={r['hash'] for r in barrier_models}
    texture_keys={k for r in barrier_models for k in r['texture_hashes']}
    barrier_textures=[r for r in manifest['textures'].values() if r['hash'] in texture_keys]
    placements=[]
    for section in manifest['sections']:
        raw=(scene/section['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=section['sha256']:raise ValueError('Scene section differs from manifest')
        count,offset=struct.unpack_from('<I',raw,24)[0],struct.unpack_from('<I',raw,36)[0]
        for i in range(count):
            at=offset+i*144;obj=raw[at+72:at+144]
            # Original object bytes8..23 contain a bounded name, not a mode flag.
            keys=struct.unpack_from('<4I',obj,24)
            if any(f'{k:08x}' in barrier_keys for k in keys):
                inst=raw[at+8:at+72]
                placements.append({'source_section':section['id'],'source_instance_offset':struct.unpack_from('<I',raw,at)[0],
                    'source_object_offset':struct.unpack_from('<I',raw,at+4)[0],
                    'source_translation':list(struct.unpack_from('<3f',inst,32)),
                    'original_instance_flags_hex':f'{struct.unpack_from("<I",inst,24)[0]:08x}',
                    'bound_slot_keys':[f'{k:08x}' for k in keys]})
    build=(project/'tools/build_streamed_rockport.sh').read_text()
    files=re.search(r"'CFILES=([^']+)'",build)
    linked=files.group(1).split() if files else []
    return {'schema':1,'target':'Need for Speed Most Wanted (2005), USA GameCube',
        'source_sha256':{'dol':DOL_SHA256,'attributes':ATTR_SHA,'zdir':ZDIR_SHA},
        'evidence_limits':['Collection counts are not playable-car/object/song counts',
            'String presence does not prove a code path is reachable on GameCube',
            'Path hash matches require payload/consumer verification; all duplicate directory records are retained',
            'Barrier names identify candidates, not recovered visibility/collision masks',
            'This audit changes no running game behaviour'],
        'attribute_collection_counts':classes,'physical_vehicle_profiles':profiles,
        'candidate_archive_ranges':matches,'original_group_strings':groups,
        'conservative_group_string_xrefs':xrefs,'system_strings':systems,
        'barrier_models':barrier_models,'barrier_texture_variants':barrier_textures,
        'barrier_placement_occurrences':len(placements),
        'barrier_unique_source_instance_offsets':len({r['source_instance_offset'] for r in placements}),
        'barrier_first_placements':placements[:8],
        'barrier_all_placements_sha256':hashlib.sha256(json.dumps(placements,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'production_cfiles':linked,
        'original_physics_modules_linked':[n for n in linked if n.startswith('mw_physics_')],
        'original_camera_modules_linked':[n for n in linked if n.startswith('mw_original_camera_')],
        'audio_modules_linked':[n for n in linked if any(w in n for w in ('audio','sound','ndsp'))]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','attributes','zdir','scene','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--car-scene',type=Path)
    a=p.parse_args();r=audit(a.dol,a.attributes,a.zdir,a.scene,Path(__file__).resolve().parents[1])
    payloads=[x for x in r['candidate_archive_ranges'] if x['candidate_name'] in METADATA_ENTRIES]
    if set(x['candidate_name'] for x in payloads)!=set(METADATA_ENTRIES):
        raise ValueError('Requested metadata not fully matched')
    r['next_metadata_request']={'entries':list(METADATA_ENTRIES),'payload_records':payloads,
        'total_payload_bytes':sum(x['bytes'] for x in payloads),
        'original_archives_required':sorted({x['archive'] for x in payloads})}
    if a.car_scene:
        raw=a.car_scene.read_bytes();car=json.loads(raw)
        r['bmw_light_export_evidence']={'scene_json_sha256':hashlib.sha256(raw).hexdigest(),
            'lamp_parts_present':[x for x in car['parts'] if any(n in x['name'] for n in ('HEADLIGHT','BRAKELIGHT'))],
            'exporter_unresolved_note':car['unresolved'],
            'unresolved_texture_aliases_from_material_research':
                ['02b52399','267d188c','a532fc46','a7e6ea53','d947f346','f68ef19f'],
            'alias_evidence':'research/notes/materials-fidelity/findings.md',
            'interpretation':'Lamp geometry is present; unresolved bindings still need original per-car state/context recovery.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'classes':len(r['attribute_collection_counts']),
        'barrier_models':len(r['barrier_models']),'barrier_placements':r['barrier_placement_occurrences'],
        'candidate_ranges':len(r['candidate_archive_ranges'])},indent=2))
