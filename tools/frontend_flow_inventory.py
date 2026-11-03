#!/usr/bin/env python3
"""Read-only inventory of original USA GC compressed frontend FEng packages.

No menu order, Alias character limit, memory-card capacity or script semantics is
inferred from resource/string presence. Decoded original FNGs remain private.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
from nfs_rockport import chunks
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

FRONT_SHA='6a815221485bca9ea44c16ab9729255f816167606ba4fdd0873e583ecbbdc1c8'
RELEVANT=('MainMenu.fng','MainMenu_Sub.fng','PressStart.fng','MC_ProfileManager.fng',
          'MC_DeleteProfile.fng','MC_Bootup_GC.fng','MC_Main_GC.fng','MC_List.fng')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def frontend_jdlz(raw):
    """Same bounded backref layout as nfs_jdlz; record up to3unused tailbytes.

    Actual frontend packets sometimes finish with3nonzero flag bytes. These
    bytes are retained in the report, not interpreted or silently truncated.
    """
    if len(raw)<16 or raw[:8]!=b'JDLZ\x02\x10\0\0':raise ValueError('JDLZ header')
    size,packed=struct.unpack_from('<II',raw,8)
    if not 1<=size<=8*1024*1024 or packed!=len(raw):raise ValueError('JDLZ size')
    output=bytearray();position=16;flags1=flags2=1
    def byte():
        nonlocal position
        if position>=len(raw):raise ValueError('Truncated JDLZ')
        value=raw[position];position+=1;return value
    while len(output)<size:
        if flags1==1:flags1=byte()|256
        if flags2==1:flags2=byte()|256
        if flags1&1:
            a,b=byte(),byte()
            if flags2&1:length=(((a&0xf0)<<4)|b)+3;distance=(a&15)+1
            else:length=(a&31)+3;distance=(((a&0xe0)<<3)|b)+17
            if distance>len(output) or length>size-len(output):raise ValueError('JDLZ backref')
            for _ in range(length):output.append(output[-distance])
            flags2>>=1
        else:output.append(byte())
        flags1>>=1
    trailer=raw[position:]
    if len(trailer)>3:raise ValueError('Unexpected JDLZ trailer length')
    return bytes(output),trailer


def package_info(raw):
    if len(raw)<48 or raw[:4]!=b'FEn\xe7' or struct.unpack_from('<I',raw,4)[0]!=len(raw)-8:
        raise ValueError('Invalid FEng root')
    at=8;records=[]
    while at<len(raw):
        if at+8>len(raw):raise ValueError('Truncated FEng child')
        tag=raw[at:at+4];size=struct.unpack_from('<I',raw,at+4)[0];end=at+8+size
        if end>len(raw):raise ValueError('FEng child outside root')
        label=bytes((*tag[:3],tag[3]&0x7f)).decode('ascii')
        records.append({'tag':label,'tag_hex':tag.hex(),'offset':at,'bytes':size});at=end
    if not records or records[0]['tag']!='PkHd':raise ValueError('Missing PkHd')
    header_end=16+records[0]['bytes']
    end=raw.find(b'\0',40,header_end)
    if end<0:raise ValueError('Unterminated package name')
    name=raw[40:end].decode('ascii')
    if not re.fullmatch(r'[A-Za-z0-9_]+\.fng',name):raise ValueError('Unexpected package name')
    strings=[m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{4,}',raw)]
    resources=sorted({s for s in strings if re.fullmatch(r'[A-Za-z0-9_ ()-]+\.(?:tga|ffn)',s,re.I)})
    return {'name':name,'decoded_bytes':len(raw),'decoded_sha256':digest(raw),
            'top_level_chunk_counts':dict(Counter(r['tag'] for r in records)),
            'resource_names':resources}


def inventory(frontend,dol,output_directory=None):
    raw=frontend.read_bytes();image_raw=dol.read_bytes()
    if digest(raw)!=FRONT_SHA or digest(image_raw)!=DOL_SHA256:raise ValueError('Unexpected original USA sources')
    image=DolImage(image_raw);packages=[];names=set()
    for kind,start,end in chunks(raw):
        if kind!=0x30210:continue
        if end-start<24:raise ValueError('Short packed frontend entry')
        key=struct.unpack_from('<I',raw,start)[0];magic=raw[start+4:start+8]
        declared,packed=struct.unpack_from('<II',raw,start+12)
        if magic==b'JDLZ':size=packed
        elif magic==b'HUFF':size=packed+16
        else:raise ValueError('Unknown frontend compression')
        if size<16 or start+4+size>end:raise ValueError('Compressed entry range')
        encoded=raw[start+4:start+4+size]
        if any(raw[start+4+size:end]):raise ValueError('Nonzero outer alignment')
        if magic==b'JDLZ':decoded,trailer=frontend_jdlz(encoded)
        else:
            from nfs_huff_reference import decode
            decoded=decode(encoded,declared,instruction_limit=20000000,timeout_us=10000000);trailer=b''
        info=package_info(decoded)
        if len(decoded)!=declared or info['name'] in names:raise ValueError('Bad decoded size/duplicate name')
        names.add(info['name']);info.update(source_chunk_offset=start-8,source_key=f'{key:08x}',
            compressed_bytes=size,compression=magic.decode(),compressed_sha256=digest(encoded),
            unused_jdlz_trailer_hex=trailer.hex())
        packages.append(info)
        if output_directory:
            output_directory.mkdir(parents=True,exist_ok=True);path=output_directory/info['name']
            if path.exists() and path.read_bytes()!=decoded:raise ValueError('Existing FNG differs')
            if not path.exists():
                with path.open('xb') as f:f.write(decoded)
    selected={p['name']:p for p in packages if p['name'] in RELEVANT}
    if set(selected)!=set(RELEVANT):raise ValueError('Expected original menus missing')
    references=image.strings(r'(?i)(PMCreateNew|PMLoad|PMDelete|PMSave|PMPopDelete|CreateUIProfileManager|CreateUIDeleteProfile|MainCareer|MainQuickRace|MainCustomize|MainOptions|MainProfileManager|PressStart\.fng|MainMenu\.fng)')
    for r in references:r['address']=f'{r["address"]:08x}'
    return {'schema':1,'source_sha256':{'frontend':FRONT_SHA,'dol':DOL_SHA256},
        'package_count':len(packages),'compression_counts':dict(Counter(p['compression'] for p in packages)),
        'packages':packages,'selected_original_menus':selected,'dol_flow_strings':references,
        'limits':['String/resource presence does not establish reachable GameCube buttons or menu order',
            'PC_key resources occur in the GameCube archive and do not imply PC flows should be ported',
            'Alias maximum count/length/character set and initial menu selection remain unproved',
            'No original script interpreter or rendering/timing reconstruction is claimed']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frontend','dol','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--decoded-directory',type=Path)
    p.add_argument('--art',type=Path)
    a=p.parse_args();r=inventory(a.frontend,a.dol,a.decoded_directory)
    if a.art:
        from nfs_tpk import parse
        art=a.art.read_bytes()
        if digest(art)!='bc3c7c33d8b2620deaa5506da8c43c7cecd6fa5ea3d3f369d8baf4bbee753920':
            raise ValueError('Unexpected original FRONTB art source')
        wanted={name.rsplit('.',1)[0].upper() for p in r['selected_original_menus'].values() for name in p['resource_names']}
        r['source_art_sha256']=digest(art)
        r['matched_source_art']=[{'name':t['name'],'hash':t['hash'],'width':t['width'],'height':t['height'],'rgba_sha256':digest(t['rgba'])} for t in parse(art) if t['name'].upper() in wanted]
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'packages':r['package_count'],'compression_counts':r['compression_counts'],
                     'selected_menus':list(r['selected_original_menus'])}))
