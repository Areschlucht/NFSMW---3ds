# Same-hash original model equivalence checkpoint

Audit result:1782 of1784 ambiguous model-hash groups have identical consumed
geometry **and** the conservative material/metadata guards below. Those1782
groups contain4975 decodable raw variants. No genuine consumed-geometry
difference was found among those variants. The remaining2 groups contain5
decoder-rejected variants and remain unresolved; they cannot use the sharing map.

The audit retains4980 raw identities and10870 source occurrences. It does not
choose a global canonical variant by model hash or erase source bytes/provenance.
The opt-in decoder accepts only the independently proven nonconsumed triangle
header statistic mismatch; all descriptor, attribute, finite-position and bounds
checks remain enabled.

## What is compared

Each ordered triangle includes its original texture hash and all three ordered
corners: decoded float32 XYZ, original signed-short Q12 UV bytes, and **all four
original colour bytes**. This retains the fourth material/night-light metadata
byte rather than substituting the prototype's generated alpha1. Original signed
zero bits survive float32 packing. A separate signature covers every ordered
strip corner, including degenerate triangles omitted by the face decoder.

The conservative sharing key additionally guards:

- Raw64-byte matrix and the full160-byte model header. The statistic is
  nonconsumed by the draw emitter, but the recovered LOD consumer uses its
  original signed>39 gate; it is therefore retained in the guarded key.
- Every draw descriptor's bytes4..15, retaining primitive/index-width flags,
  format, corner count and unknown/material fields. Only the relocatable blob
  offset is excluded; all fetched attributes are covered separately.
- Each consumed8-byte texture/material reference and the entire reference leaf.
- All28 bytes of geometry metadata and every unknown model/geometry leaf.

Thus geometry-only matches never imply full sharing when these guards differ.
Different source index widths can be geometrically equivalent but still fail the
conservative key. No such guarded mismatch occurred in the decodable ambiguous
groups here. All variant names also agree within their original hash groups.
Unknown guards can cause unnecessary nonmerges on future data, which is safer
than accidentally merging a distinct material. This does not prove the current
3DS shader implements the original GX material pipeline.

Alignment/padding and other unconsumed raw-layout differences account for the
raw identities without changing these checked semantics. Their exact original
bytes remain attached as aliases. Do not rewrite the original archives or treat
the consumed-signature key as an original-game identifier.

## Safe exporter use

Research files:

- `/workspace/port-research/hardware-optimization/model-equivalence/audit.json`
  contains all layered signatures, classifications and exact aliases.
- `catalog.json` maps each raw SHA256 in the ambiguous groups to an
  `original_hash:catalog_sha256` key, or null for unresolved models. Preserve this
  entire tuple, source offset/section and raw SHA for selection/provenance.

The exporter can share a decoded immutable geometry/material payload only when
these verified catalog keys match. Instance transforms, original LOD slots,
section residency, source occurrence ordering and load ownership remain separate.
Never infer that identical payload means identical activation. Single-raw-variant
hashes are outside this audit and retain their independently validated raw key.
The same material texture hash can still resolve through a different external
bank: preserve verified texture source identity/bank context outside this model
key. Mutable original runtime material state also remains separately owned.

Unresolved groups, all `Invalid geometry metadata/bounds`:

| Original hash | Name | Raw variants | Source sections |
| --- | --- | ---: | --- |
| 20d180ce | SOUND_TUNNEL_OVERPASS_00 | 3 | 2208,1853,1854 |
| 3c2b497a | ANM_TOWERCRANEARM_07 | 2 | 1841,1414 |

Do not replace these with a nearby model, count them as ready geometry, or relax
the decoder to manufacture faces. The source records may be non-render objects;
that classification remains unproven.

## Reproduction and checks

```sh
python tools/perf_model_equivalence.py --output \
  /workspace/port-research/hardware-optimization/model-equivalence/audit.json
python tools/perf_model_equivalence_validate.py
```

The full source-stream SHA256 is verified against the inventory before decoding.
Each representative raw model is SHA256 checked against its occurrence record.
Only one model is decoded at a time using an mmap of the original stream; global
triangle arrays are never accumulated. The result retains only signatures and
provenance. Mutation checks on real source data confirm RGB, fourth metadata byte,
UV, matrix, material-reference and original statistic changes break the appropriate
equivalence. All current ambiguous-group aliases have identical original
statistics, so retaining this additional guard does not change the1782-group
sharing result. Catalogschema2 keys replace the initial statistic-zeroed keys.
Shared decoder, renderer and exporter files were not modified.
