# Original road network and bounded native traffic foundation

This pass supplies an immutable native road-network pack, original typed street
attributes and a portable follower. It does not edit the shared application,
renderer, collision bank, source archives or packaging/build configuration.
Original traffic spawning, lane selection, overtaking, signals, collision response
and vehicle material/attachment behavior are not claimed as recovered.

## Concrete original navigation data

The existing complete `L2RA.BUN` contains top-level chunk0003B800 at file69630,
with its aligned CARP resource at69640. The original loader803076E0 recognizes
that chunk and aligns its payload. Original tag consumers802F8EE0..802F9130 bind
the RNhd, RNpf, RNnd, RNsg and RNrd resource records; they are not guessed from
coordinates or filenames.

The original resource descriptor has bit40000000 set; its pointer is relative
to the descriptor itself. The exporter independently checks all ranges/strides.
All original node adjacency arrays are reciprocal with their original segments.

| Original tag | Count | Stride | Original data file offset |
| --- | ---: | ---: | ---: |
| RNnd | 4385 | 32 | 9CEC0 |
| RNsg | 6538 | 22 | CCD40 |
| RNpf | 710 | 64 | BF2E0 |
| RNrd | 1308 | 8 | CA460 |

`RNnd+0..8` are the three original float32 coordinates. Segment endpoints at
RNsg+0/+2 index those nodes, proved by802F9DB8. Source node ID is+12, signed
profile selector is+14, adjacency count is byte+16 and up to seven original
segment references begin+18. Original803051D4 visits that adjacency order and
excludes the passed segment and flag1 candidates. The source flag word is
RNsg+10; do not infer all remaining flags from numerical correlations.

Coordinates are the original internal basis:

```
native(A,B,C) = (-sourceY, sourceZ, sourceX)
viewer world = (C,B,A)
viewer local = (C,B,A) - road.origin
```

No race checkpoint positions or generated test roads are used for this network.

## Original packed road curves

Original802FA314 linearly interpolates uncurved segments and dispatches flag100
segments to802FA984. The latter uses the source float32 constant at8040E750,
6.00748899159953e-05, unsigned lengths at RNsg+12/+14 and signed direction bytes
at+16..21. For original node positions P0/P1:

```
control1 = P0 + ((u16be(segment+14) * scale) * s8(segment+19..21))
control2 = P1 + ((u16be(segment+12) * scale) * s8(segment+16..18))
```

The original cubic basis is the actual constant matrix at803EB9BC. Portable
sampling preserves original coefficient/FMA ordering. Analytic tangents are
provided for the port's follower; original traffic steering providers remain
separate work.

The bounded original execution supplies an already-initialized static Bézier
container with an empty linked list. It does not patch source instructions or
replace the road sampler. It reuses the existing explicit paired-single model,
whose general FPSCR, subnormal/NaN and exact fused-tie limitations still apply.

## MWT1 native data and work bounds

Private asset:
`/workspace/port-research/street-systems/native-v1/road-network.mwt`.
It is422296 bytes, SHA256
848044fdc738bbca37c8bff825229aa07fff06bf588032148a9790b255bdd844.

MWT1 version1 uses a192-byte header: magic/version/total/CRC, exact original
node/segment/profile counts and offsets, grid dimensions and CSR offsets, original
L2RA SHA at64, original DOL SHA at96, grid origin/cell size at128, and reserved
bytes. CRC covers bytes16..end. Nodes32B and profiles64B retain their original
bytes; each32B segment keeps the original22B, two zero bytes, a port-generated
float32 approximate arc length at24 and four reserved zero bytes.

The128-unit spatial grid has44x49 cells,9250 segment references and at most93
candidate references per cell. Bounds use the full cubic control hull, avoiding
loss of curved segments that leave their endpoint rectangle. Grid offsets/IDs,
all counts/ranges, finite coordinates/lengths, source IDs and reciprocal
adjacency are validated before a borrowed view is published. Failed decode
leaves the caller's prior view unchanged. Keep source bytes immutable/alive.

`mw_traffic_nearest` is a **spawn-only** approximate nearest query. It visits
nearby indexed cells, deduplicates segment IDs with1024 stack bytes and rejects
queries above512 distinct candidates. It uses16 chord subdivisions per candidate;
this is not the original closest-road query. Do not invoke it for every actor
every frame. The initial player spawn checks14 source candidates in the test.

`mw_traffic_step` does no allocation, IO, whole-graph search or car-model decode.
It examines only the current node's<=7 original neighboring segments, with at
most16 transitions and112 neighbor checks per actor update. `MwTrafficWork`
reports samples, neighbor checks, transitions and nearest-query candidates.
Each actor is44 host bytes; the suggested production pool is four active cars,
with a declared maximum of eight. The caller must enforce its fixed pool.

The follower is an explicit **native port policy**, not original traffic AI:
caller-chosen speed, approximate arc-length time, the straightest eligible source
connection, no immediate U-turn and stopping at dead ends. Source flag1 candidates
are conservatively excluded following the cited original adjacency consumer.
This can stop actors at junctions; original broader traversal/lanes need recovery.
An admission callback lets the caller bind stream/event state and reject roads.
Negative callback results abort transactionally; a newly blocked current segment
stops its actor. Reverse traversal and normalized native forward vectors work.

Parent rendering should convert position/forward using the basis above, cull
actors by actual view/distance and share each original car mesh/texture across
its instances. A model loader or original traffic spawner is not part of this
portable graph module. Never scan/clone the static whole-city world per actor.

## Original traffic models and breakable evidence

Private `street-attributes.json` preserves all181 `smackable` definitions and
all10 `trafficpattern` definitions through the verified ATTRIBUTES reader.
Every field retains its source offset, type and original bytes. Traffic-pattern
array94E3C795 contains24-byte typed records, whose first class/key references
resolve to original pvehicle records. Each record's model, scalar float and two
remaining words are exported without assigning unproved frequency/speed units.
The exact VLT label hashes additionally match `Vehicles`94E3C795 and
`SpawnTime`BF2FDB5C. The observed SpawnTime value is4; its complete original time
consumer/spawn policy is not recovered merely by this name match.

Default traffic explicitly selects:

| Collection key | Original model |
| --- | --- |
| A0C7BB59 | TRAFHA |
| 7DBE89DD | TRAFPICKUPA |
| DBB93C72 | TRAFNEWS |
| D601789E | TRAFTAXI |

Seventeen distinct models occur across the regional patterns. These typed
associations do not by themselves recover initial spawn density or AI behavior.

Smackable records include original mass, rigidbodyspecs references, effect-linkage
records and EventSequencer strings. A collection count is not an instance count
or proof of a destructible replacement. Concrete render-instance/collision-group
bindings, damage thresholds, replacement states, impulses and pursuit-breaker
sequencing remain a separate integration task. This pass deliberately introduces
no blanket object-name deletion or invented breakable damage engine.

## Validation and reproduction

The source Python model exactly matched640 bounded original sampler outputs:
128 genuine source segments at t=0,.25,.5,.75,1. The compiled native sampler
matches all640 original points with maximum observed absolute error0.
This sample is not a proof of every possible IEEE/FPSCR operand combination.

Host ASan/UBSan tests verify all13076 reciprocal adjacency references and run
28800 bounded actor steps across eight actors for60 simulated seconds. They
traverse1195 aggregate source units and20 junctions; observed maxima are two
neighbor checks and three samples per actor frame. Stopped/dead-end behavior,
admission failure rollback, malformed/recomputed-CRC sidecars and invalid input
are checked. These are host workload checks, not measured3DS performance.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/street_systems_export.py \
 --l2ra /workspace/port-research/rockport/samples/L2RA.BUN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --output /workspace/port-research/street-systems/native-v1 --verify-original

cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fno-fast-math \
 -ffp-contract=off -fsanitize=address,undefined -no-pie -Iinclude \
 tests/test_traffic.c source_bmw/mw_traffic.c -lm -o /tmp/nfsmw-traffic-test
/tmp/nfsmw-traffic-test \
 /workspace/port-research/street-systems/native-v1/road-network.mwt \
 /workspace/port-research/street-systems/native-v1/road-curves.reference
```

No SDK build, emulator traffic run or hardware measurement was performed by this
subtask. Original archives and native assets remain private.
