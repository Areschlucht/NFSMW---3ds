#!/usr/bin/env python3
"""Verify native opening NIS frame arithmetic against the unchanged USA DOL.

Original files and verification evidence remain outside the public repository.
This checks transform/rotation providers, not complete original scene execution.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from opening_nis_export import CameraReference,cameras,bhash,native_key
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference

class DirectorReference(CameraReference):
    def __init__(self,raw):
        super().__init__(raw)
        self.extra_allowed=((0x8010abcc,0x8010ac40),(0x8010b0fc,0x8010b2ac),(0x8007d76c,0x8007da8c),(0x800798a0,0x80079990),(0x80060ac0,0x80060b8c))
        self.subject=None
    def _hook(self,u,address,size,data):
        # Preserve unmodified eMulVector/eCreateRotationZ and original scalar/
        # paired-single reference semantics. No original instruction patching.
        if self.subject is not None and address==0x8007d69c:
            u.mem_write(u.reg_read(self.reg.UC_PPC_REG_3),struct.pack('>16f',*self.subject));u.reg_write(self.reg.UC_PPC_REG_PC,u.reg_read(self.reg.UC_PPC_REG_LR));return
        if self.subject is not None and address==0x80079b64:
            i=u.reg_read(self.reg.UC_PPC_REG_4)
            if i>1:raise ValueError('Original selector escaped original two-track list')
            u.reg_write(self.reg.UC_PPC_REG_3,0x60004000+i*0x1000);u.reg_write(self.reg.UC_PPC_REG_PC,u.reg_read(self.reg.UC_PPC_REG_LR));return
        OriginalContactReference._hook(self,u,address,size,data)
    def transform(self,m,p):
        self.u.mem_write(0x60001000,struct.pack('>16f',*m))
        self.u.mem_write(0x60001100,struct.pack('>3f',*p))
        self.run(0x8010abcc,(0x60001200,0x60001000,0x60001100))
        return struct.unpack('>3f',self.u.mem_read(0x60001200,12))
    def rotation(self,angle):
        self.run(0x8010b1d0,(0x60001200,angle))
        return struct.unpack('>16f',self.u.mem_read(0x60001200,64))

def verify(dol):
    repo=Path(__file__).resolve().parents[1]
    reference=DirectorReference(dol.read_bytes())
    with tempfile.TemporaryDirectory() as directory:
        lib=Path(directory)/'director.so'
        wrapper=Path(directory)/'wrapper.c';wrapper.write_text('#include "mw_nis_director.h"\n#include <string.h>\nint choose(const void *data,size_t bytes,const float*subject,const float*scene){MwNisPack p;MwNisScene s;MwNisDirector d={.has_subject=true,.has_scene=true};uint32_t index;if(!mw_nis_open(&p,data,bytes)||!mw_nis_find(&p,"GenericStart",&s))return -1;memcpy(d.subject,subject,64);memcpy(d.scene,scene,64);return mw_nis_director_choose_track(&d,&p,&s,&index)?(int)index:-1;}\n')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math','-fPIC','-shared','-I'+str(repo/'include'),str(repo/'source_bmw/mw_nis.c'),str(repo/'source_bmw/mw_nis_director.c'),str(repo/'source_bmw/mw_gekko_math.c'),str(wrapper),'-lm','-o',str(lib)],check=True)
        native=ctypes.CDLL(str(lib));array3=ctypes.c_float*3;array16=ctypes.c_float*16
        native.mw_nis_director_transform.argtypes=[ctypes.POINTER(ctypes.c_float)]*3
        native.mw_nis_director_transform.restype=ctypes.c_bool
        native.mw_nis_director_scene_frame.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.c_uint16,ctypes.c_uint32]
        native.mw_nis_director_scene_frame.restype=ctypes.c_bool
        transforms=rotations=0
        def same(a,b):return struct.pack('<'+str(len(a))+'f',*a)==struct.pack('<'+str(len(b))+'f',*b)
        for heading in range(0,65536,127):
            original=reference.rotation((heading-0x4000)&65535)
            result=array16();assert native.mw_nis_director_scene_frame(result,array3(123.25,-84.5,92),heading,0)
            expected=list(original);expected[12:15]=[123.25,-84.5,92]
            if not same(result,expected):raise ValueError(f'Root rotation mismatch heading{heading}: {list(result)} != {expected}')
            rotations+=1
            for p in ((1.25,5.0,-2.125),(100.125,-0.0001,8.0),(-2500.75,3500.5,100.25)):
                out=array3();assert native.mw_nis_director_transform(result,array3(*p),out)
                expected=reference.transform(list(result),p)
                if not same(out,expected):raise ValueError(f'Transform mismatch {heading} {p}: {list(out)} != {expected}')
                transforms+=1
        private=Path('/workspace/port-research/opening-nis');source=cameras((private/'raw/0e1075eb.bin').read_bytes())[bhash('GenericStart')]
        native_asset=(private/'native-camera-v2/opening-cameras.nis').read_bytes();storage=ctypes.create_string_buffer(native_asset)
        native.choose.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float)];native.choose.restype=ctypes.c_int
        manager=0x60002000;group=0x60002100;raw=bytearray(128);struct.pack_into('>I',raw,0,group);struct.pack_into('>I',raw,20,1);reference.u.mem_write(manager,bytes(raw));reference.u.mem_write(group,struct.pack('>5I',bhash('GenericStart'),0,2,0,0))
        for i,track in enumerate(source['tracks']):
            header=bytearray(40);struct.pack_into('>h',header,20,len(track['keys']));reference.u.mem_write(0x60004000+i*0x1000,bytes(header)+b''.join(native_key(k) for k in track['keys']))
        choices=0
        with DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin') as sqrt:
            reference.sqrt_reference=sqrt
            for heading in range(0,65536,379):
                subject=array16();assert native.mw_nis_director_scene_frame(subject,array3(2350,-500,90),heading,0)
                reference.subject=list(subject);reference.u.mem_write(0x60002200,struct.pack('>16f',*subject))
                reference.run(0x8007d76c,(manager,bhash('GenericStart'),0x60002200));original=reference.u.reg_read(reference.reg.UC_PPC_REG_3)
                actual=native.choose(storage,len(native_asset),subject,subject)
                if original!=actual:raise ValueError(f'Original track decision mismatch {heading}: {original}!={actual}')
                choices+=1
        return dict(dol_sha256=hashlib.sha256(dol.read_bytes()).hexdigest(),rotation_matrices=rotations,whole_vector_transforms=transforms,original_track_decisions=choices,float_bit_mismatches=0,original_code_patched=False,original_functions=['8010ABCC eMulVector','8010B1D0 eCreateRotationZ','8010B0FC eSin','8007D76C ChooseGoodSceneCameraTrackIndex'],limits=['Explicit source origin after original terrain correction','Individual arithmetic/provider comparisons, not complete original NIS execution','Original selector with explicit source player matrix/list accessor providers','Paired-single semantic adapter follows existing bounded source reference'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    evidence=verify(args.dol);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
if __name__=='__main__':main()
