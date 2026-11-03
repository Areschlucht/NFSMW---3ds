# Exact streamed texture upload contract

The manual conversion in `perf_tiling.py` matches pinned tex3ds v2.3.0
GPU_RGBA8 payloads byte-for-byte in47 cases:all35 native WTX dimensions plus12
real original textures, comparing1279488 GPU bytes. Every vertically flipped
control fails. The actual C helper `streamed_world_texture_rgba8` was then
checked against the same47 cases:reference mode exactly matches tex3ds, and
production mode exactly preserves the intended source RGB/opacity policy.
GPU upload/final rendered pixels remain separate emulator/hardware checks.

Root selected `zero_transparent_rgb=false` for production to preserve original
hidden RGB. The tex3ds-compatible zeroing mode is an offline reference control
only. Production deliberately differs from tex3ds at those transparent RGB bytes;
it must not be described as an identical tex3ds payload.

Artifacts: `/workspace/port-research/hardware-optimization/tiling/validation.json`,
source PNGs, tex3ds uncompressed raw/T3X files and source WTX hashes. Docker used
the pinned SDK image with `--network none` and a task-owned mount only.

## Exact tex3ds-reference order

1. Read/validate WTX1 header128, dimensions, payload length and CRC. Source
   pixels are ordinary top-to-bottom row-major RGBA. Native quality tier0 is
   not rescaled.
2. Apply the original `world_rgba` opacity policy:alpha test is enabled only
   for mode==1. When blend==0 and alphaTest!=1, force alpha255 while retaining
   RGB. For supported blend1/2 or alphaTest1, retain source alpha. Reject
   unsupported blend modes rather than guess.
3. In offline reference mode only, for parity with the PNG→tex3ds pipeline, make all four components
   zero when the **effective alpha is zero**. Otherwise reverse RGBA to ABGR
   bytes. This is a measured tex3ds transparent-pixel canonicalization, not
   an assumption that invisible source RGB never matters to filtered edges.
   Production instead retains these RGB components even when alpha0.
4. Swizzle into8x8 Morton tiles with tiles in row-major order. Keep source row0
   at texture row0. **Do not vertically flip the upload.** Existing renderer
   UV conversion `v_gpu=1-v_source` remains unchanged.
5. Upload exactly width*height*4 texel bytes as GPU_RGBA8, with the usual linear
   allocation, cache flush and GPU lifetime rules. Container metadata is not
   texture pixel memory.

For source pixel(x,y), using effective RGBA after opacity policy:

```text
morton = (x&1) | ((y&1)<<1) | ((x&2)<<1) | ((y&2)<<2)
       | ((x&4)<<2) | ((y&4)<<3)
byte_offset = (((y>>3)*(width>>3)+(x>>3))*64 + morton)*4
gpu[byte_offset..+4] = [A,B,G,R]
// Offline tex3ds reference mode only: [0,0,0,0] if A==0.
```

The current native corpus has2703 WTX resources. Its alpha/blend combinations
include619 with alphaTest2/blend0; interpreting any nonzero alphaTest as enabled
would therefore be wrong. All actual dimensions are power-of-two8..512 with
aspect ratios up to64:1. Synthetic cases cover every actual dimension, including
8,16,32,128 squares and both rectangular orientations. Reject unsupported
non-power-of-two dimensions until their padding/subtexture coordinates have
their own validated contract; no rescale/padding guess is introduced here.

## Transparent-pixel difference

The initial direct RGBA→ABGR swizzle differed at transparent colored pixels.
For example source RGBA(0,0,17,0) is stored by tex3ds as ABGR(0,0,0,0), not
(0,17,0,0). Adding only this canonicalization makes all47 cases exact.

This also affects real original textures in the test set:

| WTX resource | Changed bytes without alpha0 RGB canonicalization |
| --- | ---: |
| 0a082df4-097823b2… | 1098 |
| 1a8a292b-4847ccf0… | 9780 |

For opaque-policy textures, force alpha255 **before** any reference alpha0 check, so
otherwise valid original RGB is preserved. Raw source WTX RGBA remains untouched;
reference zeroing applies to its GPU conversion target only. The production
renderer preserves source RGB-at-zero-alpha to retain original filtering input;
the two policies are explicitly separate and their edge pixels still need an
emulator comparison.

## T3X and raw container bytes

Commands tested are `tex3ds -f rgba8 -z none -r` and the same command without
`-r`. Even raw mode prepends a4-byte fake compression header:byte0=0 followed
by24-bit little-endian uncompressed length. The actual tiled GPU payload starts
at byte4. Every single-image T3X in this corpus has17 bytes of texture/subimage
metadata before the same4-byte header. Its suffix is exactly the entire raw
file; the GPU payload matches after stripping container headers.

All current inputs already satisfy native power-of-two dimensions and no mipmap
option is passed. Thus no extra texel padding or mip allocations occur in these
comparisons. The17-byte metadata observation is for these single-image files,
not a general T3X atlas parser.

## Reproduction

```sh
python tools/perf_tiling.py
# Recheck previously generated pinned reference files without reconversion:
python tools/perf_tiling.py --reuse-reference
python tools/perf_tiling_native.py
```

The script validates12 real WTX bounds/CRCs, applies the same opacity function
as the exporter, writes lossless PNGs, invokes the pinned offline SDK, and compares
every GPU byte. It saves positive and vertical-flip control results, source and
GPU hashes, and container metadata lengths. Native validation compiles the actual
pure C helper with strict warnings, checks both policies against independent
expected bytes, verifies output guard bytes/source immutability, and rejects
unsupported dimensions, insufficient capacity, unsupported blend and null inputs.
Production differs from tex3ds at14161 component bytes across all cases, exactly
the expected hidden RGB preservation differences. No main/build/shader files or
shared emulator state were changed.
