#!/usr/bin/env python3
"""Extract identified USA ZDIR entries privately, preserving duplicate records.

Names are directory-hash candidates, never executable instructions/output paths.
Archive SHA256 is verified against the completed collection receipt. Extraction
is streamed, read-only, and refuses to replace differing existing payloads.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from audit_whole_game import directory_records, name_hash, ZDIR_SHA


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(1048576):
            h.update(block)
    return h.hexdigest()


def extract(zdir, archives, receipts, entries, output):
    raw = zdir.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ZDIR_SHA:
        raise ValueError('Unexpected USA ZDIR')
    records = directory_records(raw)
    jobs = []
    for name in sorted(set(entries)):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_ .\\-]+', name):
            raise ValueError('Unexpected candidate name')
        matches = [r for r in records if r['hash'] == f'{name_hash(name):08x}']
        if not matches:
            raise ValueError('Candidate has no directory match: ' + name)
        for row in matches:
            # Directory record offset is unique even for duplicate hash/extents.
            leaf = f"{row['hash']}-record{row['directory_record_offset']:05d}.bin"
            jobs.append({'candidate_name': name, **row, 'file': leaf})
    sources = {}
    for index in sorted({r['archive'] for r in jobs}):
        name = f'ZZDATA{index}.BIN'
        path = archives / name
        receipt = receipts['archives'][name]
        if path.is_symlink() or path.stat().st_size != receipt['bytes'] or file_sha(path) != receipt['sha256']:
            raise ValueError('Source archive differs from verified receipt: ' + name)
        sources[index] = path
    output.mkdir(parents=True, exist_ok=True)
    result = []
    for job in jobs:
        target = output / job['file']
        h = hashlib.sha256()
        # Compute first, before opening a destination. Names are not trusted paths.
        with sources[job['archive']].open('rb') as source:
            source.seek(job['offset_bytes'])
            left = job['bytes']
            while left:
                b = source.read(min(left, 1048576))
                if not b:
                    raise ValueError('Truncated indexed source')
                h.update(b)
                left -= len(b)
        sha = h.hexdigest()
        if target.exists():
            if target.is_symlink() or target.stat().st_size != job['bytes'] or file_sha(target) != sha:
                raise ValueError('Existing output differs: ' + job['file'])
        else:
            with sources[job['archive']].open('rb') as source, target.open('xb') as destination:
                source.seek(job['offset_bytes'])
                left = job['bytes']
                while left:
                    b = source.read(min(left, 1048576))
                    if not b:
                        raise ValueError('Source changed during extraction')
                    destination.write(b)
                    left -= len(b)
            if file_sha(target) != sha:
                raise ValueError('Source changed during extraction; retained output for review')
        result.append({**job, 'sha256': sha,
                       'archive_sha256': receipts['archives'][f"ZZDATA{job['archive']}.BIN"]['sha256']})
    report = {'schema': 1, 'zdir_sha256': ZDIR_SHA, 'entries': result,
              'limits': ['Candidate names require internal payload/consumer validation',
                         'All duplicate hash records are preserved; selection precedence is not invented']}
    manifest = output / 'manifest.json'
    text = json.dumps(report, indent=2) + '\n'
    if manifest.exists() and manifest.read_text() != text:
        raise ValueError('Existing extraction manifest differs')
    if not manifest.exists():
        with manifest.open('x') as f:
            f.write(text)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('zdir', 'archives', 'receipts', 'inventory', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--prefix', default='CARS\\')
    a = p.parse_args()
    inventory = json.loads(a.inventory.read_text())
    names = [r['candidate_name'] for r in inventory['candidate_archive_ranges']
             if r['candidate_name'].startswith(a.prefix)]
    if not names:
        raise ValueError('No requested candidates')
    r = extract(a.zdir, a.archives, json.loads(a.receipts.read_text()), names, a.output)
    print(json.dumps({'extracted_records': len(r['entries']),
                      'bytes': sum(x['bytes'] for x in r['entries'])}))
