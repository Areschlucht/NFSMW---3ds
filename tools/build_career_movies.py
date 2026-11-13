#!/usr/bin/env python3
"""Prepare source-pinned GameCube movies for bounded JPEG/PCM 3DS playback.

Private conversion assets only. No movie is replaced by an in-engine NIS render,
and this converter does not choose story playback/completion/skip policy.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from PIL import Image, __version__ as PILLOW_VERSION

DOL_SHA = '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
ZDIR_SHA = 'd5726a00d086edb5f8a47ff4bffa4715f84b44441987fd323141a6dfaf1ba333'
WIDTH, HEIGHT, RATE_N, RATE_D, SAMPLE_RATE = 320, 224, 982047, 32767, 32000
AUDIO_BLOCK = 4096
JPEG_CAP = 65536
OPENING_CANDIDATES = ('ealogo', 'storyfmv_pin11', 'storyfmv_bus12',
                      'storyfmv_rac01', 'storyfmv_cro06_coh06a', 'storyfmv_raz08',
                      'storyfmv_saf25', 'storyfmv_rap30')


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def exact_read(stream, count):
    parts = []
    remaining = count
    while remaining:
        data = stream.read(remaining)
        if not data:
            if not parts:
                return None
            raise ValueError('Partial decoded video frame')
        parts.append(data)
        remaining -= len(data)
    return b''.join(parts)


def video_only_source(source, target, expected_frames):
    """Preserve all original video blocks beyond an earlier SCEl audio end.

    FFmpeg EA demux ends at SCEl; several supplied files retain video blocks
    after that tag. Copy exact video blocks into a temporary video-only EA
    container instead of dropping source frames or synthesizing replacements.
    """
    frames, after_audio_end, seen_audio_end = 0, 0, False
    h = hashlib.sha256()
    with source.open('rb') as src, target.open('wb') as dst:
        while header := src.read(8):
            if len(header) != 8:
                raise ValueError('Truncated source EA block')
            tag, length = struct.unpack('<4sI', header)
            if length < 8 or length > 2 * 1024 * 1024:
                raise ValueError('Unbounded source EA block')
            payload = src.read(length - 8)
            if len(payload) != length - 8:
                raise ValueError('Truncated source EA payload')
            if tag == b'SCEl':
                seen_audio_end = True
            if tag in (b'MVhd', b'MV0K', b'MV0F'):
                dst.write(header + payload)
                h.update(header + payload)
                if tag != b'MVhd':
                    frames += 1
                    after_audio_end += seen_audio_end
    if frames != expected_frames:
        raise ValueError('Source video block/header count mismatch')
    return {'method': 'Exact MVhd/MV0K/MV0F blocks copied into temporary video-only EA',
            'source_video_blocks': frames, 'video_blocks_after_audio_end': after_audio_end,
            'copied_video_blocks_sha256': h.hexdigest()}


def convert(row, source, output, quality):
    stem = row['file'].removesuffix('_english_ntsc.vp6')
    if not stem or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in stem):
        raise ValueError('Unsafe original movie stem')
    if digest(source) != row['sha256']:
        raise ValueError('Original movie SHA differs: ' + stem)
    m = row['media']
    if (m['width'], m['height'], m['rate_numerator'], m['rate_denominator']) != (640, 448, RATE_N, RATE_D):
        raise ValueError('Unexpected source movie video profile')
    audio_stream = next(s for s in row['ffprobe']['streams'] if s['codec_type'] == 'audio')
    if (audio_stream['codec_name'], int(audio_stream['sample_rate']), audio_stream['channels']) != ('adpcm_ea_r3', SAMPLE_RATE, 2):
        raise ValueError('Unexpected source movie audio profile')
    target, report_path = output / (stem + '.nvm'), output / (stem + '.json')
    if target.exists() or report_path.exists():
        if not target.exists() or not report_path.exists():
            raise FileExistsError('Partial existing movie conversion: ' + stem)
        report = json.loads(report_path.read_text())
        if report['source_sha256'] != row['sha256'] or report['jpeg_quality'] != quality or report['sha256'] != digest(target):
            raise FileExistsError('Existing movie conversion differs: ' + stem)
        return report
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nfsmw-movie-', dir=output) as temporary:
        temporary = Path(temporary)
        pcm_path, movie_path = temporary / 'audio.pcm', temporary / 'movie.nvm'
        video_path = temporary / 'video.ea'
        demux_preparation = video_only_source(source, video_path, m['declared_video_frames'])
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(source),
                        '-map', '0:a:0', '-ac', '2', '-ar', str(SAMPLE_RATE),
                        '-c:a', 'pcm_s16le', '-f', 's16le', str(pcm_path)], check=True)
        pcm_bytes = pcm_path.stat().st_size
        if not pcm_bytes or pcm_bytes % 4:
            raise ValueError('Invalid decoded PCM shape')
        pcm_frames = pcm_bytes // 4
        frames = m['declared_video_frames']
        if not 0 < frames <= 65535:
            raise ValueError('Unbounded movie frame count')
        audio_crcs = []
        with pcm_path.open('rb') as pcm:
            while data := pcm.read(AUDIO_BLOCK * 4):
                audio_crcs.append(zlib.crc32(data))
        audio_crc_at = 128 + frames * 16
        data_at = (audio_crc_at + len(audio_crcs) * 4 + 15) & ~15
        indexes = []
        with movie_path.open('w+b') as movie, (temporary / 'ffmpeg.log').open('w+b') as errors:
            movie.write(bytes(data_at))
            command = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(video_path),
                       '-map', '0:v:0', '-vf', f'scale={WIDTH}:{HEIGHT}:flags=lanczos',
                       '-fps_mode', 'passthrough', '-pix_fmt', 'rgb24', '-threads', '2',
                       '-f', 'rawvideo', 'pipe:1']
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
            try:
                while raw := exact_read(process.stdout, WIDTH * HEIGHT * 3):
                    if len(indexes) >= frames:
                        raise ValueError('Decoded more video frames than source')
                    encoded = io.BytesIO()
                    Image.frombytes('RGB', (WIDTH, HEIGHT), raw).save(encoded, format='JPEG',
                        quality=quality, subsampling=2, optimize=False, progressive=False)
                    jpeg = encoded.getvalue()
                    if not jpeg or len(jpeg) > JPEG_CAP:
                        raise ValueError('JPEG frame exceeds target decoder budget')
                    indexes.append((movie.tell(), len(jpeg), zlib.crc32(jpeg), 0))
                    movie.write(jpeg)
                    movie.write(bytes((-movie.tell()) % 4))
                if process.wait() or len(indexes) != frames:
                    errors.seek(0)
                    raise ValueError(f'Incomplete source video decode ({len(indexes)}/{frames}): ' + errors.read(4096).decode(errors='replace'))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
            audio_at = movie.tell()
            with pcm_path.open('rb') as pcm:
                while block := pcm.read(1024 * 1024):
                    movie.write(block)
            total = movie.tell()
            if total > 0x7fffffff:
                raise ValueError('Movie exceeds target file-offset budget')
            index = b''.join(struct.pack('<4I', *record) for record in indexes)
            index += struct.pack('<' + str(len(audio_crcs)) + 'I', *audio_crcs)
            header = bytearray(128)
            largest = max(record[1] for record in indexes)
            struct.pack_into('<4s19I', header, 0, b'NVM1', 1, total, 0, WIDTH, HEIGHT,
                RATE_N, RATE_D, frames, 128, 16, audio_crc_at, len(audio_crcs), data_at,
                audio_at, pcm_frames, SAMPLE_RATE, 2, largest, zlib.crc32(index))
            header[80:112] = bytes.fromhex(row['sha256'])
            struct.pack_into('<I', header, 112, AUDIO_BLOCK)
            struct.pack_into('<I', header, 12, zlib.crc32(header[16:]))
            movie.seek(0)
            movie.write(header)
            movie.write(index)
        movie_path.rename(target)
    video_us = (frames * RATE_D * 1000000 + RATE_N - 1) // RATE_N
    audio_us = (pcm_frames * 1000000 + SAMPLE_RATE - 1) // SAMPLE_RATE
    report = {'schema': 1, 'stem': stem, 'source_file': row['file'],
        'source_sha256': row['sha256'], 'sha256': digest(target), 'bytes': total,
        'width': WIDTH, 'height': HEIGHT, 'frames': frames,
        'rate_numerator': RATE_N, 'rate_denominator': RATE_D,
        'audio_rate': SAMPLE_RATE, 'audio_channels': 2, 'audio_frames': pcm_frames,
        'audio_block_frames': AUDIO_BLOCK, 'audio_blocks': len(audio_crcs),
        'video_duration_us': video_us, 'audio_duration_us': audio_us,
        'presentation_duration_us': max(video_us, audio_us),
        'max_jpeg_bytes': largest, 'jpeg_quality': quality,
        'source_video_frame_count_preserved': True, 'audio_trim_or_padding': False,
        'video_demux_preparation': demux_preparation,
        'pillow_version': PILLOW_VERSION,
        'ffmpeg_version': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
        'limits': ['Offline JPEG/PCM conversion, not original VP6/ADPCM target decoding',
                   'Exact original rational frame rate; full desktop-decoded audio tail retained',
                   'Half stored dimensions preserves stored frame aspect; original display-aspect producer remains separate',
                   'No in-engine NIS replacement or story playback/skip-order policy',
                   'Old3DS playback throughput and DSP synchronization need target measurement']}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input-directory', 'inventory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--movie', action='append', default=[])
    parser.add_argument('--quality', type=int, default=82)
    args = parser.parse_args()
    if not 1 <= args.quality <= 95:
        raise ValueError('JPEG quality must be1..95')
    inventory = json.loads(args.inventory.read_text())
    if inventory['source_sha256'] != {'dol': DOL_SHA, 'zdir': ZDIR_SHA}:
        raise ValueError('Unexpected source inventory')
    rows = {r['file'].removesuffix('_english_ntsc.vp6'): r for r in inventory['movies']}
    wanted = args.movie or list(OPENING_CANDIDATES)
    if len(set(wanted)) != len(wanted) or any(stem not in rows for stem in wanted):
        raise ValueError('Unknown/duplicate source movie stem')
    reports = []
    for stem in wanted:
        r = convert(rows[stem], args.input_directory / rows[stem]['file'], args.output, args.quality)
        reports.append({k: r[k] for k in ('stem', 'bytes', 'sha256', 'frames', 'audio_frames', 'max_jpeg_bytes')})
        print(json.dumps(reports[-1]), flush=True)
    summary = args.output / 'summary.json'
    # This is a receipt of this invocation, not an overwrite of original media.
    summary.write_text(json.dumps({'schema': 1, 'movies': reports}, indent=2) + '\n')


if __name__ == '__main__':
    main()
