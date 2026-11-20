#!/usr/bin/env python3
"""Bind explicit original physical profile, powertrain and collision parameters.

This exports source data, not an assertion that all runtime provider gates are
implemented. Original inputs remain private; no executable bytes are embedded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from build_vehicle_dynamics import export as wheel_export
from vehicle_attributes import VehicleAttributes
from vehicle_export_contact import component_reference
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_verify_original import ATTR_SHA

BANK_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'

def export(attributes,dol,body_report,bundle,profile,levels):
    attr=attributes.read_bytes();exe=dol.read_bytes();bank=bundle.read_bytes()
    if hashlib.sha256(attr).hexdigest()!=ATTR_SHA or hashlib.sha256(exe).hexdigest()!=DOL_SHA256 or hashlib.sha256(bank).hexdigest()!=BANK_SHA:raise ValueError('Unknown original revision')
    bodies=json.loads(body_report.read_text());body=bodies['profiles'][profile]
    if bodies['bundle_sha256']!=BANK_SHA:raise ValueError('Unknown physical collision source')
    half=struct.unpack_from('<3h',bank,body['root_offset']+16)
    if list(half)!=body['physical_halfextent_mm']:raise ValueError('Physical root extent provenance mismatch')
    db=VehicleAttributes(attr);image=DolImage(exe);physical=db.find('pvehicle',profile);rows={};bindings={};fields={}
    for role in ('engine','transmission','induction','nos','tires','chassis'):rows[role],bindings[role]=component_reference(db,physical,role,levels.get(role))
    def field(role,name):
        row=physical if role=='pvehicle' else rows[role];v=db.field_value(row,name);fields[role+'/'+name]=v
        value=v['value'];return value['values'] if isinstance(value,dict) and 'values' in value else value
    mass=field('pvehicle','MASS');tensor=field('pvehicle','TENSOR_SCALE')[:3]
    if mass!=body['mass']['value'] or tensor!=body['tensor_scale']['value'][:3]:raise ValueError('Physical report profile mismatch')
    for name in ('local_cg','gravity'):
        v=body[name];off=v['file_offset'];original=bytes.fromhex(v['original_bytes'])
        if attr[off:off+len(original)]!=original or v['source_sha256']!=ATTR_SHA:raise ValueError('Body provenance mismatch')
    wheels,wheel_report=wheel_export(attributes,dol,profile,levels)
    mechanical=bytearray(128)+struct.pack('<7f',*[field('chassis',n) for n in ('DRAG_COEFFICIENT','AERO_COEFFICIENT','AERO_CG')],*[image.f32(a) for a in (0x8041f280,0x8041f284,0x8041f278,0x8041f27c)])
    struct.pack_into('<4s7I',mechanical,0,b'MMP1',1,156,0,physical['key'],rows['chassis']['key'],128,7)
    mechanical[64:96]=bytes.fromhex(ATTR_SHA);mechanical[96:128]=bytes.fromhex(DOL_SHA256);struct.pack_into('<I',mechanical,12,zlib.crc32(mechanical[16:]))
    torque=field('engine','TORQUE');braking=field('engine','ENGINE_BRAKING');ratios=field('transmission','GEAR_RATIO');efficiency=field('transmission','GEAR_EFFICIENCY');yaw=field('tires','YAW_CONTROL');limiter=field('engine','SPEED_LIMITER')
    for values,capacity in ((torque,16),(braking,16),(ratios,10),(efficiency,10),(yaw,16)):
        if not values or len(values)>capacity:raise ValueError('Unsupported source curve capacity')
    data=bytearray(1084);struct.pack_into('<4s7I',data,0,b'NVR1',2,len(data),0,physical['key'],620,684,812)
    data[32:64]=bytes.fromhex(BANK_SHA);data[64:96]=bytes.fromhex(ATTR_SHA);data[96:128]=bytes.fromhex(DOL_SHA256);data[128:464]=wheels;data[464:620]=mechanical
    struct.pack_into('<3h2xf3ffIf3fI',data,620,*half,mass,*tensor,body['gravity']['value'],1,field('tires','YAW_SPEED'),*body['local_cg']['value'][:3],len(yaw))
    struct.pack_into('<10I',data,684,*[rows[n]['key'] for n in ('engine','transmission','induction','nos')],len(torque),len(braking),len(ratios),len(efficiency),len(limiter),0)
    struct.pack_into('<f',data,720,field('induction','PSI'))
    struct.pack_into('<2f',data,804,field('induction','SPOOL_TIME_UP'),field('induction','SPOOL_TIME_DOWN'))
    nums=[field('engine',n) for n in ('IDLE','MAX_RPM','RED_LINE','FLYWHEEL_MASS')]+[field('transmission',n) for n in ('FINAL_GEAR','TORQUE_SPLIT','TORQUE_CONVERTER','CLUTCH_SLIP','SHIFT_SPEED')]+[field('nos',n) for n in ('NOS_DISENGAGE','TORQUE_BOOST','NOS_CAPACITY','RECHARGE_MIN','RECHARGE_MAX','RECHARGE_MIN_SPEED','RECHARGE_MAX_SPEED')]+[field('induction',n) for n in ('LOW_BOOST','HIGH_BOOST','VACUUM','SPOOL')]
    struct.pack_into('<20f',data,724,*nums)
    position=812
    for values,capacity in ((torque,16),(braking,16),(ratios,10),(efficiency,10),(yaw,16)):
        struct.pack_into('<'+'f'*capacity,data,position,*(values+[0.]*(capacity-len(values))));position+=capacity*4
    assert position==1084
    struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    return bytes(data),{'schema':2,'physical_profile':profile,'physical_key':f'{physical["key"]:08x}','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'component_bindings':bindings,'source_sha256':{'attributes':ATTR_SHA,'dol':DOL_SHA256,'collision_bundle':BANK_SHA},'body':body,'fields':fields,'wheel_parameters':wheel_report,'runtime_gates':['Source task/controller/contact/body-collision providers required','Native original power supports exponents0..2; other exponent domains reject','Nonempty speed limiter remains unsupported; active induction and story-owned sabotage use original timed branches']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('attributes','dol','body-report','bundle','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--profile',required=True)
    for n in ('engine','transmission','induction','nos','tires','brakes','chassis'):p.add_argument('--'+n+'-level',type=int,required=True)
    a=p.parse_args();data,report=export(a.attributes,a.dol,a.body_report,a.bundle,a.profile,{n:getattr(a,n+'_level') for n in ('engine','transmission','induction','nos','tires','brakes','chassis')})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('Existing runtime profile differs')
    a.output.write_bytes(data);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(a.profile,len(data),report['sha256'])
