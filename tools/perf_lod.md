# Original world model LOD recovery

Recovered the original ordered-slot decision and projected-size/FOV producers.
The portable optional module is `include/mw_lod_select.h` and
`source_bmw/mw_lod_select.c`. It is not added to production build/main. It does
not invent distance bands, activate sections or choose the highest LOD globally.

Validated primitives:

- Slot decision:9276 exact output matches against bounded unmodified original
  PPC802BEC38..802BED60, including all gates and boundary values.
- Original FOV coefficient:all65536 uint16 inputs match float32 bits against
  original800FFF14 and original polynomial sine/cosine.
- Projected-size producer:9510 exact score matches when supplied the original
  square-root stage as a host reference callback. Default target `sqrtf` instead
  differs in85 deliberately concentrated integer-boundary cases. The default
  NULL-callback score producer is therefore **not globally1:1**. The subsequently
  implemented portable `mw_gekko_sqrt_newton2` callback closes all9510 measured
  score cases; see `perf_gekko_math.md`. Production must use that callback to
  obtain this measured boundary behavior.

Strict pinned ARMv6K compilation passes:1148 bytes text, no static data/BSS.
No physical3DS timing or complete full-map renderer validation is claimed.

## Original consumer and source fields

The actual per-instance consumer starts802BEA40, called from the section spatial
tree traversal802BF270 at802BF340. This is downstream of original region
activation and section admission. It resolves an instance's signed object index
at instance+0x3E into a72-byte object row. The four bound model handles reside at
object+0x28,+0x2C,+0x30,+0x34, after previously recovered binding/fallback.

The selection uses original bound slots0,2,3. Slot1 is not directly chosen by
this decision; its handle can already alias slot0/2 through the original binding
fallback. Never replace a missing chosen handle with an invented sibling.

Fields consumed by the recovered math/decision:

| Field | Original source/producer |
| --- | --- |
| Instance translationXYZ | Original64-byte instance+0x20,+0x24,+0x28 |
| Instance flags | Originalinstance+0x18 |
| Object size/radius operand | Original72-byte objectfloat+0x38 |
| Bound slot0 model header statistic | Resolved handle+0x0C header, signed16 at header+0x14 |
| Bound slot0 metric | Resolved headerfloat+0x9C |
| Camera position | View/camera+0x40,+0x44,+0x48 copied into drawcontext+0x94..9C |
| Camera forward | View/camera+0x50,+0x54,+0x58 copied into context+0xA4..AC |
| Projection coefficient | View+0x0C copied into context+0xB4 |
| Context flags | Drawcontext+0x84 |
| Original view state | Getter800FE3E8 reads8041ACA0 |

Copies are at802BF724..802BF760. The source object loader byte-swaps float+0x38
at802BD844..848; it is not replaced by recomputed AABB size in this path.
The exporter should preserve raw original headers/instance/object rows, as the
world-streaming exporter now does. The semantic authored name/producer of the
model+0x9C field remains unproven; its exact consumed offset and arithmetic are
proven. Getter state is produced from view/camera ownership lists around800FE3F4;
calling it a user graphics-quality setting would be an unsupported inference.

All position/radius operands must use the same original source coordinate units.
The translation is **not an AABB center**. Baked TRN geometry can be far from its
model origin, making that distinction significant. Use original nativeXYZ with
Zup, or apply the same orthogonal viewer transform to translation, camera and
forward consistently. Do not feed normalized scene coordinates while leaving
the original size operand or constant6 unscaled. The module expects original
source units, avoiding this ambiguity.

## Projected-size score

The recovered producer802BEB24..802BEC38 computes the following, retaining
single-precision and fused multiply-add ordering in the portable function:

```text
d = original_instance_translation - original_camera_position
R = original_object_float_at_0x38 + 6.0f
if dot(d, camera_forward) < -R: score = 0
else:
    squared_distance = dot(d,d)
    distance = original_sqrt_stage(squared_distance) if squared_distance > 5e-11f else 0
    gap = distance - R
    projected = projection_coefficient
    if gap > R: projected = (R * projection_coefficient) / gap
    score = truncate_toward_zero(projected)
```

Original constants:80409AE4=6,80409AE8=5.00000006675716e-11,
80409AEC=0.5,80409AF0=1,80409AF4=0,80409AF8=8.699999809265137.
The original square-root stage uses `frsqrte`, two single-precision refinement
steps, then multiplication by squared distance. It can differ by an ULP from
correctly rounded `sqrtf`; truncation then changes an integer score. Example:
translation(0,48.66667175292969,0), camera0, forward(0,1,0), object operand0,
projection128 yields native-sqrt score17 versus original18. That can change
visibility, so the difference is not dismissed as cosmetic.

The math callback receives squared distance and returns the **complete original
sqrt-stage result**, not just its reciprocal estimate. No external reference
source/lookup tables are copied into the runtime module. Host verification uses
the already checksum-pinned external Dolphin estimate with original PPC
refinement instructions. The independently implemented portable helper is now
separately validated against this oracle; the external oracle itself is not
linked into the3DS app.
Invalid/nonfinite/out-of-int32 portable inputs return false for explicit caller
handling; bounded valid source inputs are the validated domain.

## Projection coefficient and units

View producer800FFF84 calls800FFF14 at80100048 and stores the result to view+0x0C
at80100050. FOV is the unsigned16 camera field+0xC4. Original angle units are
one full turn65536, with integer half-FOV `fov >> 1`. The coefficient is:

```text
ratio = original_sine(half_FOV) / original_sine((half_FOV+0x4000) & 0xffff)
coefficient = ratio == 0 ? 10.0f : 256.0f / ratio
```

The polynomial and reduction constants/order are implemented rather than calling
target `sinf`/`tanf`. Every possible input was compared to original code. The
fixed256 factor is an original projected-size scale, not the3DS viewport width
or height. Rescaling it to400/240 would change the recovered selector. How the
eventual3DS camera maps authored FOV to its display is a separate integration
decision; do not silently claim a viewport change preserves original LOD output.

## Exact slot rules after score production

First reject score<=1. If instanceflags has0x02000000, add10 with original32-bit
wrapping arithmetic. Then:

| Gate | Choice |
| --- | --- |
| Contextflags&0x1800, score<32 | No model |
| Contextflags&0x1800, score>=32, instanceflags&0x80 | Slot2 |
| Contextflags&0x1800, score>=32, flags&0x01000100 | Slot0 |
| Contextflags&0x1800, score>=32, neither flag case | Slot3 |
| Otherwise contextflags&0x20, score>=32 | Slot2; below32 no model |
| Otherwise originalstate>2, score>22 | Slot2; score<=22 no model |
| Otherwise score<=17 | No model |
| Otherwise | Slot0 with the metric refinement below |

In the final branch, if slot0 resolves to a model header and its **signed**
original header statistic is>39, compute `score / max(metric_9c,6.0f)`.
Ratios>=8.699999809265137 retain slot0; smaller ratios choose slot2. NaN metric
also clamps to6 through the original ordered comparison. If handle/header is
missing or the signed statistic<=39, this refinement is skipped. A null selected
slot always means no model. No slot1 fallback is introduced here.

Although the header statistic is not consumed by the draw-packet emitter, this
LOD consumer **does consume it** for the>39 gate. Preserve its original signed
bits; replacing it with emitted-triangle count would change LOD behavior.

## Gates outside this primitive

The full consumer also checks original visibility-table bits, instance byte
flags against context masks, and optional AABB/frustum hierarchy results before
the projected-size/slot logic. These remain distinct from original region
activation. After slot choice it queues deferred/normal draw records with
further original flags. This checkpoint does not emulate or replace that entire
render pipeline, define unknown flag names, or claim all shaders/materials work.

## Reproduction

Host reference dependencies already cached at `/workspace/toolchains/python-deps`:

```sh
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_lod_verify.py \
  --output /workspace/port-research/hardware-optimization/lod/decision-validation.json
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_lod_projection_verify.py
PYTHONPATH=/workspace/toolchains/python-deps python tools/perf_lod_score_verify.py
```

All oracles SHA-pin the USA DOL to
33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166.
Decision PPC is unmodified; FOV skips only two noncontributing Gekko paired-single
ABI spills/reloads, with opcodes checked. Score oracle intercepts only the
otherwise unsupported reciprocal estimate using the external pinned reference.
Execution addresses and instruction counts are bounded. Reports and inspected
disassembly live under `/workspace/port-research/hardware-optimization/lod/`.
