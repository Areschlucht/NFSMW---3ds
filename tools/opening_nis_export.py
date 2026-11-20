#!/usr/bin/env python3
"""Recover original opening NIS camera curves, with bounded original tangents.

This does not decode the separate compressed ELF actor-animation banks. Scene
anchor and actor-provider modes remain explicit runtime responsibilities.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from map_recovery_contact_reference import OriginalContactReference

GLOBAL_SHA='4164d8be4fd215d682b803202055abc10ffcb28a56942645e6554b3e7dac57fc'
NAMES=('GenericStart','IntroNisDD','IntroNis04','IntroNis05','IntroNis10','EndingNis03')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bhash(name):
    h=0xffffffff
    for c in name.encode('ascii'):h=(h*33+c)&0xffffffff
    return h
def chunks(data,start,end):
    at=start
    while at<end:
        if at+8>end:raise ValueError('Short source chunk')
        kind,n=struct.unpack_from('<II',data,at);stop=at+8+n
        if stop>end:raise ValueError('Source chunk exceeds parent')
        yield kind,at+8,stop
        at=stop
def cameras(data):
    found={}
    for kind,a,b in chunks(data,0,len(data)):
        if kind not in range(0x8003b200,0x8003b204):continue
        for child,c,d in chunks(data,a,b):
            if child!=0x3b210:raise ValueError('Unsupported camera child')
            key,count=struct.unpack_from('<II',data,c)
            if key not in {bhash(n) for n in NAMES}:continue
            if key in found or not 0<count<=16:raise ValueError('Ambiguous source scene')
            at=c+8;tracks=[]
            for _ in range(count):
                header=data[at:at+40]
                if len(header)!=40:raise ValueError('Short source track')
                duration=struct.unpack_from('<f',header,16)[0];keys=struct.unpack_from('<h',header,20)[0]
                name=header[23:40].split(b'\0',1)[0].decode('ascii')
                if not 0<duration<=600 or not 0<keys<=1024:raise ValueError('Source timing/count invalid')
                start=at;at+=40
                records=[data[at+i*132:at+(i+1)*132] for i in range(keys)];at+=132*keys
                if at>d or any(len(r)!=132 for r in records):raise ValueError('Source key exceeds track')
                previous=-1
                for r in records:
                    floats=struct.unpack_from('<28f',r,12);time=floats[1]
                    if not all(math.isfinite(v) for v in floats) or not previous<time<1:raise ValueError('Source keys not finite/ordered')
                    previous=time
                tracks.append({'name':name,'duration':duration,'keys':records,'source_offset':start,'raw_header':header})
            if at!=d:raise ValueError('Unconsumed source camera bytes')
            found[key]={'key':key,'tracks':tracks,'source_offset':c,'source_bytes':d-c}
    if set(found)!={bhash(n) for n in NAMES}:raise ValueError('Missing original opening camera')
    return found
def native_key(raw):
    # Original constructor797C4 swaps these float/word lanes only.
    return raw[:12]+b''.join(raw[a:a+4][::-1] for a in range(12,124,4))+raw[124:]

class CameraReference(OriginalContactReference):
    def __init__(self,dol):
        if sha(dol)!=DOL_SHA256:raise ValueError('Wrong original executable')
        super().__init__(dol,None)
        self.extra_allowed=((0x8007e550,0x8007eac8),(0x8007e4d8,0x8007e550),
          (0x800798a0,0x80079ae0),(0x8007e134,0x8007e1f4),(0x80060d50,0x80060d88),
          (0x8007a328,0x8007a354),(0x8007a3c0,0x8007a488),(0x8005d1f0,0x8005d368),
          (0x800791b8,0x80079270),(0x8007c0bc,0x8007c390),(0x80079698,0x8007974c))
        self.relative_calls=0
    def _hook(self,u,address,size,data):
        if address==0x8007d480:
            # Explicit identity actor/ground provider for local-basis tangents.
            # Runtime must resolve mode3; this is not an original actor trace.
            self.relative_calls+=1;u.reg_write(self.reg.UC_PPC_REG_PC,u.reg_read(self.reg.UC_PPC_REG_LR));return
        super()._hook(u,address,size,data)
    def run(self,start,args=(),floats=()):
        r=self.reg;u=self.u;self.pair1={};self.instructions=0
        for i in range(32):u.reg_write(r.UC_PPC_REG_FPR0+i,0)
        for i,v in enumerate(args,3):u.reg_write(r.UC_PPC_REG_0+i,v)
        for i,v in enumerate(floats,1):self.putfloating(i,v)
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        u.emu_start(start,0x6000fff0,count=30000,timeout=500000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original camera budget exhausted')
    def tangents(self,track,index,endpoint):
        records=track['keys'];base=0x60010000
        header=bytearray(40);struct.pack_into('>h',header,20,len(records))
        self.u.mem_write(base,bytes(header)+b''.join(native_key(r) for r in records))
        self.u.mem_write(0x60001000,bytes(64))
        self.run(0x8007e550,(0x60000000,0x60001000,0x60001010,0x60001020,0x60001024,base+40+index*132,endpoint,base))
        return struct.unpack('>3f',self.u.mem_read(0x60001000,12))+struct.unpack('>3f',self.u.mem_read(0x60001010,12))+struct.unpack('>2f',self.u.mem_read(0x60001020,8))
    def fov(self,focal,tangent):
        self.run(0x8007a328,(),(focal,));turn=self.u.reg_read(self.reg.UC_PPC_REG_3)
        self.run(0x8007a3c0,(),(focal,tangent));return float(turn),self.floating(1)
    def cubic(self,p0,m0,p1,m1,t):
        self.u.mem_write(0x60002000,struct.pack('>4f',p0,m0,p1,m1)+bytes(28))
        self.run(0x800791b8,(0x60002000,));self.run(0x80079200,(0x60002000,),(t,));return self.floating(1)
    def linear(self,p0,p1,t,vector):
        base=0x60003000;curve=0x60003200;key=0x60003300;output=0x60003400
        obj=bytearray(0xc8);struct.pack_into('>I',obj,0xc4,key)
        struct.pack_into('>I',obj,0x84 if vector else 0x8c,curve)
        self.u.mem_write(base,bytes(obj));self.u.mem_write(key,bytes(132))
        self.u.mem_write(curve,struct.pack('>4f',p0,0,p1,0)+bytes(116))
        self.run(0x8007c0bc if vector else 0x8007c28c,(base,output),(t,))
        return struct.unpack('>f',self.u.mem_read(output,4))[0] if vector else self.floating(1)

def build(global_path,dol_path,output):
    data=global_path.read_bytes();dol=dol_path.read_bytes()
    if sha(data)!=GLOBAL_SHA:raise ValueError('Wrong original global camera bank')
    scenes=cameras(data);reference=CameraReference(dol);scene_rows=[];track_rows=[];key_rows=[];evidence=[]
    for name in NAMES:
        scene=scenes[bhash(name)];first=len(track_rows)
        for track in scene['tracks']:
            first_key=len(key_rows)
            for index,raw in enumerate(track['keys']):
                tangent=[reference.tangents(track,index,e) for e in range(2)]
                focal=struct.unpack_from('<2f',raw,84);mapped=[reference.fov(focal[e],tangent[e][7]) for e in range(2)]
                key_rows.append(raw+struct.pack('<16f',*tangent[0],*tangent[1])+struct.pack('<4f',mapped[0][0],mapped[1][0],mapped[0][1],mapped[1][1]))
            track_rows.append(struct.pack('<24sIIIfI20x',track['name'].encode(),len(scene_rows),first_key,len(track['keys']),track['duration'],track['source_offset']))
            evidence.append({'scene':name,'track':track['name'],'keys':len(track['keys']),'duration':track['duration'],'source_offset':track['source_offset']})
        scene_rows.append(struct.pack('<32s4I16x',name.encode(),scene['key'],first,len(scene['tracks']),0))
    scene_at=128;track_at=scene_at+64*len(scene_rows);key_at=track_at+64*len(track_rows)
    result=bytearray(128)+b''.join(scene_rows)+b''.join(track_rows)+b''.join(key_rows)
    struct.pack_into('<4s10I',result,0,b'NIS1',1,len(result),0,len(scene_rows),len(track_rows),len(key_rows),scene_at,track_at,key_at,212)
    result[48:80]=bytes.fromhex(GLOBAL_SHA);result[80:112]=bytes.fromhex(DOL_SHA256)
    struct.pack_into('<I',result,12,zlib.crc32(result[16:]));output.mkdir(parents=True,exist_ok=True)
    path=output/'opening-cameras.nis'
    if path.exists() and path.read_bytes()!=result:raise ValueError('Existing native cameras differ')
    path.write_bytes(result)
    im=DolImage(dol)
    report={'schema':1,'bytes':len(result),'sha256':sha(result),'source_global_sha256':GLOBAL_SHA,'source_dol_sha256':DOL_SHA256,
      'scenes':len(scene_rows),'tracks':evidence,'keys':len(key_rows),'original_tangent_calls':len(key_rows)*2,
      'identity_relative_provider_calls':reference.relative_calls,
      'consumer_windows':[{'start':hex(a),'end':hex(b),'sha256':sha(im.read(a,b-a))} for a,b in [(0x800798a0,0x80079990),(0x8007e550,0x8007eac8),(0x8007a328,0x8007a354),(0x8007a3c0,0x8007a488)]],
      'limits':['Camera curves only; compressed ELF actor animation is not decoded',
        'Mode3 ground/actor provider supplied as identity for local-basis tangent export; runtime must bind actual original provider',
        'Raw eye/target mode0 and3 are not silently converted to world positions',
        'FOV converted by actual original focal/atan lookup; interpolation and aspect policy must retain units',
        'Track choice, scene scheduler and original actor matrices remain separate integration responsibilities']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

def verify_host(asset,dol):
    class Pack(ctypes.Structure):
        _fields_=[('data',ctypes.c_void_p),('bytes',ctypes.c_size_t)]+[(n,ctypes.c_uint32) for n in ('scenes','tracks','keys','scene_at','track_at','key_at')]
    class Scene(ctypes.Structure):
        _fields_=[('name',ctypes.c_char_p)]+[(n,ctypes.c_uint32) for n in ('hash','first_track','track_count')]
    class Track(ctypes.Structure):
        _fields_=[('name',ctypes.c_char_p),('first_key',ctypes.c_uint32),('key_count',ctypes.c_uint32),('duration',ctypes.c_float)]
    class Camera(ctypes.Structure):
        _fields_=[('eye',ctypes.c_float*3),('target',ctypes.c_float*3),('roll',ctypes.c_float),('fov',ctypes.c_float),('key',ctypes.c_uint32),('eye_mode',ctypes.c_uint8),('target_mode',ctypes.c_uint8),('flags',ctypes.c_uint8*4),('reference_flags',ctypes.c_uint8*4),('finished',ctypes.c_bool)]
    Resolver=ctypes.CFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_uint8,ctypes.c_bool,ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float))
    @Resolver
    def identity(ctx,mode,target,source,out):
        ctypes.memmove(out,source,12);return mode<=3
    raw=asset.read_bytes();storage=ctypes.create_string_buffer(raw);reference=CameraReference(dol.read_bytes());cases=0
    root=Path(__file__).resolve().parents[1]
    def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
    def number(at):return struct.unpack_from('<f',raw,at)[0]
    with tempfile.TemporaryDirectory(prefix='nfsmw-nis-') as tmp:
        lib=Path(tmp)/'nis.so'
        subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_nis.c'),'-lm','-o',str(lib)],check=True)
        c=ctypes.CDLL(str(lib));c.mw_nis_open.argtypes=[ctypes.POINTER(Pack),ctypes.c_void_p,ctypes.c_size_t];c.mw_nis_open.restype=ctypes.c_bool
        c.mw_nis_scene.argtypes=[ctypes.POINTER(Pack),ctypes.c_uint32,ctypes.POINTER(Scene)];c.mw_nis_scene.restype=ctypes.c_bool
        c.mw_nis_track.argtypes=[ctypes.POINTER(Pack),ctypes.POINTER(Scene),ctypes.c_uint32,ctypes.POINTER(Track)];c.mw_nis_track.restype=ctypes.c_bool
        c.mw_nis_camera_sample.argtypes=[ctypes.POINTER(Pack),ctypes.POINTER(Track),ctypes.c_float,Resolver,ctypes.c_void_p,ctypes.POINTER(Camera)];c.mw_nis_camera_sample.restype=ctypes.c_bool
        p=Pack();assert c.mw_nis_open(ctypes.byref(p),storage,len(raw))
        for i in range(p.scenes):
            scene=Scene();assert c.mw_nis_scene(ctypes.byref(p),i,ctypes.byref(scene))
            for j in range(scene.track_count):
                track=Track();assert c.mw_nis_track(ctypes.byref(p),ctypes.byref(scene),j,ctypes.byref(track))
                for k in range(track.key_count):
                    at=p.key_at+(track.first_key+k)*212;first=number(at+16);last=number(at+212+16) if k+1<track.key_count else 1
                    for fraction in (0,.25,.5,.75,.999):
                        seconds=f32(f32(f32(f32(last-first)*fraction)+first)*track.duration)
                        result=Camera();assert c.mw_nis_camera_sample(ctypes.byref(p),ctypes.byref(track),seconds,identity,None,ctypes.byref(result))
                        key=p.key_at+(track.first_key+result.key)*212;start=number(key+16);end=number(key+212+16) if result.key+1<track.key_count else 1
                        u=max(0,min(1,f32(f32(f32(seconds/track.duration)-start)/f32(end-start))))
                        output=list(result.eye)+list(result.target)+[result.roll,result.fov]
                        offsets=[(28+a*4,132+a*4,40+a*4,164+a*4) for a in range(3)]+[(52+a*4,144+a*4,64+a*4,176+a*4) for a in range(3)]+[(76,156,80,188),(196,204,200,208)]
                        for axis,fields in enumerate(offsets):
                            values=[number(key+field) for field in fields]
                            cubic_flag=raw[key+(3 if 3<=axis<6 else 2)]
                            expected=reference.cubic(*values,u) if cubic_flag else reference.linear(values[0],values[2],u,axis<6)
                            if struct.pack('>f',output[axis])!=struct.pack('>f',expected):raise AssertionError((scene.name,track.name,k,fraction,axis,output[axis],expected))
                            cases+=1
    return {'original_scalar_curve_bit_cases':cases,'guest_code_bytes_patched':0,
            'scope':'Actual original endpoint tangents/focal conversion, cubic coefficient/value calls and original GetEye/GetDutch linear branches selected by source flags; identity caller resolver, not whole original cinematic playback'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('global','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--verify-host',action='store_true')
    a=p.parse_args();r=build(getattr(a,'global'),a.dol,a.output)
    if a.verify_host:
        r['verification']=verify_host(a.output/'opening-cameras.nis',a.dol)
        (a.output/'manifest.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('bytes','sha256','scenes','keys','original_tangent_calls','verification') if k in r}))
