#!/usr/bin/env python3
"""Bound the original Width-only trigger constructor; no original hit claim."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from race_trigger_reference import Reference,f32,_fma,bits
from vehicle_ppc_reference import DOL_SHA256

def verify(raw):
    ref=Reference(raw);u=ref.u;stack=0x81600000;source=0x81601000;obj=0x81602000
    if ref.image.f32(0x803ec3b4)!=.25 or ref.image.f32(0x803ec3b8)!=50 or ref.image.f32(0x803ec3a8)!=1:raise ValueError('Width constants changed')
    widths=[.125,.25,.5,1,2,8,16,25,40,50,80,100,160,200,320,512,1024]
    for width in widths:
        ref.reg(1,stack);ref.reg(3,source);ref.reg(31,obj)
        u.mem_write(stack,bytes(256));u.mem_write(source,struct.pack('>f',width));u.mem_write(obj,bytes(64))
        ref.writes=((stack,stack+256),(obj+0x38,obj+0x3c))
        ref.run(0x8019acc0,0x8019ad00)
        actual=struct.unpack('>3f',bytes(u.mem_read(stack+0x30,12)))
        if [bits(x)for x in actual]!=[bits(width),bits(50),bits(1)]:raise AssertionError('Original Width parameter conversion differs')
        kind=(struct.unpack('>I',bytes(u.mem_read(obj+0x38,4)))[0]>>24)&15
        if kind!=1:raise AssertionError('Width fallback is not kind1')
        operand=_fma(width,f32(width*.25),.25)
        if bits(ref.fp(1))!=bits(operand):raise AssertionError('Original Width broadphase operand differs')
    return {'schema':1,'dol_sha256':DOL_SHA256,'original_width_constructor_cases_matched':len(widths),'widths':widths,
        'window':{'start':'8019acc0','end_exclusive':'8019ad00','sha256':hashlib.sha256(ref.image.read(0x8019acc0,0x40)).hexdigest()},
        'source_constants':{'803ec3b4':.25,'803ec3b8':50,'803ec3a8':1},'shape_kind':1,'internal_parameters':['Width',50,1],
        'internal_half_extents':['Width/2',50,.5],'equivalent_native_source_dimensions':[1,'Width',50],
        'limits':['Unmodified bounded original scalar constructor only; existing dimensional half-extents recovery supplies subsequent conversion',
                  'Does not establish original vehicle narrowphase, optional plane/direction predicates or script scheduling','Native swept detector remains an explicit port adaptation']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=verify(a.dol.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(report,indent=2)+'\n').encode()
    if a.output.exists()and a.output.read_bytes()!=data:raise ValueError('Existing output differs')
    if not a.output.exists():a.output.write_bytes(data)
    print(json.dumps(report))
