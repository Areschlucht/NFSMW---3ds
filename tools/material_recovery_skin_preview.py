#!/usr/bin/env python3
"""Export canonical BMW source-derived diffuse preview and separate fourth byte.

This is not the final original GX indexed skin. Preset/parts/source selection
logical mask/128 blend and CPU/native palette adaptation are recovered;
original indexed edge-color quantization remains unresolved. Never use GLOSS as opacity.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from material_recovery_carparts import CarParts
from material_recovery_paint import pack_paint_word,masked_word,rgb5a3_cpu_word,cpu_word_rgb5a3
from material_recovery_presets import report
from material_recovery_vehicle import texture_hash
from gc_texture import rgb5a3

SOURCE_RGBA_SHA256='7e0736720566b870032ba7c6bb8432d57dcd3a44784e552dfe805fc34eed8c5c'
MASK_RGBA_SHA256='dcffc9bba6c3764802a4f3f72252d0f9bb0c4cdba3dd88f80d2e8b6008c071be'


def export(bundle,source_path,mask_path,output):
    db=CarParts(bundle)
    rows=[r for r in report(bundle)['records'] if r['preset_name']=='M3GTRCAREERSTART']
    if len(rows)!=1 or rows[0]['model_name']!='BMWM3GTRE46':
        raise ValueError('Expected the unique original hero BMW preset')
    row=rows[0];keys=[int(x,16) for x in row['part_keys']]
    base=db.part(keys[76]);vinyl=db.part(keys[77])
    if db.value(vinyl,'REMAP')!=0 or db.value(vinyl,'TEXTURE',text=True)!='PSRTEST':
        raise ValueError('Canonical source selection changed; requires renewed recovery')
    components=[db.value(base,n) for n in ('RED','GREEN','BLUE','GLOSS')]
    base_word=pack_paint_word(*components)
    source=Image.open(source_path).convert('RGBA');mask=Image.open(mask_path).convert('RGBA')
    if source.size!=(512,512) or mask.size!=source.size:raise ValueError('Original dimensions mismatch')
    raw=source.tobytes();mraw=mask.tobytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_RGBA_SHA256 or hashlib.sha256(mraw).hexdigest()!=MASK_RGBA_SHA256:
        raise ValueError('Decoded original source/mask fingerprint mismatch')
    # Invert the exact pinned decoded RGB5A3 values without repeating HUFF.
    # The source has a unique native inverse. Mask opaque black/white can have
    # two native representations, accepted only when their effective weights
    # are identical (zero or full coverage); partial ambiguity is rejected.
    inverse={}
    for native in range(65536):inverse.setdefault(rgb5a3(native),set()).add(rgb5a3_cpu_word(native))
    source_cache={};mask_cache={}
    color=bytearray();gloss=bytearray();gx_gloss=bytearray();words=bytearray();native_pixels=bytearray();unique=set();native_unique=set()
    for at in range(0,len(raw),4):
        r,g,b,native=raw[at:at+4];mr,mg,mb,_=mraw[at:at+4]
        if mr!=mg or mr!=mb:raise ValueError('Original mask is not grayscale')
        pixel=(r,g,b,native);mpixel=tuple(mraw[at:at+4])
        if pixel not in source_cache:
            candidates=inverse.get(pixel,set())
            if len(candidates)!=1:raise ValueError('Ambiguous native source palette inverse; original raw palette needed')
            source_cache[pixel]=next(iter(candidates))
        if mpixel not in mask_cache:
            weights={min(128,(v>>16)&255) for v in inverse.get(mpixel,set())}
            if len(weights)!=1:raise ValueError('Ambiguous original native partial mask weight')
            mask_cache[mpixel]=next(iter(weights))
        word=masked_word(base_word,source_cache[pixel],mask_cache[mpixel])
        packed=cpu_word_rgb5a3(word);display=rgb5a3(packed)
        unique.add(word);native_unique.add(packed);words.extend(struct.pack('<I',word));native_pixels.extend(struct.pack('>H',packed))
        color.extend((*display[:3],255));gloss.append(word>>24);gx_gloss.append(display[3])
    output.mkdir(parents=True,exist_ok=True)
    diffuse=output/'de3ad3c6-logical-diffuse.png';gpath=output/'de3ad3c6-fourth-byte.png'
    Image.frombytes('RGBA',source.size,bytes(color)).save(diffuse)
    Image.frombytes('L',source.size,bytes(gloss)).save(gpath)
    Image.frombytes('L',source.size,bytes(gx_gloss)).save(output/'de3ad3c6-gx-fourth-byte.png')
    (output/'de3ad3c6-rgb5a3-linear-be.bin').write_bytes(native_pixels)
    (output/'de3ad3c6-native-words-le.bin').write_bytes(words)
    result=dict(status='development-only native-adapter-derived diffuse preview; original indexed edge quantization not established',
        target_alias='BMWM3GTRE46_SKIN1',target_hash=f'{texture_hash("BMWM3GTRE46_SKIN1"):08x}',
        width=source.width,height=source.height,preset='M3GTRCAREERSTART',preset_offset=row['file_offset'],
        preset_record_sha256=row['record_sha256'],bundle_sha256=db.sha256,
        base_part=base['name'],base_part_key=base['key'],base_attributes=dict(zip(('RED','GREEN','BLUE','GLOSS'),components)),
        vinyl_part=vinyl['name'],vinyl_part_key=vinyl['key'],source_name='BMWM3GTRE46_PSRTEST',source_hash='849ff2f5',mask_hash='02c984a0',
        source_rgba_sha256=SOURCE_RGBA_SHA256,mask_rgba_sha256=MASK_RGBA_SHA256,
        remap=0,logical_blend='separate mask>=128: source; otherwise separately truncate source*mask/128 and base*(128-mask)/128 per byte',
        diffuse_png=diffuse.name,diffuse_rgba_sha256=hashlib.sha256(color).hexdigest(),
        fourth_byte_png=gpath.name,fourth_byte_sha256=hashlib.sha256(gloss).hexdigest(),
        native_word_bytes_sha256=hashlib.sha256(words).hexdigest(),unique_logical_words=len(unique),unique_native_halfwords=len(native_unique),
        native_rgb5a3_sha256=hashlib.sha256(native_pixels).hexdigest(),gx_fourth_byte_sha256=hashlib.sha256(gx_gloss).hexdigest(),
        native_adapter_verification='paint-native-adapter-verification.json:65536decode+65536encode+256arbitraryCPUwords matchoriginalPPC',
        opacity='Diffuse preview alpha forced255 because body paint is opaque; original source alpha is never used as visibility',
        fourth_byte_scope='CPU base byte is original GLOSS128; source byte comes from exact original RGB5A3 CPU adapter (3-bit alpha shifted5). Both CPU byte and GX-normalized fourth byte are exported separately; neither is diffuse opacity.',
        limitations=['Original indexed edge palette quantization is unresolved; native halfword encoding itself is recovered',
                     'No reflection, specular, Fresnel, body material composition or original lighting is baked',
                     'This is a reviewable diffuse preview, not a claim of an exact final GameCube skin'])
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle',type=Path);p.add_argument('source_png',type=Path);p.add_argument('mask_png',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();r=export(a.bundle.read_bytes(),a.source_png,a.mask_png,a.output)
    print(r['target_hash'],r['unique_logical_words'],r['diffuse_rgba_sha256'])
