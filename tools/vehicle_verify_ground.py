#!/usr/bin/env python3
"""Stateful ground-wheel chain versus separately executed original PPC stages.

This is a composition check, not an uninterrupted whole-car executable trace.
Synthetic queries/steering/input routing are explicit; no original tick claim.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_export_contact import component_reference
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT
from vehicle_contact_frame_reference import OriginalWheelFrameReference
from vehicle_verify_contact import Wheel,BrakeState,Parameters,BrakeAttrs,Calibration,Math,UNARY,BINARY,raw_state,BRAKE_MAP,FLOAT_MAP
from vehicle_verify_contact_frame import Vector,Frame
from vehicle_verify_suspension import Axle,Output as SuspensionOutput,Math as SuspensionMath,POWER
from vehicle_verify_original import ATTR_SHA

class GroundWheel(C.Structure):_fields_=[('tire',Wheel),('compression',C.c_float),('air',C.c_float)]
class GroundInput(C.Structure):_fields_=[(n,Vector) for n in ['normal','direction','velocity','up']]+[(n,C.c_float) for n in ['w','speed','mass','dt','extra','antiroll']]
class GroundOutput(C.Structure):_fields_=[('suspension',SuspensionOutput),('frame',Frame),('force',Vector)]
def f32(x):return C.c_float(x).value
def bits(x):return struct.pack('>f',x)
def vector(v):return [getattr(v,k) for k in ['x','y','z']]

def verify(dol,attributes,dolphin):
    raw=attributes.read_bytes();assert hashlib.sha256(raw).hexdigest()==ATTR_SHA
    db=VehicleAttributes(raw);source=OriginalPpcReference(dol.read_bytes());source.initialize_contact_curves();root=Path(__file__).resolve().parents[1];rng=random.Random(200518)
    count=0;contacts=0;airborne=0;steep=0;locked=0;callbacks=[];profiles=[]
    with tempfile.TemporaryDirectory(prefix='mw-ground-') as tmp,DolphinFrsqrteReference(dolphin) as estimate:
        library=Path(tmp)/'ground.so';modules=['ground','suspension','contact_frame','contact','brakes','lateral','friction']
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/('source_bmw/mw_physics_'+s+'.c')) for s in modules],str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(library)],check=True)
        impl=C.CDLL(str(library));step=impl.mw_physics_ground_wheel_step;step.argtypes=[C.POINTER(GroundWheel),C.POINTER(GroundInput),C.POINTER(Axle),C.POINTER(Parameters),C.POINTER(GroundOutput),C.POINTER(SuspensionMath),C.POINTER(Math)];step.restype=C.c_bool
        anti=impl.mw_physics_ground_antiroll;anti.argtypes=[C.POINTER(GroundWheel),C.POINTER(C.c_float),C.POINTER(C.c_float)];anti.restype=None
        ps=OriginalWheelFrameReference(dol.read_bytes(),estimate)
        def cb(kind,a,b=0):
            try:return source.scalar_math(kind,a,estimate,b)
            except Exception as e:callbacks.append(str(e));return float('nan')
        sqrt=UNARY(lambda a,_:cb('sqrt',a));angle=BINARY(lambda a,b,_:cb('angle',a,b));sine=UNARY(lambda a,_:cb('sin',a));power=POWER(lambda a,b,_:cb('pow',a,b));contact_math=Math(sqrt,angle,sine,None);suspension_math=SuspensionMath(power,None)
        def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
        def equal(label,a,b):
            if bits(a)!=bits(b):raise AssertionError((count,label,a,b,bits(a).hex(),bits(b).hex()))
        for profile_name in ['bmwm3gtre46','m3gtre46careerstart']:
            physical=db.find('pvehicle',profile_name);rows={role:component_reference(db,physical,role)[0] for role in ['tires','brakes','chassis']};fields={role:db.fields(row) for role,row in rows.items()};t=fields['tires'];b=fields['brakes'];ch=fields['chassis'];profiles.append(dict(name=profile_name,key=physical['key']))
            wheels=(GroundWheel*4)();reference_states=[];compressions=[0]*4;airs=[0]*4
            axles=[Axle(*[ch[k]['value'][axle] for k in ['SPRING_STIFFNESS','SPRING_PROGRESSION','SHOCK_STIFFNESS','SHOCK_EXT_STIFFNESS','SHOCK_VALVING','SHOCK_DIGRESSION','TRAVEL','RIDE_HEIGHT']],ch['SHOCK_BLOWOUT']['value']) for axle in [0,1]]
            for index in range(4):
                wheels[index].tire.index=index;wheels[index].tire.brake=BrakeState(.3433,0,0,0,0,0,0,index>>1,0,0)
                for n,v in dict(lat_grip=1,grip=1,lat_scale=1,long_scale=1,budget=10000,curve=1,combined=1,coupling=.15).items():setattr(wheels[index].tire,n,v)
                reference_states.append(bytes(raw_state(wheels[index].tire)))
            for frame_index in range(128):
                original_anti=source.suspension_antiroll(layout(rows['chassis']),compressions)
                forces=(C.c_float*4)();anti(wheels,(C.c_float*2)(*ch['SWAYBAR_STIFFNESS']['value']),forces)
                for index in range(4):equal('antiroll snapshot',forces[index],original_anti[index])
                for index in range(4):
                    # Deliberately include release/lock, flight/landing and a
                    # compressed near-vertical surface which must free-spin.
                    phase=frame_index%32;normal=[0,.9999,0] if phase<24 else [.995,.1,0]
                    w=-.5 if phase<4 else rng.choice([-.12,-.08,-.04,.02])
                    speed=0 if phase<4 else 12+frame_index*.1;lat=7 if 12<=phase<20 else rng.uniform(-.5,.5)
                    in_=GroundInput(Vector(*normal),Vector(0,0,1),Vector(lat,0,speed),Vector(0,1,0),w,speed,1300,1/60,0,forces[index]);state=bytearray(reference_states[index])
                    # Caller supplies current engine/brake inputs after the
                    # previous-state distribution stage; no producer inference.
                    for name,value in dict(normal=1 if 8<=phase<12 else 0,hand=1 if index>=2 and 12<=phase<20 else 0,drive=500 if 4<=phase<8 else 0,brake=0).items():
                        setattr(wheels[index].tire.brake,name,value);struct.pack_into('>f',state,BRAKE_MAP[name],value)
                    sfrow=db.find('simsurface',['asphalt','grass','gravel','unknown'][(frame_index//32)%4]);sf=db.fields(sfrow)
                    p=Parameters(*[(C.c_float*2)(*t[k]['value']) for k in ['STATIC_GRIP','DYNAMIC_GRIP','GRIP_SCALE']],BrakeAttrs((C.c_float*2)(*b['BRAKES']['value']),b['EBRAKE']['value'],(C.c_float*2)(*b['BRAKE_LOCK']['value'])),Calibration(4,10,1.2,100,10),None,sf['LATERAL_GRIP']['value'],sf['DRIVE_GRIP']['value'],sf['ROLLING_RESISTANCE']['value'])
                    frame=ps.frame(vector(in_.normal),vector(in_.direction),vector(in_.velocity));normal_dot=ps.normal_dot_up(vector(in_.normal),vector(in_.up))
                    suspension=source.suspension_load(layout(rows['chassis']),index>>1,in_.w,normal_dot,compressions[index],in_.dt,in_.extra,original_anti[index],in_.mass)
                    if suspension['has_contact']:
                        _,state=source.contacted_wheel(layout(rows['tires']),layout(rows['brakes']),layout(sfrow),state,[frame['lateral_velocity'],frame['longitudinal_velocity'],in_.speed,f32(frame['normal_load_factor']*suspension['normal_force']),in_.dt],estimate)
                        force=ps.world_force(vector(in_.normal),frame['lateral_axis'],vector(in_.up),suspension['normal_force'],in_.mass,in_.dt,frame['lateral_velocity'],struct.unpack_from('>f',state,0xd8)[0],struct.unpack_from('>f',state,0xdc)[0]);contacts+=1
                    else:
                        state=source.wheel_brake(layout(rows['brakes']),state,in_.dt,step=True);force=[0,0,0];airborne+=1;steep+=int(suspension['compression']>0)
                    new_air,new_compression=ps.compression_tail(suspension['compression'],airs[index],in_.dt)
                    output=GroundOutput();assert step(C.byref(wheels[index]),C.byref(in_),C.byref(axles[index>>1]),C.byref(p),C.byref(output),C.byref(suspension_math),C.byref(contact_math));assert not callbacks,callbacks
                    for name,_ in SuspensionOutput._fields_:
                        actual=getattr(output.suspension,name);want=suspension[name]
                        if isinstance(actual,bool):assert actual==want,(count,name,actual,want)
                        else:equal('suspension '+name,actual,want)
                    for name,offset in BRAKE_MAP.items():
                        actual=getattr(wheels[index].tire.brake,name);want=struct.unpack_from('>I' if name in ['axle','locked','direction'] else '>f',state,offset)[0]
                        if name in ['axle','locked','direction']:assert actual==want,(count,name,actual,want)
                        else:equal('brake '+name,actual,want)
                    for name,offset in FLOAT_MAP.items():equal('tire '+name,getattr(wheels[index].tire,name),struct.unpack_from('>f',state,offset)[0])
                    for component,want in zip(['x','y','z'],force):equal('world force '+component,getattr(output.force,component),want)
                    equal('compression tail',wheels[index].compression,new_compression);equal('airtime tail',wheels[index].air,new_air)
                    locked+=bool(wheels[index].tire.brake.locked);compressions[index]=new_compression;airs[index]=new_air;reference_states[index]=state;count+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,dolphin_commit=COMMIT,physical_profiles=profiles,stateful_wheel_steps=count,contact_steps=contacts,free_steps=airborne,compressed_free_steps=steep,locked_steps=locked,float_bit_mismatches=0,limitations=['stage-chain comparison with persistent state, not uninterrupted whole-car trace','explicit synthetic query/steering/torque/input producers; no scheduler inference','pow/sine/sqrt callbacks execute original math; default pow precision remains separately reported','body force integration, bottomout chassis correction, material persistence and source gameplay mode transitions remain external'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--dolphin-reference',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes,a.dolphin_reference),indent=2))
