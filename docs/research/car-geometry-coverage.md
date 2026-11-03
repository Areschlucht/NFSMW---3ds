# Car geometry coverage and count diagnostics

2026-11-03. Read-only inspection of the 305 SHA-verified extracted car candidate
entries. No production decoder, game asset, runtime or playable build is changed.
Names are path-hash candidates, not a verified playable roster.

## Measured coverage

There are 83 candidate geometry records containing 8,866 named model parts.
The existing strict `decode_brakes` B-only pass successfully decodes 28 geometry
records, finds no B parts in 28, and rejects 27. The latter category is mostly a
header-statistic comparison failure, with other unsupported data preserved as
failures rather than silently skipped.

Independent descriptor/topology diagnostics inspect 2,882 B parts:

| Declared header +0x14 statistic versus strip topology | Parts |
| --- | ---: |
| Matches emitted index-nondegenerate count only | 2,554 |
| Matches both raw and index-nondegenerate counts | 280 |
| Matches raw strip triangle count only | 2 |
| Matches neither count | 45 |
| Unsupported descriptor | 1 |

Across all 8,866 parts, corresponding counts are 6,760 nondegenerate-only,
1,898 both, 21 raw-only, 178 neither and nine unsupported descriptors.
Repeated-index triangles are counted separately from `sum(vertex_count - 2)`.
Geometric zero-area triangles with distinct indices are not removed by this
measurement. The source header statistic is never overwritten.

A concrete discrepancy: 911GT2_KIT00_BODY_B declares 3,456, contains 4,180 raw
strip triangles and 3,450 index-nondegenerate triangles. Therefore merely adding
or subtracting all repeated-index triangles does not explain the header. Do not
replace the strict check with a guessed raw-count equality.

## Actual detail levels

The absence of B parts is often original packaging, not failed decompression:
COPMIDSIZEINT has 17 A parts; SEMI has C/D/E parts; TRAF4DSEDA and TRAF4DSEDB also
have C/D/E. Select actual available original LODs through source binding rules;
do not invent B meshes or identify all absent-B entries as corrupt cars.
The private report preserves suffix counts and representative exact source names
for every geometry record without B parts.

## Original consumer evidence and its limits

Existing `tools/perf_lod.md` recovers a signed16 header statistic at +0x14 used by
original section LOD consumer 802BEA40, through a resolved model handle. Existing
world-mesh tools already preserve the advisory source statistic separately from
emitted topology, after original descriptor-emitter parity was established.
This supports preserving the header, not rewriting it to match exported faces.
It does not by itself prove every car descriptor variant is decoded correctly.

A bounded execution of original GX descriptor emitter 8011773C..801181C0 confirms
one actual compiled car format22 descriptor from 911GT2_KIT00_BODY_B: flags9E,
30 vertices and a 320-byte original display-list packet. The intercepted original
GXCallDisplayList points to the exact source packet and length. Packet SHA256:
`181a18796df7e57e54fe51606d9250e79c37acb1208732cc9be182b7d16f4178`.
This is one compiled-packet parity case, not validation of all index/normal/UV
semantics or a full car render.

An attempted raw-descriptor adaptation of the world reference did not match the
expected raw byte stream. That remains a failure, not positive evidence. The
reference helper raises on mismatch. Do not enable permissive count handling in
the production car decoder until raw format22 emitter behaviour, all consumed
array bounds, and strip topology parity have been validated independently.

## Reproduction

```sh
PYTHONPATH=tools python tools/car_geometry_diagnostics.py \
  --directory /workspace/port-research/all-car-candidates \
  --output /workspace/port-research/all-car-candidates/strip-count-diagnostics.json
```

The tool checks extraction SHA/size, bounded chunk ranges, descriptor/blob ranges,
compiled primitive/count headers, index widths, and preserves unsupported records
explicitly. Importable `verify_car_emitter(dol, descriptor, packet)` additionally
runs the bounded original loop with GX hooks; its caller supplies the exact
original descriptor and packet, and failed raw cases must remain failures.
Raw game data and the full 8,866-part diagnostic report remain private.

Next decoder amendment, after remaining parity proof: expose an explicit
statistic-discrepancy diagnostic separate from decoded topology while preserving
original +0x14 for LOD. Keep malformed bounds, reference indices, display lists,
array capacities and unknown descriptor formats as hard failures. No blanket
"accept triangle mismatch" change is justified by this checkpoint alone.
