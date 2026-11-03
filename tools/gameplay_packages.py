#!/usr/bin/env python3
"""Strict read-only reader for the observed USA GameCube multi-package VPAK.

The 272-package file differs from the single-database ATTRIBUTES envelope.
Embedded BIN/VLT readers remain strict. A bounded in-memory envelope adapter
reuses their relocation/type checks; provenance is restored to original offsets.
This recovers data structure, not gameplay field or activation semantics.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from vehicle_attributes import VehicleAttributes, string


class PendingParent(ValueError):
    pass


class Dependencies:
    def __init__(self, base):
        self.types = dict(base.types)
        self.classes = dict(base.classes)
        self.names = {k: set(v) for k, v in base.names.items()}
        self.owners = {k: (v, base) for k, v in base.collections.items()}

    def _resolve_collection(self, cls, key):
        try:
            return self.owners[cls, key]
        except KeyError:
            raise PendingParent(f'Unresolved collection parent {cls:08x}/{key:08x}') from None

    def add(self, db):
        if self.owners.keys() & db.collections.keys():
            raise ValueError('Duplicate collection across packages/schema')
        for key, value in db.types.items():
            if key in self.types and self.types[key] != value:
                raise ValueError('Conflicting type definition')
        self.types.update(db.types)
        self.classes.update(db.classes)
        for key, names in db.names.items():
            self.names.setdefault(key, set()).update(names)
        for key, row in db.collections.items():
            self.owners[key] = row, db


class GameplayPackages:
    def __init__(self, raw, schema, labels=()):
        raw = bytes(raw)
        if len(raw) < 16 or raw[:4] != b'VPAK':
            raise ValueError('Missing packed gameplay VPAK header')
        count, names_at, names_size = struct.unpack_from('<3I', raw, 4)
        table_end = 16 + count * 20
        if not 1 <= count <= 4096 or table_end > names_at or names_at % 64:
            raise ValueError('Invalid packed directory bounds/alignment')
        if names_size < count or names_at + names_size > len(raw):
            raise ValueError('Invalid packed name region')
        if any(raw[table_end:names_at]):
            raise ValueError('Nonzero directory padding')
        names = raw[names_at:names_at + names_size]
        starts = {0} | {i + 1 for i, b in enumerate(names[:-1]) if b == 0}
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.entries = []
        ranges = [(0, names_at + names_size)]
        seen_names = set()
        for i in range(count):
            no, bs, vs, bo, vo = struct.unpack_from('<5I', raw, 16 + i * 20)
            if no not in starts:
                raise ValueError('Package name is not at a string boundary')
            name = string(names, no, names_size - no)
            if not name or name in seen_names:
                raise ValueError('Empty/duplicate package name')
            seen_names.add(name)
            for offset, size in ((bo, bs), (vo, vs)):
                if offset % 64 or size < 8 or offset + size > len(raw):
                    raise ValueError('Invalid embedded stream bounds/alignment')
                ranges.append((offset, offset + size))
            self.entries.append(dict(index=i, name=name, bin_bytes=bs, vlt_bytes=vs,
                                     bin_offset=bo, vlt_offset=vo))
        ranges.sort()
        for left, right in zip(ranges, ranges[1:]):
            if left[1] > right[0]:
                raise ValueError('Overlapping packed streams/header')
        self.dependencies = Dependencies(schema)
        pending = list(self.entries)
        self.databases = {}
        self.load_order = []
        while pending:
            loaded = []
            for entry in pending:
                bo, bs = entry['bin_offset'], entry['bin_bytes']
                vo, vs = entry['vlt_offset'], entry['vlt_bytes']
                vpos = (128 + bs + 63) & ~63
                envelope = bytearray(vpos + vs)
                struct.pack_into('<4s8I', envelope, 0, b'VPAK', 1, 64, 9, 0, bs, vs, 128, vpos)
                envelope[128:128 + bs] = raw[bo:bo + bs]
                envelope[vpos:] = raw[vo:vo + vs]
                try:
                    db = VehicleAttributes(envelope, labels=labels, dependency=self.dependencies)
                except PendingParent:
                    continue
                db.sha256 = self.sha256
                db.offsets = {'bin': bo, 'vlt': vo}
                self.dependencies.add(db)
                self.databases[entry['name']] = db
                self.load_order.append(entry['name'])
                loaded.append(entry)
            if not loaded:
                raise ValueError('Unresolved/cyclic cross-package inheritance')
            pending = [e for e in pending if e not in loaded]
        # Make every recovered name visible to all packages, regardless of load order.
        for db in self.databases.values():
            db.names = self.dependencies.names

    def report(self):
        return {'schema': 1, 'source_sha256': self.sha256,
                'package_count': len(self.entries),
                'collection_count': sum(len(d.collections) for d in self.databases.values()),
                'collection_classes': dict(Counter(d.label(c) for d in self.databases.values()
                                                   for c, _ in d.collections)),
                'packages': [{**e, 'collections': len(self.databases[e['name']].collections)}
                             for e in self.entries],
                'limits': ['Package/collection counts are not race counts',
                           'Field layout recovery does not establish original runtime semantics',
                           'Envelope adaptation is in memory; file offsets and hashes identify original source']}


def dol_labels(raw):
    """Only whole printable identifier-like strings; hash matches remain labels."""
    return sorted({m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]+', raw)
                   if re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_]{0,95}', m.group())})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for field in ('gameplay', 'attributes', 'output'):
        p.add_argument('--' + field, required=True, type=Path)
    p.add_argument('--dol', type=Path)
    a = p.parse_args()
    labels = dol_labels(a.dol.read_bytes()) if a.dol else ()
    base = VehicleAttributes(a.attributes.read_bytes(), labels=labels)
    db = GameplayPackages(a.gameplay.read_bytes(), base, labels=labels)
    result = db.report()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('package_count', 'collection_count', 'collection_classes')}))
