#!/usr/bin/env python3
"""Export original Rockport road topology/curves and typed street-system records.

MWT1 adds only a bounded native spatial index and approximate16-sample arc lengths.
The original32-byte nodes,22-byte segments and64-byte profiles remain unchanged.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from map_recovery_ps_reference import f32

ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
CURVE_SCALE=6.00748899159953e-05
WINDOWS=((0x803076e0,0x80307778),(0x802f8ee0,0x802f9130),
         (0x802f9db8,0x802f9de8),(0x803051d4,0x80305234),
         (0x802fa314,0x802fa380),(0x802fa984,0x802fac90))
def sha(data):return hashlib.sha256(data).hexdigest()


def curve(a,b,s,t):
    if not struct.unpack_from('>H',s,10)[0]&256:
        return [f32(a[i]+f32(f32(b[i]-a[i])*t)) for i in range(3)]
    la,lb=struct.unpack_from('>2H',s,12);d=struct.unpack_from('>6b',s,16)
    c1=[f32(a[i]+f32(f32(lb*CURVE_SCALE)*d[i+3])) for i in range(3)]
    c2=[f32(b[i]+f32(f32(la*CURVE_SCALE)*d[i])) for i in range(3)]
    result=[]
    for i in range(3):
        co=[]
        for row in ((-1,3,-3,1),(3,-6,3,0),(-3,3,0,0),(1,0,0,0)):
            v=f32(c1[i]*row[1]);v=f32(a[i]*row[0]+v);v=f32(c2[i]*row[2]+v);co.append(f32(b[i]*row[3]+v))
        value=f32(f32(t*t)*co[1]+f32(f32(f32(t*t)*t)*co[0]))
        result.append(f32(f32(t*co[2]+value)+co[3]))
    return result


def control_bounds(a,b,s):
    if not struct.unpack_from('>H',s,10)[0]&256:return [a,b]
    la,lb=struct.unpack_from('>2H',s,12);d=struct.unpack_from('>6b',s,16)
    return [a,b,[f32(a[i]+f32(f32(lb*CURVE_SCALE)*d[i+3])) for i in range(3)],
            [f32(b[i]+f32(f32(la*CURVE_SCALE)*d[i])) for i in range(3)]]


def network(raw):
    at=0;found=[]
    while at<len(raw):
        if at+8>len(raw):raise ValueError('Truncated L2RA chunk')
        tag,size=struct.unpack_from('<II',raw,at)
        if at+8+size>len(raw):raise ValueError('L2RA chunk exceeds source')
        if tag==0x3b800:found.append((at,size))
        at+=8+size
    if len(found)!=1:raise ValueError('Expected one original WRoadNetwork chunk')
    chunk,size=found[0];base=(chunk+8+15)&~15
    if raw[base:base+4]!=b'CARP':raise ValueError('Missing aligned CARP resource')
    entries={}
    for tag,stride in ((b'RNhd',14),(b'RNnd',32),(b'RNpf',64),(b'RNrd',8),(b'RNsg',22)):
        hits=[i for i in range(base,base+256,16) if raw[i:i+4]==tag]
        if len(hits)!=1:raise ValueError('Missing unique RN directory record')
        entry=hits[0];_,flags,count,relative=struct.unpack_from('>4sIII',raw,entry)
        length=flags&0x1fffffff;start=entry+relative
        if flags>>29!=2 or count*stride!=length or start<base+192 or start+length>chunk+8+size:raise ValueError('Invalid relative RN data range')
        entries[tag.decode()]={'entry_offset':entry,'data_offset':start,'count':count,'stride':stride,'bytes':length,'sha256':sha(raw[start:start+length])}
    nodes=[];segments=[]
    nr=entries['RNnd'];sr=entries['RNsg']
    for i in range(nr['count']):
        p=raw[nr['data_offset']+i*32:nr['data_offset']+(i+1)*32]
        position=struct.unpack_from('>3f',p);index,profile=struct.unpack_from('>2H',p,12);degree=p[16]
        if index!=i or not 1<=degree<=7 or any(not math.isfinite(v) or abs(v)>20000 for v in position):raise ValueError('Invalid source node')
        adjacent=list(struct.unpack_from('>'+str(degree)+'H',p,18))
        if len(set(adjacent))!=degree or any(j>=sr['count'] for j in adjacent):raise ValueError('Invalid source node adjacency')
        nodes.append({'position':position,'adjacent':adjacent,'raw':p,'profile_signed':profile if profile<32768 else profile-65536})
    for i in range(sr['count']):
        p=raw[sr['data_offset']+i*22:sr['data_offset']+(i+1)*22];a,b=struct.unpack_from('>2H',p);index,flags=struct.unpack_from('>2H',p,8)
        if a>=len(nodes) or b>=len(nodes) or a==b or index!=i or i not in nodes[a]['adjacent'] or i not in nodes[b]['adjacent']:raise ValueError('Invalid source segment endpoints/id')
        av,bv=nodes[a]['position'],nodes[b]['position'];last=curve(av,bv,p,0);length=0
        for j in range(1,17):
            point=curve(av,bv,p,j/16);length+=math.dist(last,point);last=point
        if not .001<=length<=10000:raise ValueError('Invalid original curve length')
        segments.append({'nodes':(a,b),'flags':flags,'raw':p,'length':f32(length),'controls':control_bounds(av,bv,p)})
    for i,n in enumerate(nodes):
        if sorted(n['adjacent'])!=[j for j,s in enumerate(segments) if i in s['nodes']]:raise ValueError('Source adjacency is not reciprocal')
    return nodes,segments,entries


class OriginalCurveReference:
    """Executes the original sampler; initialized static Bezier container supplied.

    Existing explicit paired-single hooks retain their general FP limitations.
    Original bytes/branches are never patched; external global initialization
    supplies an empty linked container and the already-initialized flag.
    """
    def __init__(self,raw):
        from map_recovery_contact_reference import OriginalContactReference
        from unicorn import ppc_const as r
        self.r=r;self.ref=OriginalContactReference(raw,None);self.u=self.ref.u
        self.ref.extra_allowed=((0x802fa314,0x802fa380),(0x802fa984,0x802fac90),
            (0x801930e8,0x8019310c),(0x80193e7c,0x801940e8),
            (0x80193e04,0x80193e2c),(0x801934ec,0x80193550))
        self.u.mem_write(0x804aa704,struct.pack('>I',1));self.u.mem_write(0x804aa700,struct.pack('>I',0x60008000));self.u.mem_write(0x60008000,struct.pack('>I',0x60008000))
    def sample(self,a,b,s,t):
        u=self.u;r=self.r;u.mem_write(0x60000100,struct.pack('>3f',*a));u.mem_write(0x60000200,struct.pack('>3f',*b));u.mem_write(0x60000300,s);u.mem_write(0x60000400,bytes(16));self.ref.pair1={};self.ref.instructions=0
        for n,v in ((1,0x7000ff00),(3,0x60000000),(4,0x60000100),(5,0x60000200),(6,0x60000300),(7,0x60000400)):u.reg_write(r.UC_PPC_REG_0+n,v)
        self.ref.putpair(1,(t,t));u.reg_write(r.UC_PPC_REG_LR,0x6000fff0);u.emu_start(0x802fa314,0x6000fff0,count=5000,timeout=100000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original sampler instruction budget')
        return struct.unpack('>3f',bytes(u.mem_read(0x60000400,12)))


def attributes(raw):
    if sha(raw)!=ATTR_SHA:raise ValueError('Unexpected original attributes')
    db=VehicleAttributes(raw);patterns=[];smackables=[]
    for (cls,key),row in db.collections.items():
        label=db.label(cls)
        if label=='smackable':smackables.append({'key':f'{key:08x}','name':db.label(key),'fields':db.fields(row)})
        if label!='trafficpattern':continue
        fields=db.fields(row);records=fields['0x94e3c795']['value']['values'];cars=[]
        for item in records:
            value=bytes.fromhex(item['raw_hex'])
            if len(value)!=24:raise ValueError('Invalid source TrafficPatternRecord')
            c,k,zero,weight,flag,last=struct.unpack('>IIIfII',value)
            target=db.collections.get((c,k))
            if not target or db.label(c)!='pvehicle' or zero:raise ValueError('Unresolved source traffic vehicle')
            model=db.fields(target)['MODEL']['value']['text']
            cars.append({'class_key':f'{c:08x}','collection_key':f'{k:08x}','collection_name':db.label(k),'model':model,'source_scalar_float':weight,'source_word16':flag,'source_word20':last,'original_bytes':value.hex()})
        patterns.append({'key':f'{key:08x}','name':db.label(key),'cars':cars,'fields':fields})
    return {'source_sha256':ATTR_SHA,'traffic_patterns':patterns,'smackables':smackables,
            'limits':['Source typed records and values, not recovered spawn frequency/speed units','Smackable definitions do not establish render-instance/damage-state bindings']}


def build(a):
    raw=a.l2ra.read_bytes();dol=a.dol.read_bytes()
    if sha(dol)!=DOL_SHA256:raise ValueError('Unexpected original USA DOL')
    im=DolImage(dol)
    if im.f32(0x8040e750)!=CURVE_SCALE:raise ValueError('Unexpected original road tangent scale')
    nodes,segments,entries=network(raw);step=128.
    minx=math.floor(min(c[0] for s in segments for c in s['controls'])/step)*step
    minz=math.floor(min(c[2] for s in segments for c in s['controls'])/step)*step
    nx=math.floor((max(c[0] for s in segments for c in s['controls'])-minx)/step)+1
    nz=math.floor((max(c[2] for s in segments for c in s['controls'])-minz)/step)+1
    grid=[[] for _ in range(nx*nz)]
    for i,s in enumerate(segments):
        xs=[c[0] for c in s['controls']];zs=[c[2] for c in s['controls']]
        for z in range(math.floor((min(zs)-minz)/step),math.floor((max(zs)-minz)/step)+1):
            for x in range(math.floor((min(xs)-minx)/step),math.floor((max(xs)-minx)/step)+1):grid[z*nx+x].append(i)
    offsets=[0];ids=[]
    for cell in grid:ids+=cell;offsets.append(len(ids))
    nd=b''.join(n['raw'] for n in nodes);sg=b''.join(s['raw']+bytes(2)+struct.pack('<fI',s['length'],0) for s in segments)
    profile=entries['RNpf'];pf=raw[profile['data_offset']:profile['data_offset']+profile['bytes']]
    nd_at=192;sg_at=nd_at+len(nd);pf_at=sg_at+len(sg);grid_at=pf_at+len(pf);refs_at=grid_at+len(offsets)*4
    data=bytearray(192)+nd+sg+pf+struct.pack('<'+str(len(offsets))+'I',*offsets)+struct.pack('<'+str(len(ids))+'H',*ids)
    struct.pack_into('<4s15I',data,0,b'MWT1',1,len(data),0,len(nodes),len(segments),nd_at,sg_at,profile['count'],pf_at,nx,nz,len(ids),grid_at,refs_at,0)
    data[64:96]=bytes.fromhex(sha(raw));data[96:128]=bytes.fromhex(DOL_SHA256);struct.pack_into('<3f',data,128,minx,minz,step);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    a.output.mkdir(parents=True,exist_ok=True)
    def write(name,payload):
        path=a.output/name
        if path.exists() and path.read_bytes()!=payload:raise ValueError('Existing output differs: '+name)
        if not path.exists():path.write_bytes(payload)
    write('road-network.mwt',data);report={'schema':1,'source_sha256':{'l2ra':sha(raw),'dol':DOL_SHA256},'bytes':len(data),'sha256':sha(data),'entries':entries,'nodes':len(nodes),'segments':len(segments),'profiles':profile['count'],'grid':{'cell':step,'columns':nx,'rows':nz,'references':len(ids),'max_candidates_per_cell':max(map(len,grid))},'degree_counts':dict(Counter(len(n['adjacent']) for n in nodes)),'source_segment_flag_counts':dict(Counter(s['flags'] for s in segments)),'code_windows':[{'start':f'{lo:08x}','end_exclusive':f'{hi:08x}','sha256':sha(im.read(lo,hi-lo))} for lo,hi in WINDOWS]}
    if a.verify_original:
        ref=OriginalCurveReference(dol);indices=sorted({i*(len(segments)-1)//127 for i in range(128)});count=0;vectors=[]
        for i in indices:
            s=segments[i];av,bv=[nodes[j]['position'] for j in s['nodes']]
            for t in (0,.25,.5,.75,1):
                actual=ref.sample(av,bv,s['raw'],t);expected=curve(av,bv,s['raw'],t)
                if actual!=tuple(expected):raise ValueError(f'Original road curve differs: {i}/{t} {actual} != {expected}')
                vectors.append(struct.pack('<I4f',i,t,*actual))
                count+=1
        report['original_curve_comparisons']=count
        write('road-curves.reference',struct.pack('<4sII',b'MWTC',1,count)+b''.join(vectors))
    typed=attributes(a.attributes.read_bytes());write('street-attributes.json',(json.dumps(typed,indent=2)+'\n').encode())
    report.update(traffic_patterns=len(typed['traffic_patterns']),smackable_definitions=len(typed['smackables']),traffic_models=sorted({c['model'] for p in typed['traffic_patterns'] for c in p['cars']}),limits=['Native follower policy is a port adaptation, not original traffic AI','Original curves/topology only; no guessed race-marker navigation','Traffic spawn/lane/overtake/signal and collision response producers remain separate','Smackable render/collision actor bindings and state transitions remain unresolved'])
    write('manifest.json',(json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:report[k] for k in ('bytes','nodes','segments','profiles','traffic_patterns','smackable_definitions','sha256')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('l2ra','dol','attributes','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--verify-original',action='store_true');build(p.parse_args())
