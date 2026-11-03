#!/usr/bin/env python3
"""New original projection-argument comparisons; leaves prior cache proof intact."""
import argparse,ctypes,hashlib,json,struct,subprocess,tempfile
from pathlib import Path
from camera_recovery_verify import Reference,DOL_SHA
class Projection(ctypes.Structure):
    _fields_=[('vertical',ctypes.c_float),('aspect',ctypes.c_float),('y_factor',ctypes.c_float)]
class ProjectionReference(Reference):
    MATRIX=0x81603000;CAMERA=0x81604000
    def projection(self,raw_fov,width,height,full_height,correction,aspect_scale,fov_scale):
        from unicorn.ppc_const import UC_PPC_REG_28,UC_PPC_REG_29,UC_PPC_REG_30,UC_PPC_REG_FPR0
        u=self.uc;view=bytearray(0x124);struct.pack_into('>I',view,0,self.MATRIX)
        u.mem_write(self.INSTANCE,bytes(view));vp=bytearray(0x30);struct.pack_into('>2I',vp,0x20,width,height);u.mem_write(self.LAYOUT,bytes(vp))
        cam=bytearray(0x100);struct.pack_into('>H',cam,0xc4,raw_fov);u.mem_write(self.CAMERA,bytes(cam));u.mem_write(self.MATRIX,bytes(0x180))
        u.mem_write(0x8041ac60,struct.pack('>I',full_height));u.mem_write(0x8041ac00,struct.pack('>f',aspect_scale));u.mem_write(0x8041abfc,struct.pack('>f',fov_scale))
        u.reg_write(UC_PPC_REG_28,self.CAMERA);u.reg_write(UC_PPC_REG_29,self.MATRIX);u.reg_write(UC_PPC_REG_30,self.LAYOUT)
        u.reg_write(UC_PPC_REG_FPR0+31,struct.unpack('>Q',struct.pack('>d',correction))[0])
        self.allowed=((0x801000ec,0x80100210),(0x800ffbf8,0x800ffc04));self.extra_write_ranges=((self.MATRIX,self.MATRIX+0x180),)
        self.run(0x801000ec,0x80100210)
        fov=struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+1)))[0]
        aspect=struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+2)))[0]
        factor=struct.unpack('>f',bytes(u.mem_read(self.MATRIX+0x110,4)))[0]
        return fov,aspect,factor

def verify(dol_path):
    root=Path(__file__).resolve().parents[1];reference=ProjectionReference(dol_path.read_bytes());cases=0;examples=[]
    with tempfile.TemporaryDirectory(prefix='camera-projection-') as temporary:
        lib=Path(temporary)/'projection.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_camera_profile.c'),'-lm','-o',str(lib)],check=True)
        c=ctypes.CDLL(str(lib));c.mw_original_camera_projection.argtypes=[ctypes.c_uint16,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_float,ctypes.c_float,ctypes.c_float,ctypes.POINTER(Projection)];c.mw_original_camera_projection.restype=ctypes.c_bool
        for raw in [1,4096,8192,14199,16384,20000,27000]:
            for width,height,full in [(640,480,480),(512,448,480),(640,240,480),(400,240,240),(320,240,240)]:
                for correction in [.8,.86,1]:
                    for aspect_scale,fov_scale in [(1,1),(.9,.75),(1.1,.9)]:
                        correction=ctypes.c_float(correction).value;aspect_scale=ctypes.c_float(aspect_scale).value;fov_scale=ctypes.c_float(fov_scale).value
                        expected=reference.projection(raw,width,height,full,correction,aspect_scale,fov_scale);actual=Projection()
                        assert c.mw_original_camera_projection(raw,width,height,full,correction,aspect_scale,fov_scale,ctypes.byref(actual))
                        if struct.pack('>3f',actual.vertical,actual.aspect,actual.y_factor)!=struct.pack('>3f',*expected):raise AssertionError((raw,width,height,full,actual.vertical,actual.aspect,actual.y_factor,expected))
                        cases+=1
                        if raw==14199 and width==640 and height==480 and correction==ctypes.c_float(.8).value and aspect_scale==1:examples.append(dict(raw_fov=raw,viewport=[width,height],vertical_fov=actual.vertical,aspect=actual.aspect))
    ranges=[(0x801000ec,0x80100210),(0x80329cc0,0x80329d90)]
    return dict(dol_sha256=DOL_SHA,original_ranges=[dict(start=f'{a:08x}',end=f'{b:08x}',sha256=hashlib.sha256(reference.dol.read(a,b-a)).hexdigest()) for a,b in ranges],projection_argument_float_bit_cases=cases,instructions_patched=0,examples=examples,proof='OriginalSDK storescot/aspect in00 andcot in11, provingvertical-FOVargument afterexplicitviewportYfactor',limitations=['Projection argument path only; matrixtrig/depth conversion not reproduced','GC aspect correction not automatically appropriate for3DS','Actual single-player viewport record/runtimeglobal changes not yet traced'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dol',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.dol),indent=2))
