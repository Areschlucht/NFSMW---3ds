#!/usr/bin/env python3
"""Read-only verified USA archive extraction and complete music segment validation.

Original streams and optional decoded audio are private outputs, never Git assets.
Header/descriptor recovery is distinct from the original music state interpreter.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import wave

from audit_whole_game import directory_records, name_hash, ZDIR_SHA
from music_metadata_inspect import inspect_mpf, STREAM_BYTES


def require(value, text):
    if not value:
        raise ValueError(text)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(1048576):
            h.update(data)
    return h.hexdigest()


def extract(source, entry, target):
    h = hashlib.sha256()
    if target.exists():
        with source.open('rb') as f:
            f.seek(entry['offset_bytes'])
            left = entry['bytes']
            while left:
                data = f.read(min(1048576, left))
                require(data, 'Truncated archive range')
                h.update(data)
                left -= len(data)
        require(target.stat().st_size == entry['bytes'] and digest(target) == h.hexdigest(),
                'Existing output differs; refusing overwrite')
        return h.hexdigest()
    with source.open('rb') as f, target.open('xb') as output:
        f.seek(entry['offset_bytes'])
        left = entry['bytes']
        while left:
            data = f.read(min(1048576, left))
            require(data, 'Truncated archive range')
            output.write(data)
            h.update(data)
            left -= len(data)
    return h.hexdigest()


def header(data):
    require(len(data) >= 17 and data[:4] == b'SCHl' and data[8:12] == b'GSTR', 'Unsupported segment header')
    size = struct.unpack_from('<I', data, 4)[0]
    require(size == len(data), 'Incomplete segment header')
    at = 16
    patches = {}
    while at < size:
        tag = data[at]
        at += 1
        if tag == 0xff:
            break
        if tag in (0xfc, 0xfd):
            continue
        require(at < size, 'Missing patch length')
        count = data[at]
        at += 1
        require(count <= 4 and at + count <= size and tag not in patches, 'Invalid patch bounds/duplication')
        patches[tag] = int.from_bytes(data[at:at + count], 'big')
        at += count
    else:
        raise ValueError('No patch terminator')
    require({0x80, 0x82, 0x84, 0x85} <= patches.keys(), 'Missing explicit stream properties')
    require(patches[0x80] == 3 and 0x83 not in patches and 0xa0 not in patches,
            'Unobserved codec override/version')
    require(patches[0x82] > 0 and patches[0x84] > 0, 'Invalid channels/rate')
    return patches


def inspect_segments(path, mpf):
    report = inspect_mpf(mpf, path.stat().st_size)
    at, end = struct.unpack_from('>II', mpf, 0x34)
    descriptors = list(struct.iter_unpack('>II', mpf[at:end]))
    segments = []
    blocks = Counter()
    with path.open('rb') as f:
        require(f.read(4).hex() == report['track_checksum_hex'], 'MPF/MUS checksum-word mismatch')
        for i, (offset, duration) in enumerate(descriptors):
            start = offset * 128
            limit = descriptors[i + 1][0] * 128 if i + 1 < len(descriptors) else path.stat().st_size
            f.seek(start)
            initial = f.read(8)
            require(initial[:4] == b'SCHl', 'Descriptor does not point to SCHl')
            size = struct.unpack_from('<I', initial, 4)[0]
            require(17 <= size <= 4096 and start + size <= limit, 'Invalid SCHl bounds')
            patches = header(initial + f.read(size - 8))
            require(patches[0x85] * 1000 // patches[0x84] == duration,
                    'MPF duration differs from explicit SCHl samples/rate')
            cursor = start
            count = 0
            while cursor + 8 <= limit:
                f.seek(cursor)
                tag, size = struct.unpack('<4sI', f.read(8))
                require(tag in (b'SCHl', b'SCCl', b'SCDl', b'SCEl'), 'Unsupported EA block')
                require(size >= 8 and cursor + size <= limit, 'Block exceeds segment range')
                blocks[tag.decode()] += 1
                cursor += size
                count += 1
                if tag == b'SCEl':
                    break
            else:
                raise ValueError('No complete segment end block')
            segments.append({'index': i, 'offset': start, 'bytes': cursor - start,
                             'padding_to_next_descriptor': limit - cursor, 'blocks': count,
                             'duration_ms': duration, 'samples': patches[0x85],
                             'sample_rate': patches[0x84], 'channels': patches[0x82],
                             'version_patch': patches[0x80]})
    return report, segments, dict(blocks)


def decode_first(path, segment, output):
    clip = output / (path.stem + '-first.schl')
    wav = output / (path.stem + '-first.wav')
    with path.open('rb') as f:
        f.seek(segment['offset'])
        data = f.read(segment['bytes'])
    if clip.exists():
        require(clip.read_bytes() == data, 'Existing segment differs')
    else:
        clip.write_bytes(data)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                            'stream=codec_name,sample_rate,channels', '-of', 'json', str(clip)],
                           check=True, capture_output=True, text=True)
    identity = json.loads(probe.stdout)['streams'][0]
    if not wav.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-n', '-i', str(clip),
                        '-c:a', 'pcm_s16le', str(wav)], check=True, capture_output=True)
    with wave.open(str(wav), 'rb') as f:
        frames, rate, channels = f.getnframes(), f.getframerate(), f.getnchannels()
    require(rate == segment['sample_rate'] and channels == segment['channels'],
            'Decoded PCM rate/channels differ from explicit SCHl declarations')
    return {'ffprobe': identity, 'frames': frames, 'sample_rate': rate, 'channels': channels,
            'declared_frames': segment['samples'], 'frame_delta': frames - segment['samples'],
            'wav_sha256': digest(wav), 'wav_file': wav.name, 'subjective_listening_performed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('archives', 'zdir', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--receipts', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/research/archive-receipts.json')
    p.add_argument('--decode-first', action='store_true')
    p.add_argument('--check-rejections', action='store_true')
    a = p.parse_args()
    raw = a.zdir.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ZDIR_SHA, 'Unexpected USA ZDIR')
    records = directory_records(raw)
    receipts = json.loads(a.receipts.read_text())['archives']
    rows = {}
    for stem in STREAM_BYTES:
        for suffix in ('MPF', 'MUS'):
            key = name_hash('SOUND\\PFDATA\\' + stem + '.' + suffix)
            matches = [r for r in records if r['hash'] == f'{key:08x}']
            require(len(matches) == 1, 'Ambiguous/missing original music directory entry')
            rows[stem, suffix] = matches[0]
    sources = {r['archive'] for r in rows.values()}
    for i in sources:
        name = f'ZZDATA{i}.BIN'
        source = a.archives / name
        require(source.stat().st_size == receipts[name]['bytes'] and digest(source) == receipts[name]['sha256'],
                'Original archive differs from verified receipt')
    a.output.mkdir(parents=True, exist_ok=True)
    results = {}
    rejections = 0
    for stem, expected in STREAM_BYTES.items():
        paths = {}
        hashes = {}
        for suffix in ('MPF', 'MUS'):
            row = rows[stem, suffix]
            target = a.output / f'{stem}.{suffix}'
            hashes[suffix] = extract(a.archives / f'ZZDATA{row["archive"]}.BIN', row, target)
            paths[suffix] = target
        require(paths['MUS'].stat().st_size == expected, 'Unexpected paired music entry size')
        mpf, segments, blocks = inspect_segments(paths['MUS'], paths['MPF'].read_bytes())
        profile = Counter((x['channels'], x['sample_rate'], x['version_patch']) for x in segments)
        results[stem] = {'source_ranges': {s: rows[stem, s] for s in ('MPF', 'MUS')},
                         'sha256': hashes, 'segment_count': len(segments), 'block_counts': blocks,
                         'profiles': [{'channels': c, 'sample_rate': r, 'version_patch': v, 'count': n}
                                      for (c, r, v), n in profile.items()], 'segments': segments}
        if a.check_rejections:
            with paths['MUS'].open('rb') as f:
                f.seek(segments[0]['offset'])
                first = f.read(8)
                size = struct.unpack_from('<I', first, 4)[0]
                data = first + f.read(size - 8)
            variants = [data[:16], b'xxxx' + data[4:],
                        data.replace(b'\x80\x01\x03', b'\x80\x01\x04', 1),
                        data.replace(b'\x82\x01\x02', b'\x82\x01\x00', 1)]
            for damaged in variants:
                try:
                    header(damaged)
                except ValueError:
                    rejections += 1
                else:
                    raise AssertionError('Accepted malformed segment header')
        if a.decode_first:
            results[stem]['first_segment_decode'] = decode_first(paths['MUS'], segments[0], a.output)
    report = {'schema': 1, 'maps': results, 'malformed_headers_rejected': rejections, 'limits': ['No 3DS playback or music-state interpreter implemented',
              'Segment descriptors are not a recovered song playlist', 'Decoded original audio remains private']}
    (a.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: {'segments': v['segment_count'], 'blocks': v['block_counts'],
                         'decode': v.get('first_segment_decode')} for k, v in results.items()}, indent=2))


if __name__ == '__main__':
    main()
