#!/usr/bin/env python3
"""Convert source car exteriors with explicit original-package coverage.

Uses the established KIT00 native renderer adapter and original texture pixel
pipeline. Does not imply car ownership, saved presets, source physics, complete
interiors/damage or original paint/shader behavior. Failed packages are reported,
never replaced with another model or a placeholder texture.
"""
import argparse
import copy
import gzip
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image
from car_traffic_tires import source_car_usage
import build_starter_cars as native

FRONTEND_SHA='adbb364d58f348ee95d2b59e99d0312b1bd8079d77be7bc76bd40461ee2cc9c2'
from build_starter_cars import (ATTR_SHA, PAINT_SOURCE_SHA, CarParts,
    VehicleAttributes, decode_part, sha, texture_hash)


def source_models(exports,candidates,car):
    records=json.loads((exports/'manifest.json').read_text())['records']
    record=next(r for r in records if r['candidate_name']==f'CARS\\{car}\\GEOMETRY.BIN')
    entries=json.loads((candidates/'manifest.json').read_text())['entries']
    source=next(e for e in entries if e['candidate_name']==record['candidate_name'])
    raw=(candidates/source['file']).read_bytes()
    if sha(raw)!=record['source_sha256'] or sha(raw)!=source['sha256']:
        raise ValueError('Original geometry hash mismatch')
    # A rejected driver is explicitly outside the static exterior scope, while
    # a rejected window/body remains a conversion failure (never a hidden hole).
    rejected=[r for r in record['rejected'] if '_DRIVER_' not in r['name']]
    if rejected:raise ValueError('Rejected exterior source part: '+json.dumps(rejected,sort_keys=True))
    directory=exports/f"{source['hash']}-{source['directory_record_offset']}"
    rows=[(p,json.loads(gzip.decompress(p.read_bytes()))) for p in sorted(directory.glob('*.mesh.json.gz'))]
    damage0=any('_KIT00_DAMAGE0_BODY_' in r['name'] for _,r in rows)
    lod=record['selected_offline_lod'];models=[]
    for path,row in rows:
        name=row['name']
        if damage0:
            wanted=(name.startswith(car+'_KIT00_DAMAGE0_') or '_KIT00_FRONT_TIRE_' in name or '_KIT00_FRONT_BRAKE_' in name or '_KIT00_REAR_BRAKE_' in name)
        else:wanted=(name==f'{car}_BASE_{lod}' or '_KIT00_' in name and 'DAMAGE' not in name)
        if not wanted:continue
        class Cache:
            def __init__(self):self.index=0
            def verify(self,descriptor,packet,widths):
                value=row['descriptor_parity_checks'][self.index];self.index+=1
                if sha(packet)!=value['source_sha256']:raise ValueError('Verified geometry descriptor changed')
                return value
        cache=Cache();actual=decode_part(raw,row['source_model_offset'],row['source_model_offset']+row['source_model_bytes'],cache)
        if cache.index!=len(row['descriptor_parity_checks']) or any(json.dumps(actual[k],sort_keys=True)!=json.dumps(row[k],sort_keys=True) for k in actual):
            raise ValueError('Original geometry differs from independently decoded export')
        row['mesh_export_sha256']=sha(path.read_bytes());models.append(row)
    if not models or not any('_BODY_' in r['name'] for r in models):raise ValueError('No complete intact source body')
    bodies=[r for r in models if '_BODY_' in r['name']]
    if len(bodies)==1:
        body_lateral=max(abs(p[1]) for p in bodies[0]['positions'])
        for row in models:
            if 'WINDOW' in row['name'] and min(abs(p[1]) for p in row['positions'])>body_lateral+1:
                raise ValueError('Source part transform/admission unresolved: '+row['name']+' lies outside original body lateral bounds')
    return dict(record,original_directory_entry=source,
        native_selection='KIT00_DAMAGE0 intact exterior' if damage0 else 'KIT00 intact static models',
        omitted_rejected_driver_parts=[r for r in record['rejected'] if '_DRIVER_' in r['name']]),models


def coarse_source_models(exports,candidates,car,base_directory):
    """Use a genuine monolithic coarse body and independently checked wheels.

    Original per-part live LOD selection is NOT asserted by this offline policy.
    In particular no invalid high-LOD window is dropped from a high-LOD body.
    """
    record,body=source_models(exports,candidates,car)
    if record['selected_offline_lod']!='E' or len(body)!=1 or body[0]['name']!=car+'_KIT00_BODY_E':
        raise ValueError('Coarse policy requires exactly one intact original E body')
    # The body must explicitly carry source window coverage and underbody,
    # rather than treating a shell missing glazing as a complete exterior.
    textures={strip['texture_hash'] for strip in body[0]['strips']}
    if f'{texture_hash("WINDOW_MASK"):08x}' not in textures or f'{texture_hash("CARBOTTOM"):08x}' not in textures:
        raise ValueError('Coarse original body has no explicit source window/underbody coverage')
    entries=json.loads((candidates/'manifest.json').read_text())['entries']
    source=next(e for e in entries if e['candidate_name']==record['candidate_name'])
    raw=(candidates/source['file']).read_bytes()
    if sha(raw)!=record['source_sha256']:raise ValueError('Coarse wheel source differs')
    base=next(r for r in json.loads((base_directory/'manifest.json').read_text())['records'] if r['candidate_name']==record['candidate_name'])
    directory=base_directory/f"{source['hash']}-{source['directory_record_offset']}"
    wheels=[]
    for path in sorted(directory.glob('*.mesh.json.gz')):
        row=json.loads(gzip.decompress(path.read_bytes()))
        if row['name'] not in {car+'_KIT00_'+part+'_'+base['selected_offline_lod'] for part in ['FRONT_TIRE','FRONT_BRAKE','REAR_BRAKE']}:continue
        class Cache:
            def __init__(self):self.index=0
            def verify(self,descriptor,packet,widths):
                value=row['descriptor_parity_checks'][self.index];self.index+=1
                if sha(packet)!=value['source_sha256']:raise ValueError('Verified wheel descriptor changed')
                return value
        cache=Cache();actual=decode_part(raw,row['source_model_offset'],row['source_model_offset']+row['source_model_bytes'],cache)
        if cache.index!=len(row['descriptor_parity_checks']) or any(json.dumps(actual[k],sort_keys=True)!=json.dumps(row[k],sort_keys=True) for k in actual):raise ValueError('Original coarse wheel source differs')
        row['mesh_export_sha256']=sha(path.read_bytes());wheels.append(row)
    if sum('_FRONT_TIRE_' in w['name'] for w in wheels)!=1:raise ValueError('Missing original wheel mesh')
    record=dict(record,native_selection='Original complete E body plus source B wheel/brake meshes; native offline LOD adapter',
        selected_body_lod='E',selected_wheel_lod=base['selected_offline_lod'],
        unused_high_detail_rejections=base['rejected'],
        coarse_mesh_manifest_sha256=sha((exports/'manifest.json').read_bytes()),
        wheel_mesh_manifest_sha256=sha((base_directory/'manifest.json').read_bytes()))
    return record,body+wheels


def build(a):
    if a.output.exists():raise ValueError('Use a new output directory; originals and prior conversions are never overwritten')
    attributes=a.attributes.read_bytes();parts_raw=a.carparts.read_bytes()
    if sha(attributes)!=ATTR_SHA:raise ValueError('Expected original USA attributes')
    db=VehicleAttributes(attributes);parts=CarParts(parts_raw)
    if parts.sha256!=PAINT_SOURCE_SHA:raise ValueError('Expected original carpart bank')
    frontend=VehicleAttributes(a.frontend.read_bytes(),dependency=db)
    if frontend.sha256!=FRONTEND_SHA:raise ValueError('Expected original USA frontend attributes')
    palette=parts.part(texture_hash('GLOSS_L1_COLOR01'))
    paint={'name':palette['name'],'key':palette['key'],'source_sha256':parts.sha256,
        'rgba':[parts.value(palette,k) for k in ('RED','GREEN','BLUE')]+[255],'gloss':parts.value(palette,'GLOSS')}
    usage=source_car_usage(parts_raw)
    shared=native.existing_pixels(a.shared_textures)
    geometry=json.loads((a.meshes/'manifest.json').read_text())['records']
    coverage=[];built=[];a.output.mkdir(parents=True)
    for record in geometry:
        car=record['candidate_name'].split('\\')[1]
        mesh_directory=a.meshes
        for alternate in a.alternate_meshes:
            options=json.loads((alternate/'manifest.json').read_text())['records']
            matches=[r for r in options if r['candidate_name']==record['candidate_name']]
            if matches:
                if len(matches)!=1 or matches[0]['source_sha256']!=record['source_sha256']:raise ValueError('Alternate mesh source differs')
                mesh_directory=alternate;record=matches[0];break
        coarse=False
        for alternate in a.coarse_body_meshes:
            options=json.loads((alternate/'manifest.json').read_text())['records']
            matches=[r for r in options if r['candidate_name']==record['candidate_name']]
            if matches:
                if len(matches)!=1 or matches[0]['source_sha256']!=record['source_sha256']:raise ValueError('Coarse mesh source differs')
                mesh_directory=alternate;record=matches[0];coarse=True;break
        status={'id':car,'source_geometry_sha256':record['source_sha256'],
            'source_lod':record['selected_offline_lod'],'source_mesh_manifest_sha256':sha((mesh_directory/'manifest.json').read_bytes()),'source_rejections':record['rejected'],
            'status':'blocked','frontend_collection_key':None,'ecar_collection_key':None}
        try:
            ecar=db.find('ecar',car.lower());status['ecar_collection_key']=f'{ecar["key"]:08x}'
            try:fe=frontend.find('frontend',car.lower())
            except KeyError:fe=None
            native.FE_KEYS[car]=fe['key'] if fe else 0
            status['frontend_collection_key']=f'{native.FE_KEYS[car]:08x}'
            try:
                physical=db.find('pvehicle',car.lower())
                status['player_usable']=db.field_value(physical,'PlayerUsable')
                status['physical_model']=db.field_value(physical,'MODEL')
            except KeyError:status['player_usable']=None
            # Presenting the source model code is preferable to invented display
            # names when original localization has not been bound by the app.
            native.DISPLAY.setdefault(car,car)
            tire_binding=usage.get(car) if usage.get(car,{}).get('usage')==2 else None
            cached=None
            for directory in a.reuse_native:
                scene=directory/car/'scene.json'
                if scene.is_file():
                    candidate=json.loads(scene.read_text())
                    if candidate['source_geometry']['source_sha256']!=record['source_sha256']:raise ValueError('Cached source geometry differs')
                    if candidate['source_geometry']['selected_offline_lod']!=record['selected_offline_lod']:continue
                    if candidate.get('source_traffic_tire_binding')!=tire_binding:continue
                    if sha((directory/car/'body.nfm').read_bytes())!=candidate['body_sha256'] or sha((directory/car/'wheels.nwa').read_bytes())!=candidate['wheel_rig_sha256']:raise ValueError('Cached native body/rig differs')
                    for texture in candidate['textures']:
                        image=Image.open(directory/car/'textures'/(texture['hash']+'.png')).convert('RGBA')
                        if image.size!=(texture['width'],texture['height']) or sha(image.tobytes())!=texture['rgba_sha256']:raise ValueError('Cached texture source pixels differ')
                    cached=directory/car;result=candidate;break
            if cached:shutil.copytree(cached,a.output/car)
            else:
                with tempfile.TemporaryDirectory(prefix='.convert-',dir=a.output) as work:
                    args=copy.copy(a);args.output=Path(work);args.meshes=mesh_directory
                    loader=(lambda exports,candidates,model:coarse_source_models(exports,candidates,model,a.meshes)) if coarse else source_models
                    result=native.build_car(args,car,db,shared,paint,models_loader=loader,traffic_tire=tire_binding)
                    if not 1<result['half_extent']<a.half_extent_limit:raise ValueError('Native extent exceeds explicit renderer bound')
                    shutil.move(str(args.output/car),str(a.output/car))
            result['player_usable']=bool(status.get('player_usable') and status['player_usable']['value'] is True and status.get('physical_model',{}).get('value',{}).get('text')==car)
            result['limitations'] = list(dict.fromkeys(result['limitations'] + ['Native model browser presence is not career ownership or original unlock availability',
                'Offline source LOD is selected for the 3DS asset budget; original per-frame vehicle LOD transitions are not implemented',
                'Rejected driver-only geometry is explicitly omitted where listed; no rejected exterior geometry is hidden']))
            (a.output/car/'scene.json').write_text(json.dumps(result,indent=2)+'\n')
            built.append(result);status.update(status='native_mesh_ready',triangles=result['triangles'],textures=len(result['textures']),half_extent=result['half_extent'])
        except (ValueError,KeyError,IndexError,TypeError,AssertionError) as exc:
            status['reason']=type(exc).__name__+': '+str(exc)
        coverage.append(status)
        (a.output/'coverage.json').write_text(json.dumps({'schema':1,'models':coverage},indent=2)+'\n')
        print(json.dumps(status),flush=True)
    if not built:raise ValueError('No native model could be converted')
    texture_count=native.native_textures(a.output) if a.native_textures else 0
    summary={'schema':1,'attributes_sha256':ATTR_SHA,'frontend_sha256':frontend.sha256,
        'cars':[{k:r[k] for k in ('id','display_name','frontend_collection_key','ecar_collection_key','half_extent','vertices','triangles','body_sha256','wheel_rig_sha256','limitations','player_usable')} for r in built],
        'textures_native':bool(texture_count),'source_rgba_to_native_textures_compared':texture_count}
    summary['native_catalog']=native.pack_catalog(a.output,summary,parts.sha256)
    (a.output/'catalog.json').write_text(json.dumps(summary,indent=2)+'\n')
    coverage_manifest={'schema':1,'original_geometry_packages':len(geometry),'native_models':len(built),
        'attributes_sha256':ATTR_SHA,'frontend_sha256':frontend.sha256,'carparts_sha256':parts.sha256,
        'source_mesh_manifest_sha256':sha((a.meshes/'manifest.json').read_bytes()),
        'native_textures_verified':texture_count,'models':coverage}
    (a.output/'coverage.json').write_text(json.dumps(coverage_manifest,indent=2)+'\n')
    return coverage_manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('meshes','candidates','attributes','carparts','frontend','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--coarse-body-meshes',type=Path,action='append',default=[])
    p.add_argument('--alternate-meshes',type=Path,action='append',default=[])
    p.add_argument('--half-extent-limit',type=float,default=16);p.add_argument('--reuse-native',type=Path,action='append',default=[])
    p.add_argument('--shared-textures',type=Path,action='append',required=True);p.add_argument('--native-textures',action='store_true')
    a=p.parse_args()
    if not 1<a.half_extent_limit<=16:raise ValueError('Explicit native extent bound must be greater than1and at most16metres')
    result=build(a)
    print(json.dumps({k:v for k,v in result.items() if k!='models'},indent=2))
if __name__=='__main__':main()
