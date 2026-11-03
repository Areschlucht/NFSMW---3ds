# Compact world vertex fidelity research

This is an isolated research checkpoint, not an enabled production optimization.
The 20-byte and 24-byte candidates change rendered pixels and must stay disabled.
The 32-byte candidate matches the tested emulator views, but physical 3DS fidelity
and performance are still unverified.

## Representation and strict conversion

`perf_vertex20.h/.c` packs float XYZ, original signed Q12 UV, and RGBA8 into
20 bytes. `perf_vertex20_components.h/.c` independently test SHORT UV with float
RGBA (32 bytes), and float UV with byte RGBA (24 bytes). Positions retain their
original bits. Every conversion reconstructs the original 36-byte WorldVertex
and compares all bytes before accepting the record. No quantization is accepted.
NaNs, signed-zero changes, out-of-domain UV and nonrepresentable colours reject
the conversion. A failed conversion may have written a prefix; discard that
candidate buffer and retain the original representation. These are CPU buffers;
they do not establish GPU physical allocation, flushing or lifetime.

All 112077 corners of scene-v0.15 reconstruct byte-exactly on CPU with all three
codecs. Tests include all 256 colour levels, SHORT extremes, signed zero and
invalid input. Nine current corners would overflow if the already-flipped V
were packed: flipped V reaches 8.471435546875, outside signed Q12. Store the
original V and perform `1 - V/4096` in the shader. This also covers the full
original signed-short domain, rather than only today's map subset.

Unique counts remain 50176, with 112077 ordered u16 indices. Logical GPU bytes
(before trailing allocation alignment) are:

| World format | Unique vertex + index bytes | World shader source instructions |
| --- | ---: | ---: |
| Indexed float36 baseline | 2030490 | 13 |
| SHORT UV + float RGBA32 | 1829786 | 14 |
| Float UV + byte RGBA24 | 1428378 | 13 |
| SHORT UV + byte RGBA20 | 1227674 | 14 |

These memory figures are arithmetic, not measured bandwidth or FPS improvements.
The extra shader instruction may offset any UV32 bandwidth benefit.

## Loader and shader constraints

The pinned devkitPro PICA loader formats are `GPU_FLOAT,3`, `GPU_SHORT,2`,
`GPU_UNSIGNED_BYTE,4` for the full candidate. No normalization flag is requested.
The raw byte/short interpretation is consistent with both tested Azahar shader
backends: using explicit 1/255 and 1/4096 scales produces matching or nearly
matching output, rather than double-normalized attributes. This observation does
not replace an actual hardware attribute conformance test.

The assembler accepts `mul outclr, constants.zzzz, vertexcolor`, not the reversed
uniform placement. It rejects a MAD with both uniform scale and uniform bias in
the attempted source positions (`invalid source3 register: constants`). A valid
full-domain UV reconstruction is:

```text
.constf constants(0.0, 1.0, 0.00392156862745098039, 0.0)
.constf uvscale(0.000244140625, -0.000244140625, 0.0, 0.0)
mov r2, constants
mad outtc0, texcoord, uvscale, r2
```

Byte colour uses the constant's Z reciprocal255. CPU float division by255 being
exactly reversible does not make this shader arithmetic equivalent to loading
the precomputed float colour. The ablation below isolates a real difference in
that colour conversion path. The exact physical PICA rounding mechanism has not
been established.

## Pixel comparisons

Frozen baseline and all candidates use the same indexed world geometry,
materials, camera, clipping and car shader. Only world vertex representation,
loader formats and reconstruction instructions differ. Stationary reset views
cover the default start and a crowded northwest view. Comparisons crop the full
400x240 top screen, 96000 pixels. Azahar 2126.2 runs with accurate multiply and
llvmpipe inside a separate offline research container. No root emulator/state is
used. Hardware-VS here names an emulator backend, not a physical 3DS.

| Candidate / backend | Default changed pixels | Dense changed pixels | Max channel difference |
| --- | ---: | ---: | ---: |
| Full20, hardware VS | 1 | 0 | 1 |
| Byte colour24, hardware VS | 1 | 0 | 1 |
| SHORT UV32, hardware VS | 0 | 0 | 0 |
| Full20, software VS/JIT | 3 | 0 | 1 |
| Byte colour24, software VS/JIT | 3 | 0 | 1 |
| SHORT UV32, software VS/JIT | 0 | 0 | 0 |
| Full20, interpreter VS | 0 | 1 | 1 |
| Byte colour24, interpreter VS | 0 | 1 | 1 |
| SHORT UV32, interpreter VS | 0 | 0 | 0 |

The byte-colour-only ablation reproduces the full candidate's exact changed
pixels. The UV-only ablation is exact in these four comparisons. The default
hardware-VS differing pixel is (66,231), RGB (33,35,37) to (33,35,36).
Software VS/JIT additionally changes (247,68) from (68,65,62) to (68,64,62), and
(218,79) from (39,39,40) to (39,39,41). Tiny differences still fail a strict
pixel-equivalence requirement; do not silently accept them as lossless.

Interpreter VS instead differs at the dense pixel (226,98), with both full20 and
colour24 producing the same difference. Thus the mismatch is backend-dependent,
but is observed on every tested backend in at least one view. SHORT UV32 matches
all six backend/view comparisons. Per-artifact SHA256 hashes are saved alongside
these reports under the research directory. Finite views cannot prove every
possible viewpoint or hardware precision behavior.

## Reproduction and ownership

Research root: `/workspace/port-research/hardware-optimization/vertex20/`.
It contains frozen baseline/candidate project copies, source manifests, built
3dsx files, top-screen captures, amplified difference images and JSON reports.
Build each copy using its own `tools/build_rockport.sh` with
`EXTRA_CFLAGS=-DNFS_EXPERIMENTAL_WORLD_INDEX` and the pinned SDK image recorded in
that script. `perf_vertex20_prepare.py uv32` or `color24` creates new component
projects from the baseline and refuses to overwrite an existing project.

Native codec validation, from the repository root:

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Iinclude -Itools tools/perf_vertex20_test.c tools/perf_vertex20.c \
  source_bmw/world_vertex.c source_bmw/nfs_scene.c -lm -o /tmp/vertex20-test
/tmp/vertex20-test /workspace/port-research/rockport/scene-v0.15/world.nfm
cc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Iinclude -Itools tools/perf_vertex20_components_test.c \
  tools/perf_vertex20_components.c source_bmw/world_vertex.c \
  source_bmw/nfs_scene.c -lm -o /tmp/vertex-components-test
/tmp/vertex-components-test /workspace/port-research/rockport/scene-v0.15/world.nfm
```

`perf_vertex20_capture.py` operates only on `nfsmw-vertex20-emulator` with its
separate state; it requires that offline container and X display already be
prepared. Its backend modes include hardware-VS, software-VS/JIT and interpreter.
Do not run it concurrently with another capture in that container. It deliberately
does not create, restart or stop shared emulator infrastructure.

## Further exact opportunity

The current body.nfm v1 has 23112 corners and all-white colour. A strictly
preflighted white-colour car specialization could omit 16 colour bytes per
corner, retaining float position/normal/UV and replacing multiplication by white
with a move of the lighting result. Its vertex buffer would be 739584 versus
1109376 bytes, saving 369792 bytes. Preserve the original48 path for coloured
assets. The existing car ground-offset scan indexes NfsVertex GPU records, so
that scan must instead use original CPU data before freeing it. This is an
unimplemented proposal, with no pixel or speed claim.
