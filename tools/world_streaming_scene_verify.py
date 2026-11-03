"""Validate every exported asset through bounded native readers under sanitizers."""
import argparse
import ctypes
import hashlib
import json
import mmap
from pathlib import Path
import struct
import subprocess
import tempfile

from decode_world import decode_model
from nfs_rockport import chunks


def verify_original_geometry(assets,manifest,stream):
    corners=0
    with stream.open('rb') as file:
        with mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as original:
            if hashlib.sha256(original).hexdigest()!=manifest['source_sha256']:
                raise ValueError('Original stream differs from exported asset provenance')
            for record in manifest['models'].values():
                asset=(assets/record['path']).read_bytes()
                start,length=struct.unpack_from('<2I',asset,220);prefix=start%32
                raw=bytes(prefix)+original[start:start+length]
                model=decode_model(raw,prefix,len(raw),allow_triangle_statistic_mismatch=True)
                parts={k:(prefix+a,prefix+b) for k,a,b in chunks(raw[prefix:])}
                a,b=parts[0x80134100];geometry={k:(a+c,a+d) for k,c,d in chunks(raw[a:b])}
                meta=(geometry[0x134800][0]+15)&~15;table=(geometry[0x134801][0]+15)&~15;blob=(geometry[0x134802][0]+31)&~31
                colors=struct.unpack_from('>I',raw,meta+20)[0]
                vo,io,bo,no=struct.unpack_from('<4I',asset,36)
                ni=struct.unpack_from('<I',asset,20)[0]
                if ni!=len(model['faces'])*3:
                    raise ValueError('Export lost original triangle corners')
                for face_index,face in enumerate(model['faces']):
                    for corner_index,corner in enumerate(face['corners']):
                        index=struct.unpack_from('<H',asset,io+(face_index*3+corner_index)*2)[0]
                        position=model['positions'][corner[0]];uv=model['texcoords'][corner[2]]
                        rgba=raw[blob+colors+corner[1]*4:blob+colors+(corner[1]+1)*4]
                        expected=struct.pack('<3f2h4B',*position,*(round(v*4096) for v in uv),*rgba[:3],255)
                        if asset[vo+index*20:vo+(index+1)*20]!=expected or asset[no+index]!=rgba[3]:
                            raise ValueError('Exported indexed attributes differ from original source corner')
                        corners+=1
                for i in range(record['batches']):
                    p=bo+i*36;first,count,texture=struct.unpack_from('<3I',asset,p)
                    if asset[p+12:p+28]!=raw[table+i*16:table+(i+1)*16]:
                        raise ValueError('Original descriptor bytes changed')
                    if any(int(face['texture'],16)!=texture for face in model['faces'][first//3:(first+count)//3]):
                        raise ValueError('Original triangle material ordering changed')
    return corners


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stream',type=Path,help='Also compare every indexed corner/material with the original strict opt-in decoder')
    args=parser.parse_args();manifest=json.loads((args.assets/'manifest.json').read_text())
    root=Path(__file__).resolve().parents[1]
    records=[('M',r) for r in manifest['models'].values()]+[('T',r) for r in manifest['textures'].values()]+[('S',r) for r in manifest['sections']]
    for _,r in records:
        data=(args.assets/r['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=r['sha256']:
            raise ValueError('Exported asset differs from recorded payload SHA256')
    with tempfile.TemporaryDirectory(prefix='world-scene-native-') as temp:
        folder=Path(temp);listing=folder/'assets.txt'
        listing.write_text(''.join(kind+' '+str((args.assets/r['path']).resolve())+'\n' for kind,r in records))
        binary=folder/'test'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off',
                        '-fsanitize=address,undefined','-I'+str(root/'include'),str(root/'source_bmw/world_streaming_scene.c'),
                        str(root/'tests/test_world_streaming_scene.c'),'-lm','-o',str(binary)],check=True)
        result=json.loads(subprocess.check_output([str(binary),str(listing)],text=True))
        # Verify productionfloat36 reconstruction byte-for-byte. This deliberately
        # does not use the rejected GPU-byte-colour reconstruction path.
        library=folder/'scene.so'
        subprocess.run(['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),
                        str(root/'source_bmw/world_streaming_scene.c'),'-lm','-o',str(library)],check=True)
        lib=ctypes.CDLL(str(library));lib.world_streaming_scene_model_open.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
        lib.world_streaming_scene_model_expand.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
        float_cases=0
        for record in manifest['models'].values():
            data=(args.assets/record['path']).read_bytes();source=ctypes.create_string_buffer(data);view=ctypes.create_string_buffer(512)
            if lib.world_streaming_scene_model_open(source,len(data),view):raise ValueError('Native model parse failed')
            nv,ni=struct.unpack_from('<2I',data,16);vo,io=struct.unpack_from('<2I',data,36)
            vertices=ctypes.create_string_buffer(nv*36);indices=ctypes.create_string_buffer(ni*2)
            if lib.world_streaming_scene_model_expand(view,vertices,nv,indices,ni):raise ValueError('Native model expansion failed')
            expected=bytearray()
            for i in range(nv):
                x,y,z,u,v,r,g,b,a=struct.unpack_from('<3f2h4B',data,vo+i*20)
                expected.extend(struct.pack('<9f',x,y,z,u/4096,1-v/4096,r/255,g/255,b/255,1))
            if vertices.raw!=expected or indices.raw!=data[io:io+ni*2]:
                raise ValueError('Productionfloat36 expansion differs from original scalar conversions')
            float_cases+=nv
        result.update(float36_vertex_bit_comparisons=float_cases,cache_capacity=512,
                      manifest_sha256=hashlib.sha256((args.assets/'manifest.json').read_bytes()).hexdigest(),
                      limits='Asset readers/cache validated; full runtime draw integration and originalLOD/texture-provider selection remain separate')
    if args.stream:
        result['original_source_corner_comparisons']=verify_original_geometry(args.assets,manifest,args.stream)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
