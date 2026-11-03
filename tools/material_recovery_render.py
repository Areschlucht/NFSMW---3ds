#!/usr/bin/env python3
"""Record original visuallook post-effect data separately from artistic grading.

The optional runtime TEV grade is not this original bloom pipeline. Shared
ATTRIBUTES reader supplies exact typed values/source bytes; hash-confirmed
curve labels are local recovery candidates, not edits to the shared schema.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from material_recovery_vehicle import DOL_SHA256

CURVES=('ColourBloomCurve','BlackBloomCurve','DetailMapCurve')


def recover(raw,dol=None,labels=()):
    db=VehicleAttributes(raw,labels=(*labels,*CURVES,'ColourBloomTint','ColourBloomIntensity','Desaturation','BlackBloomIntensity','DetailMapIntensity'))
    rows=[]
    for name in ('default','sunset','uves','extreme_uves','copcam'):
        r=db.find('visuallook',name);fields=db.fields(r)
        for n in CURVES:
            item=fields[n];values=struct.unpack('>16f',bytes.fromhex(item['original_bytes']))
            if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite original curve data')
            item['matrix_rows']=[list(values[i:i+4]) for i in range(0,16,4)]
            item['label_evidence']='Candidate label matches the original VLT field key exactly; interpretation additionally anchored by layout/consumer'
        rows.append(dict(collection=name,fields=fields))
    result=dict(attributes_sha256=hashlib.sha256(raw).hexdigest(),class_name='visuallook',rows=rows,
        original_scope='Bloom/desaturation/detail-map parameters and curves, not a recovered 3D RGB LUT',
        artistic_runtime_scope='mw_color_grade_apply: one-stage RGB gains246/255,255/255,201/255; default disabled; no claim these are original coefficients',
        limitations=['Original final multi-pass bloom/scene blend and exact curve semantic binding are not transcribed here',
                     'Original material lighting/reflections and baked world vertex RGB are separate from optional artistic color grade'])
    if dol is not None:
        if hashlib.sha256(dol.data).hexdigest()!=DOL_SHA256:raise ValueError('Render addresses require pinned original DOL')
        ranges=[('visuallook_class_getter',0x802ec4cc,0x802ec4d8),('cubic_curve_leaf',0x802e6548,0x802e65a8),
                ('gc_64x64_lookup_loop',0x8010f184,0x8010f2e0)]
        result['dol_sha256']=DOL_SHA256
        result['code_evidence']=[dict(name=n,start=f'{a:08x}',end_exclusive=f'{b:08x}',file_offset=dol.file_offset(a,b-a),sha256=hashlib.sha256(dol.read(a,b-a)).hexdigest()) for n,a,b in ranges]
        result['curve_leaf']='802E6548 evaluates cubic Bernstein combination of Y values at offsets4,14,24,34; this leaf ignores X coordinates'
        result['gc_lookup']='8010F20C/22C call the curve leaf in nested64x64 loops with input grid0..63 dividedby64; texture population is live GC code, not proof of an RGB color LUT'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('attributes',type=Path);p.add_argument('output',type=Path);p.add_argument('--dol',type=Path)
    a=p.parse_args();r=recover(a.attributes.read_bytes(),DolImage(a.dol.read_bytes()) if a.dol else None)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(f'{len(r["rows"])} original visual-look collections')
