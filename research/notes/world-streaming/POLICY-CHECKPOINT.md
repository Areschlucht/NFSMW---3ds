# Original region and dependency policy checkpoint

This advances the inventory checkpoint into isolated, executable translations of
original policy stages. No existing decoder, scene exporter or runtime was edited.

## Original data and selector

`L2RA.BUN` contains much more than the two chunks used by the original research
index/navigation reader. Its `0x80034150` package is at payload offset 93,640,
length 103,584. Original loader `0x802C0A08` consumes its leaves:

- `0x34151`: original section span **40**, 373 configured IDs, unknown tail retained.
  This replaces the executable's default span 10 at global `0x80437068`.
- `0x34152`: 515 original variable-length polygon records; source bounds, center,
  vertex order, flags and raw bytes preserved. Record size is 36+8*vertex_count.
- `0x34153`: 435 ordered dependency records, each referring to a polygon. The
  current section-list count is signed u16 at +16; allocated capacity is byte +15;
  section IDs start at +18. Record size is 20+2*capacity. Byte +14 is preserved
  separately; it is NOT always equal to current count.
- `0x34155`: 39 original 76-byte named groups; original region IDs and additional
  section IDs preserved. Group activation/scheduling remains separate work.

`tools/world_streaming_regions.py` strictly decodes this data and exposes
`ContainingRegionSelector`. The selector implements original `0x802C1094`'s
contained-point branch: scan dependency rows in current linked-list order, perform
native 2D bounds and original polygon containment checks, and move the matching row
to the front. Overlapping regions therefore preserve original history-dependent
priority; selecting the smallest ID or nearest center would change behavior.

The translated odd/even polygon test follows `0x802BFF3C`, including each original
single-precision rounding and edge rule. The bounded original-PPC reference runs
that function and the complete original contained-point selector call path,
including its real bounds helper and list mutations; it does not replace polygon
or containment logic with a host callback.

Validation against original instructions:

- 1,545 polygon tests, three points per each of the 515 original polygons.
- 563 sequential stateful selector queries spanning all 435 dependency-row centers,
  followed by reversed and repeated traversals. Every result matches. All supplied
  centers lie inside an original dependency region.
- Outside all dependency regions, the host raises `NoContainingRegion` because the
  original nearest-region fallback is not translated yet. This is a precise
  remaining stage, not an arbitrary replacement region or activation heuristic.

See `original-regions-and-dependencies.json`,
`original-policy-stage-verification.json`, `region-polygon-original.txt`,
`region-query-original.txt`, and `world-region-loader.txt`.

## Model binding and conditional ID fallback

Original `0x802BDBE0..0x802BDCE0` consumes FOUR model hash slots at object offsets
+24,+28,+32,+36. Every supplied world row has slot0=0, so the prior three-nonzero-slot
inventory did not lose model references. The original skips zero and two sentinel
hashes, shares an earlier handle when hashes repeat, then fills null slot2 from
slot1 and null slot0 from slot1. The fourth slot has no such fallback.

The availability manifest now retains four raw slots AND the resulting bound
hash slots. These are original ordered slots, not invented distance labels.

Original `0x802B9184` conditionally resolves missing section IDs: only hundreds
1..20 and remainders 1..span-1 are eligible; an existing original ID wins, otherwise
ID+span is returned only if it exists. It does not generally add 40, and it is not
a global collision/render ID mapping. The host translation and original reference
match on 625 exhaustive binding combinations, 64 real object rows and 198 section
fallback cases. These stages are in `tools/world_streaming_policy.py`.

## Placement and collision findings

All 167 original instances referring to the newly recovered statistic-discrepant
models match an original LOD's transformed tight geometry bounds within the
EXISTING 0.15 tolerance. The 33 apparent failures from the earlier checkpoint were
caused by considering only recovered hashes, omitting already-valid sibling LODs.
No bounds tolerance or transform convention was relaxed. Transforming header AABBs
instead of geometry gives only 130 matches, so that is not a suitable substitute.

Reproduce with `tools/world_streaming_bounds.py`; results are in
`original-instance-bounds-semantics.json`.

Physical range containment now associates all 450 collision packages with 450
original indexed stream sections. 338 have sectionID-collisionID=40, 52 delta0;
the remaining60 have numerous different deltas. The exact source relations are in
`original-render-collision-containment.json`; regenerate using
`tools/world_streaming_containment.py`. Physical embedding is proved; original
activation, ID-keyed duplicate handling and query policy are distinct concerns.

## External banks and actual consumed textures

The complete stream has 416 declared texture hashes absent from its own texture
packets. Scanning supplied GLOBALA, GLOBALB and three DYNAMIC banks resolves three.
However, only **eight** of the remaining413 are actually indexed by original draw
descriptors. The rest are unused texture-reference table slots. The inventory and
availability manifest now distinguish declared references from consumed draw
textures. Do not request hundreds of assets based solely on unused table entries.

`original-external-bank-resolution.json` lists exact supplied bank hashes and
available keys. `unresolved-consumed-textures.json` lists draw counts and model and
section examples. Twenty-one model-reference hashes remain absent in the scanned
banks; no substitute model is generated.

## Reproduction and current limits

New tools are isolated under `tools/world_streaming*`. Main commands:

```sh
PYTHONPATH=tools python tools/world_streaming_regions.py \
  /workspace/port-research/rockport/samples/L2RA.BUN \
  /workspace/port-research/world-streaming/original-regions-and-dependencies.json
PYTHONPATH=/workspace/toolchains/python-deps:tools python tools/world_streaming_verify_policy.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --manifest /workspace/port-research/world-streaming/render-availability-manifest.json \
  --index /workspace/port-research/rockport/samples/L2RA.BUN \
  --output /workspace/port-research/world-streaming/original-policy-stage-verification.json
PYTHONPATH=tools:tests python -m unittest \
  tests/test_world_streaming_recovery.py tests/test_world_geometry.py tests/test_world_instances.py
```

Nineteen tests pass, including corrupt region vertex counts, nonfinite polygon
points, crossing collision ranges, original slot sentinels/fallback, source
constraints and stateful overlap order.

This is a source-backed selector POLICY STAGE suitable for review and a bounded
runtime translation. It is not full 3DS streaming yet. Remaining original systems:
nearest-region fallback, distance-based model LOD choice, predictive preload,
readiness/callback-dependent load order, dynamic special-group membership, asset
budgets and eviction, materials, the remaining external consumed references, and
integration into a bounded on-SD database/runtime loader. Original packet recovery
and header-statistic diagnostic stay isolated pending root review.
