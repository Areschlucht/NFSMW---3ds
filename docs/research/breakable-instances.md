# Exact source smackable-to-scenery instance bindings

The full source stream contains409 original0x34027 chunks with7,419 physical
SmackableParams occurrences. Identical streaming copies deduplicate into5,953
original scenery members, which resolve to7,419 exact WSI render-instance source
offsets. This is not classification by model-name fragments such as BARREL or
SIGN. Every record references an actual typed `smackable` collection in the
original ATTRIBUTES database, and its original position matches the referenced
WSI instance to within .0001 source units.

The authored exporter is `tools/breakable_instances.py`; original inputs remain
private/unchanged. New runtime files are `mw_breakables.[ch]`. No shared renderer,
main-loop, static collision, SDK build list or original mesh was changed here.

## Original binding chain

0x34027 payloads have an aligned16-byte header and64-byte parameter records.
Original80221018 visits their count and calls802212CC to endian-fix the record.
The source fields retained by the export are:

| Record offset | Established value |
| --- | --- |
|00..0C|Original quaternion values, retained without a guessed Euler conversion|
|10..1C|Original internal position `(-sourceY,sourceZ,sourceX,1)`|
|20|Original word retained; its complete meaning remains unresolved|
|24|Original dynamic resource key, consumed separately from scenery identity|
|28|Actual original `smackable` collection key|
|2C|Global scenery-member index|
|30|Local source record index|
|34|Original source flags, retained|
|38..3C|Original runtime-pointer area, not treated as portable pointers|

Original802213F8 reads+2C and calls802BCCC4, which indexes the original six-byte
global member table (L2RA0x34108). Member fields select a logical scenery section
and local instance index. The section supplies its64-byte instance array; the
instance's+3E field selects a72-byte object record. Its+44 runtime pointer is the
resolved original render blueprint. The adjacent original80221470 selects the
first actual nonzero source mesh slot. Distinguish this from stream-directory
IDs: the exporter uses the verified original logical-section mapping.

Original loader802BD878 reads an object's+40 key and resolves it with802BCC28,
storing the result at+44. L2RA0x8003410B/0x3410C provides those blueprint records;
the loader at802BDD20 retains their ordered16-byte entries and builds mesh links.
The exporter preserves every state-key/model-hash/flags entry privately, without
inventing a generic broken-state selection or reordering fragment meshes.

Concrete first example: source parameter24596192 references attribute014A1C7D
(`mediummetalpost`) and scenery member5475. That member selects logical section
101/instance23, resolving to source instance24588704 (`XS_Speed35_1b_00`). The
original parameter and WSI placement agree. This is an exact source binding,
not an inference that all objects containing Speed or Sign are breakable.

## Damage/debris semantics remain separate

The export preserves source MASS, EventSequencer and original scalar0xBE71DBAD,
plus source Booleans1F989F01/6F002423. **0xBE71DBAD is not labelled a recovered
damage threshold.** Its physical units/comparison producer remain unproved here.
No field is silently reinterpreted as a minimum speed, impulse, damage amount,
cost-to-state value or scoring reward.

Blueprints contain original base and fragment mesh links. For example the
parking-booth blueprint has its base link and seven other source mesh records.
That alone does not establish the event sequence, fragment transforms, impulse,
lifetimes or which records activate together. Original dynamic collision-resource
loading is separate from the static CARP CI admission layer. CI+18 is the scenery
group ID; it must not be repurposed as a smackable identity or broad wall mask.

## Native candidate/state API

The private NBP1 sidecar is989,064 bytes:
`/workspace/port-research/breakable-instances/native-v1/breakables.nbp`.
Its manifest/catalog retain source hashes and provenance. The160-byte header
contains CRC, bounded record/grid ranges and original stream/L2RA/ATTR hashes.
Parent should match the stream digest against its world/collision state before
binding this catalog. Each128-byte record is sorted by exact source instance
offset; a128-unit grid supplies bounded nearby candidates.

`mw_breakables_open/get/find` borrow the strict immutable catalog. Caller supplies
14,307 state bytes, indexed by original scenery member rather than physical
streaming occurrence. `reset` clears that caller-owned state. `activate(index)`
marks the member once; all duplicate scenery providers report the same state.
No source asset or archive is edited/deleted. Unknown ordinary instance offsets
remain unaffected.

`mw_breakables_sweep` returns the closest intact admitted source prop using a
native swept point versus original render bounds expanded by a caller-selected
proxy radius. Coordinates are absolute viewer-world `(sourceX,sourceZ,-sourceY)`
before local rebasing. This detector is a conservative port adaptation, **not
the original dynamic collider or exact vehicle/prop rigid-body collision**.
It allocates nothing, performs no SD reads and changes no state. Nonfinite input,
stationary movement and oversized teleport queries do not activate props.

Supply the admission callback to apply current original world/render activation;
NULL uses the cold normal-render0x10 visibility bit. Parent must not collide with
an inactive prop merely because its metadata remains in the source archive.
After a real accepted impact/damage decision, parent may call `activate`, move
the object into its dynamic representation and suppress that exact static render
instance. This module does not silently hide whole model classes, assign career
rewards, select arbitrary fragments or claim debris physics exists. Treating an
activation bit alone as complete breakage would be incomplete integration.

## Validation

The exporter checks exact WSI original-byte slices against the source stream,
all7,419 parameter/typed-key/member references, source blueprint dependencies,
finite source fields, every linked placement and identical duplicate copies.
All1,466 repeated physical parameter occurrences match their original member's
64-byte record exactly.

Strict C11 warnings-as-errors, pedantic, ASan and UBSan tests pass all7,419 actual
source prop/grid hit queries, source-offset lookup, the concrete Speed35 binding,
shared one-shot member activation, caller-buffer guards, stationary/invalid input,
unsupported IDs and ten malformed/recomputed-CRC pack cases. These are portable
candidate/state checks; they do not demonstrate a rendered prop falling apart
in the3DS runtime or original impulse/debris/physics fidelity.

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude \
 tests/test_breakables.c source_bmw/mw_breakables.c -lm \
 -o /tmp/nfsmw-breakables-test
/tmp/nfsmw-breakables-test \
 /workspace/port-research/breakable-instances/native-v1/breakables.nbp
```
