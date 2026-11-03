#!/usr/bin/env python3
"""Verify a metadata-helper ZIP against known USA archive ranges; import privately.

Archive paths and manifest strings are untrusted data, never commands. Existing
files must be identical; no payload is written until the entire bundle validates.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def verify_bundle(path, inventory):
    expected = inventory['next_metadata_request']['payload_records']
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > 24:
            raise ValueError('Unexpected ZIP member count')
        files = {}
        for member in z.infolist():
            parts = PurePosixPath(member.filename).parts
            if '\\' in member.filename or not parts or parts[0] != 'whole-game-metadata' or '..' in parts:
                raise ValueError('Unexpected ZIP member path')
            if member.is_dir():
                if len(parts) != 1:
                    raise ValueError('Unexpected nested directory')
                continue
            if len(parts) != 2 or member.file_size > 5_000_000 or parts[1] in files:
                raise ValueError('Unexpected/duplicate/oversized ZIP member')
            files[parts[1]] = z.read(member)
    manifests = [n for n in files if re.fullmatch(r'manifest-\d{8}-\d{6}-\d{3}\.json', n)]
    if len(manifests) != 1 or 'disc-file-list.json' not in files:
        raise ValueError('Expected extraction and disc-list manifests')
    rows = json.loads(files[manifests[0]].decode('utf-8-sig'))
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError('Unexpected payload record count')
    lookup = {(r['candidate_name'].upper(), r['directory_record_offset']): r for r in expected}
    seen = set()
    names = {manifests[0], 'disc-file-list.json'}
    report = []
    for row in rows:
        key = row['Entry'].upper(), row['DirectoryRecordOffset']
        if key not in lookup or key in seen:
            raise ValueError('Unexpected/duplicate source record')
        seen.add(key)
        original = lookup[key]
        for actual, wanted in ((row['Source'], f"ZZDATA{original['archive']}.BIN"),
                               (row['ArchiveOffset'], original['offset_bytes']),
                               (row['Bytes'], original['bytes']),
                               (row['EntryBytes'], original['bytes']),
                               (row['PartOffset'], 0), (row['EntryHash'], original['hash'])):
            if actual != wanted:
                raise ValueError('Manifest disagrees with known USA directory')
        name = row['Output']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in names:
            raise ValueError('Invalid/duplicate output leaf')
        names.add(name)
        data = files[name]
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != row['Bytes'] or sha != row['SHA256']:
            raise ValueError('Payload size/hash mismatch')
        report.append({'entry': row['Entry'], 'archive_offset': row['ArchiveOffset'],
                       'bytes': len(data), 'sha256': sha})
    if names != files.keys():
        raise ValueError('Unexpected extra files')
    listing = json.loads(files['disc-file-list.json'].decode('utf-8-sig'))
    if not isinstance(listing, list) or len(listing) > 100000:
        raise ValueError('Invalid disc-file list')
    for row in listing:
        name = row['Path']
        if not isinstance(name, str) or ':' in name or name.startswith(('/', '\\')) or '..' in name.replace('\\', '/').split('/'):
            raise ValueError('Disc-file list contains non-relative path')
        if not isinstance(row['Bytes'], int) or row['Bytes'] < 0:
            raise ValueError('Invalid disc-file size')
    return files, {'schema': 1, 'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'payloads': report, 'total_payload_bytes': sum(r['bytes'] for r in report),
                   'disc_listing_entries': len(listing)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('zip', type=Path)
    p.add_argument('--inventory', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/research/whole-game-inventory.json')
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    files, report = verify_bundle(a.zip, json.loads(a.inventory.read_text()))
    for name, data in files.items():
        target = a.destination / name
        if target.exists() and (target.is_symlink() or target.read_bytes() != data):
            raise ValueError('Existing destination differs: ' + name)
    a.destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = a.destination / name
        if not target.exists():
            with target.open('xb') as f:
                f.write(data)
    print(json.dumps(report, indent=2))
