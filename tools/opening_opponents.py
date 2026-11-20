#!/usr/bin/env python3
"""Recover true opening opponent identities and explicit original spawn refs."""
import argparse,hashlib,json,math,struct,zlib
from pathlib import Path
from gameplay_packages import GameplayPackages,dol_labels
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash

GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'
ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
PRESET_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'
EVENTS=(0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a)

def sha(b):return hashlib.sha256(b).hexdigest()
def verify_pose_window(dol,positions):
    from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_MEM_WRITE
    from unicorn import ppc_const as r
    image=DolImage(dol);u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN);u.mem_map(0x80000000,0x1800000);u.mem_map(0x60000000,0x1000);u.mem_map(0x70000000,0x10000)
    for section in image.sections:u.mem_write(section.address,dol[section.offset:section.offset+section.size])
    def write(cpu,access,address,size,value,data):
        if not 0x70000000<=address<=0x70010000-size:raise ValueError('Original pose write escaped output stack')
    u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(r.UC_PPC_REG_MSR,0x2000)
    for p in positions:
        u.mem_write(0x60000000,struct.pack('>3f',*p));u.reg_write(r.UC_PPC_REG_30,0x60000000);u.reg_write(r.UC_PPC_REG_1,0x70008000)
        u.emu_start(0x801c2be0,0x801c2c04,count=32,timeout=100000)
        actual=bytes(u.mem_read(0x700083d0,12));expected=struct.pack('>3f',-p[1],p[2],p[0])
        if actual!=expected:raise AssertionError('Unchanged original opponent pose basis differs')
    return len(positions)
def build(a):
    raw=a.gameplay.read_bytes();attributes=a.attributes.read_bytes();dol=a.dol.read_bytes();preset_raw=a.presets.read_bytes()
    if sha(raw)!=GAMEPLAY_SHA or sha(attributes)!=ATTR_SHA or sha(dol)!=DOL_SHA256 or sha(preset_raw)!=PRESET_SHA:raise ValueError('Pinned USA sources differ')
    labels=[*dol_labels(dol),'Opponents','PresetRide','Position','Rotation']
    schema=VehicleAttributes(attributes,labels=labels);gp=GameplayPackages(raw,schema,labels)
    rows={}
    for db in gp.databases.values():
        for (_,key),row in db.collections.items():
            if key in rows:raise ValueError('Ambiguous source collection')
            rows[key]=(db,row)
    def fields(key):
        db,row=rows[key];return {f['field_key']:f for f in db.fields(row).values()}
    def get(f,name,default=None):return f.get(vlt_hash(name),{}).get('value',default)
    def ref(f,key):
        v=f.get(key,{}).get('value',{'raw_hex':'00000000'});return int(v['raw_hex'],16)
    def checked(f):
        original=bytes.fromhex(f['original_bytes']);at=f['file_offset']
        if f['source_sha256']!=GAMEPLAY_SHA or raw[at:at+len(original)]!=original:raise ValueError('Original field byte provenance differs')
        return f
    preset_manifest=json.loads(a.preset_manifest.read_text())
    if preset_manifest['source_sha256']!=PRESET_SHA:raise ValueError('Preset manifest source differs')
    presets={r['preset_name']:r for r in preset_manifest['records']}
    actors=[];events=[];evidence=[];positions=[];strings=bytearray(b'\0');lookup={'':0}
    def string(s):
        if s not in lookup:lookup[s]=len(strings);strings.extend(s.encode('ascii')+b'\0')
        return lookup[s]
    for event in EVENTS:
        ef=fields(event);owner=checked(ef[vlt_hash('Opponents')]);keys=[int(v['raw_hex'],16) for v in owner['value']['values']]
        if not 1<=len(keys)<=3:raise ValueError('Unexpected original opponent count')
        first=len(actors)
        for key in keys:
            f=fields(key);preset=checked(f[vlt_hash('PresetRide')])['value'];pr=presets[preset];at=pr['file_offset']
            # The packed record itself owns the literal model/preset pair.
            chunk=preset_raw[at:at+656]
            if chunk[8:40].split(b'\0',1)[0].decode('ascii')!=pr['model_name'] or chunk[40:72].split(b'\0',1)[0].decode('ascii')!=preset:raise ValueError('Original preset identity bytes differ')
            spawn=ref(f,0xfb84be75);position=[0.,0.,0.];rotation=0.;spatial={}
            if spawn:
                sf=fields(spawn);pf=checked(sf[vlt_hash('Position')]);rf=checked(sf[vlt_hash('Rotation')]);position=pf['value'];rotation=rf['value']
                if bytes.fromhex(pf['original_bytes'])!=struct.pack('>3f',*position) or bytes.fromhex(rf['original_bytes'])!=struct.pack('>f',rotation):raise ValueError('Source pose scalar bytes differ')
                spatial={'position':pf,'rotation':rf}
                positions.append(position)
            if not all(math.isfinite(v) for v in (*position,rotation)):raise ValueError('Nonfinite source pose')
            model=pr['model_name'];ecar=schema.find('ecar',model.lower())['key']
            actors.append(struct.pack('<6I4f6I',key,spawn,ecar,string(model),string(preset),bool(spawn),*position,rotation,0,0,0,0,0,0))
            evidence.append({'event':f'{event:08x}','actor':f'{key:08x}','opponents':owner,'preset_field':f[vlt_hash('PresetRide')],
                'preset_record':pr,'opponent_fields':f,'spawn_ref':checked(f[0xfb84be75]),'explicit_spawn':bool(spawn),'spatial':spatial,
                'null_ref_policy':'native start-grid adapter; source road-grid placement still unported' if not spawn else ''})
        events.append(struct.pack('<4I',event,first,len(keys),0))
    data=bytearray(128)+b''.join(events)+b''.join(actors)+strings
    struct.pack_into('<4s7I',data,0,b'NRO1',1,len(data),0,5,128,208,len(actors))
    data[32:64]=bytes.fromhex(GAMEPLAY_SHA);data[64:96]=bytes.fromhex(ATTR_SHA);data[96:128]=bytes.fromhex(PRESET_SHA)
    # Strings shape is inferred from fixed event/actor record counts.
    struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    a.output.mkdir(parents=True,exist_ok=True);out=a.output/'opening-opponents.nro'
    if out.exists() and out.read_bytes()!=data:raise ValueError('Existing native packet differs')
    out.write_bytes(data)
    im=DolImage(dol)
    pose_cases=verify_pose_window(dol,positions+[[0.,0.,0.],[-0.,-0.,-0.],[1.,-2.,3.],[-8192.,16384.,-32768.]]) if a.verify_original else 0
    report={'schema':1,'bytes':len(data),'sha256':sha(data),'events':len(events),'actors':len(actors),'source_fields':evidence,'original_pose_cases':pose_cases,
      'consumer_windows':[{'start':f'{x:08x}','end':f'{y:08x}','sha256':sha(im.read(x,y-x))} for x,y in ((0x801c2a24,0x801c2a98),(0x801c2bb8,0x801c2c50),(0x801c2c50,0x801c2d20))],
      'limits':['True original event/opponent/preset/model identities','Explicit nonzero FB84BE75 is consumed as Position/Rotation; source->native(-Y,Z,X)',
       'Null source refs use original road navigator at source7-unit spacing plus bounds-derived lateral placement; native grid is an adapter, not recovered original positions',
       'Original source preset kits/rims/vinyl and AI behavior are not implied by native model availability']}
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'events':5,'actors':len(actors),'bytes':len(data),'sha256':sha(data)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('gameplay','attributes','dol','presets','preset-manifest','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--verify-original',action='store_true')
    build(p.parse_args())
