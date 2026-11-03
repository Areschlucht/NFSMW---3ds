# Streaming memory admission checkpoint

`perf_stream_budget.py` audits all 997 source sections and 435 original ordered
dependency lists, each with mandatory banks2500,2400,2600. It uses exact physical
index IDs and skips absent logical IDs, matching the recovered normal gather.
It does not infer +40 render/collision mappings. Collision bytes are joined by
the separate verified physical containment report and deduplicated by SHA256.

Reproduce with:

```sh
python tools/perf_stream_budget.py --output \
  /workspace/port-research/hardware-optimization/stream-budget/source-budget.json
```

The artifact includes SHA256 provenance, per-section and per-region numbers.
Content classes describe observed texture/model/object content; original
allocation-phase category predicates remain unverified.

## Measured source inventory

| Set | Raw section bytes | Validated stored-model triangles | Available texture hashes |
| --- | ---: | ---: | ---: |
| Three mandatory banks | 1264684 | 10001 | 221 |
| Largest raw region717 + mandatory | 4895092 | 77956 | 352 |
| Region803 + mandatory | 4849424 | 78103 | 342 |
| All997 physical sections | 108256544 | 1309940 | 1590 |

Maximum individual section is936960 bytes. Mandatory bank content comprises
936960 texture bytes,326588 model-bank bytes and1136 instance-bank bytes.
Region717 contains17 unique embedded collision packs,303648 raw bytes.
Region803 contains15,292832 bytes. Across the full file,390 unique collision
packs total5795264 bytes. These bytes already lie within sections: adding them
again to raw section totals would double-count them.

Full-source models comprise16752 raw variants,16604 accepted by the original
strict decoder and148 rejected variants. No rejected packet is silently enabled.
There are99337 object instances. Choosing a particular original LOD, transforming
or duplicating instanced geometry, or discarding geometry is not performed here.

## Converted estimates and unknown costs

For each distinct validated stored model once, the conservative allocation
estimate uses36 bytes per expanded corner plus2-byte indices and128-byte
alignment per vertex/index block. Exact dedup may lower it; DrawArrays fallback
does not exceed it. Region803 is largest at9029632 bytes; mandatory banks alone
1168384; all validated stored variants151435648 bytes. This is an estimate for
that representation, **not converted resident memory**. It excludes rejected
models, instance copies, actual LOD activation, CPU temporary vertices, materials,
textures and runtime collision structures. It neither proves nor disproves the
eventual faithful region working set fitting.

Texture hashes/source compressed package lengths cannot determine GPU residency.
Require actual padded dimensions, PICA format and mip levels from converted
assets, with `C3D_Tex.size`/actual allocator charge checked at load time. Do not
use compressed .t3x disk bytes as texture memory. Runtime collision cost needs
verified record layouts and acceleration structures; raw source length is not a
substitute. Both converted costs remain null in the audit, deliberately.

The present host-converted NFM loader also holds raw input, decoded48-byte CPU
corners, exact-index candidate vertices/indices and hash table during loading.
For112077 corners that stage includes approximately5.38MB decoded vertices,
2.36MB candidate vertex capacity,224154B indices and1MiB hash table, in addition
to raw NFM input and existing resident data. Streaming should load preconverted,
validated bounded GPU-ready records or bounded packets, rather than repeat this
whole-scene peak for overlapping regions. No asset protocol change is made here.

## SDK resource limits verified in the pinned image

Pinned libctru2.7.0 `__system_allocateHeaps` queries process resource-limit maximum
minus current usage, aligns down4096 and splits the remaining allowance. With
both weak heap-size overrides zero, small allowances split about half/half. Above
48MiB it first gives normal heap24MiB; linear heap is capped32MiB and additional
allowance returns to the normal heap. Hence New3DS physical RAM is not the
application's usable allocation budget, and default linear memory never exceeds
32MiB. Launcher/resource settings and executable usage can lower both pools.

Verified APIs in this pinned SDK:

- `envGetHeapSize()` and `envGetLinearHeapSize()` expose assigned pool sizes.
- `linearSpaceFree()` calls allocator GetFreeSpace: total free, not proof of one
  sufficiently large contiguous block. Allocation may still fail.
- `linearAlloc()` aligns128 bytes; `linearRealloc()` is unimplemented and returns
  null. Allocate final bounded blocks rather than plan to grow in place.
- `osGetMemRegionFree(MEMREGION_APPLICATION)` describes the system application
  region, not this process's malloc/linear allocatable free bytes. Default heap
  allocation already commits its regions. Do not use it as cache capacity.
- `C3D_DEFAULT_CMDBUF_SIZE` is0x40000. Framebuffers, render/depth targets, texture
  allocations, car geometry and command/driver state all need accounting before
  deciding world-cache space. Normal and linear pool capacity are independent;
  free bytes from one cannot pay allocations in the other.

These facts come from headers and ARM disassembly in pinned image
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
No physical hardware heap measurements are available in this checkpoint.

## Recommended first admission policy

Use separate **actually allocated** normal and linear arenas after graphics,
car, UI and mandatory fixed-state initialization. This makes admission capacity
real and bounds fragmentation. Proposed conservative starting ceilings, not SDK
limits:20MiB for world linear residency,12MiB for world normal residency,4MiB for
transient normal decode/IO. Lower any ceiling until allocation succeeds while
leaving2MiB linear and4MiB normal safety headroom. A launcher with less memory
gets smaller arenas or a clear initialization failure; never silently assume the
ceiling exists. Allocate or otherwise guarantee headroom rather than infer normal
free from a misleading system-region count. Tune these provisional ceilings only
after measuring actual device high-water marks.

Linear admission charges geometry, indices, texture pixels/mips and alignment
together; normal admission charges collision/query/instance/material state,
metadata and pinned ownership structures. Scratch has its own independent cap.
A1MiB input window covers every current uncompressed source section, but is not
a guaranteed decode workspace: expansion can exceed it. Reject a packet requiring
more than the declared4MiB scratch arena; split/preconvert it offline with exact
validation rather than grow unexpectedly. Keep all existing loader count/CRC
checks and reject integer overflow before allocation.

For a transition, cost the **set union** of mandatory banks, both actual viewpoint
request lists, still-required previous residency and GPU-in-flight references.
Deduplicate only by verified resource identity; a model hash alone can represent
distinct raw variants. A resident resource costs zero *additional* bytes only
when an existing owned allocation is verified. Unknown conversion costs must
produce NOT_READY/UNKNOWN_COST, never zero-cost success. Read and validate the
whole required collision/render transaction before publishing it to simulation.

On allocation/read/CRC/validation/unknown-cost failure, release only the staged
transaction, retain the last complete resident state, and report failure to the
coordinator. Do not remove required collision, substitute a different LOD, enable
804MHz/L2, or claim an unready region is safe to drive into. Explicit eviction
can select only resources no longer pinned by either viewpoint, physics or
in-flight GPU work; wait for the corresponding GPU completion before freeing.
If the verified union cannot fit, stop admission and surface that fact. Recovering
the original activation/LOD policy and converted costs precedes fidelity claims.
