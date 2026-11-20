#!/usr/bin/env python3
"""Export source physical compound packages and verify primitive world geometry.

All source assets stay in the caller's private output directory. This is not a
world contact generator; no speculative collision solver is enabled.
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
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
from vehicle_verify_original import ATTR_SHA
from vehicle_rigid_body_reference import Original,State,make_state
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from world_collision_response_shapes import body_packages

ROOT=Path(__file__).resolve().parents[1]
BUNDLE_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'
class Shape(C.Structure):
    _fields_=[('quaternion',C.c_float*4),('center',C.c_float*3),('half_extents',C.c_float*3),('radius',C.c_float),('material_key',C.c_uint32),('token',C.c_uint32),('source_flags',C.c_uint16),('runtime_flags',C.c_uint16),('bound_index',C.c_uint16),('kind',C.c_uint8)]
class Geometry(C.Structure):
    _fields_=[('floats',C.c_float*39),('shape',C.c_uint16),('penetrates_other',C.c_uint16),('delta',C.c_float*3),('overlap',C.c_float)]

def export(bundle,attributes,directory):
    raw=bundle.read_bytes();a=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BUNDLE_SHA or hashlib.sha256(a).hexdigest()!=ATTR_SHA:raise ValueError('Unknown source revision')
    db=VehicleAttributes(a);packages={p['key']:p for p in body_packages(raw)};directory.mkdir(parents=True,exist_ok=True)
    out={'bundle_sha256':BUNDLE_SHA,'attributes_sha256':ATTR_SHA,'profiles':{}}
    for profile,model in [('m3gtre46careerstart','BMWM3GTRE46'),('bmwm3gtre46','BMWM3GTRE46'),('cobaltss','COBALTSS'),('gti','GTI'),('is300','IS300'),('punto','PUNTO')]:
        p=packages[vlt_hash(model)];start=p['source_offset'];data=raw[start:start+p['source_bytes']];name=model.lower()+'.bnd';(directory/name).write_bytes(data)
        row=db.find('pvehicle',profile);ref=db.field_value(row,'rigidbodyspecs');v=ref['value'];spec=db.collections[(v['class_key'],v['collection_key'])]
        out['profiles'][profile]={'file':name,'model_key':f'{p["key"]:08x}','source_offset':start,'source_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'rigidbodyspecs':ref,
          'fields':{n:db.field_value(spec,n) for n in ('COLLISION_BOX_PAD','WALL_FRICTION','GROUND_FRICTION','WORLD_MOMENT_SCALE','GROUND_MOMENT_SCALE')}}
    (directory/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');return out

class PrimitiveOriginal(Original):
    def __init__(self,raw,estimate):
        super().__init__(raw,estimate)
        self.extra_allowed+=((0x80231f14,0x80232190),(0x80089398,0x80089658),(0x801930a8,0x80193498),(0x80089658,0x8008a6ac),(0x80314950,0x80314a3c))
    def geometry(self,shape,old,new):
        u=self.u;r=self.reg;self.pair1={};self.instructions=0
        primitive=bytearray(76);struct.pack_into('>4f',primitive,8,*shape.quaternion);struct.pack_into('>3fI3f',primitive,24,*shape.half_extents,shape.kind,*shape.center)
        def state(s):
            out=bytearray(176);struct.pack_into('>4f',out,0,*s.quaternion);struct.pack_into('>3f',out,16,*s.position);struct.pack_into('>16f',out,112,*s.orientation);return bytes(out)
        u.mem_write(self.OWNER,bytes(0x140));u.mem_write(self.OWNER,bytes(primitive));u.mem_write(self.OWNER+0x80,state(old));u.mem_write(self.STATE,bytes(176));u.mem_write(0x7000f000,bytes(4096))
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_3,self.OWNER);u.reg_write(r.UC_PPC_REG_4,self.OWNER+0x80);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        u.emu_start(0x80231f14,0x6000fff0,count=2000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Primitive prepare budget')
        previous=bytes(u.mem_read(self.OWNER+56,12))
        u.mem_write(self.OWNER+0x80,state(new));u.reg_write(r.UC_PPC_REG_3,self.OWNER);u.reg_write(r.UC_PPC_REG_4,self.OWNER+0x80);u.reg_write(r.UC_PPC_REG_5,self.STATE);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        u.emu_start(0x80231f60,0x6000fff0,count=5000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Primitive geometry budget')
        raw=bytes(u.mem_read(self.STATE,176));g=Geometry();g.floats[:]=struct.unpack_from('>39f',raw);g.shape,g.penetrates_other=struct.unpack_from('>2H',raw,156);g.delta[:]=struct.unpack_from('>3f',raw,160);g.overlap=struct.unpack_from('>f',raw,172)[0]
        return g,struct.pack('=3f',*struct.unpack('>3f',previous))

    def intersection(self,a,b,alias):
        u=self.u;r=self.reg;self.pair1={};self.instructions=0
        def pack(g):return struct.pack('>39f2H4f',*g.floats,g.shape,g.penetrates_other,*g.delta,g.overlap)
        u.mem_write(0x7000f000,bytes(4096));u.mem_write(self.OWNER,bytes(0x140));u.mem_write(self.STATE,bytes(176))
        u.mem_write(self.OWNER,pack(a));u.mem_write(self.STATE,pack(b))
        output=self.OWNER if alias==0 else self.STATE if alias==1 else 0x7000f000
        if alias==2:u.mem_write(output,pack(a))
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_3,self.OWNER);u.reg_write(r.UC_PPC_REG_4,self.STATE);u.reg_write(r.UC_PPC_REG_5,output);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        entry=0x80089658 if a.shape==1 else 0x80089d50
        u.emu_start(entry,0x6000fff0,count=40000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original intersection exceeded budget')
        hit=u.reg_read(r.UC_PPC_REG_3);raw=bytes(u.mem_read(output,176));g=Geometry()
        g.floats[:]=struct.unpack_from('>39f',raw);g.shape,g.penetrates_other=struct.unpack_from('>2H',raw,156);g.delta[:]=struct.unpack_from('>3f',raw,160);g.overlap=struct.unpack_from('>f',raw,172)[0]
        return hit,g

def verify(dol,dolphin,output,cases):
    rng=random.Random(0x31f60);errors=[]
    wrapper='''#include "mw_vehicle_world.h"
#include <string.h>
int run(const MwBodyCollisionShape *p,const MwOriginalRigidBody *a,const MwOriginalRigidBody *b,MwVehicleWorldGeometry *g,float old[3]){
 MwVehicleWorldActor actor;memset(&actor,0,sizeof(actor));actor.count=1;actor.primitives[0]=*p;
 if(!mw_vehicle_world_prepare(&actor,a))return 0;
 memcpy(old,actor.previous_position[0],12);return mw_vehicle_world_geometry(&actor,0,b,g);
}'''
    with DolphinFrsqrteReference(dolphin) as est,tempfile.TemporaryDirectory(prefix='mw-vehicle-world-') as tmp:
        ref=PrimitiveOriginal(dol.read_bytes(),est);p=Path(tmp);(p/'wrapper.c').write_text(wrapper)
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(p/'wrapper.c'),str(ROOT/'source_bmw/mw_vehicle_world.c'),str(ROOT/'source_bmw/mw_vehicle_world_intersection.c'),str(ROOT/'source_bmw/mw_body_collision_shapes.c'),str(ROOT/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(p/'world.so')],check=True)
        lib=C.CDLL(str(p/'world.so'));lib.run.argtypes=[C.POINTER(Shape),C.POINTER(State),C.POINTER(State),C.POINTER(Geometry),C.POINTER(C.c_float)];lib.run.restype=C.c_int
        for i in range(cases):
            s=Shape();s.kind=1+i%2;s.quaternion[:]=rng.choice([(0,0,0,1),(.6,0,0,.8),(0,.6,0,.8),(0,0,.6,.8)])
            s.center[:]=[rng.uniform(-3,3) for _ in range(3)];s.half_extents[:]=[rng.uniform(.05,3) for _ in range(3)]
            a=make_state(rng,i);b=make_state(rng,i+3);g=Geometry();prev=(C.c_float*3)();expected,old=ref.geometry(s,a,b)
            if not lib.run(C.byref(s),C.byref(a),C.byref(b),C.byref(g),prev):raise ValueError('Native supported geometry rejection')
            if bytes(g)!=bytes(expected) or bytes(prev)!=old:
                words=[j for j in range(44) if bytes(g)[j*4:j*4+4]!=bytes(expected)[j*4:j*4+4]]
                errors.append({'case':i,'kind':s.kind,'words':words,'previous_mismatch':bytes(prev)!=old,'actual':list(g.floats),'expected':list(expected.floats)})
        report={'cases':cases,'original_calls':cases*2,'float_bit_mismatches':len(errors),'errors':errors[:5],
          'windows':[{'start':f'{a:08x}','end':f'{b:08x}','sha256':hashlib.sha256(ref.dol.read(a,b-a)).hexdigest()} for a,b in [(0x80231f14,0x80232190),(0x80089398,0x80089658)]],
          'limits':['Explicit synthetic physical primitives; not original wall/ground intersection generation','Original code unchanged, bounded Gekko model excludes FPSCR/subnormal and exact binary64 FMA tie cases']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['original_calls','float_bit_mismatches']}))
    if errors:raise SystemExit(1)

def verify_intersection(dol,dolphin,output,cases):
    rng=random.Random(0x89d50);errors=[];counts={'box_box':0,'sphere_box':0,'hit':0,'miss':0,'actual_source_primitive':0,'edge_cases':0}
    actual=[]
    for file in sorted(output.parent.glob('*.bnd')):
        from world_collision_response_shapes import decode_bound_package
        raw=file.read_bytes();package=decode_bound_package(raw,0,len(raw))
        for bound in package['bounds'][1:]:
            flags=bound['flags']
            if flags&32 or not(flags&14) or not(flags&192) or not(flags&2) or flags&1:continue
            actual.append(bound)
    with DolphinFrsqrteReference(dolphin) as est,tempfile.TemporaryDirectory(prefix='mw-world-intersection-') as tmp:
        ref=PrimitiveOriginal(dol.read_bytes(),est);p=Path(tmp)
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_vehicle_world_intersection.c'),str(ROOT/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(p/'world.so')],check=True)
        lib=C.CDLL(str(p/'world.so'));lib.mw_vehicle_world_intersection.argtypes=[C.POINTER(Geometry)]*3;lib.mw_vehicle_world_intersection.restype=C.c_int
        for i in range(cases):
            ga=[]
            for body in range(2):
                s=Shape();s.kind=1 if body else 1+i%2;s.quaternion[:]=(0,0,0,1)
                s.center[:]=[rng.uniform(-.1,.1) for _ in range(3)];s.half_extents[:]=[rng.uniform(.2,2) for _ in range(3)]
                if not body and actual and i%4==0:
                    bound=actual[(i//4)%len(actual)];s.kind=1 if bound['flags']&64 else 2
                    s.center[:]=bound['center'];s.quaternion[:]=bound['quaternion'] if s.kind==1 else (0,0,0,1)
                    s.half_extents[:]=bound['half_extents'] if s.kind==1 else [bound['source_radius']]*3;counts['actual_source_primitive']+=1
                if body and i%3==0:s.half_extents[2]=0
                a=make_state(rng,i+body);a.position[:]=[rng.uniform(-2.5,2.5) for _ in range(3)];b=State.from_buffer_copy(bytes(a))
                if not body:
                    for axis in range(3):b.position[axis]+=rng.uniform(-.5,.5)
                if i%31==0 or i%37==0:
                    s.quaternion[:]=(0,0,0,1);s.center[:]=(0,0,0)
                    a.quaternion[:]=(0,0,0,1);b.quaternion[:]=(0,0,0,1)
                    for st in (a,b):st.orientation[:]=(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
                    if body:
                        a.position[:]=(0,1,0);b.position[:]=(0,1,0);s.half_extents[:]=(5,5,0)
                    else:
                        s.half_extents[:]=(.5,.5,.5)
                        z=.5+[-1e-5,0,1e-5][i%3];a.position[:]=(0,1,z);b.position[:]=(0,1,z)
                        if i%37==0:b.position[2]=-.5
                        counts['edge_cases']+=1
                g,_=ref.geometry(s,a,b);ga.append(g)
            alias=i%3;expected_hit,expected=ref.intersection(*ga,alias)
            a=Geometry.from_buffer_copy(bytes(ga[0]));b=Geometry.from_buffer_copy(bytes(ga[1]));out=Geometry.from_buffer_copy(bytes(a))
            result=a if alias==0 else b if alias==1 else out
            hit=lib.mw_vehicle_world_intersection(C.byref(a),C.byref(b),C.byref(result))
            counts['box_box' if a.shape==1 else 'sphere_box']+=1;counts['hit' if expected_hit else 'miss']+=1
            if hit!=expected_hit or bytes(result)!=bytes(expected):
                if not errors:(output.parent/'intersection-first-input.bin').write_bytes(bytes(ga[0])+bytes(ga[1])+struct.pack('<I',alias))
                words=[j for j in range(44) if bytes(result)[j*4:j*4+4]!=bytes(expected)[j*4:j*4+4]]
                errors.append({'case':i,'alias':alias,'native_hit':hit,'original_hit':expected_hit,'words':words,'actual':list(result.floats),'expected':list(expected.floats),'actual_overlap':result.overlap,'expected_overlap':expected.overlap})
        report={'cases':cases,'counts':counts,'mismatches':len(errors),'errors':errors[:8],
          'limits':['Unchanged original pure intersection functions with explicit synthetic source geometry','Not complete world barrier construction, packet orientation filtering or vehicle collision callback','Bounded Gekko functional model excludes FPSCR/subnormal and rare binary64 FMA ties']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['cases','counts','mismatches']}))
    if errors:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path);p.add_argument('--attributes',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--dol',type=Path);p.add_argument('--dolphin-reference',type=Path);p.add_argument('--intersection',action='store_true');p.add_argument('--cases',type=int,default=1024);a=p.parse_args()
    if a.bundle or a.attributes:
        if not a.bundle or not a.attributes:p.error('Export requires bundle and attributes')
        export(a.bundle,a.attributes,a.output)
    if a.dol:
        if not a.dolphin_reference:p.error('Verification requires pinned Dolphin reference')
        if not 1<=a.cases<=10000:p.error('Bounded case count required')
        if a.intersection:verify_intersection(a.dol,a.dolphin_reference,a.output/'intersection-verification.json',a.cases)
        else:verify(a.dol,a.dolphin_reference,a.output/'geometry-verification.json',a.cases)
