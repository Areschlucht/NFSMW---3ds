#!/usr/bin/env python3
"""Pack explicit source wheel-force parameters and compare steering slices.

No whole-car/chassis or player-assist equivalence is claimed. RefSpec upgrade
indices are explicit; ambiguous source arrays are never guessed.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import zlib
from vehicle_attributes import VehicleAttributes
from vehicle_export_contact import component_reference
from vehicle_ppc_reference import DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_dol import DolImage
from vehicle_vlt_hash import vlt_hash

ROOT=Path(__file__).resolve().parents[1]
MODULES=['mw_vehicle_dynamics','mw_physics_contact_scale','mw_physics_ground','mw_physics_contact_geometry','mw_physics_contact_frame','mw_physics_suspension','mw_physics_contact','mw_physics_brakes','mw_physics_lateral','mw_physics_friction','mw_physics_tires','mw_physics_transmission_distribution','mw_physics_transmission','mw_physics_engine','mw_gekko_math']
def sha(b):return hashlib.sha256(b).hexdigest()


def export(attributes,dol,profile,levels):
    raw=attributes.read_bytes();executable=dol.read_bytes()
    if sha(raw)!=ATTR_SHA or sha(executable)!=DOL_SHA256:raise ValueError('Unknown original revision')
    db=VehicleAttributes(raw);image=DolImage(executable);physical=db.find('pvehicle',profile);rows={};bindings={};provenance={}
    for name in ('tires','brakes','chassis','transmission'):
        rows[name],bindings[name]=component_reference(db,physical,name,levels.get(name))
    def field(role,name):
        value=db.field_value(physical if role=='pvehicle' else rows[role],name)
        provenance[role+'/'+name]=value;decoded=value['value']
        return decoded['values'] if isinstance(decoded,dict) and 'values' in decoded else decoded
    mass=field('pvehicle','MASS');dimension=[]
    for name in ('SECTION_WIDTH','ASPECT_RATIO','RIM_SIZE'):dimension+=field('tires',name)
    ch={name:field('chassis',name) for name in ('SPRING_STIFFNESS','SPRING_PROGRESSION','SHOCK_STIFFNESS','SHOCK_EXT_STIFFNESS','SHOCK_VALVING','SHOCK_DIGRESSION','TRAVEL','RIDE_HEIGHT','SHOCK_BLOWOUT','TRACK_WIDTH','FRONT_AXLE','WHEEL_BASE','SWAYBAR_STIFFNESS')}
    scalars=[mass]+dimension
    for axle in (0,1):scalars += [ch[name][axle] for name in ('SPRING_STIFFNESS','SPRING_PROGRESSION','SHOCK_STIFFNESS','SHOCK_EXT_STIFFNESS','SHOCK_VALVING','SHOCK_DIGRESSION','TRAVEL','RIDE_HEIGHT')]+[ch['SHOCK_BLOWOUT']]
    for name in ('STATIC_GRIP','DYNAMIC_GRIP','GRIP_SCALE'):scalars+=field('tires',name)
    scalars+=field('brakes','BRAKES')+[field('brakes','EBRAKE')]+field('brakes','BRAKE_LOCK')
    scalars += [image.f32(a) for a in (0x8041f350,0x8041f354,0x8041f358,0x8041f35c,0x8041f364)]
    scalars += ch['TRACK_WIDTH']+[ch['FRONT_AXLE'],ch['WHEEL_BASE']]+ch['SWAYBAR_STIFFNESS']+[field('tires','STEERING')]
    scalars += [field('transmission','TORQUE_SPLIT')]+field('transmission','DIFFERENTIAL')
    if len(scalars)!=52:raise ValueError('Unexpected source profile dimensions')
    data=bytearray(128)+struct.pack('<52f',*scalars)
    struct.pack_into('<4s10I',data,0,b'NDP1',1,len(data),0,physical['key'],rows['tires']['key'],rows['brakes']['key'],rows['chassis']['key'],rows['transmission']['key'],128,52)
    data[64:96]=bytes.fromhex(ATTR_SHA);data[96:128]=bytes.fromhex(DOL_SHA256);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    surfaces=[]
    for (cls,key),row in sorted(db.collections.items()):
        if cls!=vlt_hash('simsurface'):continue
        fields={n:db.field_value(row,n) for n in ('LATERAL_GRIP','DRIVE_GRIP','ROLLING_RESISTANCE')}
        surfaces.append({'key':f'{key:08x}','name':db.label(key),'fields':fields})
    return bytes(data),{'schema':1,'physical_profile':{'name':db.label(physical['key']),'key':f'{physical["key"]:08x}'},'component_bindings':bindings,'provenance':provenance,'source_sha256':{'attributes':ATTR_SHA,'dol':DOL_SHA256},'scalars':scalars,'simsurfaces':surfaces,'bytes':len(data),'sha256':sha(data),'limits':['Explicit pvehicle/component indices, not a recovered saved-game upgrade selector','Wheel forces and source steering geometry only; original input assists, body forces, bottomout, chassis integration and scheduler remain external','Physical halfextent and WORLD CG offset require actual VehicleParams providers, not visual model bounds','Actual contact material must select simsurface; the pack does not silently choose asphalt','Runtime libm power/sine precision has separately documented original comparison limits']}


def verify(dol,attributes):
    from vehicle_contact_frame_reference import OriginalWheelFrameReference
    from unicorn.ppc_const import UC_PPC_REG_3,UC_PPC_REG_4
    raw=dol.read_bytes();db=VehicleAttributes(attributes.read_bytes())
    class Reference(OriginalWheelFrameReference):
        def __init__(self):
            super().__init__(raw,None)
            self.extra_allowed += ((0x80244c4c,0x80244cd0),(0x80248a34,0x80248a78))
        def ackermann(self,turns,track,base):
            self.u.mem_write(0x6000107c,struct.pack('>I',0x60002000));self.u.mem_write(0x60002020,struct.pack('>f',track));self.u.mem_write(0x60002054,struct.pack('>f',base));self.putfloating(1,turns)
            self.run(0x80244c4c,0x80244cd0,[(UC_PPC_REG_3,0x60001000)])
            return self.floating(28),self.floating(29)
        def fallback(self,scale,mode,input):
            self.u.mem_write(0x600010a8,struct.pack('>I',0x60002000));self.u.mem_write(0x60002048,struct.pack('>f',scale));self.u.mem_write(0x600030c8,struct.pack('>h',mode));self.u.mem_write(0x6000308c,struct.pack('>f',input))
            self.run(0x80248a34,0x6000fff0,[(UC_PPC_REG_3,0x60001000),(UC_PPC_REG_4,0x60003000)])
            return self.floating(1)
    ref=Reference();rng=random.Random(20051109);fallback_cases=geometry_cases=0
    with tempfile.TemporaryDirectory(prefix='mw-dynamics-') as tmp:
        lib=Path(tmp)/'dynamics.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),*[str(ROOT/'source_bmw'/(s+'.c')) for s in MODULES],'-lm','-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));fallback=dll.mw_vehicle_dynamics_steer_fallback;fallback.argtypes=[C.c_float,C.c_int,C.c_float,C.POINTER(C.c_float)];fallback.restype=C.c_bool
        geometry=dll.mw_vehicle_dynamics_ackermann;geometry.argtypes=[C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float)];geometry.restype=C.c_bool
        for profile in ('m3gtre46careerstart','bmwm3gtre46','cobaltss','gti','is300','punto'):
            p=db.find('pvehicle',profile);t,_=component_reference(db,p,'tires',0);ch,_=component_reference(db,p,'chassis',0)
            scale=db.field_value(t,'STEERING')['value'];track=db.field_value(ch,'TRACK_WIDTH')['value'][0];base=db.field_value(ch,'WHEEL_BASE')['value']
            for i in range(256):
                mode=i%3;input=C.c_float(rng.uniform(-1,1)).value;want=ref.fallback(scale,mode,input);out=C.c_float()
                assert fallback(scale,mode,input,C.byref(out))
                if struct.pack('>f',out.value)!=struct.pack('>f',want):raise AssertionError(('fallback',profile,i,out.value,want))
                fallback_cases+=1
                turns=C.c_float(rng.uniform(-.49,.99)).value;want=ref.ackermann(turns,track,base);angles=(C.c_float*2)();assert geometry(turns,track,base,angles)
                if [struct.pack('>f',v) for v in angles]!=[struct.pack('>f',v) for v in want]:raise AssertionError(('ackermann',profile,i,list(angles),want))
                geometry_cases+=1
    return {'fallback_original_cases':fallback_cases,'ackermann_original_cases':geometry_cases,'float_bit_mismatches':0,'ranges':['80248A34..80248A78','80244C4C..80244CD0'],'limits':['Fallback selected only when original steering-interface path is absent/inactive; not normal player assist','Ackermann comparison stops before original trigonometry/body rotation; it verifies exact left/right angles, not arbitrary libm sine/cosine','Unchanged original slice execution with explicit synthetic original inputs; not whole-car telemetry']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('attributes','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--profile',required=True);p.add_argument('--verify-original',action='store_true')
    for name in ('tires','brakes','chassis','transmission'):p.add_argument('--'+name+'-level',type=int)
    a=p.parse_args();data,report=export(a.attributes,a.dol,a.profile,{n:getattr(a,n+'_level') for n in ('tires','brakes','chassis','transmission')})
    if a.verify_original:report['steering_verification']=verify(a.dol,a.attributes)
    if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('Existing profile differs')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if not a.output.exists():a.output.write_bytes(data)
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('provenance','simsurfaces','scalars')},indent=2))
