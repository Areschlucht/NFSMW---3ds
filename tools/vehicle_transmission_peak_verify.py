#!/usr/bin/env python3
"""Original startup peak-torque RPM and EngineRacer upper-speed selector proof."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from vehicle_attributes import VehicleAttributes
from vehicle_transmission_policy_verify import PolicyReference,EXTRA_ABI
from vehicle_ppc_reference import DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_vlt_hash import vlt_hash as h

for reg in range(28,32):
    off=0x38+(reg-28)*8
    EXTRA_ABI[0x802247f4+(reg-28)*4]=0xf0000000|(reg<<21)|(1<<16)|off
    EXTRA_ABI[0x8022497c+(reg-28)*4]=0xe0000000|(reg<<21)|(1<<16)|off

class PeakReference(PolicyReference):
    def peak(self,engine,induction):
        from unicorn.ppc_const import UC_PPC_REG_5,UC_PPC_REG_6
        self.setup(engine,induction);u=self.uc;out=0x8160b000
        u.mem_write(out,b'\xa5'*4);u.reg_write(UC_PPC_REG_5,out);u.reg_write(UC_PPC_REG_6,0)
        self.allowed=((0x802247ec,0x80224994),(0x80223d30,0x802240ac),(0x80058124,0x8005812c));self.write_ranges=((out,out+4),)
        try:torque=self._call(0x802247ec,self.INSTANCE,r4=0x81601200,float_result=True)
        finally:self.write_ranges=()
        return torque,struct.unpack('>f',bytes(u.mem_read(out,4)))[0]
    def upper_limit(self,engine):
        from unicorn.ppc_const import UC_PPC_REG_31,UC_PPC_REG_MSR,UC_PPC_REG_PC,UC_PPC_REG_FPR0
        obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x14,0x803fdfc8);struct.pack_into('>I',obj,0x150,self.ENGINE)
        self.uc.mem_write(self.OBJECT,bytes(obj));self.uc.mem_write(self.ENGINE,engine)
        self.uc.reg_write(UC_PPC_REG_31,self.OBJECT);self.uc.reg_write(UC_PPC_REG_MSR,0x2000)
        self.allowed=((0x802577a8,0x80257808),(0x80269f0c,0x80269f14));self.count=0
        self.uc.emu_start(0x802577a8,0x80257808,count=50,timeout=200000)
        assert self.uc.reg_read(UC_PPC_REG_PC)==0x80257808
        return tuple(struct.unpack('>d',struct.pack('>Q',self.uc.reg_read(UC_PPC_REG_FPR0+r)))[0] for r in (21,26))

def verify(dol,attributes):
    data=attributes.read_bytes();assert hashlib.sha256(data).hexdigest()==ATTR_SHA
    db=VehicleAttributes(data);ref=PeakReference(dol.read_bytes());root=Path(__file__).resolve().parents[1]
    class Curve(C.Structure):_fields_=[('values',C.POINTER(C.c_float)),('count',C.c_size_t),('idle',C.c_float),('maximum',C.c_float),('redline',C.c_float)]
    class Induction(C.Structure):_fields_=[(n,C.c_float) for n in ['low','high','vacuum','spool']]
    def bits(v):return struct.pack('>f',v)
    def f32(v):return C.c_float(v).value
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    rows=[];cases=0;upper=0
    inds=[r for r in db.collections.values() if r['class_key']==h('induction')]
    default=db.find('induction','default')
    with tempfile.TemporaryDirectory(prefix='mw-peak-') as tmp:
        so=Path(tmp)/'peak.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission_policy.c'),str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));peak=lib.mw_physics_transmission_peak_torque;peak.argtypes=[C.POINTER(Curve),C.POINTER(Induction),C.POINTER(C.c_float),C.POINTER(C.c_float)];peak.restype=C.c_bool
        for e in db.collections.values():
            if e['class_key']!=h('engine'):continue
            ef=db.fields(e);values=ef['TORQUE']['value']['values'];array=(C.c_float*len(values))(*values)
            curve=Curve(array,len(values),*(ef[n]['value'] for n in ['IDLE','MAX_RPM','RED_LINE']));el=layout(e)
            original_limits=ref.upper_limit(el);expected_limits=(f32(curve.idle*ref.dol.f32(0x803fbb0c)),f32(curve.redline*ref.dol.f32(0x803fbb0c)))
            assert list(map(bits,original_limits))==list(map(bits,expected_limits));upper+=1
            chosen={r['key']:r for r in [default,inds[0],inds[len(inds)//2],inds[-1]]}
            try:same=db.find('induction',e['key']);chosen[same['key']]=same
            except KeyError:pass
            for ind in chosen.values():
                fields=db.fields(ind);params=Induction(*(fields[n]['value'] for n in ['LOW_BOOST','HIGH_BOOST','VACUUM','SPOOL']))
                expected=ref.peak(el,layout(ind));torque=C.c_float();rpm=C.c_float();assert peak(C.byref(curve),C.byref(params),C.byref(torque),C.byref(rpm));actual=(torque.value,rpm.value)
                if list(map(bits,expected))!=list(map(bits,actual)):raise AssertionError((db.label(e['key']),db.label(ind['key']),expected,actual))
                cases+=1
                if e['key'] in (h('bmwm3gtre46'),h('m3gtre46careerstart')) and ind['key']==default['key']:rows.append(dict(engine=db.label(e['key']),induction='default',raw_torque=actual[0],peak_torque_rpm=actual[1],minimum_omega=original_limits[0],maximum_omega=original_limits[1]))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,peak_float_bit_cases=cases,upper_limit_cases=upper,upper_selector=dict(vtable='803FDFC8',slot='70',implementation='80269F0C',result=1,field='RED_LINE'),bmw=rows,limitations=['EngineRacer startup tuning pointerNULL; optional non-NULL tuning requires separate port','Peak is sampled induction-adjusted torque, not peak horsepower'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol,a.attributes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
