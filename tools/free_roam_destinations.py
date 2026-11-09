#!/usr/bin/env python3
"""Recover typed original free-roam shop/safehouse/race entry records.

Positions, radii and respawn references remain in original source units. This
exports data and bounded action-dispatch evidence, not shop economy or race AI.
"""
import argparse
import copy
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from race_story_export import keys
from gameplay_packages import GameplayPackages,dol_labels
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash

ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'
ZONE_ACTIONS={'safehouse':(2,'MainMenu_Sub.fng'),'carlot':(5,'Car_Select.fng'),
              'customshop':(3,'CustomizeMain.fng')}


def compact(f):
    return {k:f[k] for k in ('field_key','field_name','type','value','source_collection',
                             'source_sha256','file_offset','original_bytes')}


def collect(rows,gameplay,dol):
    if hashlib.sha256(gameplay).hexdigest()!=GAMEPLAY_SHA:raise ValueError('Unexpected source gameplay')
    if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA executable')
    if vlt_hash('RaceTriggers')!=0x58dc14c0:raise ValueError('Unexpected field-label hash')
    by={r['key']:r for r in rows}
    if len(by)!=len(rows):raise ValueError('Ambiguous source collection keys')
    checked=set()
    def field(row,name):
        f=row['fields'][name];raw=bytes.fromhex(f['original_bytes']);at=f['file_offset']
        if f['source_sha256']!=GAMEPLAY_SHA or at<0 or gameplay[at:at+len(raw)]!=raw:
            raise ValueError('Field source provenance differs')
        checked.add((f['source_sha256'],at,len(raw)));return f
    def scalar(row,name,kind,count=1):
        f=field(row,name)
        if f['type']!=kind:raise ValueError('Unexpected original spatial type')
        value=f['value'];values=value if count!=1 else [value]
        if len(values)!=count or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in values):raise ValueError('Invalid finite scalar/vector')
        fmt='>'+str(count)+('f' if kind!='EA::Reflection::Int32' else 'i')
        if struct.pack(fmt,*values).hex()!=f['original_bytes']:raise ValueError('Typed value differs from original bytes')
        return value,compact(f)
    def reference(row,name):
        result=list(keys(field(row,name)))
        for key in result:
            if key and key not in by:raise ValueError('Unresolved collection key')
        return result
    def one(row,name):
        result=reference(row,name)
        if len(result)!=1:raise ValueError('Expected scalar original key')
        return result[0]
    def spatial(row,rotation=False):
        position,p=scalar(row,'Position','Attrib::Types::Vector3',3)
        result={'key':f'{row["key"]:08x}','source_name':row['name'],'position_source':position,
                'position_provenance':p}
        if rotation:
            value,f=scalar(row,'Rotation','EA::Reflection::Float');result.update(rotation_source_degrees=value,rotation_provenance=f)
        return result
    destinations=[];owners=[]
    for row in rows:
        z=row['fields'].get('ZoneType',{}).get('value')
        if z not in ZONE_ACTIONS or '0x64893da8' not in row['fields']:continue
        children=reference(row,'0x64893da8')
        if len(set(children))!=len(children):raise ValueError('Duplicate menu gate child')
        owners.append({'key':f'{row["key"]:08x}','source_name':row['name'],'zone_type':z,
                       'ordered_zone_keys':[f'{k:08x}' for k in children],
                       'child_field':compact(field(row,'0x64893da8'))})
        for key in children:
            target=by[key]
            if field(target,'ZoneType')['value']!=z:raise ValueError('Zone type disagrees with owner')
            record=spatial(target);radius,rp=scalar(target,'Radius','EA::Reflection::Float')
            if radius<=0:raise ValueError('Nonpositive original radius')
            index,bp=scalar(target,'0x6ce23062','EA::Reflection::Int32')
            respawn_key=one(target,'0x2241f4cd')
            if not respawn_key:raise ValueError('Missing source respawn')
            record.update(kind=z,owner_key=f'{row["key"]:08x}',radius_source=radius,
                radius_provenance=rp,bin_index=index,bin_provenance=bp,
                respawn=spatial(by[respawn_key],True),respawn_field=compact(field(target,'0x2241f4cd')),
                zone_type_provenance=compact(field(target,'ZoneType')),
                original_frontend_mode=ZONE_ACTIONS[z][0],original_frontend_package=ZONE_ACTIONS[z][1])
            destinations.append(record)
    race_entries=[];race_owners=[]
    owner_keys={r['key'] for r in rows if '0x58dc14c0' in r['fields']};bin_for_owner={}
    for row in rows:
        if '0x6ce23062' not in row['fields'] or '0x916e0e78' not in row['fields']:continue
        matches=owner_keys&set(reference(row,'0x916e0e78'))
        for key in matches:
            index,provenance=scalar(row,'0x6ce23062','EA::Reflection::Int32')
            if not 1<=index<=16 or key in bin_for_owner:raise ValueError('Ambiguous original race owner bin')
            bin_for_owner[key]={'bin_index':index,'bin_owner_key':f'{row["key"]:08x}','bin_index_provenance':provenance}
    if set(bin_for_owner)!=owner_keys:raise ValueError('Incomplete direct bin ownership')
    for owner in rows:
        if '0x58dc14c0' not in owner['fields']:continue
        children=reference(owner,'0x58dc14c0')
        race_owners.append({'key':f'{owner["key"]:08x}','source_name':owner['name'],
            'ordered_trigger_keys':[f'{k:08x}' for k in children],
            'race_triggers_field':compact(field(owner,'0x58dc14c0')),**bin_for_owner[owner['key']]})
        for key in children:
            trigger=by[key];event_key=one(trigger,'0x277566f3')
            if not event_key or 'NumLaps' not in by[event_key]['fields']:raise ValueError('Trigger does not resolve race definition')
            entry=spatial(trigger);radius,rp=scalar(trigger,'Radius','EA::Reflection::Float')
            if radius<=0:raise ValueError('Nonpositive trigger radius')
            event=by[event_key];mode=field(event,'0x0f6bcde1');event_id=field(event,'0xa78403ec')
            entry.update(kind='race_entry',owner_key=f'{owner["key"]:08x}',**bin_for_owner[owner['key']],radius_source=radius,
                radius_provenance=rp,event_key=f'{event_key:08x}',event_source_name=event['name'],
                event_type_source=mode['value'],event_type_provenance=compact(mode),
                event_display_source_id=event_id['value'],event_id_provenance=compact(event_id),
                event_reference=compact(field(trigger,'0x277566f3')))
            race_entries.append(entry)
    image=DolImage(dol)
    addresses=(0x8014bf68,0x8014c068,0x80162b14,0x80162bac,0x801c5160,0x801c5260,0x8019af10,0x8019af54,0x801c0098,0x801c00b4,0x801c5f00,0x801c5f34)
    return {'schema':1,'source_sha256':{'gameplay':GAMEPLAY_SHA,'dol':DOL_SHA256},
        'destination_counts':dict(Counter(r['kind'] for r in destinations)),
        'race_entry_count':len(race_entries),'race_owner_count':len(race_owners),
        'independent_original_field_ranges_checked':len(checked),
        'menu_gate_owners':owners,'destinations':destinations,'race_owners':race_owners,'race_entries':race_entries,
        'consumer_evidence':{'zone_frontend_dispatch':'8014bf68..8014c064',
            'customshop_extra_condition':'8014c000..8014c02c requires current ride and byte+10 != ff',
            'icon_selector':'80162b14..80162ba8',
            'icon_hashes':{'carlot':'4eaee18b','safehouse':'0ed39f69','customshop':'0cf07089'},
            'respawn_key_consumer':'801c5184..801c51b4 reads2241f4cd and stores manager+114; conditional safehouse path also stores+118',
            'race_target_consumer':'8019af14..8019af4c reads277566f3 then resolves event through801a4364',
            'jump_to_safehouse':'801c0098..00b0 registers JumpToSafeHouse to801c5f00; callback opens frontendmode2 MainMenu_Sub.fng without direct teleport'},
        'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}',
            'sha256':hashlib.sha256(image.read(a,b-a)).hexdigest()} for a,b in zip(addresses[::2],addresses[1::2])],
        'limits':['Source positions/radii are not a guessed nearest-distance interaction implementation',
            'BinIndex is preserved, not assigned an invented unlock comparison',
            'Source respawn transform is explicit; in-engine safehouse save/return scheduling remains separate',
            'Menus dispatch to original frontend packages; shop inventories/prices/economy/customization are not implemented',
            'Race entries resolve original events; selection availability, trigger actors, acceptance/pursuit gates and races remain integration work']}


class ActionReference:
    """Original case-sensitive action branches; custom ride condition is not bypassed."""
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA executable')
        self.image=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN);self.u.mem_map(0x80000000,0x1800000)
        for s in self.image.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.result=None
        stops={0x8014bf94:'safehouse',0x8014bfc8:'carlot',0x8014bffc:'customshop_requires_ride',0x8014c054:'none'}
        def code(u,address,size,_):
            if address in stops:self.result=stops[address];u.emu_stop()
            elif not any(a<=address<b for a,b in ((0x8014bf7c,0x8014c054),(0x80063034,0x80063098))):raise ValueError('Action escaped bounded window')
        def write(u,access,address,size,value,_):raise ValueError('Unexpected original dispatch write')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def branch(self,zone):
        raw=zone.encode('ascii')
        if len(raw)>63 or b'\0' in raw:raise ValueError('Invalid synthetic type')
        self.u.mem_write(0x8160003c,struct.pack('>I',0x81601000));self.u.mem_write(0x81601000,raw+b'\0');self.u.reg_write(self.r.UC_PPC_REG_31,0x81600000);self.result=None
        self.u.emu_start(0x8014bf7c,0x817ffffc,count=2000,timeout=100000)
        if self.result is None:raise ValueError('Original action budget exhausted')
        return self.result


def verify_actions(dol):
    ref=ActionReference(dol);rows=[]
    for zone in ('safehouse','carlot','customshop','','SAFEHOUSE','CARLOT','Customshop','unknown','safehouse2'):
        expected=zone if zone in ('safehouse','carlot') else 'customshop_requires_ride' if zone=='customshop' else 'none'
        actual=ref.branch(zone)
        if actual!=expected:raise AssertionError((zone,actual,expected))
        rows.append({'input':zone,'original_branch':actual})
    return rows


def check_rejections(rows,gameplay,dol):
    zone=next(i for i,r in enumerate(rows) if r['fields'].get('ZoneType',{}).get('value')=='safehouse' and 'Position' in r['fields'] and '0x2241f4cd' in r['fields'] and r['fields']['0x2241f4cd']['value'].get('raw_hex')!='00000000')
    race=next(i for i,r in enumerate(rows) if 'Position' in r['fields'] and r['fields'].get('0x277566f3',{}).get('value',{}).get('raw_hex') not in (None,'00000000'))
    cases=[]
    for label,index,field,change in (
        ('position_value_differs_from_original',zone,'Position',lambda f:f['value'].__setitem__(0,f['value'][0]+1)),
        ('radius_bytes_disagree_with_source',zone,'Radius',lambda f:f.__setitem__('original_bytes','00000000')),
        ('respawn_key_differs_from_original',zone,'0x2241f4cd',lambda f:f['value'].__setitem__('raw_hex','ffffffff')),
        ('race_key_differs_from_original',race,'0x277566f3',lambda f:f['value'].__setitem__('raw_hex','ffffffff'))):
        damaged=list(rows);damaged[index]=copy.deepcopy(rows[index]);change(damaged[index]['fields'][field])
        try:collect(damaged,gameplay,dol)
        except ValueError:cases.append(label)
        else:raise AssertionError('Accepted corrupted export input: '+label)
    for label,g,d in (('wrong_gameplay_source',b'X'+gameplay[1:],dol),('wrong_dol_source',gameplay,b'X'+dol[1:])):
        try:collect(rows,g,d)
        except ValueError:cases.append(label)
        else:raise AssertionError('Accepted wrong original source')
    return cases


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('attributes','gameplay','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--verify-original',action='store_true')
    p.add_argument('--check-rejections',action='store_true')
    a=p.parse_args();dol=a.dol.read_bytes();gameplay=a.gameplay.read_bytes();attributes=a.attributes.read_bytes()
    if hashlib.sha256(attributes).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected source schema')
    labels=dol_labels(dol);source=GameplayPackages(gameplay,VehicleAttributes(attributes,labels=labels),labels)
    rows=[{'key':key,'name':db.label(key),'package':package,'parent':row['parent'],'fields':db.fields(row)}
          for package,db in source.databases.items() for (_,key),row in db.collections.items()]
    report=collect(rows,gameplay,dol)
    if a.verify_original:report['original_action_branch_cases']=verify_actions(dol)
    if a.check_rejections:report['malformed_inputs_rejected']=check_rejections(rows,gameplay,dol)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('destination_counts','race_entry_count','race_owner_count','independent_original_field_ranges_checked')},indent=2))
