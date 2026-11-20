#!/usr/bin/env python3
"""Source CarTypeInfo traffic-tire binding; private offline reference only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from nfs_rockport import chunks
from material_recovery_vehicle import texture_hash
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
PARTS_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'


def source_car_usage(raw):
    if hashlib.sha256(raw).hexdigest()!=PARTS_SHA:raise ValueError('Expected original USA car info bank')
    matches=[(a,b) for k,a,b in chunks(raw) if k==0x34600]
    if len(matches)!=1:raise ValueError('Ambiguous original car-info table')
    a,b=matches[0]
    if b-a!=8+84*208 or raw[a:a+8]!=bytes.fromhex('1111111111111111'):raise ValueError('Unexpected source car-info layout')
    result={}
    for i in range(84):
        at=a+8+i*208;name=raw[at:at+16].split(b'\0')[0].decode('ascii')
        if not name or name in result:raise ValueError('Invalid/duplicate source car name')
        geometry=raw[at+32:at+64].split(b'\0')[0].decode('ascii')
        usage=struct.unpack_from('<I',raw,at+148)[0]
        if usage>4:raise ValueError('Unknown source car usage enum')
        result[name]={'usage':usage,'record':i,'record_file_offset':at,
            'usage_file_offset':at+148,'usage_original_bytes':raw[at+148:at+152].hex(),
            'geometry':geometry,'source_sha256':PARTS_SHA,
            'tire_source':f'{texture_hash(name+"_TIRE"):08x}',
            'tire_target':f'{texture_hash("TRAFFIC_TIRE"):08x}' if usage==2 else None}
    return result


class OriginalTrafficTire:
    def __init__(self,dol):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Expected original USA executable')
        self.r=r;self.dol=DolImage(dol);self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.dol.sections:self.u.mem_write(s.address,dol[s.offset:s.offset+s.size])
        self.allowed=[];self.count=0
        def code(u,address,size,_):
            if not any(a<=address<b for a,b in self.allowed):raise ValueError(f'Original traffic reference escaped{address:08x}')
            self.count+=1
        def write(u,access,address,size,value,_):
            if not (0x81600000<=address<address+size<=0x81630000 or 0x817fe000<=address<address+size<=0x81800000 or 0x80437980<=address<address+size<=0x80437984):raise ValueError('Traffic reference write escaped private ranges')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,start,stop):
        self.count=0;self.u.reg_write(self.r.UC_PPC_REG_1,0x817ff000)
        self.u.emu_start(start,stop,timeout=1000000,count=2000000)
        if self.u.reg_read(self.r.UC_PPC_REG_PC)!=stop:raise ValueError('Original traffic reference budget exceeded')
    def verify_loader(self,bank):
        rows=source_car_usage(bank);a,b=next((a,b) for k,a,b in chunks(bank) if k==0x34600)
        chunk=bytearray(bank[a-8:b]);struct.pack_into('>2I',chunk,0,0x34600,b-a)
        node=0x81600000;self.u.mem_write(node,bytes(chunk));self.u.reg_write(self.r.UC_PPC_REG_3,node);self.u.reg_write(self.r.UC_PPC_REG_LR,0x81700000)
        self.allowed=[(0x802d92f0,0x802d93bc),(0x802d9a6c,0x802d9a84),(0x8005cb10,0x8005cbd0)]
        self.run(0x802d92f0,0x81700000)
        base=struct.unpack('>I',self.u.mem_read(0x80437980,4))[0]
        if base!=node+16:raise ValueError('Original source car table alignment differs')
        for name,row in rows.items():
            at=base+row['record']*208
            if bytes(self.u.mem_read(at,len(name)))!=name.encode('ascii') or struct.unpack('>I',self.u.mem_read(at+148,4))[0]!=row['usage']:raise ValueError('Original CarTypeInfo loader usage differs')
        return len(rows)
    def binding(self,usage,old_target,old_cache=123):
        obj=0x81610000;info=0x81620000
        self.u.mem_write(obj,bytes(0x1800));self.u.mem_write(info+148,struct.pack('>I',usage))
        self.u.reg_write(self.r.UC_PPC_REG_30,info)
        self.allowed=[(0x802c80f8,0x802c8108)]
        self.run(0x802c80f8,0x802c8108)
        selected=self.u.reg_read(self.r.UC_PPC_REG_29)
        if selected!=int(usage==2):raise ValueError('Source traffic usage test differs')
        self.u.mem_write(obj+0x2c4,struct.pack('>2I',old_target,old_cache));self.u.reg_write(self.r.UC_PPC_REG_31,obj)
        self.allowed=[(0x802c815c,0x802c81c8),(0x80062ecc,0x80062efc)]
        self.run(0x802c815c,0x802c81c8)
        target,cache=struct.unpack('>2I',self.u.mem_read(obj+0x2c4,8))
        expected=texture_hash('TRAFFIC_TIRE') if usage==2 else old_target
        if target!=expected or cache!=(0xffffffff if usage==2 and old_target!=expected else old_cache):raise ValueError('Original tire alias/cache update differs')
        return {'usage':usage,'old_target':f'{old_target:08x}','new_target':f'{target:08x}','cache':cache}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--carparts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=source_car_usage(a.carparts.read_bytes());r=OriginalTrafficTire(a.dol.read_bytes());loaded=r.verify_loader(a.carparts.read_bytes())
    cases=[]
    for usage in [0,1,2,3,4,0xffffffff]:
        for old in [0,123,texture_hash('TRAFFIC_TIRE'),0xffffffff]:cases.append(r.binding(usage,old))
    out={'schema':1,'carparts_sha256':PARTS_SHA,'dol_sha256':DOL_SHA256,'original_loader_rows':loaded,
        'constructor_usage_range':['802c80f8','802c8108'],'constructor_alias_range':['802c815c','802c81c8'],
        'source_usage_offset':148,'source_traffic_enum':2,'target_name':'TRAFFIC_TIRE','target_hash':f'{texture_hash("TRAFFIC_TIRE"):08x}',
        'unchanged_original_binding_cases':cases,'car_types':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'loader_rows':loaded,'binding_cases':len(cases),'traffic_models':sum(x['usage']==2 for x in rows.values())}))
if __name__=='__main__':main()
