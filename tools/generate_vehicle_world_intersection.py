#!/usr/bin/env python3
"""Deterministically lower two SHA-pinned pure collision functions to native C.

No instruction interpreter, machine code, DOL image or asset table is emitted.
Generated fixed control flow invokes independently authored vector/math helpers.
The small source scalar thresholds/permutation constants are checksum recorded.
"""
import argparse
import hashlib
from pathlib import Path
import re
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

TRACE=False
FUNCTIONS=[('box_box',0x80089658,0x80089d50),('sphere_box',0x80089d50,0x8008a4b8)]
PREAMBLE=r'''/* Generated fixed native collision math. Regenerate with
 tools/generate_vehicle_world_intersection.py and the privately supplied DOL.
 No runtime instruction decoding or game executable data is used. */
#include "mw_vehicle_world.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <stdint.h>
#include <string.h>
typedef struct { unsigned char bytes[2048]; int bad; } VwWorkspace;
static uint32_t vw_read(VwWorkspace *m,uint32_t p);
static void vw_write(VwWorkspace *m,uint32_t p,uint32_t v){
 if(p<0x1000||p>0x17fc){m->bad=1;return;}memcpy(m->bytes+p-0x1000,&v,4);
}
static float vw_float(VwWorkspace *m,uint32_t p){uint32_t u=vw_read(m,p);float f;memcpy(&f,&u,4);return f;}
static void vw_store(VwWorkspace *m,uint32_t p,float f){uint32_t u;memcpy(&u,&f,4);vw_write(m,p,u);}
static void vw_half(VwWorkspace *m,uint32_t p,uint16_t v){
 if(p<0x1000||p>0x17fe){m->bad=1;return;}memcpy(m->bytes+p-0x1000,&v,2);
}
static unsigned vw_cmp(float a,float b){return isnan(a)||isnan(b)?1:a<b?8:a>b?4:2;}
static unsigned vw_icmp(int32_t a,int32_t b){return a<b?8:a>b?4:2;}
/* Fixed source vector helper contracts. All reads precede writes for aliases. */
static float vw_call(VwWorkspace *m,uint32_t target,uint32_t a,uint32_t b,uint32_t c,float scale){
 float x[4],y[4],z[3];unsigned count=target==0x801930a8?4:3;
 if(target==0x80193420)return mw_gekko_sqrt_newton1(scale);
 if(target==0x80193458){float root=mw_gekko_sqrt_newton1(scale);return root==0?root:1/root;}
 for(unsigned i=0;i<count;i++)x[i]=vw_float(m,a+i*4);
 if(target!=0x80193408&&target!=0x8019321c)for(unsigned i=0;i<count;i++)y[i]=vw_float(m,b+i*4);
 switch(target){
 case 0x801930a8:{float ax=x[0]*y[0],ay=x[1]*y[1];return fmaf(x[2],y[2],ax)+fmaf(x[3],y[3],ay);}
 case 0x801930c8:{float ax=x[0]*y[0],ay=x[1]*y[1];return fmaf(x[2],y[2],ax+ay);}
 case 0x8019338c:for(unsigned i=0;i<3;i++)x[i]=x[i]-y[i]; /* fall through */
 case 0x80193408:{float ax=x[0]*x[0],ay=x[1]*x[1];return fmaf(x[2],x[2],ax+ay);}
 case 0x80193130:for(unsigned i=0;i<3;i++)z[i]=x[i]+y[i];break;
 case 0x80193154:case 0x8019319c:for(unsigned i=0;i<3;i++)z[i]=x[i]-y[i];break;
 case 0x8019321c:for(unsigned i=0;i<3;i++)z[i]=x[i]*scale;c=b;break;
 case 0x8019330c:for(unsigned i=0;i<3;i++){float product=x[i]*scale;z[i]=product+y[i];}break;
 default:m->bad=1;return 0;
 }
 for(unsigned i=0;i<3;i++){vw_store(m,c+i*4,z[i]);}return scale;
}
'''
POSTAMBLE=r'''
int mw_vehicle_world_intersection(const MwVehicleWorldGeometry *a,const MwVehicleWorldGeometry *b,MwVehicleWorldGeometry *out){
 if(!a||!b||!out||a->shape<1||a->shape>2||b->shape!=1)return -1;
 const float *af=(const float *)a,*bf=(const float *)b;
 for(unsigned i=0;i<39;i++)if(!isfinite(af[i])||!isfinite(bf[i]))return -1;
 for(unsigned i=0;i<3;i++)if(!isfinite(a->delta[i])||!isfinite(b->delta[i])||a->dimension[i]<0||b->dimension[i]<0)return -1;
 VwWorkspace m;memset(&m,0,sizeof(m));memcpy(m.bytes+0x500,a,sizeof(*a));memcpy(m.bytes+0x600,b,sizeof(*b));memcpy(m.bytes+0x700,out,sizeof(*out));
 uint32_t result=out==a?0x1500:out==b?0x1600:0x1700;
 int hit=a->shape==1?vw_box_box(&m,0x1500,0x1600,result):vw_sphere_box(&m,0x1500,0x1600,result);
 if(m.bad)return -1;
 MwVehicleWorldGeometry g;memcpy(&g,m.bytes+result-0x1000,sizeof(g));
 for(unsigned i=0;i<39;i++)if(!isfinite(((const float *)&g)[i]))return -1;
 if(!isfinite(g.overlap))return -1;
 *out=g;return hit;
}
'''

def lower(image,name,start,end):
    cs=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN);cs.skipdata=True
    ins=list(cs.disasm(image.read(start,end-start),start))
    targets={int(i.op_str.split(',')[-1].strip(),0) for i in ins if i.mnemonic in ('b','beq','bne','blt','bgt','ble','bge','bso')}
    lines=[f'/* Source window {start:08x}..{end:08x} SHA256 {hashlib.sha256(image.read(start,end-start)).hexdigest()} */',f'static int vw_{name}(VwWorkspace *m,uint32_t a,uint32_t b,uint32_t out){{',
      ' uint32_t r[32]={0};float f[32]={0};unsigned cr[8]={0};r[1]=0x1400;r[3]=a;r[4]=b;r[5]=out;']
    def reg(t):return 'r['+t[1:]+']'
    def fp(t):return 'f['+t[1:]+']'
    def num(t):return str(int(t,0))
    def address(t):
        mt=re.fullmatch(r'(-?0x[0-9a-f]+|-?[0-9]+)\((r[0-9]+)\)',t)
        if not mt:raise ValueError('Address '+t)
        return f'({reg(mt[2])}+({num(mt[1])}))'
    def bit(t):
        mt=re.fullmatch(r'cr([0-7])(lt|gt|eq|un)',t);return int(mt[1]),{'lt':8,'gt':4,'eq':2,'un':1}[mt[2]]
    for i in ins:
        op=i.mnemonic;args=[v.strip() for v in i.op_str.split(',')];w=image.u32(i.address)
        if i.address in targets:lines.append(f'L_{i.address:08x}:;')
        if TRACE:lines.append(f' if(vw_probe)vw_probe(0x{i.address:08x},f,r,m->bytes);')
        if w>>26 in (56,60) or op in ('stmw','lmw','mflr','mtlr','crclr'):continue
        if op=='stwu':code=f'{reg(args[0])}={address(args[1])};'
        elif op in ('lis','li'):code=f'{reg(args[0])}=(uint32_t)({num(args[1])})'+('<<16;' if op=='lis' else ';')
        elif op in ('addi','add'):code=f'{reg(args[0])}={reg(args[1])}+({num(args[2]) if op=="addi" else reg(args[2])});'
        elif op=='mr':code=f'{reg(args[0])}={reg(args[1])};'
        elif op=='slwi':code=f'{reg(args[0])}={reg(args[1])}<<{num(args[2])};'
        elif op in ('lwz','lfs'):code=f'{reg(args[0]) if op=="lwz" else fp(args[0])}={"vw_read" if op=="lwz" else "vw_float"}(m,{address(args[1])});'
        elif op in ('lwzx','lfsx'):code=f'{reg(args[0]) if op=="lwzx" else fp(args[0])}={"vw_read" if op=="lwzx" else "vw_float"}(m,{reg(args[1])}+{reg(args[2])});'
        elif op in ('stw','stfs','sth'):code=f'{ {"stw":"vw_write","stfs":"vw_store","sth":"vw_half"}[op]}(m,{address(args[1])},{fp(args[0]) if op=="stfs" else reg(args[0])});'
        elif op=='stfsx':code=f'vw_store(m,{reg(args[1])}+{reg(args[2])},{fp(args[0])});'
        elif op in ('fmr','fneg','fabs'):code=f'{fp(args[0])}='+{'fmr':'','fneg':'-','fabs':'fabsf('}[op]+fp(args[1])+(');' if op=='fabs' else ';')
        elif op in ('fadds','fsubs','fmuls','fdivs'):code=f'{fp(args[0])}={fp(args[1])}'+{'fadds':'+','fsubs':'-','fmuls':'*','fdivs':'/'}[op]+fp(args[2])+';'
        elif op=='fmsubs':code=f'{fp(args[0])}=fmaf({fp(args[1])},{fp(args[2])},-{fp(args[3])});'
        elif op in ('fcmpu','cmpwi','cmpw'):
            field=0
            if args[0].startswith('cr'):field=int(args.pop(0)[2:])
            code=f'cr[{field}]='+('vw_cmp('+fp(args[0])+','+fp(args[1]) if op=='fcmpu' else 'vw_icmp((int32_t)'+reg(args[0])+','+(' (int32_t)'+reg(args[1]) if op=='cmpw' else num(args[1])))+');'
        elif op=='cror':
            d,dm=bit(args[0]);a,am=bit(args[1]);b,bm=bit(args[2]);code=f'cr[{d}]=(cr[{d}]&~{dm}u)|(((cr[{a}]&{am}u)||(cr[{b}]&{bm}u))?{dm}u:0);'
        elif op=='b':code='goto L_'+f'{int(args[-1],0):08x}'+';'
        elif op in ('beq','bne','blt','bgt','ble','bge','bso'):
            field=int(args[0][2:]) if len(args)>1 else 0;mask={'beq':2,'bne':2,'blt':8,'bge':8,'bgt':4,'ble':4,'bso':1}[op]
            code=f'if({"!" if op in ("bne","bge","ble") else ""}(cr[{field}]&{mask}u))goto L_{int(args[-1],0):08x};'
        elif op=='bl':
            target=int(args[0],0)
            if target==0x80314950:code='if(r[3]<0x1000||r[3]+r[5]>0x1800)m->bad=1;else memset(m->bytes+r[3]-0x1000,(int)r[4],r[5]);'
            else:code=f'f[1]=vw_call(m,0x{target:08x},r[3],r[4],r[5],f[1]);'
        elif op=='blr':code='return (int32_t)r[3];'
        else:raise ValueError(f'Unsupported source instruction {i.address:08x} {op} {args}')
        lines.append(' '+code)
    return '\n'.join(lines)+'\n}\n'

def generate(dol,output):
    raw=dol.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unknown source executable')
    im=DolImage(raw);data=PREAMBLE+('\nvoid (*vw_probe)(uint32_t,const float *,const uint32_t *,const unsigned char *)=0;\n' if TRACE else '')+'\nstatic uint32_t vw_read(VwWorkspace *m,uint32_t p){\n uint32_t v;if(p>=0x1000&&p<=0x17fc){memcpy(&v,m->bytes+p-0x1000,4);return v;}\n switch(p){\n'
    for at in [*range(0x803d3ef8,0x803d3f48,4),*range(0x803eb388,0x803eb3a8,4)]:data+=f' case 0x{at:08x}:return UINT32_C(0x{im.u32(at):08x});\n'
    data+=' default:m->bad=1;return 0;}\n}\n'
    for name,start,end in FUNCTIONS:data+=lower(im,name,start,end)
    output.write_text(data+POSTAMBLE)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',action='store_true');p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();TRACE=a.trace;generate(a.dol,a.output)
