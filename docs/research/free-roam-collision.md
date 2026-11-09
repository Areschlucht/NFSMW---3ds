# Exact free-roam collision blocker and original scenery-group gate

This read-only audit identifies the actual wall stopping the unsteered prototype
at its Colonial spawn. No shared runtime, source archive or collision payload is
edited by this tool. The parent owns the rendering/collision integration.

## Actual native blocking contact

The host probe uses the production controller, original WST selector, bounded NWC
activation and native ground/wall queries. It advances with throttle1, no steering,
two120Hz substeps per60Hz frame. The first wall stop occurs at frame196:

| Item | Original source value |
| --- | --- |
| section / collision package | 141 / 101 |
| CI file offset | 24602960 |
| CA file offset | 24597072 |
| asset index / wall index | 2 / 2 |
| CI +24 (group ID) | 3 |
| loaded CI flags / wall flags | C0 / C2 |
| material key | 00000000 |
| native contact | (-2482.51733,166.637665,354.297913) |

The tested segment is native
`(-2482.38501,166.637665,354.401031)` ->
`(-2482.58667,166.637665,354.244019)`.

Group3 is **BARRIER_SPLINE_458**. Nearby PLAYER barrier source instance24588384
belongs to this exact group through member5480, logical scenery101/instance18.
The collision ownership is an original numeric link, not a proximity-based
exclusion or model-name heuristic. Its original scenery flags02808070 include
suppression bit10, which the prototype's zero draw context had not tested.

## Proven original collision consumer

The collision instance's big-endian halfword at **+24** is its original scenery
**group ID**. It was previously conservatively named a possible prop field.
Two exact DOL query windows establish the relationship:

- **802F2000..802F2014** loads CI+18hex, permits zero, otherwise reads the byte
  from **8043604C[group ID]** and skips the instance if that byte is zero.
- **802F2700..802F2714** performs the same test in the other query path.
- 8043604C is the same state-byte table written by group setter802BD42C..802BD46C
  and cleared by reset802BD588..802BD58C.

The exact rule is:

```
admit CI when group_id == 0 OR original_group_state[group_id] != 0
```

Any nonzero state is admitted, not just bit1. This is independent of the later
CI/primitive exclusion-mask tests. The proven load-time OR of C0 for grouped
instances is retained. **Do not fix this by excluding all C0 walls**: an active
career gate must still collide. Apply the shared numeric group state before both
wall and ground query traversal.

`OriginalGroupGate` executes only those unchanged integer instructions, with
explicit synthetic CI/group-state inputs and a write guard. **4,608 cases** pass:
both query windows, nine group IDs including zero, and all256 state-byte values.
The report pins the original DOL SHA and exact code-window hashes. Geometry and
the complete original query functions are outside these bounded comparisons.

## Static ground and walls remain intact

Across deduplicated NWC package payloads:

- Group0 has **6,640 CI records**, **38,347 ground nodes**, **37,454 walls**.
- Group1 has no CI records at all. Its visible unnamed scenery members therefore
  must not be confused with ordinary collision ownership.
- Only nonzero group754 has ground: two CI records, five ground nodes, no walls.
  Other grouped instances are wall-only. Group754 still needs its source state.
- Every nonzero collision group ID resolves to the original L2RA group directory.
- The45,803 walls have loaded flags02:37,094; C2:8,349;12:351;06:9.

The static-normal-wall regression segment
`(-2447.614293,170,396.274078)` ->
`(-2446.385705,170,394.695924)` crosses group0 package130, sourceCI28703456,
sourceCA28702304, asset7/wall11, flags02, material6CA26F9B. That wall must remain
blocking when the inactive race group3 wall stops blocking.

## Render state is not the same test

Keep original per-instance flags plus exact sparse apply/reset operations for
rendering. Do not hide every member of an inactive group: unnamed group1 has
many initial flags8000 without suppression10. Original reset only changes groups
whose state byte was nonzero. The renderer applies the independently recovered
Drawcontext+84 mask. The collision code uses numeric group-state admission.
Both consumers must share the same activation plan, while preserving their own
original flag semantics. No global ARROW/BARRIER filename deletion is warranted.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/free_roam_collision_audit.py \
  --collision dist/v018-shipping-install/3ds/nfsmw-rockport/world.nwc \
  --scene /workspace/port-research/world-streaming/scene-native \
  --road dist/v018-shipping-install/3ds/nfsmw-rockport/road.nrd \
  --metadata dist/v018-shipping-install/3ds/nfsmw-rockport/world-streaming.bin \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --verify-original --trace-forward \
  --output /workspace/port-research/free-roam-collision/audit-final.json
```

The optional forward probe compiles host production components in a temporary
directory. It is a collision diagnosis, not a3DS build or physical-console test.
Private baseline contact and counts are preserved under free-roam-collision/.
Root should test the same blocking segment with group3 inactive and active, retain
ordinary group0 walls/ground, test real career-lock IDs, and verify traversal
through the previously blocked location in the emulator before distributing a
new exploration build.
