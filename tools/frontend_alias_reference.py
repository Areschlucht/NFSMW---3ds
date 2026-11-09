#!/usr/bin/env python3
"""Read-only original Alias evidence and current 3DS source-review snapshot.

No SDK compilation, filesystem mutation of saves or original callback execution.
An identifier/resource occurrence is evidence of vocabulary, not full semantics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

LABELS = ('CreateUIProfileManager','PMCreateNew','PMLoad','PMDelete','PMPopDelete',
          'PMSave','CreateUIDeleteProfile','MainProfileManager')
PACKAGES = ('MC_ProfileManager.fng','MC_DeleteProfile.fng','MC_Bootup_GC.fng',
            'MC_Main_GC.fng','MainMenu.fng','PressStart.fng')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def review(dol, frontend, project):
    raw = dol.read_bytes()
    if sha(raw) != DOL_SHA256:
        raise ValueError('Unexpected USA DOL')
    image = DolImage(raw)
    strings = image.strings(r'(?i)(Profile|PMCreate|PMLoad|PMDelete|PMPopDelete|PMSave|Rename|NameEntry)')
    identifiers = []
    for row in strings:
        if row['text'] not in LABELS:
            continue
        pointer = struct.pack('>I', row['address'])
        locations = [image.address(m.start()) for m in re.finditer(re.escape(pointer), raw)
                     if any(s.offset <= m.start() and m.start()+4 <= s.offset+s.size for s in image.sections)]
        identifiers.append({'text':row['text'],'address':f'{row["address"]:08x}',
                            'conservative_materialized_references':image.constant_xrefs([row['address']]),
                            'direct_pointer_word_locations':[f'{n:08x}' for n in locations]})
    inventory = json.loads((frontend/'inventory.json').read_text())
    indexed = {p['name']:p for p in inventory['packages']}
    packages = []
    for name in PACKAGES:
        record = indexed[name]
        payload = (frontend/name).read_bytes()
        if len(payload) != record['decoded_bytes'] or sha(payload) != record['decoded_sha256']:
            raise ValueError('Decoded frontend differs from original inventory: '+name)
        packages.append({'name':name,'bytes':len(payload),'sha256':sha(payload),
                         'profile_name_literals':[m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{4,}',payload)
                                                  if re.search(rb'(?i)(alias|profile|rename|nameentry)',m.group())]})
    sources = {}
    for relative in ('source_rockport/rockport_main.c','source_bmw/mw_alias.c','include/mw_alias.h'):
        data = (project/relative).read_bytes()
        sources[relative] = {'sha256':sha(data),'bytes':len(data)}
    main = (project/'source_rockport/rockport_main.c').read_text()
    alias = (project/'source_bmw/mw_alias.c').read_text()
    return {'schema':1,'dol_sha256':DOL_SHA256,'original_identifiers':identifiers,
            'validated_original_packages':packages,'reviewed_source_snapshot':sources,
            'source_constructs_observed':{
                'fopen_failure_treated_as_missing':"if(!check)continue;" in main,
                'input_has_touch_then_direction_processing':main.find('if(down&KEY_TOUCH)') < main.find('unsigned rows=frontend_rows();'),
                'new_id_derived_from_current_maximum':'id=s->aliases[i].id+1' in alias,
                'save_corruption_write_guard':'if(alias_storage_blocked)' in main},
            'limits':['Static constructs are a review snapshot, not runtime bug tests',
                      'No original alias capacity, charset, rename support or exact menu ordering proved',
                      'Conservative xref absence is not proof of dead/unreachable code',
                      'No SDK build or original callback execution performed']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','frontend','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    a=p.parse_args();result=review(a.dol,a.frontend,a.project)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'validated_packages':len(result['validated_original_packages']),
                      'original_profile_identifiers':len(result['original_identifiers']),
                      'source_constructs_observed':result['source_constructs_observed']}))
