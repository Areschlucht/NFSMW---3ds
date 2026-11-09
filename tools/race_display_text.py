#!/usr/bin/env python3
"""Recover exact original race display-name keys and supplied English text.

Only the source-ID getter and bounded two-ASCII-string formatting dependency are
supplied synthetically for original execution. Prefix handling, dot substitution,
ASCII case folding and hash arithmetic stay original. Missing names stay missing.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

ENGLISH_SHA256='fda4935491869ddaa3eba335c3425aa9cbc8fcbd82a58a20f7334ecbbbd8fa4a'


def language_entries(raw,pin=True):
    if pin and hashlib.sha256(raw).hexdigest()!=ENGLISH_SHA256:
        raise ValueError('Unexpected supplied English source')
    if len(raw)<24:raise ValueError('Truncated language header')
    kind,size=struct.unpack_from('<II',raw)
    _,count,table,strings=struct.unpack_from('<4I',raw,8)
    table+=8;strings+=8
    if kind!=0x39000 or size!=len(raw)-8 or not 0<count<=100000 or not 24<=table<=strings<len(raw) or table+count*8!=strings:
        raise ValueError('Invalid language region layout')
    result={};previous=-1
    for i in range(count):
        key,offset=struct.unpack_from('<II',raw,table+i*8);at=strings+offset
        if key<=previous or not strings<=at<len(raw) or (offset and raw[at-1]):
            raise ValueError('Invalid key order/string boundary')
        stop=raw.find(b'\0',at)
        if stop<0:raise ValueError('Unterminated language string')
        result[key]={'raw':raw[at:stop],'file_offset':at,'table_file_offset':table+i*8}
        previous=key
    return result


def language_key(source_id):
    if not isinstance(source_id,str) or '\0' in source_id:raise ValueError('Invalid source ID')
    value=('TRACKNAME_'+source_id).encode('ascii')
    if len(value)>=64:raise ValueError('Source exceeds verified format bound')
    value=value.replace(b'.',b'_')
    key=0xffffffff
    for c in value:
        if 97<=c<=122:c-=32
        key=(key*33+c)&0xffffffff
    return key


def check_rejections(raw):
    language_entries(raw)
    variants={'short_header':raw[:20]}
    _,_,table,_=struct.unpack_from('<4I',raw,8);table+=8
    for name,at,value in (
        ('wrong_chunk',0,0),('wrong_size',4,0),('excessive_count',12,100001),
        ('table_outside_file',16,0xffffffff),
        ('duplicate_language_key',table+8,struct.unpack_from('<I',raw,table)[0]),
        ('inside_string_offset',table+4,struct.unpack_from('<I',raw,table+4)[0]+1)):
        data=bytearray(raw);struct.pack_into('<I',data,at,value);variants[name]=data
    data=bytearray(raw);data[-1]=ord('X');variants['unterminated_final_string']=data
    for name,data in variants.items():
        try:language_entries(bytes(data),pin=False)
        except ValueError:pass
        else:raise AssertionError('Malformed language accepted: '+name)
    return list(variants)


class NameReference:
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
        self.im=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for section in self.im.sections:self.u.mem_write(section.address,raw[section.offset:section.offset+section.size])
        if self.im.c_string(0x803e0888)!='TRACKNAME_':raise ValueError('Original prefix differs')
        self.done=False
        def code(u,pc,size,data):
            if pc==0x801a5158:
                if u.reg_read(r.UC_PPC_REG_LR)!=0x80163120:raise ValueError('Unexpected source-ID getter origin')
                u.reg_write(r.UC_PPC_REG_3,0x81603000);u.reg_write(r.UC_PPC_REG_PC,0x80163120)
            elif pc==0x80132914:
                if u.reg_read(r.UC_PPC_REG_LR)!=0x8016313c or u.reg_read(r.UC_PPC_REG_4)!=64:raise ValueError('Unexpected formatter call')
                def cstring(at):return bytes(u.mem_read(at,256)).split(b'\0',1)[0]
                if cstring(u.reg_read(r.UC_PPC_REG_5))!=b'%s%s':raise ValueError('Unexpected format')
                text=cstring(u.reg_read(r.UC_PPC_REG_6))+cstring(u.reg_read(r.UC_PPC_REG_7))
                if len(text)>=64:raise ValueError('Unverified formatting truncation')
                u.mem_write(u.reg_read(r.UC_PPC_REG_3),text+b'\0'*(64-len(text)))
                u.reg_write(r.UC_PPC_REG_3,len(text));u.reg_write(r.UC_PPC_REG_PC,0x8016313c)
            elif pc==0x817ffffc:self.done=True;u.emu_stop()
            elif not any(a<=pc<b for a,b in ((0x801630cc,0x80163164),(0x80183b54,0x80183bb8),(0x80183768,0x80183780))):
                raise ValueError(f'Execution escaped name windows: {pc:08x}')
        def write(u,access,address,size,value,data):
            if not 0x8160f000<=address or address+size>0x81610100:raise ValueError('Original write escaped stack')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def key(self,source_id):
        encoded=source_id.encode('ascii');language_key(source_id)
        u=self.u;r=self.r;self.done=False
        u.mem_write(0x81603000,encoded+b'\0')
        u.reg_write(r.UC_PPC_REG_1,0x81610000);u.reg_write(r.UC_PPC_REG_3,0x803e0888)
        u.reg_write(r.UC_PPC_REG_4,0x81602000);u.reg_write(r.UC_PPC_REG_LR,0x817ffffc)
        u.emu_start(0x801630fc,0x817ffff8,count=20000,timeout=100000)
        if not self.done:raise ValueError('Original name execution budget exhausted')
        return u.reg_read(r.UC_PPC_REG_3)


def recover(english,dol,catalog,verify_original=False,frontend_directory=None):
    if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
    language=language_entries(english);image=DolImage(dol)
    reference=NameReference(dol) if verify_original else None
    events=[];verified=0
    for event in catalog['race_definition_candidates']:
        field=event['fields'].get('0xa78403ec')
        source=field['value'] if field else ''
        key=language_key(source)
        if reference:
            if reference.key(source)!=key:raise ValueError('Original name-key mismatch')
            verified+=1
        row={'event_key':event['key'],'source_event_name':event['name'],'source_id':source,
             'language_key':f'{key:08x}','status':'missing'}
        if field:row['source_id_provenance']={k:field[k] for k in ('source_sha256','file_offset','original_bytes','source_collection')}
        if key in language:
            text=language[key]['raw']
            # Actual matched titles are ASCII; other English encodings are not
            # established by this task and must not be silently reinterpreted.
            row.update(status='matched',display_text=text.decode('ascii'),
                       language_file_offset=language[key]['file_offset'],
                       language_table_file_offset=language[key]['table_file_offset'])
        events.append(row)
    if reference:
        for value in ('10.2.1','10.2.1.r','10.2.1.R','','MaxLoad','maxload','unknown.id'):
            if reference.key(value)!=language_key(value):raise ValueError('Synthetic original key mismatch')
            verified+=1
    menu_candidates=[]
    if frontend_directory:
        wanted={'career','challenge series','quick race','my cars','alias manager','options','press start','press start button'}
        selected=('MainMenu.fng','MainMenu_Sub.fng','PressStart.fng','MC_ProfileManager.fng','MC_DeleteProfile.fng')
        for key,row in language.items():
            try:text=row['raw'].decode('ascii')
            except UnicodeDecodeError:continue
            if text.lower() not in wanted:continue
            matches=[]
            for name in selected:
                raw=(frontend_directory/name).read_bytes()
                for order,label in (('<','little'),('>','big')):
                    at=raw.find(struct.pack(order+'I',key))
                    if at>=0:matches.append({'fng':name,'byte_order':label,'offset':at,'fng_sha256':hashlib.sha256(raw).hexdigest()})
            menu_candidates.append({'language_key':f'{key:08x}','text':text,'literal_key_candidates':matches})
    ranges=((0x801630cc,0x80163164),(0x801a5158,0x801a51c0),(0x80183b54,0x80183bb8),(0x80183768,0x80183780))
    return {'schema':1,'english_sha256':ENGLISH_SHA256,'dol_sha256':DOL_SHA256,
        'language_entries':len(language),'event_definitions':len(events),
        'status_counts':dict(Counter(row['status'] for row in events)),
        'original_name_key_cases':verified,'events':events,'menu_candidates':menu_candidates,
        'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(image.read(a,b-a)).hexdigest()} for a,b in ranges],
        'limits':['Original source-ID getter and bounded two-string formatting supplied synthetically during reference execution',
                  'Dot replacement, ASCII uppercasing and hash loop remain original instructions',
                  'Missing challenge/template/special IDs remain missing; no fabricated display names',
                  'Language table includes shared cross-platform text; entries alone do not establish GameCube visibility',
                  'FNG literal-key occurrences are candidates, not complete label binding or original menu order']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('english','dol','catalog','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--frontend-directory',type=Path);p.add_argument('--verify-original',action='store_true')
    p.add_argument('--check-rejections',action='store_true')
    a=p.parse_args();r=recover(a.english.read_bytes(),a.dol.read_bytes(),json.loads(a.catalog.read_text()),a.verify_original,a.frontend_directory)
    if a.check_rejections:r['malformed_language_inputs_rejected']=check_rejections(a.english.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('language_entries','event_definitions','status_counts','original_name_key_cases')}))
