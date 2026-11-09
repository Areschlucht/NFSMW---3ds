#!/usr/bin/env python3
"""Pack recovered race references for bounded native access, without unlock rules."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib
from event_type_reference import original_table

MISSING=0xffffffff


def build(catalog, dol, display=None):
    types=dict(original_table(dol))
    events=catalog['race_definition_candidates']
    titles={}
    if display is not None:
        if display['dol_sha256']!=hashlib.sha256(dol).hexdigest() or display['english_sha256']!='fda4935491869ddaa3eba335c3425aa9cbc8fcbd82a58a20f7334ecbbbd8fa4a':raise ValueError('Unexpected display-text provenance')
        for entry in display['events']:
            if entry['event_key'] in titles:raise ValueError('Duplicate display event')
            titles[entry['event_key']]=entry
        if set(titles)!={e['key'] for e in events}:raise ValueError('Display event set differs')
    nodes={};references=[];strings=bytearray(b'\0');string_offsets={'':0};event_rows=[]
    def text(value):
        if not isinstance(value,str) or '\0' in value:raise ValueError('Invalid source string')
        if value not in string_offsets:
            string_offsets[value]=len(strings);strings.extend(value.encode('ascii')+b'\0')
        return string_offsets[value]
    def node(value):
        if value.get('status')=='null':return 0
        if value.get('status')!='resolved':raise ValueError('Unresolved route node')
        key=int(value['key'],16);fields=value.get('spatial_fields',{});mask=0;values=[]
        for bit,name,size in [(1,'Position',3),(2,'Rotation',1),(4,'0x6d9e21ad',3),(8,'Radius',1)]:
            if name in fields:
                mask|=bit;v=fields[name]['value'];parts=[v] if size==1 else v
                if not isinstance(parts,list) or len(parts)!=size or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in parts):raise ValueError('Bad spatial source')
                if struct.pack('>'+str(size)+'f',*parts).hex()!=fields[name]['original_bytes']:raise ValueError('Source float bytes differ')
            else:parts=[0]*size
            values.extend(parts)
        record=struct.pack('<II8f',key,mask,*values)
        if key in nodes and nodes[key]!=record:raise ValueError('Conflicting spatial node')
        nodes[key]=record;return key
    for event in sorted(events,key=lambda e:int(e['key'],16)):
        first=len(references)
        checkpoints=event.get('ordered_checkpoint_refs',{}).get('nodes',[])
        for entry in checkpoints:
            key=node(entry)
            if not key:raise ValueError('Null ordered checkpoint')
            references.append(key)
        def one(field):
            values=event.get(field,{}).get('nodes',[])
            if len(values)>1:raise ValueError('Expected scalar route association')
            return node(values[0]) if values else 0
        start=one('startgrid_ref');finish=one('finishline_ref')
        fields=event['fields'];laps=fields['NumLaps']['value']
        if not isinstance(laps,int) or not 0<=laps<=0xffffffff:raise ValueError('Invalid original lap count')
        def scalar(name):
            value=fields.get(name,{}).get('value','')
            if not isinstance(value,str):raise ValueError('Expected original text')
            return value
        title=''
        if display is not None:
            entry=titles[event['key']]
            if entry['source_id']!=scalar('0xa78403ec'):raise ValueError('Display source ID differs')
            if entry['status']=='matched':title=entry['display_text']
            elif entry['status']!='missing':raise ValueError('Unknown display status')
        row=[int(event['key'],16),text(event['name']),text(scalar('Region')),laps,
             first,len(checkpoints),start,finish,text(scalar('0xf572ede8')),
             text(scalar('0xb70268c0')),text(scalar('0xa78403ec')),types.get(scalar('0x0f6bcde1'),-1)&0xffffffff,text(title),0,0,0]
        event_rows.append(struct.pack('<16I',*row))
    event_bytes=b''.join(event_rows);node_bytes=b''.join(nodes[k] for k in sorted(nodes))
    ref_bytes=struct.pack('<'+str(len(references))+'I',*references)
    eo=128;no=eo+len(event_bytes);ro=no+len(node_bytes);so=ro+len(ref_bytes)
    payload=event_bytes+node_bytes+ref_bytes+strings
    header=bytearray(128)
    struct.pack_into('<4s15I',header,0,b'NRE1',3 if display is not None else 2,128+len(payload),0,len(events),len(nodes),len(references),len(strings),eo,no,ro,so,0,0,0,0)
    provenance=catalog['summary']['source_sha256']
    header[64:96]=bytes.fromhex(provenance['gameplay']);header[96:128]=bytes.fromhex(provenance['dol'])
    result=header+payload;struct.pack_into('<I',result,12,zlib.crc32(result[16:]))
    return bytes(result),{'schema':1,'events':len(events),'nodes':len(nodes),'checkpoint_references':len(references),
        'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),'source_sha256':provenance,'format_version':3 if display is not None else 2,
        'localized_titles':sum(e['status']=='matched' for e in titles.values()),
        'english_sha256':display['english_sha256'] if display is not None else None,
        'limits':['Source definitions include templates/challenges; not a playable event count',
                  'Coordinates/rotation/dimensions stay in source form; absent fields are explicit mask bits',
                  'Movie strings are data references, not automatically executed transitions',
                  'No progression unlocks or field consumer meanings are invented']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--display-text',type=Path);p.add_argument('--dol',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();data,report=build(json.loads(a.catalog.read_text()),a.dol.read_bytes(),json.loads(a.display_text.read_text()) if a.display_text else None)
    if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('Existing pack differs')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if not a.output.exists():a.output.write_bytes(data)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
