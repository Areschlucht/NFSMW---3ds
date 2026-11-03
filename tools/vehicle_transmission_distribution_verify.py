#!/usr/bin/env python3
"""Original complete final wheel torque/grip distribution comparisons."""
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
from vehicle_transmission_verify import TransmissionReference,EXTRA_ABI
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash as h

for reg in range(20,32):
    offset=0x98+(reg-20)*8
    EXTRA_ABI[0x8024a014+(reg-20)*4]=0xf0000000|(reg<<21)|(1<<16)|offset
    EXTRA_ABI[0x8024a530+(reg-20)*4]=0xe0000000|(reg<<21)|(1<<16)|offset

class Wheel(C.Structure):
    _fields_=[(n,C.c_float) for n in ['omega','compression','long_slip','last_lateral','drive','grip']]+[('locked',C.c_uint)]
class Parameters(C.Structure):
    _fields_=[('torque',C.c_float),('split',C.c_float),('differential',C.c_float*3)]+[(n,C.c_float) for n in ['body_lateral','body_forward','steering']]+[('flags',C.c_uint),('strength',C.c_float)]
FIELDS={'omega':0xd0,'compression':0x78,'long_slip':0xf0,'last_lateral':0x130,'drive':0xe0,'grip':0xec,'locked':0x134}

class DistributionReference(TransmissionReference):
    def __init__(self,raw):
        super().__init__(raw)
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_FPR1
        self.torque=0
        def callback(uc,address,size,unused):uc.reg_write(UC_PPC_REG_FPR1,struct.unpack('>Q',struct.pack('>d',self.torque))[0])
        self.uc.hook_add(UC_HOOK_CODE,callback,begin=self.CALLBACK,end=self.CALLBACK)
    def distribute(self,transmission,parameters,wheels):
        from unicorn.ppc_const import UC_PPC_REG_2,UC_PPC_REG_13
        u=self.uc;actor=bytearray(0x1cc);common=bytearray(0xd0)
        struct.pack_into('>I',actor,0xe4,self.ENGINE);struct.pack_into('>I',actor,0xf8,0x8160a000)
        struct.pack_into('>I',actor,0x114,parameters.flags);struct.pack_into('>f',actor,0x11c,parameters.strength)
        for off,value in [(0x40,parameters.body_lateral),(0x48,parameters.body_forward),(0x8c,parameters.steering)]:struct.pack_into('>f',common,off,value)
        u.mem_write(self.ENGINE,transmission);u.mem_write(0x81609000,bytes(common))
        u.mem_write(0x8160a000,bytes(4)+struct.pack('>I',0x8160a100));table=bytearray(0x50);struct.pack_into('>I',table,0x4c,self.CALLBACK);u.mem_write(0x8160a100,bytes(table))
        before=[]
        for index,wheel in enumerate(wheels):
            raw=bytearray(0x140)
            for name,off in FIELDS.items():struct.pack_into('>I' if name=='locked' else '>f',raw,off,getattr(wheel,name))
            address=0x81610000+index*0x1000;struct.pack_into('>I',actor,0x1bc+index*4,address);u.mem_write(address,bytes(raw));before.append(raw)
        u.mem_write(self.OBJECT,bytes(actor));self.torque=parameters.torque
        self.allowed=((0x8024a00c,0x8024a568),(0x80249ea4,0x8024a00c),(0x80058124,0x8005812c),(0x80193bb4,0x80193c74),(0x8005d1f0,0x8005d338),(self.CALLBACK,self.CALLBACK+4))
        self.write_ranges=tuple((0x81610000+i*0x1000,0x81610140+i*0x1000) for i in range(4))
        u.reg_write(UC_PPC_REG_2,0x80516dc0);u.reg_write(UC_PPC_REG_13,0x80506dc0)
        try:self._call(0x8024a00c,self.OBJECT,r4=0x81609000)
        finally:self.write_ranges=()
        assert bytes(u.mem_read(self.OBJECT,len(actor)))==actor
        assert bytes(u.mem_read(0x81609000,len(common)))==common
        output=[]
        for i,wheel in enumerate(wheels):
            data=bytes(u.mem_read(0x81610000+i*0x1000,0x140));mutable=set(range(0xe0,0xe4))|set(range(0xec,0xf0))
            assert all(a==b for at,(a,b) in enumerate(zip(before[i],data)) if at not in mutable)
            output.append((struct.unpack_from('>f',data,0xe0)[0],struct.unpack_from('>f',data,0xec)[0]))
        return output

def verify(dol,attributes):
    data=attributes.read_bytes()
    if hashlib.sha256(data).hexdigest()!=ATTR_SHA:raise ValueError('Attributes checksum')
    db=VehicleAttributes(data);ref=DistributionReference(dol.read_bytes());root=Path(__file__).resolve().parents[1]
    rng=random.Random(20051126);cases=0;rows=0;angle_calls=0;traces=[]
    bits=lambda v:struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-distribution-') as temporary:
        so=Path(temporary)/'distribution.so'
        sources=['transmission_distribution','transmission','engine','contact','brakes','lateral','friction','contact_scale']
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/f'source_bmw/mw_physics_{s}.c') for s in sources],str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));ANGLE=C.CFUNCTYPE(C.c_float,C.c_float,C.c_float)
        original_angle=lib.mw_physics_contact_angle_turns;original_angle.argtypes=[C.c_float,C.c_float];original_angle.restype=C.c_float
        def angle(x,z):
            nonlocal angle_calls
            angle_calls+=1;return original_angle(x,z)
        callback=ANGLE(angle)
        distribute=lib.mw_physics_transmission_distribute;distribute.argtypes=[C.POINTER(Parameters),C.POINTER(Wheel),ANGLE];distribute.restype=C.c_bool
        for transmission in db.collections.values():
            if transmission['class_key']!=h('transmission'):continue
            fields=db.fields(transmission);differential=fields['DIFFERENTIAL']['value']['values']
            if len(differential)!=3:continue
            rows+=1;layout=bytes(db.bin[transmission['layout']:transmission['layout']+132])
            for torque in (-1000,0,1000):
                for compression in [(0,0,0,0),(.1,.1,.1,.1),(.1,0,0,0),(0,0,.1,.1)]:
                    for flags in (0,1,2,3):
                        for steering in (-1,0,1):
                            params=Parameters(torque,fields['TORQUE_SPLIT']['value'],(C.c_float*3)(*differential),rng.uniform(-30,30),rng.uniform(-30,30),steering,flags,rng.uniform(0,1))
                            wheels=(Wheel*4)(*(Wheel(rng.uniform(-100,100),compression[i],rng.uniform(-100,100),rng.uniform(-100,100),rng.uniform(-100,100),rng.uniform(.5,2),rng.randrange(2)) for i in range(4)))
                            expected=ref.distribute(layout,params,wheels)
                            assert distribute(C.byref(params),wheels,callback)
                            actual=[(w.drive,w.grip) for w in wheels]
                            if [[bits(v) for v in pair] for pair in expected]!=[[bits(v) for v in pair] for pair in actual]:raise AssertionError(('distribution',db.label(transmission['key']),torque,compression,flags,steering,expected,actual))
                            cases+=1
                            if db.label(transmission['key'])=='bmwm3gtre46' and torque==1000 and flags==0 and steering==0:traces.append(dict(compression=compression,output=actual))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,transmission_collections=rows,full_function_cases=cases,portable_original_angle_calls=angle_calls,bmw_trace=traces,original_function='8024A00C..8024A568',limitations=['IEngine.GetTransmissionTorque callback explicitlysupplied as input','wheel spring compression/slip/local velocity/steering producers remaincallerresponsibilities','no whole-engine angular update or whole-car chassis integrationclaimed'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=verify(a.dol,a.attributes);a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['full_function_cases'],result['portable_original_angle_calls'])
