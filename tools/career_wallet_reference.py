#!/usr/bin/env python3
"""Bounded original new-career cash reset, winner award, debit and bonus checks.

Original game code/data are external. Attribute lookup, current-event identity,
actor interface identity and event-completion query are explicit supplied inputs.
This does not recover the entire opening story or first-car affordability flow.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_attributes import vlt_hash

GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'


class Reference:
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA executable')
        self.im=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x600000)
        for s in self.im.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.u.mem_map(0x60000000,0x10000);self.u.mem_map(0x70000000,0x10000)
        self.u.reg_write(r.UC_PPC_REG_MSR,self.u.reg_read(r.UC_PPC_REG_MSR)|(1<<13))
        self.stop=set();self.mode='';self.calls=[];self.event_key=0
        def hook(u,pc,size,_):
            if pc in self.stop:u.emu_stop();return
            if self.mode=='award':
                if pc in (0x6000f000,0x6000f004,0x801a6eb0,0x801a7710,0x801a4b8c,0x801bc634,0x80057250):
                    if pc==0x6000f000:u.reg_write(r.UC_PPC_REG_3,0x60002000)
                    elif pc==0x6000f004:u.reg_write(r.UC_PPC_REG_3,self.player_index)
                    elif pc==0x801a6eb0:u.reg_write(r.UC_PPC_REG_3,0x60006000)
                    elif pc==0x801a7710:u.reg_write(r.UC_PPC_REG_3,self.event_key)
                    elif pc==0x801a4b8c:
                        if u.reg_read(r.UC_PPC_REG_4)!=self.event_key or u.reg_read(r.UC_PPC_REG_5)!=2:raise ValueError('Original completion-query arguments differ')
                        u.reg_write(r.UC_PPC_REG_3,self.previously_won)
                    elif pc==0x80057250:
                        if u.reg_read(r.UC_PPC_REG_4)!=0xd8baa07b or u.reg_read(r.UC_PPC_REG_5):raise ValueError('Original CashValue field lookup differs')
                        u.reg_write(r.UC_PPC_REG_3,0x60007100)
                    self.calls.append(f'{pc:08x}');u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
                if 0x801c3a48<=pc<0x801c3b2c or 0x801a4f3c<=pc<0x801a5080:return
            if self.mode=='reset' and 0x8015fce4<=pc<0x8015fd14:return
            if self.mode=='debit' and 0x8015fdf8<=pc<0x8015fe1c:return
            if self.mode=='bonus' and 0x801602a0<=pc<0x801602c4:return
            raise ValueError(f'Original wallet execution escaped: {pc:08x}')
        def write(u,access,at,size,value,_):
            if not (0x60000000<=at and at+size<=0x60010000 or 0x70000000<=at and at+size<=0x70010000):raise ValueError(f'Original wallet write escaped: {at:08x}')
        self.u.hook_add(UC_HOOK_CODE,hook);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def execute(self,pc,mode,stops,registers):
        self.mode=mode;self.stop=set(stops);self.calls=[];u=self.u;r=self.r
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        for n,v in registers:u.reg_write(r.UC_PPC_REG_0+n,v)
        u.emu_start(pc,0x6000fff0,count=10000,timeout=100000)
        if u.reg_read(r.UC_PPC_REG_PC) not in self.stop|{0x6000fff0}:raise ValueError('Original wallet execution budget')
    def word(self,at):return struct.unpack('>I',bytes(self.u.mem_read(at,4)))[0]
    def reset(self,cash):
        self.u.mem_write(0x60000000,bytes(64));self.u.mem_write(0x6000000c,struct.pack('>I',cash))
        self.execute(0x8015fce4,'reset',(0x8015fd14,),[(3,0x60000000)])
        return self.word(0x6000000c),self.u.mem_read(0x60000008,1)[0]
    def debit(self,cash,amount):
        self.u.mem_write(0x6000000c,struct.pack('>I',cash));self.execute(0x8015fdf8,'debit',(),[(3,0x60000000),(4,amount)])
        return self.word(0x6000000c)
    def bonus(self,cash,enabled):
        self.u.mem_write(0x60000004,bytes(12));self.u.mem_write(0x6000000c,struct.pack('>I',cash));self.execute(0x801602a0,'bonus',(),[(3,0x60000000),(4,int(enabled))])
        return self.word(0x6000000c),self.word(0x60000004)
    def award(self,cash,prize,event_key,rank=1,mode=2,latched=False,player_index=0,previously_won=0):
        u=self.u;self.player_index=player_index;self.previously_won=previously_won;self.event_key=event_key
        u.mem_write(0x60000000,bytes(0xe000));u.mem_write(0x8041d30c,struct.pack('>I',0x60003000));u.mem_write(0x8041c484,struct.pack('>I',0x60008000))
        u.mem_write(0x60001004,struct.pack('>I',0x60001100));u.mem_write(0x60001148,struct.pack('>HI',0,0))
        u.mem_write(0x6000114c,struct.pack('>I',0x6000f000));u.mem_write(0x60002004,struct.pack('>I',0x60002100));u.mem_write(0x60002140,struct.pack('>H',0));u.mem_write(0x60002144,struct.pack('>I',0x6000f004))
        u.mem_write(0x60000010,struct.pack('>I',rank));u.mem_write(0x60004aac,struct.pack('>I',0x60005000));u.mem_write(0x60004aa8,struct.pack('>I',mode));u.mem_write(0x600076a8,struct.pack('>I',latched))
        u.mem_write(0x60005004,struct.pack('>I',0x60007000));u.mem_write(0x60007100,struct.pack('>f',prize))
        u.mem_write(0x60008020,struct.pack('>2I',0x60009000,0x6000a000));u.mem_write(0x600090f0,struct.pack('>I',cash));u.mem_write(0x6000a0f0,struct.pack('>I',cash))
        self.execute(0x801c3a48,'award',(0x801c3cc4,0x801c3ca4,0x801c3c88,0x801c3bbc,0x801c3b2c),[(26,0x60000000),(27,0x60001000)])
        return self.word(0x600090f0+player_index*0x1000),self.word(0x600076a8)


def verify(a):
    raw=a.dol.read_bytes();gameplay=a.gameplay.read_bytes()
    if hashlib.sha256(gameplay).hexdigest()!=GAMEPLAY_SHA:raise ValueError('Unexpected original gameplay')
    catalog=json.loads(a.catalog.read_text());ref=Reference(raw)
    if vlt_hash('CashValue')!=0xd8baa07b:raise ValueError('Unexpected field-name hash')
    rows=[]
    for row in catalog['race_definition_candidates']:
        if not row['name'].startswith(('16_1_','16_2_')):continue
        field=row['fields']['0xd8baa07b'];value=field['value'];at=field['file_offset'];original=bytes.fromhex(field['original_bytes'])
        if field['source_sha256']!=GAMEPLAY_SHA or gameplay[at:at+len(original)]!=original or original!=struct.pack('>f',value):raise ValueError('CashValue provenance mismatch')
        rows.append({'key':row['key'],'name':row['name'],'cash_value':value,'field':field})
    cases=0
    for cash in (0,1,30000,0xffffffff):
        if ref.reset(cash)!=(0,16):raise ValueError('Original new-career reset differs')
        cases+=1
    for cash in (0,1,10000,30000,0xffffffff):
        for amount in (0,1,26000,27000,35000,0xffffffff):
            if ref.debit(cash,amount)!=max(0,cash-amount):raise ValueError('Original debit differs')
            cases+=1
        for enabled in (False,True):
            if ref.bonus(cash,enabled)!=((cash+(10000 if enabled else 0))&0xffffffff,2):raise ValueError('Original optional bonus differs')
            cases+=1
    for row in rows:
        prize=row['cash_value'];key=int(row['key'],16)
        for rank in (1,2,3):
            for mode in (1,2):
                for latched in (False,True):
                    for player in (0,1):
                        actual=ref.award(123,prize,key,rank,mode,latched,player)
                        expected=(123+int(prize) if rank==1 and mode==2 and not latched else 123)
                        if actual[0]!=expected:raise ValueError({'event':row['name'],'rank':rank,'mode':mode,'latched':latched,'player':player,'actual':actual,'expected':expected})
                        cases+=1
    report={'schema':1,'source_sha256':{'dol':DOL_SHA256,'gameplay':GAMEPLAY_SHA},'original_cases':cases,'new_career_cash_after_reset':0,'optional_bonus':10000,'opening_events':rows,'wallet_offset':'active frontend profile +0xF0, career subobject +0x0C','race_award_gate':'rank1, career mode2, one-shot event cash flag clear, supplied player controller index0/1','lua_AwardCash_is_racer_accumulator':True,'limits':['No unconditional initial30000 constant is inferred','Three legitimate source prize wins total30000; this is not proof of exact scripted Razor loss/first-car timing','Optionalbonus source detection/caller ordering is not recovered; do not grant automatically','Actor/attribute lookup/previous-completion results are explicit reference inputs','Affordability checks, successful car purchase and original complete profile save remain separate'],'code_windows':[]}
    for lo,hi in ((0x8013c480,0x8013c4b4),(0x8015fce4,0x8015fd14),(0x8015fdf8,0x8015fe1c),(0x801602a0,0x801602c4),(0x801a4f3c,0x801a5080),(0x8019e030,0x8019e044),(0x801c3a48,0x801c3b2c),(0x8012f0c4,0x8012f0f4)):
        report['code_windows'].append({'start':f'{lo:08x}','end_exclusive':f'{hi:08x}','sha256':hashlib.sha256(ref.im.read(lo,hi-lo)).hexdigest()})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':cases,'new_career_cash':0,'opening_CashValue':{r['name']:r['cash_value'] for r in rows}}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','gameplay','catalog','output'):p.add_argument('--'+n,type=Path,required=True)
    verify(p.parse_args())
