#!/usr/bin/env python3
"""Check emulator captures from the documented1024x768 dual-screen layout.

Requires Pillow. This detects partial HUD labels and verifies reset/grade/wheel
behaviour; it is not original-game pixel parity or physical-console validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageChops

def verify(folder,prefix):
    def screen(name,box):
        return Image.open(folder/(prefix+name+'.png')).convert('RGB').crop(box)
    def top(name):return screen(name,(312,192,712,432))
    def bottom(name):return screen(name,(352,432,672,672))
    def difference(a,b):return ImageChops.difference(top(a),top(b)).getbbox()
    result={'reset_difference':difference('spawn','reset'),
        'garage_reset_difference':difference('garage','garage-reset'),
        'neutral_restored_difference':difference('spawn','neutral-restored'),
        'driving_difference':difference('spawn','accelerating'),
        'wheel_difference':difference('garage','garage-roll'),
        'filter_difference':difference('spawn','warm')}
    failures=[]
    for name in ['spawn','reset','accelerating','braked','stats','help','warm','neutral-restored']:
        image=bottom(name)
        speed=sum(sum(c)>400 for c in image.crop((6,30,102,140)).get_flattened_data())
        menu=sum(sum(c)>400 for c in image.crop((10,208,106,236)).get_flattened_data())
        if speed<=100 or menu<=20:failures.append(name)
    result['missing_hud_labels']=failures
    menu=[hashlib.sha256(bottom('stable-menu-'+str(i)).tobytes()).hexdigest() for i in range(1,21)]
    result['menu_frames']=20;result['menu_image_variants']=len(set(menu))
    result['hardware_validated']=False
    if failures:raise ValueError('Missing HUD labels: '+','.join(failures))
    if any(result[k] is not None for k in ['reset_difference','garage_reset_difference','neutral_restored_difference']):raise ValueError('Reset/neutral restore mismatch')
    if any(result[k] is None for k in ['driving_difference','wheel_difference','filter_difference']):raise ValueError('Expected movement/filter change absent')
    if len(set(menu))!=1:raise ValueError('Idle menu changed between frames')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--prefix',required=True);p.add_argument('--output',type=Path)
    a=p.parse_args();r=verify(a.folder,a.prefix);text=json.dumps(r,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    print(text,end='')
