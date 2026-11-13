# Exact vehicle vertex indexing

`vehicle_index_encode` replaces repeated full48-byte NfsVertex values with
stable unique vertices and an unsigned16-bit index list. It does not change
geometry, normals, UVs, color/alpha, triangle order, material batches or wheel
groups. This is a native rendering optimization, not a recovered original-game
vertex layout or a measured target FPS improvement.

## Contract and bounded work

`include/vehicle_index.h` returns VehicleIndexedVertices containing owned ordinary
malloc buffers, unique vertex_count and original index_count. FNV-1a hashes all
48 source bytes. Open addressing resolves collisions with a full48-byte memcmp;
the first occurrence determines unique order. Positive/negative zero and even
low mantissa-bit differences remain distinct. No float canonicalization occurs.

Inputs must be finite triangle lists with count1..200000 and count divisible by3.
The NFM decoder remains responsible for semantic normal/UV/color validation.
At most65535 unique vertices are allowed by this API. A power-of-two hash table
has at least twice the input count; total collision probes are capped at count*32.
Overflow, invalid data, allocation failure or exhausted probe budget returns an
explicit result and leaves the caller's previous output unchanged. A caller may
keep its existing DrawArrays path. Free a previous successful result before a
successful replacement; vehicle_index_free is safe on NULL/zeroed results.

Returned vertex allocation capacity can exceed unique vertex_count. It is a
startup buffer to copy and free; only vertex_count*48 bytes belong in the GPU
vertex region. No speculative realloc is needed for the rendering savings.

## Integration points

The parent owns shared main-loop/build changes. For each non-world car mesh:

1. Keep the original decoded batch ranges, texture slots and wheel-rig groups.
2. Index the original decoded NfsVertex list before changing V coordinates.
3. Allocate flushed linear memory for unique vertices followed by aligned
   uint16_t indices, as with the existing world-index path.
4. Copy only unique vertex_count*48 bytes, then apply the existing `v=1-v` change
   once to each unique GPU vertex. Retain the original index_count and batch
   first/count values for draw iteration and original-data validation.
5. Ground-offset/bounds loops over the unique GPU vertex buffer must use its
   unique count, rather than the original expanded scene count. The source NFM's
   original count should remain available separately.
6. Use DrawElements with each unchanged batch's index range and original
   texture/model matrix. Deduplicating across two batches does not merge their
   material binding or wheel transformation; those remain per draw.

An integration that copies/updates the old expanded count into the smaller unique
buffer would overrun into indices. The supplied helper alone does not alter a
live buffer, texture or draw command.

## Actual six-mesh measurements

These are current private original-derived NFM assets: BMW source-normal v0.18,
all four native-v2 starter cars, and native-v2 TRAFHA. GPU bytes below are useful
vertex/index bytes before the parent's128-byte allocation alignment. Raw source
NFM files can have32-byte vertex records; this comparison uses the actual expanded
48-byte GPU NfsVertex used by the current car shader.

| Mesh | Expanded vertices | Unique vertices | Old GPU bytes | Indexed GPU bytes | Saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| BMW M3 GTR | 23112 | 8087 | 1109376 | 434400 | 60.84% |
| Cobalt SS | 21573 | 7507 | 1035504 | 403482 | 61.04% |
| Golf GTI | 20952 | 7330 | 1005696 | 393744 | 60.85% |
| Lexus IS300 | 20418 | 6844 | 980064 | 369348 | 62.31% |
| Fiat Punto | 22368 | 8146 | 1073664 | 435744 | 59.42% |
| TRAFHA | 2700 | 1270 | 129600 | 66360 | 48.80% |

Savings are memory/transfer quantities. Draw-call count and triangle count are
unchanged; GPU post-transform-cache effectiveness and frame time still need
target/emulator measurement. No distant geometry or traffic detail was deleted
to obtain these results.

## Verification

`tests/test_vehicle_index.c` reconstructs every original48-byte vertex in all
six meshes and compares it byte for byte. It repeats encoding to establish
deterministic output, preserves every source batch/texture range and wheel group,
and checks original/unique position extents agree. Source wheels.nwa is validated
against each NFM's original batch count and body CRC before group assertions.
It also applies the actual existing V flip to expanded and unique copies, then
reconstructs/compares all48 GPU attribute bytes again after that transformation.

Synthetic tests cover every float component's low bits, signed-zero and seams,
exact stable index order, invalid pointers/counts/nonfinite data, the65535-unique
boundary and transactional overflow. Deliberately clustered hashes exercise
successful collision resolution and bounded-budget fallback. ASan/UBSan, strict
C11/pedantic warnings and scoped whitespace checks pass.

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude \
 tests/test_vehicle_index.c source_bmw/vehicle_index.c source_bmw/nfs_scene.c \
 source_bmw/wheel_motion.c -lm -o /tmp/nfsmw-vehicle-index-test
/tmp/nfsmw-vehicle-index-test \
 /workspace/port-research/bmw/scene-v0.18-source-normals \
 /workspace/port-research/starter-cars/native-v2/COBALTSS \
 /workspace/port-research/starter-cars/native-v2/GTI \
 /workspace/port-research/starter-cars/native-v2/IS300 \
 /workspace/port-research/starter-cars/native-v2/PUNTO \
 /workspace/port-research/starter-cars/native-v2/TRAFHA
```

Original assets remain private. This subtask did not edit shared runtime/build
files, perform an SDK build, commit or push.
