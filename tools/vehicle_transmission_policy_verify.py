#!/usr/bin/env python3
"""Original induction, startup shift-table and request-policy comparisons."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_attributes import VehicleAttributes
from vehicle_transmission_verify import TransmissionReference,EXTRA_ABI
from vehicle_vlt_hash import vlt_hash as h
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256

for reg in range(17,32):
    offset=0x48+(reg-17)*8
    EXTRA_ABI[0x80224cc4+(reg-17)*4]=0xf0000000|(reg<<21)|(1<<16)|offset
    EXTRA_ABI[0x80224fa8+(reg-17)*4]=0xe0000000|(reg<<21)|(1<<16)|offset
for reg in range(26,32):
    offset=0x18+(reg-26)*8
    EXTRA_ABI[0x80223db0+(reg-26)*4]=0xf0000000|(reg<<21)|(1<<16)|offset
    EXTRA_ABI[0x8022408c+(reg-26)*4]=0xe0000000|(reg<<21)|(1<<16)|offset
for reg in range(27,32):
    offset=0x28+(reg-27)*8
    EXTRA_ABI[0x80255de8+(reg-27)*4]=0xf0000000|(reg<<21)|(1<<16)|offset
    EXTRA_ABI[0x80255f68+(reg-27)*4]=0xe0000000|(reg<<21)|(1<<16)|offset

class PolicyReference(TransmissionReference):
    def setup(self,engine,induction,transmission=None):
        self.uc.mem_write(self.ENGINE,engine);self.uc.mem_write(0x81605000,induction)
        self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8))
        self.uc.mem_write(0x81601200,bytes(8)+struct.pack('>I',0x81605000)+bytes(8))
        if transmission is not None:
            self.uc.mem_write(0x81603000,transmission)
            self.uc.mem_write(0x81601100,bytes(8)+struct.pack('>I',0x81603000)+bytes(8))
    def induction(self,engine,induction,rpm,amount):
        from unicorn.ppc_const import UC_PPC_REG_5,UC_PPC_REG_6,UC_PPC_REG_FPR2
        self.setup(engine,induction);u=self.uc
        u.reg_write(UC_PPC_REG_5,0);u.reg_write(UC_PPC_REG_6,0)
        u.reg_write(UC_PPC_REG_FPR2,struct.unpack('>Q',struct.pack('>d',amount))[0])
        self.allowed=((0x80223d30,0x802240ac),)
        return self._call(0x80223da8,self.INSTANCE,rpm,r4=0x81601200)
    def shift_tables(self,engine,induction,transmission):
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_5,UC_PPC_REG_6,UC_PPC_REG_7,UC_PPC_REG_8,UC_PPC_REG_LR,UC_PPC_REG_MSR,UC_PPC_REG_PC
        self.setup(engine,induction,transmission);u=self.uc
        for reg,value in [(UC_PPC_REG_1,self.STACK),(UC_PPC_REG_3,0x81601100),(UC_PPC_REG_4,self.INSTANCE),(UC_PPC_REG_5,0x81601200),(UC_PPC_REG_6,0x8160b000),(UC_PPC_REG_7,0x8160b100),(UC_PPC_REG_8,10),(UC_PPC_REG_LR,self.STOP),(UC_PPC_REG_MSR,0x2000)]:u.reg_write(reg,value)
        u.mem_write(0x8160b000,b'\xa5'*40);u.mem_write(0x8160b100,b'\xa5'*40)
        self.allowed=((0x80224cb8,0x80224ff0),(0x802240ac,0x80224268),(0x80223d30,0x802240ac),(0x80058124,0x8005812c))
        self.write_ranges=((0x8160b000,0x8160b028),(0x8160b100,0x8160b128));self.count=0
        try:u.emu_start(0x80224cb8,self.STOP,count=2000000,timeout=10000000)
        finally:self.write_ranges=()
        if u.reg_read(UC_PPC_REG_PC)!=self.STOP:raise RuntimeError(('shift table budget',self.count,hex(u.reg_read(UC_PPC_REG_PC))))
        return u.reg_read(UC_PPC_REG_3),struct.unpack('>10f',bytes(u.mem_read(0x8160b000,40))),struct.unpack('>10f',bytes(u.mem_read(0x8160b100,40))),self.count
    def shift_request(self,transmission,up,down,gear,rpm,throttle,idle):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_3
        self.uc.mem_write(0x81603000,transmission);layout=bytearray(96);struct.pack_into('>f',layout,0x5c,idle);self.uc.mem_write(self.ENGINE,bytes(layout))
        obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x164,0x81603000);struct.pack_into('>I',obj,0x150,self.ENGINE)
        struct.pack_into('>f',obj,0x90,throttle);struct.pack_into('>10f',obj,0xa0,*up);struct.pack_into('>10f',obj,0xc8,*down)
        # The sole virtual callback here is exact maxgear=count-1.
        struct.pack_into('>I',obj,0x54,0x8160a100);self.uc.mem_write(self.OBJECT,bytes(obj))
        table=bytearray(0x20);struct.pack_into('>I',table,0x1c,self.CALLBACK);self.uc.mem_write(0x8160a100,bytes(table))
        self.mode=struct.unpack_from('>H',transmission,2)[0]-1
        self.allowed=((0x80255de0,0x80255f84),(0x80058124,0x8005812c),(self.CALLBACK,self.CALLBACK+4))
        # _call chooses float return whenever rpm is supplied; use r3 afterwards.
        self._call(0x80255de0,self.OBJECT,rpm,r4=gear)
        return self.uc.reg_read(UC_PPC_REG_3)

def verify(dol,attributes,limit=None):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Attributes checksum')
    db=VehicleAttributes(raw);ref=PolicyReference(dol.read_bytes());rng=random.Random(20051125)
    root=Path(__file__).resolve().parents[1]
    class Curve(ctypes.Structure):_fields_=[('values',ctypes.POINTER(ctypes.c_float)),('count',ctypes.c_size_t),('idle',ctypes.c_float),('maximum',ctypes.c_float),('redline',ctypes.c_float)]
    class Induction(ctypes.Structure):_fields_=[(n,ctypes.c_float) for n in ['low','high','vacuum','spool']]
    class Tables(ctypes.Structure):_fields_=[('up',ctypes.c_float*10),('down',ctypes.c_float*10),('count',ctypes.c_size_t)]
    def bits(v):return struct.pack('>f',v)
    def f32(v):return ctypes.c_float(v).value
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    counts={'induction':0,'shift_tables':0,'shift_request':0};rows=0;traces=[]
    with tempfile.TemporaryDirectory(prefix='mw-shift-policy-') as temporary:
        so=Path(temporary)/'policy.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission_policy.c'),str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));ind=lib.mw_physics_transmission_induction_raw;ind.argtypes=[ctypes.POINTER(Curve),ctypes.POINTER(Induction),ctypes.c_float,ctypes.c_float];ind.restype=ctypes.c_float
        tables=lib.mw_physics_transmission_shift_tables;tables.argtypes=[ctypes.POINTER(Curve),ctypes.POINTER(Induction),ctypes.POINTER(ctypes.c_float),ctypes.c_size_t,ctypes.POINTER(Tables)];tables.restype=ctypes.c_bool
        request=lib.mw_physics_transmission_shift_request;request.argtypes=[ctypes.POINTER(Tables),ctypes.POINTER(ctypes.c_float),ctypes.c_size_t,ctypes.c_uint,*([ctypes.c_float]*3)];request.restype=ctypes.c_uint
        engines=[r for r in db.collections.values() if r['class_key']==h('engine')]
        engines.sort(key=lambda r:db.label(r['key'])!='bmwm3gtre46')
        for engine in engines:
            try:induction=db.find('induction',engine['key']);trans=db.find('transmission',engine['key'])
            except KeyError:continue
            e=db.fields(engine);p=db.fields(induction);t=db.fields(trans);values=e['TORQUE']['value']['values'];ratios=t['GEAR_RATIO']['value']['values']
            if len(values)<2 or len(ratios)<3 or e['MAX_RPM']['value']<=e['IDLE']['value']:continue
            rows+=1;array=(ctypes.c_float*len(values))(*values);curve=Curve(array,len(values),e['IDLE']['value'],e['MAX_RPM']['value'],e['RED_LINE']['value'])
            params=Induction(*(p[n]['value'] for n in ['LOW_BOOST','HIGH_BOOST','VACUUM','SPOOL']));ratio_array=(ctypes.c_float*len(ratios))(*ratios)
            el,il,tl=layout(engine),layout(induction),layout(trans)
            threshold=f32(params.spool*f32(curve.redline-curve.idle)+curve.idle)
            for rpm in [-1000,0,1,curve.idle,f32(threshold-1),threshold,f32(threshold+1),curve.redline,curve.maximum+1000]:
                for amount in (-1,0,.5,1,2):
                    expected=ref.induction(el,il,rpm,amount);actual=ind(ctypes.byref(curve),ctypes.byref(params),rpm,amount)
                    if bits(expected)!=bits(actual):raise AssertionError(('induction',db.label(engine['key']),rpm,amount,expected,actual,bits(expected).hex(),bits(actual).hex()))
                    counts['induction']+=1
            original,up,down,steps=ref.shift_tables(el,il,tl);actual=Tables();assert tables(ctypes.byref(curve),ctypes.byref(params),ratio_array,len(ratios),ctypes.byref(actual))
            if original!=1 or [bits(v) for v in up]!=[bits(v) for v in actual.up] or [bits(v) for v in down]!=[bits(v) for v in actual.down]:raise AssertionError(('shift_tables',db.label(engine['key']),up,list(actual.up),down,list(actual.down)))
            counts['shift_tables']+=1
            for gear in range(len(ratios)):
                for rpm in [0,curve.idle,curve.redline,*[f32(up[gear]+n) for n in (-1,0,1)],*[f32(down[gear]+n) for n in (-1,0,1)]]:
                    for throttle in (0,.5,1):
                        expected=ref.shift_request(tl,up,down,gear,rpm,throttle,curve.idle);decision=request(ctypes.byref(actual),ratio_array,len(ratios),gear,rpm,throttle,curve.idle)
                        if expected!=decision:raise AssertionError(('request',db.label(engine['key']),gear,rpm,throttle,expected,decision))
                        counts['shift_request']+=1
            trace=dict(name=db.label(engine['key']),up=list(up),down=list(down),original_instructions=steps);traces.append(trace)
            print(json.dumps(trace),flush=True)
            if limit is not None and rows>=limit:break
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,vehicle_collections=rows,cases=counts,traces=traces,limitations=['induction optional tuning/output pointers areNULL in this checkpoint','gear-request classification is not the caller inhibit/manual/airborne wrapper','startup original induction argument order is preserved, not corrected'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--limit',type=int);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=verify(a.dol,a.attributes,a.limit);a.output.write_text(json.dumps(result,indent=2)+'\n')
