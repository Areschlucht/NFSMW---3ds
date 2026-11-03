#!/usr/bin/env python3
"""Whole-channel original cubic state comparisons with explicit scalar PSQ ABI."""
import argparse,ctypes,hashlib,json,random,struct,subprocess,tempfile
from pathlib import Path
from camera_recovery_verify import Reference,DOL_SHA
class Cubic(ctypes.Structure):
    _fields_=[('value',ctypes.c_float),('derivative',ctypes.c_float),('target',ctypes.c_float),('target_derivative',ctypes.c_float),('cubic',ctypes.c_float*4),('progress',ctypes.c_float),('duration',ctypes.c_float),('state',ctypes.c_int16),('mode',ctypes.c_int16)]
def values(s):return [s.value,s.derivative,s.target,s.target_derivative,*s.cubic,s.progress,s.duration,s.state,s.mode]
def packed(s):return struct.pack('>10f2h',*values(s))
class CubicReference(Reference):
    def __init__(self,raw):
        super().__init__(raw)
        from unicorn import UC_HOOK_CODE
        from unicorn import ppc_const as r
        self.abi={}
        def abi(u,a,size,user):
            if a==self.stop:return
            word=struct.unpack('>I',bytes(u.mem_read(a,4)))[0]
            if word>>26 in (56,60):
                register=(word>>21)&31;base=(word>>16)&31;offset=word&0xfff
                if base!=1 or (word>>12)&15:raise ValueError('Unapproved PSQ form')
                if offset&0x800:offset-=4096
                address=u.reg_read(r.UC_PPC_REG_1)+offset
                if not self.STACK-0x100<=address<address+8<=self.STACK+0x100:raise ValueError('PSQ stack escaped')
                self.abi[f'{a:08x}']=f'{word:08x}'
                if word>>26==60:
                    number=struct.unpack('>d',struct.pack('>Q',u.reg_read(r.UC_PPC_REG_FPR0+register)))[0]
                    u.mem_write(address,struct.pack('>f',number)+bytes(4))
                else:
                    number=struct.unpack('>f',bytes(u.mem_read(address,4)))[0]
                    u.reg_write(r.UC_PPC_REG_FPR0+register,struct.unpack('>Q',struct.pack('>d',number))[0])
                u.reg_write(r.UC_PPC_REG_PC,a+4)
            elif word>>26==4:raise ValueError('Unexpected paired arithmetic')
        self.uc.hook_add(UC_HOOK_CODE,abi)
    def step(self,state,dt,limit,accel):
        from unicorn import ppc_const as r
        u=self.uc;u.mem_write(self.INSTANCE,packed(state));self.allowed=((0x80208128,0x8020826c),(0x80207eb8,0x80207f68),(0x80207f68,0x80208128))
        u.reg_write(r.UC_PPC_REG_3,self.INSTANCE);u.reg_write(r.UC_PPC_REG_LR,0x81700100)
        for reg in range(32):u.reg_write(r.UC_PPC_REG_FPR0+reg,0)
        for reg,number in enumerate((dt,limit,accel),1):u.reg_write(r.UC_PPC_REG_FPR0+reg,struct.unpack('>Q',struct.pack('>d',number))[0])
        self.run(0x80208128,0x81700100)
        return bytes(u.mem_read(self.INSTANCE,44))
def verify(path):
    root=Path(__file__).resolve().parents[1];reference=CubicReference(path.read_bytes());rng=random.Random(0x80208128);cases=0
    vectors=[]
    for state in [0,1,2]:
        for mode in [0,1,-1]:
            for duration in [-1,0,0.000001,0.00001,.05,.2,1,3]:
                for dt in [-.01,0,1/120,1/30,.5,2]:
                    for limits in [(0,0),(2,0),(0,3),(2,3)]:
                        if duration==0 and state==2 and any(limits):continue
                        vectors.append((Cubic(-2,.3,5,-.5,(ctypes.c_float*4)(.5,-.3,.2,1),.5,duration,state,mode),dt,*limits))
    for _ in range(400):vectors.append((Cubic(*[rng.uniform(-20,20) for _ in range(4)],(ctypes.c_float*4)(*[rng.uniform(-10,10) for _ in range(4)]),rng.random(),rng.uniform(.05,3),rng.choice([1,2]),rng.choice([0,1])),rng.uniform(0,.1),rng.choice([0,1,10]),rng.choice([0,2,100])))
    with tempfile.TemporaryDirectory(prefix='camera-cubic-') as temporary:
        so=Path(temporary)/'cubic.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_camera_cubic.c'),'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));function=lib.mw_original_camera_cubic_step;function.argtypes=[ctypes.POINTER(Cubic),ctypes.c_float,ctypes.c_float,ctypes.c_float];function.restype=ctypes.c_bool
        for initial,dt,limit,accel in vectors:
            dt,limit,accel=[ctypes.c_float(x).value for x in (dt,limit,accel)]
            expected=reference.step(initial,dt,limit,accel);actual=Cubic.from_buffer_copy(bytes(initial));assert function(ctypes.byref(actual),dt,limit,accel)
            if packed(actual)!=expected:raise AssertionError((values(initial),dt,limit,accel,values(actual),struct.unpack('>10f2h',expected)))
            cases+=1
    return dict(dol_sha256=DOL_SHA,whole_channel_bit_cases=cases,scalar_psq_abi=reference.abi,instructions_patched=0,original_step='80208128..80208268',limitations=['Original scalar channel numerical state only; authored camera durations/modes and scheduler still need consumer closure','PSQ stack saves model scalar float32 only; no paired arithmetic executed','Invalid/nonfinite or singular limit metadata rejected by portable API'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',required=True,type=Path);a=p.parse_args();print(json.dumps(verify(a.dol),indent=2))
