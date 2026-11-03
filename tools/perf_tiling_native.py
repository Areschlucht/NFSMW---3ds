#!/usr/bin/env python3
"""Verify the actual portable streamed upload C helper against tex3ds corpus."""
import ctypes as c
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image
from perf_tiling import tiled_rgba8

def main():
    root=Path(__file__).resolve().parent.parent;research=Path('/workspace/port-research/hardware-optimization/tiling')
    report=json.loads((research/'validation.json').read_text());rows=[]
    with tempfile.TemporaryDirectory(prefix='mw-tiling-native-') as temp:
        lib=Path(temp)/'texture.so';source=root/'source_rockport/streamed_world_texture.c'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(source),'-o',str(lib)],check=True)
        dll=c.CDLL(str(lib));function=dll.streamed_world_texture_rgba8
        function.argtypes=[c.POINTER(c.c_uint8),c.c_size_t,c.POINTER(c.c_uint8),c.c_uint,c.c_uint,c.c_uint,c.c_uint,c.c_bool];function.restype=c.c_bool
        for row in report['cases']:
            name=row['name'];width=row['width'];height=row['height'];size=width*height*4
            effective=Image.open(research/(name+'.png')).convert('RGBA').tobytes()
            if 'source_name' in row:
                rgba=(Path('/workspace/port-research/world-streaming/scene-native/textures')/row['source_name']).read_bytes()[128:];alpha=row['alpha'];blend=row['blend']
            else:rgba=effective;alpha=1;blend=0
            source_buffer=(c.c_uint8*size).from_buffer_copy(rgba)
            golden=(research/(name+'.raw')).read_bytes()[4:]
            results={}
            for zero in (True,False):
                buffer=(c.c_uint8*(size+32))(*([0xa7]*(size+32)));out=c.cast(c.byref(buffer,16),c.POINTER(c.c_uint8))
                assert function(out,size,source_buffer,width,height,alpha,blend,zero)
                assert bytes(buffer[:16])==bytes([0xa7])*16 and bytes(buffer[size+16:])==bytes([0xa7])*16
                actual=bytes(buffer[16:size+16]);expected=tiled_rgba8(effective,width,height,zero_transparent_rgb=zero)
                assert actual==expected and bytes(source_buffer)==rgba
                if zero:assert actual==golden
                results['reference_zero_rgb' if zero else 'production_preserve_rgb']=dict(exact_policy_bytes=True,tex3ds_changed_bytes=sum(a!=b for a,b in zip(actual,golden)),gpu_sha256=hashlib.sha256(actual).hexdigest())
            rows.append(dict(name=name,**results))
        sentinel=(c.c_uint8*256)(*([0xa7]*256));original=bytes(sentinel)
        src=(c.c_uint8*256)()
        for width,height,blend,capacity in ((8,8,0,255),(7,8,0,256),(8,9,0,256),(1025,8,0,256),(8,8,3,256)):
            assert not function(sentinel,capacity,src,width,height,1,blend,False)
            assert bytes(sentinel)==original
        assert not function(None,256,src,8,8,1,0,False)
        assert not function(sentinel,256,None,8,8,1,0,False)
    result=dict(cases=len(rows),gpu_bytes_compared_per_policy=sum(r['gpu_bytes'] for r in report['cases']),
                actual_c_reference_policy_all_tex3ds_bytes_exact=True,
                actual_c_production_policy_all_source_preserving_bytes_exact=True,
                production_tex3ds_changed_bytes=sum(r['production_preserve_rgb']['tex3ds_changed_bytes'] for r in rows),
                bounds_guards_and_source_immutability_passed=True,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rows=rows)
    (research/'native-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
