# Exact world indexing checkpoint

This is a reviewed optimization prototype and audit harness. It is not wired
into the v0.16 renderer by these files. The parent agent owns any production
integration and emulator/hardware checks.

## Result on the current world

The v0.16 world GPU format uses float32 XYZ, UV and RGBA (36 bytes). Exact byte
deduplication preserves every value, signed zero, triangle corner order and
material boundary:

| Representation | Vertex records | GPU bytes including indices |
| --- | ---: | ---: |
| v0.15 expanded, 48-byte vertices | 112,077 | 5,379,696 |
| v0.16 expanded, 36-byte vertices | 112,077 | 4,034,772 |
| Proposed exact indexed world, 36-byte vertices/u16 | 50,176 | 2,030,490 |

The proposed storage is 49.675% smaller than v0.16. The unique vertex bytes are
1,806,336; the index stream is 224,154 bytes. The vertex region already happens
to be 128-byte aligned in size for this scene. Allocator metadata/tail padding
is not counted in the table.

Native ASan/UBSan checks reconstruct all 112,077 ordered corners and all 1,046
ordered material streams exactly. The full packed stream and reconstructed
stream have the same SHA-256:

```text
d31638a18bc77f85c46028421b10b68ad81ffbb2fa2dbd18755961ccd68e41fb
```

No triangle ordering, culling, texture, model placement, colour precision,
render distance or file-format changes are required by exact indexing.

## Prototype and failure paths

`perf_world_index.c/.h` consumes validated `NfsVertex` data and returns CPU
allocations containing the exact existing `WorldVertex` representation plus
u16 indices. It uses first-occurrence ordering and byte comparisons. A fixed
bound of 200,000 source corners matches the current scene decoder.

The hash table has bounded size and a total probe budget of `count * 32`.
Allocation failure, probe-budget exhaustion, invalid input and more than 65,536
unique records are explicit return statuses. Every failure leaves an empty
output; overflow/budget/allocation failure can retain the existing DrawArrays
path. Output must be empty before calling; free any earlier result first.

Tests cover the exact u16 boundary, overflow cleanup, signed-zero distinction,
low-bit float colour distinction, nonfinite input, nonconsecutive reuse,
source preservation, material reconstruction and double-free-safe cleanup.
The prototype also compiles cleanly for the pinned ARMv6K/hard-float toolchain
with `-Wall -Wextra -Werror` (888 bytes of ARM text in this build).

## GPU integration requirements

The pinned SDK exposes:

```c
void C3D_DrawElements(GPU_Primitive_t primitive, int count, int type,
                     const void *indices);
// C3D_UNSIGNED_SHORT == 1
```

Use the unchanged batch/run count as the **index count** and an index pointer
offset by the unchanged `first` field:

```c
C3D_DrawElements(GPU_TRIANGLES, count, C3D_UNSIGNED_SHORT,
                 gpu_indices + first);
```

The malloc pointers returned by the prototype are not GPU buffers. Copy them to
GPU-accessible linear memory and flush CPU writes before drawing. A single
linear allocation containing the vertex region followed by a 128-byte-aligned
index region, with total allocation rounded up to 128 bytes, is a conservative
layout. Do not pad individual index runs: a `uint16_t` offset preserves the
required 2-byte entry alignment even when it is not 4/16/128-byte aligned.

The pinned libctru `linearAlloc` implementation requests 128-byte alignment.
The inspected Citro3D `BufInfo_Init` initializes `base_paddr` to `0x18000000`.
`C3D_DrawElements` converts the index pointer to a physical address, returns
without a draw when it is below the bound buffer base, and emits:

```text
(index_physical_address - buffer_base_physical_address) | (type << 31)
```

Thus vertex/index memory must be GPU-accessible and the offset must not consume
the type bit. A single contiguous linear allocation avoids ambiguity if a
future renderer changes the buffer base. The SDK does not add an explicit
pointer-alignment check. Native codec boundary tests are not proof of all
hardware edge cases; actual data uses a maximum index of 50,175, not 65,535.

The same SDK disassembly explicitly writes zero to `GPU_VERTEX_OFFSET` at
`C3D_DrawElements + 0xa8..0xb8` (literal `0x000f022a`), so a preceding car
`DrawArrays(first > 0)` does not leave a stale base vertex. It writes 1 to
`GPUREG_RESTART_PRIMITIVE` (`0x025f`) before the draw. This is a register write;
no CPU index-sentinel scan is present. The index count is forwarded to
`GPUREG_NUMVERTICES` (`0x0228`) without a CPU clamp. Hardware maximum-count or
special-index behavior is not established by this inspection.

These details were checked in this exact offline image:

```text
devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5
```

## Visibility and cache models

The audit compiles a host bridge to the actual portable reset-camera and
visibility functions. It reproduces all 24 existing sampled visible-triangle
counts and merged-draw counts exactly. Cache modeling uses those actual merged
visible runs, resetting the hypothetical cache at every draw.

| View | Index references | Merged draws | Hypothetical FIFO32 misses |
| --- | ---: | ---: | ---: |
| Starting view | 31,464 | 84 | 16,589 |
| Dense northwest, heading +30° | 98,127 | 169 | 48,917 |

The JSON includes FIFO/LRU models at 8, 16 and 32 entries. These are explicit
models, not a statement that PICA200 has any particular post-transform cache,
retains entries across draws, or executes this many vertex shaders. Indexed
GPU throughput and FPS need a renderer implementation, pixel comparison and
stock-hardware measurements. Indexing can add index-fetch work, and no speedup
is guaranteed from a smaller allocation alone.

## Reproduce

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Iinclude -Itools tests/test_perf_world_index.c tools/perf_world_index.c \
  source_bmw/world_vertex.c source_bmw/nfs_scene.c -lm -o /tmp/test-perf-index
/tmp/test-perf-index /workspace/port-research/rockport/scene-v0.15/world.nfm
python -m unittest discover -s tests -p 'test_perf_world_index.py'
python tools/perf_world_index_audit.py \
  /workspace/port-research/rockport/scene-v0.15/world.nfm \
  --pose start /workspace/port-research/rockport/scene-v0.15/road.nrd \
  --pose northwest /workspace/port-research/rockport/v0.14/inspection-northwest-road.nrd \
  --output /workspace/port-research/hardware-optimization/indexed-world
```

The raw output files are research GPU streams without a loading protocol. They
must not be copied into an installation ZIP and loaded as trusted sidecars.
The current production proposal instead derives indexing at startup after the
existing NFM validation, retaining the existing asset protocol.

## Further source-equivalent packing opportunity

Every current world corner's float colours reconstruct bit-exactly from RGBA8,
and every UV reconstructs bit-exactly from the original signed S16/4096 pair
with the existing V flip. Keeping float32 positions and those original-like
attributes would make a 20-byte GPU format. The current scene would remain
50,176 unique records and need 1,227,674 bytes including u16 indices.

This is a CPU representation check only. A GPU shader would need integer-to-
float UV scaling and colour normalization; PICA float rounding, interpolation
and final pixels must be compared before accepting it. No such shader or
renderer integration is part of this checkpoint. The audit reports the exact
reconstruction counts so future work can reject any scene whose attributes
cannot be packed without losing source information.
