#!/usr/bin/env python3
"""Exercise supplied gameplay data, cross-package inheritance and corrupt headers."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from gameplay_packages import GameplayPackages, dol_labels
from vehicle_attributes import VehicleAttributes


def verify(raw, attributes, dol):
    labels = dol_labels(dol)
    base = VehicleAttributes(attributes, labels=labels)
    game = GameplayPackages(raw, base, labels=labels)
    original = {game.sha256: raw, base.sha256: attributes}
    fields = 0
    references = Counter()
    for db in game.databases.values():
        for row in db.collections.values():
            for field in db.fields(row).values():
                source = original[field['source_sha256']]
                at = field['file_offset']
                expected = bytes.fromhex(field['original_bytes'])
                if source[at:at + len(expected)] != expected:
                    raise AssertionError('Attribute provenance mismatch')
                fields += 1
                value = field['value']
                items = value['values'] if isinstance(value, dict) and 'values' in value else [value]
                for item in items:
                    if isinstance(item, dict) and 'class_key' in item:
                        key = item['class_key'], item['collection_key']
                        references['resolved' if key in game.dependencies.owners else 'external_or_null'] += 1
    mutations = []
    def changed(at, value):
        copy = bytearray(raw)
        struct.pack_into('<I', copy, at, value)
        return bytes(copy)
    cases = {
        'empty_directory': changed(4, 0),
        'excessive_directory': changed(4, 0xffffffff),
        'names_beyond_file': changed(8, len(raw) + 64),
        'name_not_at_boundary': changed(16, 1),
        'bin_beyond_file': changed(28, (len(raw) + 127) & ~63),
        'bin_overlaps_header': changed(28, 0),
        'streams_overlap': changed(32, struct.unpack_from('<I', raw, 28)[0]),
        'truncated_payload': raw[:-128],
    }
    for name, damaged in cases.items():
        try:
            GameplayPackages(damaged, base)
        except (ValueError, UnicodeDecodeError):
            mutations.append(name)
        else:
            raise AssertionError('Accepted corrupt source: ' + name)
    return {'schema': 1, 'gameplay_sha256': hashlib.sha256(raw).hexdigest(),
            'attributes_sha256': base.sha256, 'packages': len(game.entries),
            'collections': sum(len(db.collections) for db in game.databases.values()),
            'decoded_fields_with_original_byte_provenance': fields,
            'typed_reference_counts': dict(references), 'rejected_mutations': mutations,
            'limits': ['Unresolved/null references are counted, not assigned invented targets',
                       'Layout/provenance checks do not prove runtime semantics or original consumer parity']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('gameplay', 'attributes', 'dol', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = verify(a.gameplay.read_bytes(), a.attributes.read_bytes(), a.dol.read_bytes())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
