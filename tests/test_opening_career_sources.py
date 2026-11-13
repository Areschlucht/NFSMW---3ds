"""Source-bound script paths and short-HUFF decoder guard regression.

PYTHONPATH=tools:/workspace/toolchains/python-deps python \
 tests/test_opening_career_sources.py opening-evidence.json GAMEPLAY.BIN report.json
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
from build_opening_career import GAMEPLAY_SHA256, Lua50, verify_script_paths
from nfs_huff_reference import decode


def rejected(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('Malformed source input was accepted')


if __name__ == '__main__':
    assert len(sys.argv) == 4
    evidence = json.loads(Path(sys.argv[1]).read_text())
    gameplay = Path(sys.argv[2]).read_bytes()
    assert hashlib.sha256(gameplay).hexdigest() == GAMEPLAY_SHA256
    paths = verify_script_paths(evidence['scripts'])
    short = [s for s in evidence['scripts'] if s['decoded_bytes'] < 184]
    assert len(short) == 29
    for s in short:
        encoded = gameplay[s['compressed_offset']:s['compressed_offset']+s['compressed_bytes']]
        assert hashlib.sha256(encoded).hexdigest() == s['compressed_sha256']
        decoded = decode(encoded, s['decoded_bytes'])
        assert hashlib.sha256(decoded).hexdigest() == s['decoded_sha256']
        assert Lua50(decoded).root == s['prototype']
    source = short[0]
    encoded = gameplay[source['compressed_offset']:source['compressed_offset']+source['compressed_bytes']]
    expected = source['decoded_bytes']
    bad = bytearray(encoded)
    struct.pack_into('<I', bad, 8, 0)
    rejected(lambda: decode(bad, 0))
    rejected(lambda: decode(encoded, expected+1))
    rejected(lambda: decode(encoded[:-1], expected))
    rejected(lambda: decode(b'NOPE'+encoded[4:], expected))
    decoded = decode(encoded, expected)
    for n in (0, 13, 17, len(decoded)-1):
        rejected(lambda n=n: Lua50(decoded[:n]))
    rejected(lambda: Lua50(b'NOPE'+decoded[4:]))
    rejected(lambda: Lua50(decoded+b'\0'))
    mutated = bytearray(decoded)
    struct.pack_into('<I', mutated, 18, 65537)
    rejected(lambda: Lua50(mutated))
    report = {'schema': 1, 'gameplay_sha256': GAMEPLAY_SHA256,
              'original_lua_subset_path_cases': len(paths),
              'path_cases': paths, 'short_huff_scripts_verified': len(short),
              'shortest_original_uncompressed_bytes': min(s['decoded_bytes'] for s in short),
              'malformed_huff_rejections': 4, 'malformed_lua_rejections': 7,
              'limits': ['Lua5.0 subset instruction model with supplied safe mocks, not original native Lua VM execution',
                         'No graphics/audio/vehicle/police runtime is implemented by these host checks']}
    Path(sys.argv[3]).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('path_cases', 'limits')}))
