#!/usr/bin/env python3
"""Build a native 400x240 frontend backdrop from verified original-art NUI2.

The 3DS composition is an adaptation; it does not claim recovered GC/DS layouts.
Original fonts/logo and source-art provenance remain identifiable. No SDK needed.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
from PIL import Image

NUI_SHA='b8bee03d7491f54c0f8854c1bfea1bfdc3056540d518075bc26661530d0e4be2'
WIDTH,HEIGHT=400,240


def build(source):
    if hashlib.sha256(source).hexdigest()!=NUI_SHA:raise ValueError('Unexpected validated original-art NUI2')
    if source[:4]!=b'NUI2':raise ValueError('Missing NUI2')
    version,size,crc,count,tc,font,title,logo,bg,tw,th=struct.unpack_from('<11I',source,4)
    if (version,size,tc,tw,th)!=(2,len(source),37,256,160) or zlib.crc32(source[48:])!=crc:
        raise ValueError('NUI2 header/CRC differs')
    if not 0<count<=256 or font!=48+(count+tc)*12 or title!=font+65536 or logo!=title+40960 or bg!=logo+65536 or len(source)!=bg+320*240*2:
        raise ValueError('NUI2 layout differs')
    glyphs=source[48:48+count*12];alpha=source[font:font+65536];original_logo=source[logo:logo+65536]
    rgb=bytearray(320*240*3)
    for y in range(240):
        for x in range(320):
            value=struct.unpack_from('<H',source,bg+(x*240+239-y)*2)[0]
            rgb[(y*320+x)*3:(y*320+x)*3+3]=bytes(((value>>11)*255//31,((value>>5)&63)*255//63,(value&31)*255//31))
    image=Image.frombytes('RGB',(320,240),bytes(rgb)).resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    pixels=image.tobytes();background=bytearray(WIDTH*HEIGHT*2)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r,g,b=pixels[(y*WIDTH+x)*3:(y*WIDTH+x)*3+3]
            struct.pack_into('<H',background,(x*HEIGHT+HEIGHT-1-y)*2,((r>>3)<<11)|((g>>2)<<5)|(b>>3))
    go=96;fo=go+len(glyphs);lo=fo+len(alpha);bo=lo+len(original_logo)
    data=bytearray(96)+glyphs+alpha+original_logo+background
    struct.pack_into('<4s10I',data,0,b'NUT1',1,len(data),zlib.crc32(data[96:]),WIDTH,HEIGHT,count,go,fo,lo,bo)
    data[64:96]=bytes.fromhex(NUI_SHA)
    return bytes(data),{'schema':1,'format':'NUT1','bytes':len(data),'source_nui_sha256':NUI_SHA,
        'glyphs':count,'width':WIDTH,'height':HEIGHT,'gpu_texture_bytes':512*256*4,
        'font_alpha_sha256':hashlib.sha256(alpha).hexdigest(),
        'logo_rgba_sha256':hashlib.sha256(original_logo).hexdigest(),
        'background_rgb565_sha256':hashlib.sha256(background).hexdigest(),
        'output_sha256':hashlib.sha256(data).hexdigest(),
        'limits':['400x240 backdrop composition is a new3DS adaptation, not original GC/DS layout recovery',
                  'Source background already contains previously documented original-art composition',
                  'No GPU upload/3D car, original frontend animation, menu sound or hardware result is implemented by this asset builder']}


class Glyph(ctypes.Structure):
    _fields_=[('x',ctypes.c_uint16),('y',ctypes.c_uint16),('advance',ctypes.c_uint16),
              ('width',ctypes.c_uint8),('height',ctypes.c_uint8),('left',ctypes.c_int8),('top',ctypes.c_uint8)]
class View(ctypes.Structure):
    _fields_=[('data',ctypes.c_void_p),('background',ctypes.c_void_p),('font',ctypes.c_void_p),('logo',ctypes.c_void_p),('bytes',ctypes.c_size_t),('ascii',Glyph*128)]
class Model(ctypes.Structure):
    _fields_=[('page',ctypes.c_char_p),('alias',ctypes.c_char_p),('selection',ctypes.c_char_p),('detail',ctypes.c_char_p)]


def verify(data,output):
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='mw-top-host-') as temporary:
        library=Path(temporary)/'frontend.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_frontend_top.c'),'-o',str(library)],check=True)
        lib=ctypes.CDLL(str(library));open_=lib.mw_frontend_top_open;open_.argtypes=[ctypes.POINTER(View),ctypes.c_void_p,ctypes.c_size_t];open_.restype=ctypes.c_bool
        render=lib.mw_frontend_top_render;render.argtypes=[ctypes.POINTER(View),ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(Model)];render.restype=ctypes.c_bool
        pack=lib.mw_frontend_top_pack;pack.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];pack.restype=ctypes.c_bool
        raw=ctypes.create_string_buffer(data);view=View();assert open_(ctypes.byref(view),raw,len(data))
        guarded=(ctypes.c_uint8*(WIDTH*HEIGHT*2+32))(*([0xa5]*(WIDTH*HEIGHT*2+32)));canvas=ctypes.byref(guarded,16)
        models=[Model(b'MAIN MENU',b'DRIVER',b'BMW M3 GTR',b'SELECT AN OPTION ON THE TOUCH SCREEN'),
                Model(b'QUICK RACE',b'DRIVER',b'Riverfront & Marina',b'CHOOSE AN EVENT ON THE TOUCH SCREEN'),
                Model(b'ALIAS MANAGER',b'DRIVER',b'YOUR DRIVER PROFILE',b'CREATE OR SELECT AN ALIAS BELOW')]
        for i,model in enumerate(models):
            assert render(ctypes.byref(view),canvas,WIDTH*HEIGHT*2,ctypes.byref(model))
            assert bytes(guarded[:16])==bytes([0xa5])*16 and bytes(guarded[-16:])==bytes([0xa5])*16
            save_preview(bytes(guarded[16:-16]),output/('top-'+str(i)+'.png'))
        before=bytes(guarded);assert not render(ctypes.byref(view),canvas,WIDTH*HEIGHT*2-1,ctypes.byref(models[0]));assert bytes(guarded)==before
        gpu=(ctypes.c_uint8*(512*256*4))();assert pack(gpu,len(gpu),canvas,WIDTH*HEIGHT*2)
        source=bytes(guarded[16:-16]);actual=bytes(gpu)
        # Independent bit interleave, not the C table used by the implementation.
        checked=0
        for y in range(256):
            for x in range(512):
                interleave=sum(((x>>b)&1)<<(2*b) | ((y>>b)&1)<<(2*b+1) for b in range(3))
                at=(((y//8)*64+x//8)*64+interleave)*4
                if x<WIDTH and y<HEIGHT:
                    value=struct.unpack_from('<H',source,(x*HEIGHT+HEIGHT-1-y)*2)[0]
                    expected=bytes((255,(value&31)*255//31,((value>>5)&63)*255//63,(value>>11)*255//31))
                else:expected=b'\xff\0\0\0'
                assert actual[at:at+4]==expected;checked+=1
        invalid=[]
        cases={'short':data[:80]}
        for name,offset,value in [('width',16,401),('offset',28,100),('glyph_count',24,0),('reserved',44,1)]:
            b=bytearray(data);struct.pack_into('<I',b,offset,value);cases[name]=bytes(b)
        b=bytearray(data);b[-1]^=1;cases['payload_crc']=bytes(b)
        b=bytearray(data);b[96+2]=255;struct.pack_into('<I',b,12,zlib.crc32(b[96:]));cases['glyph_bounds']=bytes(b)
        for name,b in cases.items():
            previous=ctypes.string_at(ctypes.byref(view),ctypes.sizeof(view));bad=ctypes.create_string_buffer(b)
            assert not open_(ctypes.byref(view),bad,len(b));assert ctypes.string_at(ctypes.byref(view),ctypes.sizeof(view))==previous;invalid.append(name)
        return {'host_decoder_and_render_pass':True,'guarded_models':len(models),'independently_compared_gpu_texels':checked,'malformed_assets_rejected':invalid,'sdk_or_hardware_tested':False}


def save_preview(canvas,path):
    rgb=bytearray(WIDTH*HEIGHT*3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            value=struct.unpack_from('<H',canvas,(x*HEIGHT+HEIGHT-1-y)*2)[0]
            rgb[(y*WIDTH+x)*3:(y*WIDTH+x)*3+3]=bytes(((value>>11)*255//31,((value>>5)&63)*255//63,(value&31)*255//31))
    Image.frombytes('RGB',(WIDTH,HEIGHT),bytes(rgb)).save(path)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nui',type=Path,required=True);p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--verify-host',action='store_true')
    a=p.parse_args();data,report=build(a.nui.read_bytes());a.output_directory.mkdir(parents=True,exist_ok=True)
    target=a.output_directory/'frontend-top.nut'
    if target.exists() and target.read_bytes()!=data:raise ValueError('Existing top asset differs')
    if not target.exists():target.write_bytes(data)
    if a.verify_host:report['verification']=verify(data,a.output_directory)
    (a.output_directory/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
