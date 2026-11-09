# Resolution of the axis-aligned trigger-query reference discrepancy

The previous 14/160 differences are now explained for the tested zero-yaw,
zero-motion box inputs. The original routine being queried generates **directed
contact data**, and its result is not a plain symmetric geometric-overlap test.
This report does not close general rotated OBB or concrete player-provider work.
No runtime/shared source changes, original byte patches, SDK build or commit were
performed by this subtask.

## What was compared incorrectly

The original `8008A630 -> 80089658` call writes contact point, normal and depth in
addition to a Boolean result. The earlier oracle asked whether any geometric
intersection exists. The original routine can find an intersecting pair but fail
to produce its directed face-contact result. Treating that outcome as an unknown
floating-point mismatch obscured an observable control-flow difference.

The earlier geometric-overlap results remain correct as geometric facts. The
modeled original results also remain unchanged. Their disagreement does not by
itself establish a broken paired-single hook or justify substituting generic SAT
for the original call.

## Exact original axis-aligned control flow

The source axis order table at `803D3EF8` is **(0,2,1)**. The query evaluates both
boxes' face axes, retaining the first best axis under its strict improvement
comparison. Source tie order matters; ordinary X/Y/Z order fails expanded tests.

For aligned inputs with zero supplied motion vector, projected tangential axes
have exact zero dot products. The zero branches at `8008981C..80089858` do not
add/subtract those second-box tangential scaled axes. The chosen support point is
therefore the second box's face **center**, rather than a face corner.

The later reflected-point construction at `80089B00..80089B3C` doubles those
zero tangential projections and cannot move that center toward the face edges.
The final fallback accepts only when both tangential inside tests counted at
`80089A98..80089AA8` succeed; `80089D0C..80089D1C` compares the count with two.
Thus intersecting faces with an outside face center can return false.

An independent scalar model for this particular input class reproduces that:

1. Compute each axis separation `abs(centerA-centerB)-halfA-halfB`.
2. Reject if any separation is positive.
3. Choose the largest separation, with original tie order X/Z/Y.
4. Accept only if B's face center lies within A's two tangential extents.

This is a **diagnostic directed-contact model**, not a new runtime gate detector.
Swapping A and B can change its result, as it changes the original result.

## The original counterexample is now traced

A: center `(1.5,-3,2.5)`, half extents `(2,2,2.5)`.
B: center `(-2,0,0)`, half extents `(2.5,1.5,3.5)`.

Plain AABB intersection is true. The original selects axis1 (Y) and stores the
support point `(-2,-1.5,0)` at output+70. That is B's face center. Its X coordinate
is outside A's tangential interval `[-0.5,3.5]`; its Z lies at A's boundary.
The final original inside count is one, so the routine returns false.

All **46 actual original dot-product calls** along this exact trace match an
independent scalar dot oracle. Fresh reference instances reproduce the result.
This pins this counterexample to observed original contact-generation branches,
without needing a claim about exact Gekko rounding in arbitrary other cases.

## Expanded validation

`tools/race_gate_reference_diagnostics.py` executes unchanged, whitelisted
original builder/query instructions through the existing bounded reference.

| Deterministic set | Pairs | Geometric intersections | Forward directed contacts | Overlap/contact differences | Order asymmetries |
| --- | ---: | ---: | ---: | ---: | ---: |
| Earlier sweep | 160 | 23 | 9 | 14 | 8 |
| Expanded general | 500 | 49 | 26 | 23 | 17 |
| Deliberately intersecting | 500 | 500 | 213 | 287 | 168 |

Across **1,160 pairs / 2,320 forward-and-reverse original queries**, the directed
scalar model has **zero differences**. All seventeen distinct cases from the
old sweep exhibiting either discrepancy or order asymmetry are also replayed
with fresh reference instances, with unchanged outputs. The counterexample gets
one additional fully observed trace: **2,338 original query invocations total**.

The source axis-order detail was needed to close a new tied-separation case:
centerA `(2,2,7.5)`, halfA `(3.5,3.5,1)`; centerB `(-1.25,6.25,4.25)`, halfB
`(3.75,1.75,3.25)`. In reverse order, Z precedes tied Y in the original and yields
false. A guessed X/Y/Z policy incorrectly predicted true.

## Reproduce and remaining limits

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/race_gate_reference_diagnostics.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/race-gate-reference-resolution/verification.json
```

The private report includes exact source-window/table hashes, all old sweep
counterexamples and asymmetries, fresh replays and the detailed original trace.

The portable diagnostic is validated only for these exact dyadic, axis-aligned,
zero-motion boxes. Arbitrary rounding, rotated contact construction, sweep/motion
inputs, the concrete vehicle actor provider, notification scheduling, race mode
activation and checkpoint/lap consumers remain separate gates. An original
trigger uses the actual actor-versus-shape call path; it must not be replaced by
a symmetric SAT result or point/radius proxy merely because those are simpler.
