#!/usr/bin/env python3
"""Inspect original mixed-endian EAGL NIS animation banks; no game bytes embedded.

Frame indices are original curve units, not seconds. This tool deliberately
leaves actor binding, scene clock conversion and root transforms unresolved.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


def f32(v):
    return struct.unpack('>f', struct.pack('>f', v))[0]


class AnimationBank:
    def __init__(self, raw):
        self.sha256 = hashlib.sha256(raw).hexdigest()
        e = raw.index(b'\x7fELF')
        h = struct.unpack_from('<16sHHIIIIIHHHHHH', raw, e)
        if h[0][4:6] != b'\x01\x01' or h[2] != 8:
            raise ValueError('Expected ELF32LE MIPS relocation wrapper')
        sections = [struct.unpack_from('<10I', raw, e+h[6]+i*h[11]) for i in range(h[12])]
        names = raw[e+sections[h[13]][4]:e+sections[h[13]][4]+sections[h[13]][5]]
        def name(s): return names[s[0]:].split(b'\0',1)[0].decode('ascii')
        byname = {name(s):s for s in sections}
        ds=byname['.data'];self.data=raw[e+ds[4]:e+ds[4]+ds[5]]
        self.relocations=set()
        rs=byname['.rel.data']
        for at in range(e+rs[4],e+rs[4]+rs[5],8):
            off,typ=struct.unpack_from('<II',raw,at)
            if typ != 0x102 or off+4>len(self.data): raise ValueError('Unknown relocation')
            self.relocations.add(off)
        sy=byname['.symtab']; st=byname['.strtab']; strings=raw[e+st[4]:e+st[4]+st[5]]
        root=None
        for at in range(e+sy[4],e+sy[4]+sy[5],16):
            no,value,size,info,other,section=struct.unpack_from('<IIIBBH',raw,at)
            if strings[no:].split(b'\0',1)[0]==b'__AnimationBank:::bank': root=value
        if root is None or self.u32(root)!=28: raise ValueError('Animation bank root missing')
        count=self.u32(root+4)
        if count>4096: raise ValueError('Unbounded curve count')
        cp,np=self.ptr(root+16),self.ptr(root+20)
        self.curves=[]
        for i in range(count):
            no=self.ptr(np+i*4)
            n=self.data[no:].split(b'\0',1)[0].decode('ascii')
            self.curves.append(dict(name=n, **self.curve(self.ptr(cp+i*4))))

    def u16(self,off): return struct.unpack_from('>H',self.data,off)[0]
    def u32(self,off): return struct.unpack_from('>I',self.data,off)[0]
    def ptr(self,off):
        if off not in self.relocations: raise ValueError(f'Nonrelocated pointer {off:x}')
        p=struct.unpack_from('<I',self.data,off)[0]
        if p>=len(self.data): raise ValueError('Out of bounds pointer')
        return p
    def curve(self,off,depth=0):
        if depth>8: raise ValueError('Curve recursion limit')
        typ=self.u16(off)
        result=dict(offset=off,type=typ)
        if typ==15:
            count=self.u16(off+8)
            if count>256: raise ValueError('Child count limit')
            result['timing_header_hex']=self.data[self.ptr(off+4):self.ptr(off+4)+12].hex()
            result['children']=[self.curve(self.ptr(off+12+i*4),depth+1) for i in range(count)]
        elif typ in (10,11):
            p=self.ptr(off+4); nc=self.u16(p); bits=self.data[p+2];frames=self.u16(off+8)
            if nc>256 or frames>20000 or bits not in (4,8,16): raise ValueError('Invalid packed curve')
            coeff=[struct.unpack_from('>3f',self.data,p+4+i*12) for i in range(nc)]
            if not all(math.isfinite(v) for c in coeff for v in c):raise ValueError('Nonfinite coefficient')
            packed=p+4+12*nc;stride=(nc*bits+7)//8
            if packed+stride*max(0,frames-1)>len(self.data):raise ValueError('Packed data bounds')
            values=[list(c[2] for c in coeff)];deltas=[]
            for k in range(frames-1):
                row=[];delta=[]
                for j,(bias,scale,initial) in enumerate(coeff):
                    pos=packed+k*stride+(j*bits)//8
                    q=(self.data[pos] >> (4*(j%2)))&15 if bits==4 else self.data[pos] if bits==8 else self.u16(pos)
                    d=f32(q*scale+bias);delta.append(d);row.append(f32(values[-1][j]+d))
                values.append(row);deltas.append(delta)
            destcount=nc//4 if typ==11 else nc
            result.update(payload_offset=p,channels=nc,bits=bits,frames=frames,coefficients=coeff,
                          destination_channels=[self.u16(off+10+i*2) for i in range(destcount)],values=values,deltas=deltas)
        else: result['unsupported']=True
        return result


def verify_bank(bank, dol):
    """Compare decoded integer frames with original pinned PPC delta evaluator."""
    from map_recovery_contact_reference import OriginalContactReference
    from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_PC
    ref=OriginalContactReference(dol,None)
    ref.extra_allowed=((0x8008d78c,0x8008dc68),)
    u=ref.u
    u.mem_write(0x60010000,bank.data)
    count=0; worst=0.0
    def check(c):
        nonlocal count,worst
        if c['type']==15:
            for child in c['children']: check(child)
        elif c['type'] in (10,11):
            for frame in sorted({0,1,c['frames']//2,c['frames']-1}):
                if frame>=c['frames']:continue
                u.mem_write(0x60001000,bytes(2048))
                args=(0x60010000+c['payload_offset'],0,c['channels'],0xffffffff,frame,0x60001000,0x60001000)
                u.reg_write(UC_PPC_REG_1,0x7000ff00)
                u.reg_write(UC_PPC_REG_LR,0x6000fff0)
                for i,a in enumerate(args):u.reg_write(UC_PPC_REG_3+i,a)
                u.emu_start(0x8008d78c,0x6000fff0,timeout=1000000,count=2000000)
                if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original codec reference budget exceeded')
                result=struct.unpack('>'+str(c['channels'])+'f',bytes(u.mem_read(0x60001000,4*c['channels'])))
                error=max(abs(a-b) for a,b in zip(result,c['values'][frame]))
                worst=max(worst,error);count+=1
                if error>0: raise ValueError(f"Codec mismatch frame{frame}: {error}")
    for c in bank.curves:check(c)
    return dict(integer_frame_cases=count,max_absolute_error=worst,reference='Original SHA-pinned USA DOL 8008D78C; bounded Unicorn PPC execution')


def export_native(inputs, output):
    """Store predecoded source channels; director clocks/bindings remain external."""
    banks=[];curves=[]
    for path in sorted(inputs):
        b=AnimationBank(path.read_bytes());first=len(curves)
        scene_name=None
        for c in b.curves:
            if c['type']!=15 or len(c['children'])!=1:raise ValueError('Unsupported composite')
            child=c['children'][0]
            if child['type'] not in (10,11) or child['channels']>4:raise ValueError('Unsupported actor channel group')
            prefix,token=c['name'].split('ZPM_',1)
            token,kind=token.rsplit('_',1)
            if kind not in ('q','t','s') or scene_name not in (None,prefix):raise ValueError('Unknown actor naming')
            scene_name=prefix
            if c['timing_header_hex']!='00000001000100011e303030':raise ValueError('Unknown context-rate metadata')
            curves.append(dict(name=c['name'],token=token,kind={'t':1,'q':2,'s':3}[kind],**child))
        banks.append((scene_name,first,len(curves)-first))
    bank_offset=32;curve_offset=bank_offset+64*len(banks);data_offset=curve_offset+128*len(curves)
    payload=bytearray();records=bytearray()
    def string(value,n):
        raw=value.encode('ascii')
        if len(raw)>=n:raise ValueError('Name too long')
        return raw+bytes(n-len(raw))
    for c in curves:
        off=data_offset+len(payload)
        for i,row in enumerate(c['values']):
            delta=c['deltas'][i] if i<len(c['deltas']) else [0.0]*c['channels']
            payload.extend(struct.pack('<'+str(c['channels']*2)+'f',*(row+delta)))
        dest=c['destination_channels']
        if c['type']==11:dest=list(range(dest[0],dest[0]+4))
        records.extend(struct.pack('<64s32sIIIf4HII',string(c['name'],64),string(c['token'],32),c['frames'],c['channels'],off,30.0,*(dest+[0]*(4-len(dest))),c['kind'],0))
    total=data_offset+len(payload)
    if len(banks)>8 or len(curves)>128 or total>4*1024*1024:raise ValueError('Native asset limits exceeded')
    out=bytearray(struct.pack('<4s7I',b'NNA1',1,len(banks),len(curves),bank_offset,curve_offset,data_offset,total))
    for name,first,count in banks:out.extend(struct.pack('<48s4I',string(name,48),first,count,0,0))
    out.extend(records);out.extend(payload);output.write_bytes(out)
    return dict(banks=len(banks),curves=len(curves),bytes=len(out),sha256=hashlib.sha256(out).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-dol',type=Path);p.add_argument('--native',type=Path)
    args=p.parse_args()
    if args.native:
        print(json.dumps(export_native(args.input.glob('*.bin'),args.native),indent=2));return
    bank=AnimationBank(args.input.read_bytes());report=dict(source=args.input.name,sha256=bank.sha256,curve_time_units='frame index; source scene clock mapping unresolved',curves=bank.curves)
    if args.verify_dol:report['verification']=verify_bank(bank,args.verify_dol.read_bytes())
    s=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.write_text(s)
    else: print(s,end='')
if __name__=='__main__':main()
