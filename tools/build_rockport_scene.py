#!/usr/bin/env python3
"""Convert original TRN meshes for a bounded Rockport driving prototype."""
import argparse
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from PIL import Image
from decode_world import decode
from nfs_rockport import decode as decode_index
from nfs_tpk import parse as parse_textures, chunks
from world_instances import catalog_files, read_instances, place_instance
from world_materials import world_rgba


def sector_samples(data, sections, selected, base_id=141):
    """Slice complete indexed sectors without admitting intervening sections."""
    lookup = {s['id']:s for s in sections}
    if not selected or len(set(selected)) != len(selected):
        raise ValueError('Empty or duplicate sector selection')
    if base_id not in lookup or any(sid not in lookup for sid in selected):
        raise ValueError('Unknown selected/base sector')
    base = lookup[base_id]['offset']
    result = []
    for sid in sorted(selected):
        section = lookup[sid]
        start = section['offset'] - base
        end = start + section['bytes']
        if start < 0 or section['bytes'] <= 0 or end > len(data):
            raise ValueError(f'World sample lacks complete selected sector {sid}')
        if start % 2048:
            raise ValueError('Sector slice would change native chunk alignment')
        result.append((sid, start, data[start:end]))
    return result


def world_samples(sources, sections, selected):
    """Resolve sectors across separately supplied original archive ranges."""
    if not selected or len(set(selected)) != len(selected):
        raise ValueError('Empty or duplicate sector selection')
    lookup = {s['id']:s for s in sections}
    if any(base not in lookup for base, _ in sources) or any(sid not in lookup for sid in selected):
        raise ValueError('Unknown selected/base sector')
    result = []
    for sid in sorted(selected):
        candidates = []
        for base, data in sources:
            start = lookup[sid]['offset'] - lookup[base]['offset']
            if start >= 0 and start + lookup[sid]['bytes'] <= len(data):
                candidates.append(sector_samples(data, sections, [sid], base)[0][2])
        if not candidates:
            raise ValueError(f'World samples lack complete selected sector {sid}')
        if any(c != candidates[0] for c in candidates[1:]):
            raise ValueError(f'Conflicting source bytes for sector {sid}')
        result.append((sid, lookup[sid]['offset'], candidates[0]))
    return result


def recover_textures(paths, needed):
    found = {}
    for path in paths:
        data = path.read_bytes(); at = 0
        while at + 8 <= len(data):
            kind, size = struct.unpack_from('<II', data, at); end = at + 8 + size
            if end > len(data): break  # A supplied prefix intentionally ends inside a package.
            if kind == 0xb3300000:
                packet = data[at:end]
                parts = {k:(s,e) for k,s,e in chunks(packet,8,len(packet))}
                h,he = parts[0xb3310000]
                headers = {k:(s,e) for k,s,e in chunks(packet,h+8,he)}
                ks,ke = headers[0x33310002]
                keys = {f'{struct.unpack_from("<I",packet,p)[0]:08x}' for p in range(ks+8,ke,8)}
                if (keys & needed) - found.keys():
                    for texture in parse_textures(packet,wanted_hashes=needed-found.keys()):
                        if texture['hash'] in needed and texture['hash'] not in found:
                            found[texture['hash']] = texture
            at = end
    return found


def build(args):
    if not math.isfinite(args.cell_size) or args.cell_size < 0: raise ValueError('Invalid spatial cell size')
    if not math.isfinite(args.scenery_radius) or not 0 < args.scenery_radius <= 500 or not 0 <= args.scenery_triangles <= 50000 or not 1 <= args.scenery_textures <= 128:
        raise ValueError('Invalid scenery radius/triangle budget')
    index = decode_index(args.index.read_bytes())
    raw_world = args.world.read_bytes()
    selected = [*range(141,149), *args.extra_sector]
    sources = [(141, raw_world)]
    source_manifest = [dict(base_sector=141, name=args.world.name, sha256=hashlib.sha256(raw_world).hexdigest())]
    for base, path in args.world_range:
        data = Path(path).read_bytes()
        sources.append((int(base), data))
        source_manifest.append(dict(base_sector=int(base), name=Path(path).name, sha256=hashlib.sha256(data).hexdigest()))
    samples = world_samples(sources, index['sections'], selected)
    models, rejected, instances = [], [], []
    for sid, offset, data in samples:
        decoded, bad = decode(data)
        if bad or not decoded:
            raise ValueError(f'Selected sector {sid} decoding failed: {bad}')
        models.extend(decoded)
        for instance in read_instances(data):
            instances.append(dict(instance, offset=instance['offset']+offset, sector=sid))
    identity = (1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
    if any(tuple(m['matrix']) != identity for m in models):
        raise ValueError('Selected TRN model requires unresolved placement transform')
    needed = {f['texture'] for m in models for f in m['faces']}
    scenery = []; scenery_skipped = {}; catalog_rejected = []
    if args.scenery_bundle:
        catalog, catalog_rejected = catalog_files(args.scenery_bundle)
        # Preserve a bounded workload around the existing starting position.
        # The center only selects instances; it does not set their positions.
        center = (376.55, 2434.42)
        instances = [i for i in instances if not i['name'].startswith('TRN_')]
        def distance(i):
            b=i['bounds'];return math.hypot((b[0]+b[3])/2-center[0],(b[1]+b[4])/2-center[1])
        triangles = 0
        for instance in sorted(instances,key=distance):
            if distance(instance)>args.scenery_radius:continue
            if args.free_drive and 'TrackBarrier' in instance['name']:
                scenery_skipped['race_barrier']=scenery_skipped.get('race_barrier',0)+1;continue
            model=place_instance(instance,catalog)
            reason=None
            if model is None:reason='missing_model_or_bounds_mismatch'
            else:
                keys={f['texture'] for f in model['faces']}
                if len(needed|keys)>args.scenery_textures:reason='texture_budget'
                elif triangles+len(model['faces'])>args.scenery_triangles:reason='triangle_budget'
            if reason:
                scenery_skipped[reason]=scenery_skipped.get(reason,0)+1;continue
            needed|=keys;triangles+=len(model['faces']);models.append(model);scenery.append(model)
    if len(needed) > args.scenery_textures: raise ValueError('Too many texture references')
    textures = recover_textures(args.texture_bundle, needed)
    if args.complete_scenery:
        incomplete=[m for m in scenery if any(f['texture'] not in textures for f in m['faces'])]
        removed={id(m) for m in incomplete}
        models=[m for m in models if id(m) not in removed]
        scenery=[m for m in scenery if id(m) not in removed]
        scenery_skipped['missing_texture']=len(incomplete)
        needed={f['texture'] for m in models for f in m['faces']}
        if needed-textures.keys():raise ValueError('Required road/terrain textures are unavailable')
    out = args.output; out.mkdir(parents=True,exist_ok=True)
    texout = out/'textures'; texout.mkdir(exist_ok=True)
    records = []; manifest = []
    for key in sorted(needed):
        t = textures.get(key)
        if t:
            rgba,alpha_policy=world_rgba(t)
            image = Image.frombytes('RGBA',(t['width'],t['height']),rgba)
            image.thumbnail((128,128),Image.Resampling.LANCZOS)
        else:
            image = Image.new('RGBA',(8,8),(155,155,155,255))
            alpha_policy='missing texture placeholder'
        hist = image.getchannel('A').histogram()
        flags = bool(sum(hist[1:255])) | (bool(sum(hist[:255])) << 1)
        if t and t['blend_mode'] in (1,2): flags |= 1
        if t and t['blend_mode'] == 2: flags |= 4
        image.save(texout/(key+'.png'))
        records.append((int(key,16),image.width,image.height,flags))
        manifest.append(dict(hash=key,name=t['name'] if t else 'UNRESOLVED',missing=t is None,width=image.width,height=image.height,flags=flags,
                             alpha_test_mode=t['alpha_test_mode'] if t else None,blend_mode=t['blend_mode'] if t else None,
                             alpha_policy=alpha_policy,source_rgba_sha256=hashlib.sha256(t['rgba']).hexdigest() if t else None))
    groups = {}; ground = []; first_road = []
    for m in models:
        road = m['name'].startswith('TRN_') and '_ROAD_' in m['name']
        for face in m['faces']:
            points = [m['positions'][c[0]] for c in face['corners']]
            pts = [(p[0],p[2],-p[1]) for p in points]
            u = [pts[1][i]-pts[0][i] for i in range(3)]; v = [pts[2][i]-pts[0][i] for i in range(3)]
            normal = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            length = math.sqrt(sum(n*n for n in normal))
            if length < 1e-8: continue
            normal = [n/length for n in normal]
            cell = (math.floor(sum(p[0] for p in pts)/3/args.cell_size),math.floor(sum(p[2] for p in pts)/3/args.cell_size)) if args.cell_size else (0,0)
            group = groups.setdefault((face['texture'],*cell),[])
            for p,c in zip(pts,face['corners']): group.append([*p,*normal,*m['texcoords'][c[2]],*m['colors'][c[1]]])
            if road and abs(normal[1]) > .3:
                ground.append(pts)
                if m['name'].startswith('TRN_CT_ROAD_COLONIAL_01_CHOP_A1_R0'): first_road.append(pts)
    vertices = [v for g in groups.values() for v in g]
    low = [min(v[a] for v in vertices) for a in range(3)]; high = [max(v[a] for v in vertices) for a in range(3)]
    origin = [(a+b)/2 for a,b in zip(low,high)]; scale = 2/max(b-a for a,b in zip(low,high))
    def relative(p): return [p[a]-origin[a] for a in range(3)]
    def area(t): return abs((t[1][0]-t[0][0])*(t[2][2]-t[0][2])-(t[1][2]-t[0][2])*(t[2][0]-t[0][0]))
    spawn_tri = max(first_road,key=area)
    spawn = [sum(p[a] for p in spawn_tri)/3 for a in range(3)]
    nodes = index['road_network']['nodes']; segments = index['road_network']['segments']
    a,b = min(segments,key=lambda edge:sum((((nodes[edge[0]][2]+nodes[edge[1]][2])/2-spawn[0])**2,
                                         ((nodes[edge[0]][0]+nodes[edge[1]][0])/2-spawn[2])**2)))
    heading = math.atan2(nodes[b][2]-nodes[a][2],nodes[b][0]-nodes[a][0])
    spawn_selection=None
    if args.center_spawn:
        from road_spawn import choose_spawn
        spawn,heading,spawn_selection=choose_spawn(spawn,index['road_network'],ground)
    lookup = {f'{t[0]:08x}':i for i,t in enumerate(records)}
    batches = []; packed_vertices = []
    for key,group in sorted(groups.items()):
        batches.append((len(packed_vertices),len(group),lookup[key[0]],0))
        for v in group: packed_vertices.append([*(x*scale for x in relative(v[:3])),*v[3:]])
    if len(batches)>2048: raise ValueError('Spatial partition exceeds the runtime batch limit')
    payload = b''.join(struct.pack('<4I',*t) for t in records)
    payload += b''.join(struct.pack('<4I',*b) for b in batches)
    payload += b''.join(struct.pack('<12f',*v) for v in packed_vertices)
    header = struct.pack('<4s7I',b'NFM1',2,len(packed_vertices),len(batches),len(records),len(payload),zlib.crc32(payload),0)
    (out/'world.nfm').write_bytes(header+payload)
    contact = b''.join(struct.pack('<9f',*(v for p in t for v in relative(p))) for t in ground)
    # NRD1: 16-byte fixed header, scale/car half extent, origin/spawn/heading,
    # followed by 12 reserved bytes and original road triangles in local meters.
    config = struct.pack('<4sIII9fIII',b'NRD1',1,len(ground),zlib.crc32(contact),scale,4.53857421875/2,
                         *origin,*relative(spawn),heading,0,0,0)
    assert len(config)==64
    (out/'road.nrd').write_bytes(config+contact)
    report = dict(sectors=sorted(selected),models=[dict(name=m['name'],triangles=len(m['faces'])) for m in models],
                  textures=manifest,vertices=len(packed_vertices),triangles=len(packed_vertices)//3,ground_triangles=len(ground),
                  origin=origin,scale=scale,spawn_source_world=spawn,spawn_local=relative(spawn),heading=heading,
                  spawn_selection=spawn_selection,
                  world_sha256=hashlib.sha256(args.world.read_bytes()).hexdigest(),rejected=rejected,
                  world_sources=source_manifest,
                  scenery_instances=[dict(name=m['instance_name'],hash=m['hash'],bounds_error=m['instance_bounds_error']) for m in scenery],
                  scenery_skipped=scenery_skipped,catalog_rejected=catalog_rejected,
                  scenery_radius=args.scenery_radius,texture_budget=args.scenery_textures,cell_size=args.cell_size,batches=len(batches),
                  free_drive=args.free_drive,complete_scenery=args.complete_scenery,
                  vertex_color='Original RGB; source alpha/material byte remains uninterpreted and is not used as opacity',
                  limitations='Original TRN meshes and validated nearby scenery instances; wheels, full original materials/engine/physics unresolved. Contact uses road render triangles; scenery has no collision.')
    (out/'scene.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(models)} original meshes ({len(scenery)} scenery instances); {report["triangles"]} triangles; {len(ground)} road-contact triangles; {len(textures)}/{len(needed)} recovered textures')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('world',type=Path);p.add_argument('index',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--texture-bundle',type=Path,action='append',required=True)
    p.add_argument('--scenery-bundle',type=Path,action='append',default=[])
    p.add_argument('--cell-size',type=float,default=0,help='Partition world triangles into spatial/material groups for conservative view culling')
    p.add_argument('--scenery-radius',type=float,default=180)
    p.add_argument('--scenery-triangles',type=int,default=16000)
    p.add_argument('--scenery-textures',type=int,default=64)
    p.add_argument('--free-drive',action='store_true',help='Omit named race barriers while their activation rules are unresolved')
    p.add_argument('--complete-scenery',action='store_true',help='Omit added scenery models whose textures are unavailable')
    p.add_argument('--center-spawn',action='store_true',help='Start on a supported original navigation centerline')
    p.add_argument('--extra-sector',type=int,action='append',default=[],help='Add a complete indexed sector from the same world sample; every model must validate')
    p.add_argument('--world-range',nargs=2,action='append',default=[],metavar=('FIRST_SECTOR','FILE'),help='Additional original range beginning at an indexed sector')
    build(p.parse_args())
