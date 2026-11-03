#!/usr/bin/env python3
"""Convert supplied GameCube GLOBAL/frontend UI art into a bounded NUI2 sidecar.

Uses the existing texture decoder. No runtime image decoder is required.
The composition is a new 3DS layout; source artwork and metrics are preserved.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

from PIL import Image
from nfs_tpk import chunks, parse


def build(globala, globalb, frontb, frontvm):
    a, b = globala.read_bytes(), globalb.read_bytes()
    fd, vd = frontb.read_bytes(), frontvm.read_bytes()
    expected = [
        '980351c79b54ea5f4f4d368a0a4e542b44a74f30c48386c1b60858a4fe5e50e2',
        'b1329f35739503b13cff4838766f511b1f5e8fec28d37112da9efbc63cb0438a',
        'bc3c7c33d8b2620deaa5506da8c43c7cecd6fa5ea3d3f369d8baf4bbee753920',
        '6a815221485bca9ea44c16ab9729255f816167606ba4fdd0873e583ecbbdc1c8',
    ]
    for raw, digest in zip([a, b, fd, vd], expected):
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('UI source differs from the validated supplied GameCube files')
    ta = {t['name']: t for t in parse(a)}
    tb = {t['name']: t for t in parse(b)}
    tf = {t['name']: t for t in parse(fd)}
    font = ta['FONT_MW_BODY']
    logo = ta['MW_LOGO']
    assert (font['width'], font['height']) == (256, 256)
    assert (logo['width'], logo['height']) == (256, 64)
    assert all(font['rgba'][i:i+3] == b'\xff\xff\xff'
               for i in range(0, len(font['rgba']), 4))
    metrics = [a[s+8:e] for k, s, e in chunks(a, 0, len(a)) if k == 0x30201]
    assert len(metrics) == 1
    m = metrics[0]
    assert m[:13] == b'font_mw_body\0' and m[0x200:0x204] == b'FNTG'
    count = struct.unpack_from('>H', m, 0x20a)[0]
    assert count == 237
    records = bytearray()
    evidence = []
    for i in range(count):
        p = 0x280+i*16
        code, w, h, x, y = struct.unpack_from('>HBBHH', m, p)
        left, top = struct.unpack_from('bB', m, p+9)
        advance = struct.unpack_from('>H', m, p+14)[0]
        assert x+w <= 256 and y+h <= 256 and 0 < advance <= 32
        assert -16 <= left <= 16 and top <= 32 and w <= 32 and h <= 32
        records.extend(struct.pack('<HBBHHbBH', code, w, h, x, y, left, top, advance))
        evidence.append(dict(code=code, width=w, height=h, x=x, y=y,
                             left=left, top=top, advance=advance))
    alpha = bytes(font['rgba'][3::4])
    # The title font is a separate original gothic face. Copy only required
    # uppercase/digit glyph rectangles into a compact atlas, retaining metrics.
    title = tf['FONT_MW_TITLE']
    assert (title['width'], title['height']) == (512, 512)
    fnt = vd.find(b'FNTG', vd.find(b'font_mw_title\0'))
    assert fnt >= 0 and vd[fnt-512:fnt-499] == b'font_mw_title'
    title_count = struct.unpack_from('>H', vd, fnt+10)[0]
    wanted = set(map(ord, ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'))
    title_records, title_evidence = bytearray(), []
    atlas = Image.new('L', (256, 160))
    source = Image.frombytes('RGBA', (512, 512), title['rgba']).getchannel('A')
    ax, ay, row_h = 0, 0, 0
    for i in range(title_count):
        p = fnt+0x80+i*16
        code, w, h, x, y = struct.unpack_from('>HBBHH', vd, p)
        if code not in wanted:
            continue
        left, top = struct.unpack_from('bB', vd, p+9)
        advance = struct.unpack_from('>H', vd, p+14)[0]
        assert w <= 48 and h <= 48 and x+w <= 512 and y+h <= 512
        if ax+w > 256:
            ax, ay, row_h = 0, ay+row_h+1, 0
        assert ay+h <= 160
        atlas.paste(source.crop((x, y, x+w, y+h)), (ax, ay))
        title_records.extend(struct.pack('<HBBHHbBH', code, w, h, ax, ay, left, top, advance))
        title_evidence.append(dict(code=code, source_x=x, source_y=y,
                                   width=w, height=h, atlas_x=ax, atlas_y=ay,
                                   left=left, top=top, advance=advance))
        ax += w+1;row_h = max(row_h, h)
    assert {g['code'] for g in title_evidence} == wanted
    # Source textures are reused as static grayscale decoration, not presented
    # as a recovered frontend background. No runtime random noise is generated.
    splash = tf['WS_MWSPLASHBACK']
    background = Image.frombytes('RGBA', (splash['width'], splash['height']), splash['rgba'])
    background = background.resize((320, 240), Image.Resampling.LANCZOS)
    background = Image.alpha_composite(Image.new('RGBA', (320, 240), (18, 19, 20, 255)), background)
    background = Image.alpha_composite(background, Image.new('RGBA', (320, 240), (0, 0, 0, 150)))
    tread = tb['TREAD']
    ti = Image.frombytes('RGBA', (tread['width'], tread['height']), tread['rgba'])
    mask = ti.convert('L').resize((320, 160)).rotate(-24, expand=True)
    mask = mask.point(lambda p: p//3)
    layer = Image.new('RGBA', mask.size, (150, 150, 150, 0));layer.putalpha(mask)
    background.alpha_composite(layer, (-70, -10))
    splatter = tb['LOAD_SPLATTER']
    si = Image.frombytes('RGBA', (splatter['width'], splatter['height']), splatter['rgba'])
    si = si.resize((192, 96), Image.Resampling.LANCZOS)
    mask = si.getchannel('A').point(lambda p: p//3)
    layer = Image.new('RGBA', si.size, (160, 160, 160, 0));layer.putalpha(mask)
    background.alpha_composite(layer, (120, 144))
    rgb = background.convert('RGB').tobytes()
    packed_background = bytearray(320*240*2)
    for y in range(240):
        for x in range(320):
            red, green, blue = rgb[(y*320+x)*3:(y*320+x)*3+3]
            struct.pack_into('<H', packed_background, (x*240+239-y)*2,
                             ((red>>3)<<11)|((green>>2)<<5)|(blue>>3))
    font_offset = 48+len(records)+len(title_records)
    title_offset = font_offset+len(alpha)
    logo_offset = title_offset+256*160
    bg_offset = logo_offset+len(logo['rgba'])
    payload = records+title_records+alpha+atlas.tobytes()+logo['rgba']+packed_background
    header = struct.pack('<4s11I', b'NUI2', 2, 48+len(payload), zlib.crc32(payload),
                         count, len(title_evidence), font_offset, title_offset, logo_offset, bg_offset, 256, 160)
    provenance = dict(format='NUI2', bytes=48+len(payload), glyph_count=count,
        source_globala_sha256=hashlib.sha256(a).hexdigest(),
        source_globalb_sha256=hashlib.sha256(b).hexdigest(),
        source_frontb_sha256=hashlib.sha256(fd).hexdigest(),
        source_frontvm_sha256=hashlib.sha256(vd).hexdigest(),
        artwork=[dict(name=t['name'], hash=t['hash'], width=t['width'], height=t['height'],
                      rgba_sha256=hashlib.sha256(t['rgba']).hexdigest())
                 for t in [font, title, logo, tread, splatter, splash]],
        font_metrics='Observed FNTG glyph coordinates/offsets/advances; kerning table not yet applied',
        layout='New 3DS adaptation, not the original frontend composition',
        glyphs=evidence, title_glyphs=title_evidence)
    return header+payload, provenance


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('globala', type=Path);p.add_argument('globalb', type=Path)
    p.add_argument('frontb', type=Path);p.add_argument('frontvm', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    data, provenance = build(args.globala, args.globalb, args.frontb, args.frontvm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    provenance['output_sha256'] = hashlib.sha256(data).hexdigest()
    args.output.with_suffix('.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'Wrote {len(data)} bytes of converted original UI artwork: {args.output}')


if __name__ == '__main__':
    main()
