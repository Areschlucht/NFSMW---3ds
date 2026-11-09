# Original scenery 0x0400 transform transition

This is an executable-backed consumer recovery, not a new race scheduler or
runtime activation patch. Only `tools/scenery_transform_reference.py` and this
report are authored here. Original source assets remain unchanged and private.

## Exact result

Original `802BCCEC..802BD028` first locates the64-byte instance. A transform
mutation happens only when both conditions hold:

```
old_instance_flags & 0x00800000
(old_instance_flags ^ new_member_low_flags) & 0x0400
```

When true, the original negates **only the first three stored signed16 matrix
components** at instance offsets44,46,48 (hex2C/2E/30). The other six components
remain unchanged. The source representation is little endian with Q13 scale8192;
the executable operates on its already loaded big-endian instance.

Negation preserves the original low16-bit store semantics. In particular,
-32768 negates to integer32768 and the final halfword remains0x8000; do not clamp
it to32767 or invoke signed16 overflow in portable C. An unsigned16 subtraction
from zero, then reinterpretation as signed16, implements the source store.

After that conditional operation the original always copies the new low16 flags
while preserving the old high16 flags. Bounds0..23, the word28..31, translation
32..43, remaining matrix shorts50..61 and object reference62..63 stay byte-identical.
There is **no guessed vertical movement or translation offset** in this path.
Do not reinterpret the observed reflection as a180-degree rotation or change
bounding boxes beyond the actual original operation.

## Original arithmetic path

- `802BCD1C..802BCEC0` converts all nine source shorts to float32 with factor1/8192
  and assembles a4x4 matrix, initially with a zero translation row.
- `80329E28` builds an identity matrix. Original startup bytes80003110..18 set
  R13 to80506DC0; its SDA zero/one constants are used by this routine.
- `802BCEDC` calls8005E024 after setting the temporary identity's first diagonal
  entry to-1. Wrappers8005E024 and8010AB28 reach matrix concatenation80329EA0.
- `802BCEE4..802BCFF8` multiplies the resulting nine components by8192 and uses
  the original toward-zero integer conversion plus halfword stores.
- `802BCF10..28` injects the original translation **after** concatenation;
  `802BCFFC..802BD010` copies it back unchanged.
- `802BD014..24` preserves the instance's high flag halfword and copies the
  supplied member low halfword.

For this diagonal reflection and dyadic Q13 inputs, the portable effect is exact
integer component negation rather than a general matrix approximation. The tool
still executes the full unchanged original path instead of stubbing the matrix
operation with that inferred answer.

## Verification

Private result: `/workspace/port-research/scenery-transform/verification.json`.
The actual mapped source contains8,704 eligible provider-instance occurrences and
6,881 distinct eligible matrices. A deterministic sample spread across sorted
unique matrices covers1,024 actual matrices. Both toggle directions compare every
byte of the64-byte record, including roundtrip back to the original:

- 2,048 original queries on source matrices.
- 96 synthetic boundary/eligibility queries, including each of the three affected
  lanes, both source bit states, eligible/ineligible instances, zero, +/-1,
  +/-8192 and signed16 extrema.
- **2,144 exact original comparisons**, all passed.
- Short records and out-of-range flag arguments are rejected by the portable helper.

The reference pins the USA DOL SHA and exact code windows. Instruction budgets and
code whitelists stop escapes. Original writes are permitted only to the private
stack and the supplied instance. Existing explicit Gekko paired-single hooks are
reused; their general fused-tie/FPSCR limitations are documented, rather than
claiming they implement the whole processor. These verified reflection inputs
use exact dyadic products/sums before the original integer stores.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/scenery_transform_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --plan /workspace/port-research/free-roam-activation/bin1.json \
  --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
  --output /workspace/port-research/scenery-transform/verification.json
```

The portable `apply_source(source64,new_low_flags)` is usable by a source-side
state materializer. A renderer that retains immutable original bytes can apply
an equivalent matrix/flag overlay without deleting or permanently altering arrow
assets. Event group reset/apply ordering, collision group state, actor scheduling,
and frame-atomic render/collision publication remain caller responsibilities.
Cold exploration/career plans currently have zero0400 transitions; this recovery
supports future race activation and respawning, not a claim that races now work.
