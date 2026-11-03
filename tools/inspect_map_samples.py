#!/usr/bin/env python3
"""Validate the requested Rockport samples and report bounded chunk headers.

This is format research, not a track decoder. It never executes game code,
decompresses unknown packets or treats arbitrary payload bytes as geometry.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ARCHIVE_SIZES = (315254784, 340240384, 330981376, 346253312)
SAMPLES = (
    ('L2RA.BUN', r'TRACKS\L2RA.BUN', None),
    ('TrackMaps.bin', r'TRACKS\L2RA\TrackMaps.bin', None),
    ('STREAML2RA-first8MiB.BUN', r'TRACKS\STREAML2RA.BUN', 8 * 1024 * 1024),
)
# Only containers already observed in the supplied car/texture packages.
# Unknown track chunks remain opaque, even if their high bit is set.
CONTAINERS = {0x80134000, 0x80134010, 0x80134100,
              0xB3300000, 0xB3310000, 0xB3320000}


def name_hash(name):
    value = 0xffffffff
    for byte in name.upper().encode('ascii'):
        value = (value * 33 + byte) & 0xffffffff
    return value


def directory_records(data):
    if not data or len(data) % 24:
        raise ValueError('Directory must contain complete 24-byte records')
    rows = list(struct.iter_unpack('<6I', data))
    if any(a[0] > b[0] for a, b in zip(rows, rows[1:])):
        raise ValueError('Directory hashes are not sorted')
    bases = (0, 153933, 320066, 481678)
    for _, archive, sector, combined, size, _ in rows:
        if archive >= len(ARCHIVE_SIZES):
            raise ValueError('Invalid archive selector')
        if combined != sector + bases[archive]:
            raise ValueError('Inconsistent combined sector offset')
        offset = sector * 2048
        if offset > ARCHIVE_SIZES[archive] or size > ARCHIVE_SIZES[archive] - offset:
            raise ValueError('Entry exceeds reported archive size')
    return rows


def chunk_headers(data, logical_size=None, max_chunks=20000):
    """Inspect an entry or its prefix, preserving absolute file offsets.

    A declaration extending past a logical parent is invalid. Extending only
    past the available prefix is expected and reported as incomplete. Bounded
    unknown chunks are opaque; a valid header is not proof of known contents.
    """
    logical_size = len(data) if logical_size is None else logical_size
    if logical_size < len(data) or max_chunks < 1:
        raise ValueError('Invalid logical size or chunk budget')
    budget = [max_chunks]

    def region(start, end, depth):
        if depth > 16:
            raise ValueError('Chunk nesting limit exceeded')
        result = []
        while start < end:
            if budget[0] == 0:
                raise ValueError('Chunk count limit exceeded')
            budget[0] -= 1
            if end - start < 8:
                raise ValueError('Partial header inside logical parent')
            available = len(data) - start
            if available < 8:
                result.append(dict(offset=start, status='prefix_ends_in_header',
                                   available_bytes=max(0, available)))
                break
            kind, size = struct.unpack_from('<II', data, start)
            stop = start + 8 + size
            if stop > end:
                raise ValueError(f'Chunk at {start} exceeds logical parent')
            entry = dict(offset=start, id=f'{kind:08x}', payload_bytes=size,
                         status='complete' if stop <= len(data) else 'prefix_ends_in_payload')
            if kind in CONTAINERS:
                entry['children'] = region(start + 8, stop, depth + 1)
            result.append(entry)
            if stop > len(data):
                break
            start = stop
        return result

    return region(0, logical_size, 0)


def inspect_samples(folder, zdir):
    directory = zdir.read_bytes()
    rows = directory_records(directory)
    report = dict(zdir_sha256=hashlib.sha256(directory).hexdigest(), samples=[],
                  limitation='Header inspection only; no map geometry, road topology or collision decoding.')
    for filename, game_path, limit in SAMPLES:
        matches = [r for r in rows if r[0] == name_hash(game_path)]
        if len(matches) != 1:
            raise ValueError(f'{game_path}: expected one directory match, got {len(matches)}')
        _, archive, sector, _, size, _ = matches[0]
        expected = size if limit is None else min(size, limit)
        path = folder / filename
        if path.stat().st_size != expected:
            raise ValueError(f'{filename}: expected {expected} bytes')
        data = path.read_bytes()
        entry = dict(file=filename, game_path=game_path, archive=archive,
                     archive_offset=sector * 2048, entry_bytes=size,
                     sample_bytes=len(data), is_prefix=len(data) < size,
                     sha256=hashlib.sha256(data).hexdigest(), signature_hex=data[:16].hex())
        try:
            entry['chunks'] = chunk_headers(data, size)
            entry['chunk_layout_status'] = 'headers_fit_observed_layout'
        except ValueError as error:
            entry['chunk_layout_status'] = 'unrecognized_or_malformed'
            entry['chunk_layout_detail'] = str(error)
        report['samples'].append(entry)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=Path)
    parser.add_argument('zdir', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_samples(args.samples, args.zdir), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
