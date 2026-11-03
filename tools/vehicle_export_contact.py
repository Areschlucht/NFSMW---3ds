#!/usr/bin/env python3
"""Extract contact/suspension data through an explicitly selected pvehicle row.

A visual model/preset does not select a physical profile. Component RefSpecs are
resolved from pvehicle; ambiguous upgrade arrays require an explicit index.
The default surface is the original resolver's proven missing-key fallback,
unknown. Replace it with each contact's actual resolved surface at runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_ppc_reference import DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_dol import DolImage
from vehicle_vlt_hash import vlt_hash


def component_reference(db,physical_row,role,level=None):
    field=db.field_value(physical_row,role);value=field['value']
    if isinstance(value,dict) and 'values' in value:
        choices=value['values']
        if level is None:
            if len(choices)!=1:raise ValueError(f'{role} has {len(choices)} alternatives; supply an explicit {role} upgrade index')
            level=0
        if not 0<=level<len(choices):raise ValueError(f'{role} upgrade index exceeds original RefSpec array')
        reference=choices[level]
    else:
        if level not in (None,0):raise ValueError(f'{role} has a scalar RefSpec, not an upgrade array')
        reference=value;level=0
    if not isinstance(reference,dict) or reference.get('class_key')!=vlt_hash(role):raise ValueError(f'{role} RefSpec class mismatch')
    row=db.find(reference['class_key'],reference['collection_key'])
    return row,dict(upgrade_index=level,reference=reference,field_provenance=field)


def export(attributes,dol,collection,surface,upgrade_levels=None):
    raw=attributes.read_bytes();executable=dol.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA or hashlib.sha256(executable).hexdigest()!=DOL_SHA256:raise ValueError('Unrecognized original source revision')
    db=VehicleAttributes(raw);image=DolImage(executable);provenance={};upgrade_levels=upgrade_levels or {}
    physical=db.find('pvehicle',collection);selected={};components={}
    for role in ['tires','brakes','chassis']:
        selected[role],components[role]=component_reference(db,physical,role,upgrade_levels.get(role))
    def field(cls,name):
        row=selected[cls] if cls in selected else db.find(cls,surface)
        value=db.field_value(row,name);provenance[f'{cls}/0x{row["key"]:08x}/{name}']=value;return value['value']
    profile=dict(static_grip=field('tires','STATIC_GRIP'),dynamic_grip=field('tires','DYNAMIC_GRIP'),grip_scale=field('tires','GRIP_SCALE'),normal_brakes=field('brakes','BRAKES'),handbrake=field('brakes','EBRAKE'),brake_lock=field('brakes','BRAKE_LOCK'),calibration=[image.f32(a) for a in [0x8041f350,0x8041f354,0x8041f358,0x8041f35c,0x8041f364]],surface_lateral_grip=field('simsurface','LATERAL_GRIP'),surface_drive_grip=field('simsurface','DRIVE_GRIP'),surface_rolling_resistance=field('simsurface','ROLLING_RESISTANCE'))
    chassis={name:field('chassis',name) for name in ['SPRING_STIFFNESS','SPRING_PROGRESSION','SHOCK_STIFFNESS','SHOCK_EXT_STIFFNESS','SHOCK_VALVING','SHOCK_DIGRESSION','SWAYBAR_STIFFNESS','TRAVEL','RIDE_HEIGHT','SHOCK_BLOWOUT','TRACK_WIDTH','FRONT_AXLE','WHEEL_BASE','FRONT_WEIGHT_BIAS']}
    return dict(attributes_sha256=ATTR_SHA,dol_sha256=DOL_SHA256,physical_profile=dict(name=db.label(physical['key']),key=physical['key']),surface=surface,component_selections=components,parameters=profile,chassis_raw=chassis,provenance=provenance,selection_status='Explicit analysis profile; not proof of original gameplay/spawn selection')


def as_c(report):
    p=report['parameters'];identity=report['physical_profile']
    def value(x):return float(x).hex()+'f'
    def array(xs):return '{'+','.join(value(x) for x in xs)+'}'
    selection=' '.join(f'{role}=0x{data["reference"]["collection_key"]:08x}[{data["upgrade_index"]}]' for role,data in report['component_selections'].items())
    return '\n'.join(['/* Explicit physical pvehicle key0x%08x; %s. */'%(identity['key'],selection),'/* ATTRIBUTES SHA256 '+ATTR_SHA+'; no gameplay/spawn-selection claim. */','#include "mw_physics_contact.h"','static const MwPhysicsContactParameters mw_exported_contact_parameters={',
        '.static_grip='+array(p['static_grip'])+',','.dynamic_grip='+array(p['dynamic_grip'])+',','.grip_scale='+array(p['grip_scale'])+',',
        '.brakes={'+array(p['normal_brakes'])+','+value(p['handbrake'])+','+array(p['brake_lock'])+'},',
        '.calibration='+array(p['calibration'])+',','.lateral_curves=&mw_physics_original_lateral_curves,',
        *['.'+key+'='+value(p[key])+',' for key in ['surface_lateral_grip','surface_drive_grip','surface_rolling_resistance']],'};',''])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--dol',type=Path,required=True);p.add_argument('--physical-profile','--collection',dest='collection',required=True);p.add_argument('--surface',default='unknown');p.add_argument('--format',choices=['json','c'],default='json')
    for role in ['tires','brakes','chassis']:p.add_argument('--'+role+'-level',type=int)
    a=p.parse_args();levels={role:getattr(a,role+'_level') for role in ['tires','brakes','chassis']};report=export(a.attributes,a.dol,a.collection,a.surface,levels);print(as_c(report) if a.format=='c' else json.dumps(report,indent=2))
