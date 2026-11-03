# Original scenery flag consumers — bounded checkpoint

Read-only USA GameCube evidence. No runtime source, collision policy or scene
assets are changed by this work. Exact original executable SHA is pinned by
`tools/scenery_flag_reference.py`.

## Render rejection and its actual mask producer

The original per-instance render path at `802BEAA8..802BEAC4` reads byte +0x1B
of the 64-byte original instance. This is the low byte of its big-endian flag
word at +0x18. It XORs that byte with 0x60, ANDs it with draw-context word +0x84,
and branches to the no-draw exit at `802BF250` if the result is nonzero:

```
reject = (((instance_flags & 0xff) ^ 0x60) & draw_context_flags) != 0
```

This occurs after original preculling and before model-slot selection. It is not
part of the scalar LOD selector currently recovered in the port. The same original
context +0x84 is also consumed by later LOD logic; these are not two independent
original fields.

The context builder `800F4BF8` **unconditionally ORs 0x10** into caller flags at
`800F4C14`, then stores the result at context+0x84 at `800F4CB0`. It also adds:

- 0x02 for view-kind field +4 equal to 1 or 2;
- 0x01 for original game-state getter result 3 or 4;
- 0x100 for view-kind 16 through 21;
- 0x04 when a non-null original profile pointer's +0x1AA4 value equals 1;
- 0x40 if accumulated flags include 0x1800, and 0x02 if they include 0x1000;
- 0x20 for view-kind 3.

The tool preserves numeric state labels rather than inventing view/profile names.
The baseline suppression bit is therefore proven: source-instance flag 0x10
rejects drawing in contexts built by this original function. Passing zero context
flags in the port misses this original gate. That fact alone does not establish
which career/event groups should be activated.

## Member-state propagation and transform gate

The group propagation wrapper `802BD040` resolves loaded scenery and calls
`802BCCD8`. The latter uses the member's signed instance index times 64 and
scenery+0x20 array pointer. Its final scalar write preserves the original high
halfword and replaces the entire low halfword with the member's state:

```
instance.flags = (instance.flags & 0xffff0000) | member.flags
```

Before that write, transform mutation is entered only when both conditions hold:

```
(old_instance_flags & 0x00800000) != 0
((old_instance_flags ^ new_member_flags) & 0x400) != 0
```

That path reconstructs a float matrix from signed quantized basis fields using
1/8192, initializes another matrix, sets its first entry to -1, calls original
matrix concatenation helpers, requantizes basis fields using 8192 and truncation,
and writes translation back as floats. It is not a simple visibility Boolean.
This checkpoint identifies that branch but does **not** replace the paired-single
matrix implementation or claim an original-execution comparison for its arithmetic.

## Actual supplied source distribution

Using the prior recovered group-to-provider mapping, all 17,827 candidate source
instance occurrences were read from the original complete STREAML2RA file:

| Source-instance flags | Occurrences |
| --- | ---: |
| 0x10 clear; transform-eligible high bit clear | 9,059 |
| 0x10 set; transform-eligible high bit set | 8,704 |
| 0x10 set; transform-eligible high bit clear | 64 |

These counts are source/provider occurrences, not simultaneously visible models.
The member table includes 6,957 initial logical records with low flags 0x8070.
They support investigating missing source suppression in the port; they do not
justify removing all barriers or enabling every race group in free roam.

## Collision boundary: do not create invisible walls

The traced group propagation path updates original scenery instances. No direct
CI/CA collision update call was found in `802BD040` or its apply function.
The current port's wall queries use separate original CA banks and CI records.
This checkpoint does not establish a scene-instance-to-CI ownership mapping,
prove that CI flags use the scenery 0x10 bit, or establish which wall the user
collides with near rendered race arrows. A render-only removal must not be claimed
as a complete free-roam barrier fix.

Before publishing the fix, resolve event/free-roam group selection and trace the
original collision/dynamic-object ownership path. Apply coherent active state to
rendering and collision, retaining legitimate career locks. Diagnose a concrete
blocked route using original contact provenance rather than assigning scenery
masks to unrelated collision-wall exclusion flags.

## Reproduce and validation

```
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/scenery_flag_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/scenery-flags/verification.json
```

The verifier executes exact original scalar instruction windows in Unicorn with
bounded execution and memory-write whitelists. Render tests cover all 256 low
instance bytes against every low-byte context mask and four upper-bit contexts.
Member-copy cases stop before original epilogue/paired ABI code. Transform cases
stop at entry into the transform-changing path; no arithmetic is substituted.
Context-builder cases stop before the separate context-geometry setup helper,
whose live state producers and floating-point work are outside this checkpoint.

The report records window SHA-256 digests and explicit limitations. Raw DOL bytes,
full scenery tables and generated game-data artifacts remain private.

Validation outcome: **66,560** original render-mask comparisons, **90** unchanged-
transform low-halfword copy cases, **30** correctly detected transform-changing
branch cases, and **1,380** original context-builder comparisons all passed.
The context-builder tests verify the pre-helper scalar computation, including
unconditional 0x10; they do not execute the later context-geometry setup helper.

Root's separate integration adds the generic recovered render predicate using
`original_context_flags`. The prototype's default context remains zero, so this
checkpoint does not activate ordinary 0x10 suppression in a shipped free-roam
build. That restriction avoids claiming collision coherence before its original
ownership path is recovered. The predicate component and actual default-mask
recovery are useful independently, but the reported barrier bug remains open.
