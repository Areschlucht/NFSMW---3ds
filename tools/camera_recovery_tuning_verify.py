#!/usr/bin/env python3
"""Compare original authored tuning interpolation and export source provenance."""
import argparse,ctypes,hashlib,json,random,struct,subprocess,tempfile
from pathlib import Path
from camera_recovery_cubic_verify import CubicReference
from camera_recovery_verify import DOL_SHA
class Tuning(ctypes.Structure):
    _fields_=[('fields',ctypes.c_float*44)]
def packed(value):return struct.pack('>44f',*value.fields)
class TuningReference(CubicReference):
    LOWER=0x81605000;UPPER=0x81606000
    def parameter(self,speed):
        from unicorn import ppc_const as r
        u=self.uc;controller=bytearray(0x124);struct.pack_into('>f',controller,0x10,speed);u.mem_write(self.INSTANCE,bytes(controller))
        u.mem_write(0x8045acb8,struct.pack('>I3fI',2,0,1,1,self.LOWER))
        u.reg_write(r.UC_PPC_REG_3,0);u.reg_write(r.UC_PPC_REG_9,self.INSTANCE)
        for register,number in [(13,self.dol.f32(0x803d25fc)),(31,0)]:
            u.reg_write(r.UC_PPC_REG_FPR0+register,struct.unpack('>Q',struct.pack('>d',number))[0])
        self.allowed=((0x80073ef8,0x80073f28),)
        self.run(0x80073ef8,0x80073f28)
        return struct.unpack('>d',struct.pack('>Q',u.reg_read(r.UC_PPC_REG_FPR0+13)))[0]
    def blend(self,lower,upper,t):
        from unicorn import ppc_const as r
        u=self.uc;u.mem_write(self.LOWER,lower);u.mem_write(self.UPPER,upper)
        u.mem_write(self.INSTANCE,bytes([0xa5])*176)
        for reg in range(32):u.reg_write(r.UC_PPC_REG_FPR0+reg,0)
        u.reg_write(r.UC_PPC_REG_4,self.INSTANCE);u.reg_write(r.UC_PPC_REG_5,self.UPPER);u.reg_write(r.UC_PPC_REG_6,self.LOWER)
        u.reg_write(r.UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',t))[0]);u.reg_write(r.UC_PPC_REG_LR,0x81700100)
        self.allowed=((0x80071bb8,0x80071ec4),(0x80060d50,0x80060d88))
        self.run(0x80071bb8,0x81700100)
        return bytes(u.mem_read(self.INSTANCE,176))
def verify(path):
    root=Path(__file__).resolve().parents[1];ref=TuningReference(path.read_bytes());rng=random.Random(0x80071bb8);cases=0;modes=[]
    with tempfile.TemporaryDirectory(prefix='camera-tuning-') as temporary:
        so=Path(temporary)/'tuning.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_camera_tuning.c'),'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));f=lib.mw_original_camera_tuning_blend;f.argtypes=[ctypes.POINTER(Tuning),ctypes.POINTER(Tuning),ctypes.c_float,ctypes.POINTER(Tuning)];f.restype=ctypes.c_bool
        parameter=lib.mw_original_camera_tuning_parameter
        parameter.argtypes=[ctypes.c_float,ctypes.POINTER(ctypes.c_float)];parameter.restype=ctypes.c_bool
        parameter_cases=0
        for speed in [0,1,8,13,35.5,70.99999,71,71.00001,100,1000]+[rng.uniform(0,120) for _ in range(500)]:
            speed=ctypes.c_float(speed).value;actual=ctypes.c_float();expected=ref.parameter(speed)
            assert parameter(speed,ctypes.byref(actual))
            if struct.pack('>f',actual.value)!=struct.pack('>f',expected):raise AssertionError(('parameter',speed,actual.value,expected))
            parameter_cases+=1
        vectors=[]
        for mode in range(7):
            address=0x80416578+mode*0x160;raw=ref.dol.read(address,352)
            lower,upper=[Tuning((ctypes.c_float*44)(*struct.unpack_from('>44f',raw,offset))) for offset in [0,176]]
            modes.append(dict(mode=mode,address=f'{address:08x}',file_offset=ref.dol.file_offset(address,352),sha256=hashlib.sha256(raw).hexdigest(),samples=[list(lower.fields),list(upper.fields)]))
            for t in [0,0.00001,.1,.25,.5,.75,.9,.99999,1]+[rng.random() for _ in range(64)]:vectors.append((lower,upper,t))
        for _ in range(250):vectors.append((Tuning((ctypes.c_float*44)(*[rng.uniform(-100,100) for _ in range(44)])),Tuning((ctypes.c_float*44)(*[rng.uniform(-100,100) for _ in range(44)])),rng.uniform(-1,2)))
        for lower,upper,t in vectors:
            t=ctypes.c_float(t).value;expected=ref.blend(packed(lower),packed(upper),t);actual=Tuning.from_buffer_copy(bytes([0xa5])*176)
            assert f(ctypes.byref(lower),ctypes.byref(upper),t,ctypes.byref(actual))
            if packed(actual)!=expected:raise AssertionError((cases,t,struct.unpack('>44f',expected),list(actual.fields)))
            cases+=1
    return dict(dol_sha256=DOL_SHA,whole_sample_bit_cases=cases,speed_parameter_bit_cases=parameter_cases,instructions_patched=0,scalar_psq_abi=ref.abi,original_blend='80071BB8..80071EC0',padding='Four scalar fields; ten vec3 fields with untouched fourth lanes',modes=modes,limitations=['Raw authored fields, not a complete chase camera','Controller duration biases, source scheduler and final matrix still need producer closure'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(verify(a.dol),indent=2)+'\n');print(a.output)
