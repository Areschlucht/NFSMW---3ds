#!/usr/bin/env python3
"""Compare original camera profile-cache fragment with portable C.
No original instructions are patched. The bounded fragment executes array-count
and view-state getters; it is not a full camera/dynamics execution.
"""
import argparse,ctypes,hashlib,json,random,struct,subprocess,tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_vlt_hash import vlt_hash
DOL_SHA='33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
LABELS=['ANGLE','LAG','HEIGHT','LATOFFSET','FOV','STIFFNESS','TILTING','SELECTABLE']
class Profile(ctypes.Structure):
    _fields_=[(n,ctypes.c_float*2) for n in ['angle','lag','height','lateral','fov','stiffness']]+[('tilting',ctypes.c_uint32*2)]
class Cache(ctypes.Structure):
    _fields_=[('angle',ctypes.c_uint16),('lag',ctypes.c_float),('height',ctypes.c_float),('lateral',ctypes.c_float),('fov',ctypes.c_uint16),('stiffness',ctypes.c_float),('tilting',ctypes.c_uint16),('index',ctypes.c_uint)]
class Reference:
    INSTANCE=0x81601000;LAYOUT=0x81602000;STACK=0x817ff000
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn.ppc_const import UC_PPC_REG_PC
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA:raise ValueError('DOL SHA mismatch')
        self.dol=DolImage(raw);self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN);self.uc.mem_map(0x80000000,0x1800000)
        for s in self.dol.sections:self.uc.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.allowed=();self.stop=0;self.count=0;self.extra_write_ranges=()
        def code(u,address,size,user):
            self.count+=1
            if address==self.stop:u.emu_stop();return
            if not any(a<=address<b for a,b in self.allowed):raise ValueError(f'Unapproved camera PC {address:08x}')
        def write(u,access,address,size,value,user):
            if not(self.INSTANCE<=address and address+size<=self.INSTANCE+0x124 or self.STACK-0x100<=address and address+size<=self.STACK+0x100 or any(a<=address and address+size<=b for a,b in self.extra_write_ranges)):raise ValueError(f'Camera write escaped {address:08x}')
        self.uc.hook_add(UC_HOOK_CODE,code);self.uc.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,start,stop):
        from unicorn.ppc_const import UC_PPC_REG_PC,UC_PPC_REG_MSR,UC_PPC_REG_1,UC_PPC_REG_31
        self.stop=stop;self.count=0;u=self.uc;u.reg_write(UC_PPC_REG_MSR,0x2000);u.reg_write(UC_PPC_REG_1,self.STACK);u.reg_write(UC_PPC_REG_31,self.INSTANCE)
        u.emu_start(start,stop,count=2000,timeout=1000000)
        if u.reg_read(UC_PPC_REG_PC)!=stop:raise ValueError('Camera reference budget exceeded')
    def profile(self,p,view,scale):
        u=self.uc;layout=bytearray(132)
        for offset,name in [(0,'stiffness'),(16,'lateral'),(32,'lag'),(48,'fov'),(64,'height'),(80,'angle'),(100,'tilting')]:
            struct.pack_into('>4H',layout,offset,2,2,4,0)
            struct.pack_into('>2I' if name=='tilting' else '>2f',layout,offset+8,*getattr(p,name))
        inst=bytearray(0x124);struct.pack_into('>f',inst,0xd4,scale);struct.pack_into('>I',inst,0x118,self.LAYOUT)
        u.mem_write(self.INSTANCE,bytes(inst));u.mem_write(self.LAYOUT,bytes(layout));u.mem_write(0x8041aca0,struct.pack('>I',view&0xffffffff))
        self.allowed=((0x800688dc,0x80068af4),(0x800fe3e8,0x800fe3f4),(0x80058124,0x8005812c))
        self.run(0x800688dc,0x80068af4)
        raw=bytes(u.mem_read(self.INSTANCE+0xd8,26))
        return (struct.unpack_from('>H',raw,2)[0],*struct.unpack_from('>3f',raw,4),struct.unpack_from('>H',raw,16)[0],struct.unpack_from('>f',raw,20)[0],struct.unpack_from('>H',raw,24)[0],1 if view==3 else 0)
    def field(self,mode):
        from unicorn.ppc_const import UC_PPC_REG_4
        self.allowed=((0x800687e0,0x8006888c),);self.uc.reg_write(UC_PPC_REG_4,mode)
        self.run(0x800687e0,0x8006888c);return self.uc.reg_read(UC_PPC_REG_4)
def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('ATTRIBUTES SHA mismatch')
    db=VehicleAttributes(raw,LABELS);reference=Reference(dol.read_bytes());root=Path(__file__).resolve().parents[1]
    profiles=[]
    for row in db.collections.values():
        if row['class_key']!=vlt_hash('camerainfo'):continue
        fields=db.fields(row);arrays=[(ctypes.c_float*2)(*fields[n]['value']['values']) for n in ['ANGLE','LAG','HEIGHT','LATOFFSET','FOV','STIFFNESS']]
        profiles.append((db.label(row['key']),Profile(*arrays,(ctypes.c_uint32*2)(*fields['TILTING']['value']['values']))))
    count=0
    with tempfile.TemporaryDirectory(prefix='mw-camera-') as temporary:
        path=Path(temporary)/'camera.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_camera_profile.c'),'-lm','-o',str(path)],check=True)
        lib=ctypes.CDLL(str(path));lib.mw_original_camera_profile_cache.argtypes=[ctypes.POINTER(Profile),ctypes.c_int,ctypes.c_float,ctypes.POINTER(Cache)];lib.mw_original_camera_profile_cache.restype=ctypes.c_bool;lib.mw_original_camera_profile_field.argtypes=[ctypes.c_int];lib.mw_original_camera_profile_field.restype=ctypes.c_uint32
        for mode in range(7):assert lib.mw_original_camera_profile_field(mode)==reference.field(mode)
        for name,p in profiles:
            for view in [-1,0,1,2,3,4,31]:
                for scale in [-2,0,.125,.5,1,1.1,2]:
                    scale=ctypes.c_float(scale).value;expected=reference.profile(p,view,scale);out=Cache();assert lib.mw_original_camera_profile_cache(ctypes.byref(p),view,scale,ctypes.byref(out));actual=(out.angle,out.lag,out.height,out.lateral,out.fov,out.stiffness,out.tilting,out.index)
                    def bits(values):return struct.pack('>H3fHfHI',*values)
                    if bits(actual)!=bits(expected):raise AssertionError((name,view,scale,actual,expected))
                    count+=1
    return dict(dol_sha256=DOL_SHA,attributes_sha256=ATTR_SHA,camera_collections=len(profiles),profile_cache_bit_cases=count,selector_cases=7,original_profile_fragment='800688DC..80068AF0',instructions_patched=0,limitations=['profile selection/cache only; not full chase camera dynamics','array index follows original view state; semantic identity of state3 not yet established','FOV rawwholeturn conversion proven; horizontal/vertical projection meaning remains open','cameraScale runtime producer and original smoothing remain open'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dol',type=Path,required=True);parser.add_argument('--attributes',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.dol,args.attributes),indent=2))
