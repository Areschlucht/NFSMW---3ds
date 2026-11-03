# Original Rockport render-stream recovery checkpoint

Later findings and resolved gaps: see [POLICY-CHECKPOINT.md](POLICY-CHECKPOINT.md).
In particular, the 33 apparent placement failures below are now resolved through
original sibling LODs; the four-slot loader and original region selector are recovered.

The complete 109,279,744-byte stream is inventoried. This is an availability map,
not a proved original activation or LOD-distance policy, and not a full-city
runtime build. No existing decoder, exporter, or 3DS runtime file was changed.

## Validated inventory

- 997 original indexed sections, maximum section payload 936,960 bytes.
- 29,125 model occurrences; 13,556 model hashes; 16,752 distinct raw model blobs.
  1,784 hashes identify multiple different raw blobs. Keep source banks and offsets;
  selecting one global blob per hash discards original variants.
- 25,703 original object-table rows with all three ordered LOD slots retained,
  including zero slots, and all uninterpreted bytes preserved.
- 1,067 instance-table ranges, 99,337 original 64-byte placement records.
- 1,590 texture hashes available inside this stream. 416 geometry texture-reference
  hashes are absent here; they may be in global/external banks, which this report
  does not scan. 21 model-reference hashes are absent from this stream.
- All 997 instance sections pass the existing strict instance-table reader.
- `render-availability-manifest.json` is an 18.4 MB host manifest. It contains
  source ranges and metadata, not decoded mesh arrays. Generation maps the stream
  and copies at most one section at a time. It is NOT intended to load wholesale
  on a 3DS; conversion to a compact indexed on-SD database remains integration work.

## Original executable evidence

Verified USA DOL SHA256:
`33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`.

Original draw loop `0x8011773C..0x801181C0` reads descriptor flags at +12,
format at +13, vertex count byte at +8, and list length at +14. Compiled packets
call GXCallDisplayList at `0x803408CC`. Raw packets call GXBegin at `0x8033D2A8`
with primitive 0x98 and the descriptor vertex count, then emit position, colour,
and UV index bytes/halfwords to FIFO `0xCC008000`. The original loop does not
read the model header triangle statistic. Descriptor byte +9 is not consumed by
this loop. Refer to `original-render-stream.txt` and `render-loader.txt` for
addressed disassembly. Loaders align metadata/table to 16 bytes and blob to 32.

The bounded Unicorn reference executes these original instructions and intercepts
only GXBegin and GXCallDisplayList. Its verified report covers every packet in
all 168 triangle-statistic-rejected model occurrences: 4,826 draw occurrences,
3,330 unique descriptor/packet cases. Raw FIFO bytes match the source packet;
compiled display-list calls preserve exact packet bytes and length.

An isolated diagnostic wrapper retains the original count discrepancy and allows
the existing reader to reach all later array-index, finite-coordinate, and model
bounds checks. All 168 pass those checks. Among the resulting faces there are 209
exactly zero-area triangles with distinct position indices; the reference source
packets are retained, and no count is forced by changing degeneracy rules.

The model-level result does not prove every instance placement. Of 167 original
instance rows referencing these recovered hashes, 134 have a candidate LOD whose
transformed geometry agrees with stored world bounds within the existing 0.15
criterion. The other 33 remain unproved. Twenty-one additional model occurrences
with invalid geometry metadata (including sound-volume objects) remain rejected.

Reports: `original-packet-verification.json`,
`recovered-consumed-geometry-validation.json`, `initial-render-inventory.json`.

## Reproduction

Run from `/workspace/NFSMW---3ds`:

```sh
PYTHONPATH=tools python tools/world_streaming_inventory.py \
  --samples /workspace/port-research/rockport/samples \
  --output-directory /workspace/port-research/world-streaming
PYTHONPATH=tools python tools/world_streaming_manifest.py \
  --inventory /workspace/port-research/world-streaming/initial-render-inventory.json \
  --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
  --index /workspace/port-research/rockport/samples/L2RA.BUN \
  --output /workspace/port-research/world-streaming/render-availability-manifest.json
PYTHONPATH=/workspace/toolchains/python-deps:tools python tools/world_render_recovery_verify.py \
  --inventory /workspace/port-research/world-streaming/initial-render-inventory.json \
  --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/world-streaming/original-packet-verification.json
PYTHONPATH=tools:tests python -m unittest \
  tests/test_world_streaming_recovery.py tests/test_world_geometry.py tests/test_world_instances.py
```

Thirteen tests pass. Corruption tests verify the statistic diagnostic cannot
bypass bad indices, packet ranges, invalid compiled primitive, nonfinite positions,
or stored model bounds. The source bytes remain unchanged.

## Remaining work before runtime streaming

Trace original activation/dependency manager and LOD-distance selection; distinguish
same-hash bank variants by their original consumers; resolve external texture/model
references; prove remaining placements; establish working-set budgets from original
activation; export a bounded binary database and integrate renderer ownership/load
and eviction. Do not select a distance heuristic and call it original behavior.

Collision manifest is separately available at
`/workspace/port-research/map-collision/collision-streaming-manifest.json`:
450 physical packs, 390 unique, with duplicate aliases retained. There is no proven
global render-section to collision-ID mapping; no such mapping is invented here.
