"""Execute unmodified scalar originalLOD decision against portable selector."""
import hashlib
from pathlib import Path
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


class LodReference:
    def __init__(self,dol):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
        from unicorn import ppc_const as r
        if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Unknown original executable')
        self.r=r;self.image=DolImage(dol);self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        for low,size in ((0x10000000,0x10000),(0x802be000,0x2000),(0x800fe000,0x1000),(0x80409000,0x1000),(0x8041a000,0x1000)):
            self.uc.mem_map(low,size)
        self.uc.mem_write(0x802bec38,self.image.read(0x802bec38,0x130))
        self.uc.mem_write(0x800fe3e8,self.image.read(0x800fe3e8,12))
        self.uc.mem_write(0x80409000,self.image.read(0x80409000,0x1000))
        self.uc.reg_write(r.UC_PPC_REG_MSR,0x2000)
        self.done=False;self.result=None
        def hook(uc,a,size,unused):
            if a in (0x802bed60,0x802bf250):
                self.result=uc.reg_read(r.UC_PPC_REG_26) if a==0x802bed60 else 0
                self.done=True;uc.emu_stop()
            elif not (0x802bec38<=a<0x802bed60 or 0x800fe3e8<=a<=0x800fe3f0):
                raise ValueError(f'Original LOD escaped scalar bounds:{a:08x}')
        self.uc.hook_add(UC_HOOK_CODE,hook)

    def select(self,score,instance_flags,context_flags,state,mask,mesh,tri,metric):
        r=self.r;uc=self.uc
        for number,value in ((1,0x1000e000),(28,0x10006000),(29,0x10001000),(30,score&0xffffffff),(31,0x10002000),(26,0)):
            uc.reg_write(getattr(r,f'UC_PPC_REG_{number}'),value)
        uc.mem_write(0x10001018,struct.pack('>I',instance_flags))
        uc.mem_write(0x10006084,struct.pack('>I',context_flags))
        uc.mem_write(0x8041aca0,struct.pack('>i',state))
        for slot in range(4):
            uc.mem_write(0x10002028+slot*4,struct.pack('>I',0x10003000+slot*0x100 if mask&(1<<slot) else 0))
        uc.mem_write(0x1000300c,struct.pack('>I',0x10005000 if mesh else 0))
        uc.mem_write(0x10005014,struct.pack('>h',tri));uc.mem_write(0x1000509c,struct.pack('>f',metric))
        self.done=False;self.result=None
        uc.emu_start(0x802bec38,0x802bf254,count=1000)
        if not self.done:raise ValueError('Original LOD instruction budget exceeded')
        return -1 if not self.result else (self.result-0x10003000)//0x100


class ProjectedScoreReference(LodReference):
    """Original score producer, with only frsqrte supplied by pinned Dolphin.

    Dolphin code is an external host-only oracle, never part of the3DS module.
    """
    def __init__(self,dol,estimate):
        from unicorn import UC_HOOK_CODE
        super().__init__(dol)
        # Replace parent's selector hook by a new emulator hook boundary.
        # Parent creates one hook first; save/remove through hook enumeration is
        # unavailable, so instantiate the scalar machine afresh below.
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN
        r=self.r;self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        for low,size in ((0x10000000,0x10000),(0x802be000,0x2000),(0x80041000,0x1000),(0x80409000,0x1000)):
            self.uc.mem_map(low,size)
        for address,size in ((0x802beb24,0x114),(0x80041b14,0x20),(0x80409000,0x1000)):
            self.uc.mem_write(address,self.image.read(address,size))
        self.uc.reg_write(r.UC_PPC_REG_MSR,0x2000)
        self.distance_only=False
        def hook(uc,a,size,unused):
            if self.distance_only and a==0x802bec10:
                value=struct.unpack('>d',struct.pack('>Q',uc.reg_read(r.UC_PPC_REG_FPR0+13)))[0]
                self.result=value;self.done=True;uc.emu_stop()
            elif a==0x802bec38:
                bits=uc.reg_read(r.UC_PPC_REG_30);self.result=bits if bits<2**31 else bits-2**32
                self.done=True;uc.emu_stop()
            elif a==0x802bebdc:
                value=struct.unpack('>d',struct.pack('>Q',uc.reg_read(r.UC_PPC_REG_FPR0)))[0]
                uc.reg_write(r.UC_PPC_REG_FPR0+13,struct.unpack('>Q',struct.pack('>d',estimate(value)))[0])
                uc.reg_write(r.UC_PPC_REG_PC,a+4)
            elif not (0x802beb24<=a<0x802bec38 or 0x80041b14<=a<=0x80041b30):
                raise ValueError(f'Original projected score escaped:{a:08x}')
        self.uc.hook_add(UC_HOOK_CODE,hook)

    def score(self,translation,camera,forward,radius,projection):
        uc=self.uc;r=self.r
        self.distance_only=False
        for number,value in ((1,0x1000e000),(28,0x10006000),(29,0x10001000),(31,0x10002000)):
            uc.reg_write(getattr(r,f'UC_PPC_REG_{number}'),value)
        uc.mem_write(0x10001020,struct.pack('>3f',*translation))
        uc.mem_write(0x10006094,struct.pack('>3f',*camera))
        uc.mem_write(0x100060a4,struct.pack('>3f',*forward))
        uc.mem_write(0x10002038,struct.pack('>f',radius))
        uc.mem_write(0x100060b4,struct.pack('>f',projection))
        self.done=False;uc.emu_start(0x802beb24,0x802bec3c,count=1000)
        if not self.done:raise ValueError('Original projected score instruction budget exceeded')
        return self.result

    def distance(self,squared):
        uc=self.uc;r=self.r;self.distance_only=True
        for number,value in ((1,0x1000e000),):uc.reg_write(getattr(r,f'UC_PPC_REG_{number}'),value)
        for number,value in ((0,squared),(13,struct.unpack('>f',self.image.read(0x80409ae8,4))[0])):
            uc.reg_write(r.UC_PPC_REG_FPR0+number,struct.unpack('>Q',struct.pack('>d',value))[0])
        self.done=False;uc.emu_start(0x802bebc0,0x802bec3c,count=1000)
        if not self.done:raise ValueError('Original distance instruction budget exceeded')
        return self.result
