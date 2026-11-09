# Original trigger narrowphase: recovered inputs and open predicate mismatch

Read-only USA GameCube recovery. No SDK build, runtime change, original input
edit or commit. `tools/race_gate_containment_reference.py` supplies the bounded
references and retains negative evidence rather than claiming a finished gate.

## Actual registration and notification path

Trigger enable routine8019B840 passes its embedded shape at trigger+28 to
802EEDBC. That adapter calls8030570C, which submits an update through802F720C.
Trigger disable calls802EEDE8. The embedded shape is initialized as a generic
64-byte structure by80305234; it is not itself an independently discovered
per-trigger virtual shape class.

Actual membership-notification code1/2 eventually reaches8019B964 through
message constructor801D93D0: the direct call is801D948C. The constructor resolves
an object registry entry and the trigger owner before delivering the message.
The generic shape's callback/event-array pointer at shape+18 is consumed by
80305424 ->801EB724. This is evidence of the event path, not complete scheduling
or race lap/finish semantics.

## Half extents are now established for kind1

The original actor-versus-shape routine8030654C performs broad-phase work and
branches on low-nibble shape kind. For kind1 it constructs two geometric query
objects using80089320 and dispatches their intersection through8008A630.

Immediately before constructing the trigger query object,80306884..803068CC
multiplies stored shape parameters +0C, +14 and +2C by the float32 constant0.5
at8040EB4C. The half-extents vector is passed to80089320 at803068CC.

Combined with the separately verified constructor mapping:

```
internal position = (-sourceY, sourceZ, sourceX)
internal half extents = (sourceDimensionsY / 2,
                         sourceDimensionsZ,
                         sourceDimensionsX / 2)
```

The middle case comes from the constructor first storing2*sourceDimensionsZ as
shape+14. Horizontal source Dimensions are therefore halved at this consumer,
while vertical source Dimensions already act as the resulting half height.
Preserve the exact float32 doubling/halving sequence when porting. The scalar
window matches129 cases from126 distinct actual source tuples plus synthetic
signed/zero/asymmetric cases (one synthetic tuple duplicates a source tuple).

This establishes inputs to the kind1 geometric query. It does not justify
applying a point-in-box check to the player car. The original actor supplies
radius, velocity, position, orientation and shape half extents through its virtual
provider at offsets30/34,48/4C,50/54,60/64,88/8C,98/9C. Those concrete vehicle
provider implementations and movement/notification policies remain separate.

Kind2 and kind3 follow different branches: sphere-distance/optional plane checks
and a vertical slab condition respectively. They must not all be turned into
kind1 boxes or merged into a guessed universal checkpoint radius.

## Original generic box reference

8008A630 uses a kind-pair dispatch table at803D3F50. The kind1/kind1 entry at
803D3F60 points to80089658. The tool executes the original80089320 builder and
8008A630 ->80089658 query with explicitly supplied synthetic actor/trigger boxes.
No original code bytes are patched. Integer writes are confined to private output
and stack areas; instruction budgets and code whitelists reject escapes.

Shared explicit Gekko paired-single hooks are reused from
map_recovery_contact_reference.py. They use binary64 intermediates rounded to
binary32; exact fused ties, FPSCR and subnormal/NaN semantics are not established.
Their limitations remain relevant to the result below.

Nine dyadic unit-box boundary cases pass: along all three axes, centers1.875 and2
(with both half extents1) overlap, while2.125 does not. The observed predicate
includes touching for these cases. Twenty-four rotated pairs return symmetric
results when actor/query order is exchanged; this is only a consistency check.

## Negative evidence: general AABB equivalence is not established

The deterministic160-case axis-aligned sweep has14 differences from a plain
geometric AABB oracle. All are modeled-original false versus oracle true. The
report retains every failing input. First counterexample:

```
first center = (1.5,-3,2.5), half = (2,2,2.5)
second center = (-2,0,0), half = (2.5,1.5,3.5)
yaw = 0 for both
plain AABB overlap = true
modeled original query = false
```

Possible causes include original contact-manifold policy, insufficient input
semantics or shared paired-single modeling fidelity. None has been proved.
Therefore neither generic SAT nor a simplified AABB/point proxy is yet a verified
replacement for this original query. The tool's successful completion means the
bounded diagnostic ran; it does not turn the14 failures into positive parity.

The useful portable result from this checkpoint is the independently established
shape parameter conversion and the exact consumer chain. General containment,
swept motion, concrete actor/provider shapes, activation/notification scheduling
and original checkpoint/lap rules are still integration gates.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/race_gate_containment_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --catalog /workspace/port-research/race-story/catalog.json \
  --output /workspace/port-research/race-gate-containment/verification.json
```

The private report pins the DOL SHA, exact code-window digests, scalar counts,
boundary outcomes and the complete mismatch list. No raw game payload is emitted.

## Subsequent resolution for the aligned diagnostic

The14/160 differences are now explained by the original routine's directed
face-contact generation and source tie order, with2,320 original comparisons.
See race-gate-reference-resolution.md. This supersedes the earlier uncertainty
for those aligned inputs; it does not establish a general rotated trigger test,
actual vehicle provider or playable race detector.
