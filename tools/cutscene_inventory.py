#!/usr/bin/env python3
"""Inventory verified USA GameCube EA VP6 movies, privately extracting source data.

DOL names plus an observed language/region suffix are hash candidates until they
match directory ranges and actual MVhd payloads. No original movie data belongs
in Git. Source table order is not an inferred chronological story sequence.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

from audit_whole_game import directory_records, name_hash, ZDIR_SHA
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(1048576):
            h.update(block)
    return h.hexdigest()


def inspect_movie(path):
    size = path.stat().st_size
    with path.open('rb') as f:
        h = f.read(32)
        require(len(h) == 32 and h[:4] == b'MVhd', 'Missing EA movie header')
        require(struct.unpack_from('<I', h, 4)[0] == 32 and h[8:12] == b'06PV', 'Unsupported MVhd codec/size')
        width, height = struct.unpack_from('<HH', h, 12)
        frames, unknown, numerator, denominator = struct.unpack_from('<4I', h, 16)
        require(0 < width <= 4096 and 0 < height <= 4096 and frames > 0 and numerator > 0 and denominator > 0,
                'Invalid movie dimensions/timing')
        f.seek(0)
        at = 0
        counts = Counter()
        while at < size:
            h = f.read(8)
            require(len(h) == 8, 'Truncated EA block header')
            tag, length = struct.unpack('<4sI', h)
            require(tag in (b'MVhd', b'MV0K', b'MV0F', b'SCHl', b'SCCl', b'SCDl', b'SCEl'), 'Unsupported EA block tag')
            require(8 <= length <= size - at, 'EA block exceeds original movie')
            counts[tag.decode('ascii')] += 1
            at += length
            f.seek(at)
        require(counts['MVhd'] == 1 and counts['MV0K'] > 0 and counts['MV0K'] + counts['MV0F'] == frames,
                'Video frame blocks disagree with MVhd')
        require(counts['SCHl'] == 1 and counts['SCEl'] == 1, 'Unsupported audio stream count/termination')
    return {'container': 'EA Multimedia', 'video_fourcc': '06PV', 'width': width, 'height': height,
            'declared_video_frames': frames, 'rate_numerator': numerator, 'rate_denominator': denominator,
            'declared_duration_seconds': frames * denominator / numerator,
            'unknown_mvhd_word14_hex': f'{unknown:08x}', 'block_counts': dict(counts)}


def check_rejections(path):
    raw = path.read_bytes()
    cases = {'short_header': raw[:20], 'wrong_codec': raw[:8] + b'BAD!' + raw[12:]}
    for name, at, value, fmt in (('zero_width', 12, 0, '<H'),
                                 ('wrong_frame_count', 16, 0xffffffff, '<I'),
                                 ('oversized_first_block', 4, len(raw) + 1, '<I')):
        damaged = bytearray(raw)
        struct.pack_into(fmt, damaged, at, value)
        cases[name] = bytes(damaged)
    with tempfile.TemporaryDirectory(prefix='mw-movie-rejections-') as directory:
        target = Path(directory) / 'damaged.vp6'
        for name, damaged in cases.items():
            target.write_bytes(damaged)
            try:
                inspect_movie(target)
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed movie accepted: ' + name)
    return list(cases)


def extract(archive, row, target):
    h = hashlib.sha256()
    existing = target.exists()
    output = None if existing else target.open('xb')
    try:
        with archive.open('rb') as f:
            f.seek(row['offset_bytes'])
            left = row['bytes']
            while left:
                block = f.read(min(left, 1048576))
                require(block, 'Truncated original source')
                h.update(block)
                if output:
                    output.write(block)
                left -= len(block)
    finally:
        if output:
            output.close()
    require(target.stat().st_size == row['bytes'] and digest(target) == h.hexdigest(), 'Existing/extracted movie differs')
    return h.hexdigest()


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                       check=True, capture_output=True, text=True, timeout=90)
    result = json.loads(p.stdout)
    return {'streams': [{k: s[k] for k in ('index', 'codec_name', 'codec_type', 'width', 'height', 'pix_fmt',
                       'r_frame_rate', 'time_base', 'nb_frames', 'duration', 'sample_rate', 'channels') if k in s}
                        for s in result['streams']],
            'format_name': result['format']['format_name'], 'probe_score': result['format']['probe_score']}


def inventory(dol, zdir, archives, receipts, output, run_probe=False):
    raw = dol.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == DOL_SHA256, 'Unexpected original DOL')
    image = DolImage(raw)
    directory = zdir.read_bytes()
    require(hashlib.sha256(directory).hexdigest() == ZDIR_SHA, 'Unexpected original ZDIR')
    rows = directory_records(directory)
    by_hash = defaultdict(list)
    movie_records = []
    for row in rows:
        by_hash[row['hash']].append(row)
        with (archives / f"ZZDATA{row['archive']}.BIN").open('rb') as f:
            f.seek(row['offset_bytes'])
            if row['bytes'] >= 32 and f.read(4) == b'MVhd':
                movie_records.append(row)
    stems = image.strings(r'^MOVIES\\')
    names = {}
    unmatched = []
    for stem in stems:
        name = stem['text'] + '_english_ntsc.vp6'
        matches = by_hash.get(f'{name_hash(name):08x}', [])
        if not matches:
            unmatched.append({'stem': stem['text'], 'dol_address': f"{stem['address']:08x}"})
        for row in matches:
            require(row in movie_records, 'Name match is not an MVhd movie')
            require(row['directory_record_offset'] not in names, 'Ambiguous name matches')
            names[row['directory_record_offset']] = (name, stem)
    require(set(names) == {r['directory_record_offset'] for r in movie_records}, 'Unidentified MVhd entries remain')
    used_archives = sorted({r['archive'] for r in movie_records})
    for index in used_archives:
        key = f'ZZDATA{index}.BIN'
        expected = receipts['archives'][key]
        source = archives / key
        require(source.stat().st_size == expected['bytes'] and digest(source) == expected['sha256'], 'Original source differs from collection receipt')
    output.mkdir(parents=True, exist_ok=True)
    movies = []
    table = []
    # Consumer 801365A0..80136650 explicitly scans indices0..0x25, stride8.
    for i in range(38):
        pointer, parameter = struct.unpack('>II', image.read(0x8041ba7c + i * 8, 8))
        name = image.c_string(pointer)
        require(name.startswith('MOVIES\\'), 'Unexpected original movie-name table')
        table.append({'index': i, 'stem': name, 'uninterpreted_second_word': parameter})
    for row in movie_records:
        name, stem = names[row['directory_record_offset']]
        leaf = name.split('\\')[-1]
        require(re.fullmatch(r'[A-Za-z0-9_]+\.vp6', leaf), 'Unexpected movie leaf')
        target = output / leaf
        sha = extract(archives / f"ZZDATA{row['archive']}.BIN", row, target)
        result = {'candidate_name': name, **row, 'file': leaf, 'sha256': sha,
                  'dol_stem_address': f"{stem['address']:08x}",
                  'original_table_index': next(t['index'] for t in table if t['stem'] == stem['text']),
                  'media': inspect_movie(target)}
        if run_probe:
            result['ffprobe'] = probe(target)
        movies.append(result)
    xrefs = image.constant_xrefs([0x803e1328, 0x803e1330, 0x8041ba7c])
    return {'schema': 1, 'source_sha256': {'dol': DOL_SHA256, 'zdir': ZDIR_SHA},
            'source_archive_sha256': {f'ZZDATA{i}.BIN': receipts['archives'][f'ZZDATA{i}.BIN']['sha256'] for i in used_archives},
            'movie_count': len(movies), 'total_movie_bytes': sum(r['bytes'] for r in movies),
            'original_name_table': table, 'unmatched_dol_stems': unmatched,
            'consumer_evidence': {'filename_builder': '80132bd0..80132c7c', 'filename_format': '%sMOVIES\\%s%s%s%s',
                'region_ntsc_pointer': '803e1314', 'region_pal_pointer': '803e131c',
                'language_format_pointer': '803e1324', 'extension_pointer': '803e1328',
                'name_table_consumer': '801365a0..80136650', 'constant_references': xrefs},
            'movies': movies,
            'limits': ['All media remains private; no 3DS video player or codec integration is supplied',
                       'Source name-table order is not chronological story order',
                       'No role is assigned to the original table second word without further consumer proof',
                       'Unmatched DOL names are preserved; no missing movies are fabricated']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dol', 'zdir', 'archives', 'receipts', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--probe', action='store_true')
    p.add_argument('--check-rejections', action='store_true')
    a = p.parse_args()
    report = inventory(a.dol, a.zdir, a.archives, json.loads(a.receipts.read_text()), a.output, a.probe)
    if a.check_rejections:
        report['malformed_inputs_rejected'] = check_rejections(a.output / 'ealogo_english_ntsc.vp6')
    target = a.output / 'inventory.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'movies': report['movie_count'], 'bytes': report['total_movie_bytes'],
                      'unmatched_dol_stems': len(report['unmatched_dol_stems'])}))
