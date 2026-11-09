# Source-derived race scenery activation plans

This checkpoint authors `tools/build_race_activation.py` and this report only.
It does not edit shared runtime/build code, original inputs or published assets.
Source arrays remain private. Race entry still needs caller-owned world admission,
actual trigger/actor detection and original countdown/results integration.

## Exact event consumer is now traced

The bin group loop801A9960 is not the only original consumer. Current-event
barriers are applied by **8019F2DC** using manager pointer **+1AAC**:

1. Count getter801A61C0 reads array fieldE244F26B.
2. Name getter801A87B8 reads the indexed text and strips one leading `*`.
3. Argument getter801A8864 independently reports that leading star.
4.8019F32C calls801FE9AC(name,argument) in original array order.
5. After the loop it calls collision refresh802EE62C and802F97E8.

The event and bin fields therefore share actual source group ownership and state
semantics, despite their distinct wrappers. Array order and repeated operations
are retained. No sorting/deduplication is substituted for original operations.

The original group setter resets its byte to1, adds bit2 for a nonzero argument,
and bit4 when the original group record byte+17 is nonzero. Exports preserve the
final active_group_states as well as active_group_ids. Current native collision
admission only needs the original zero/nonzero test; other original state-byte
consumers must not be guessed.

## Entry reset is conditional, not universal

The direct caller801C4A44 is in the larger entry routine801C4890. Its local prefix
801C4A04..801C4A48 obtains the event's source ID via801A5158 and compares it using
original strcmp against the literal **e3demo** at803EEAE8. Only that exact ID calls
801FEB00 before applying the current event. Uppercase E3DEMO or trailing spaces
do not take the reset branch. None of the82 supported source courses has this ID.

Consequently ordinary event entry in this recovered path **overlays its current
base activation state**. It is not evidence of unconditional reset->apply-race.
The exported plans explicitly name their base bin; they must not silently erase
career gates or assume every race begins in the post-story open-city state.

## Explicit reset callback and the normal-exit gap

The source script descriptor803EDE68 points to **8019F36C**, immediately followed
by the literal **DisableBarriers**. That callback calls801FEB00 (reset previously
active groups, then restore SCENERY_GROUP_DOOR argument0) and additional collision
refresh routines802F97A4/802F93C8.

**Normal race-exit script/callback ordering is not proved by this checkpoint.**
There are no direct branch callers to8019F36C in the scanned executable; its script
registration is concrete, but the full script scheduler/call sites are not yet
recovered. Do not label every successful finish, cancellation or movie completion
an unconditional original DisableBarriers invocation.

A native port may explicitly restore its selected immutable free-roam snapshot
on exit as its own coherent policy, but should describe that as the port's
lifecycle implementation until original exit ordering and bin replay are proved.
A warm original reset only ORs0x10 into active members; it does not clear their
0x0400 state. Invisible inactive matrices may therefore retain their reflected
state until a later operation. These exports are absolute source-based states,
not byte-for-byte snapshots of every hypothetical warm history.

## Private concrete plans

All82 P2P/circuit courses supported by the existing route scaffold were exported
against both explicit source bases:

- `/workspace/port-research/race-activation/exploration-base/`: bin1 base.
- `/workspace/port-research/race-activation/career-bin15-base/`: early-career base.

Each directory contains `summary.json` and one `<event_key>.json` per course.
Each plan supplies:

- Exact event key/name/source ID, source field provenance and ordered operations.
- Base operations, final active_group_ids and full final active_group_states.
- Sorted source-offset overrides with expected_source_flags/effective_flags.
- Required Q13 reflections, resulting three-component row and instance SHA.
- Original render suppression counts and normal draw context0x10.

The event operations contain1,343 leading-star arguments across the82 definitions.
Those counts are source operations, not concurrently active walls or race counts.

| Source course | Event key | Event operations / stars | Bin1 overrides | Reflected provider occurrences |
| --- | --- | ---: | ---: | ---: |
| Diamond Valley (`7_2_2_p2p`) |00c6bc71|32 /14|376|142|
| `10_2_1_sprint` |c3309945|36 /24|498|325|
| Intro (`16_2_1_d_day_intro`) |f7e4440a|29 /11|254|89|

Bin1 maxima are910 overrides,78 active groups and810 reflected occurrences in
one plan. Bin15 maxima are963 overrides,83 active groups and810 reflections.
The additional53 bin15 overrides preserve the legitimate early-career lock
provider occurrences. Actual race eligibility/unlock rules remain separate.

## Reflection is exact source behaviour

The exporter reuses the independently verified `apply_source` helper from
scenery_transform_reference.py. On eligible instances with a0x0400 transition it
negates only source signed16 fields44/46/48 with exact low16 wrapping, preserves
translation/other matrix lanes, then copies the new low flag halfword. It does
not turn that operation into a180-degree rotation, move arrows vertically, delete
geometry or modify collision wall material flags. All original stream-instance
SHA values and base flag operations are checked before per-event export.

## Bounded verification

For each base, **84 original event-apply loop cases** pass:82 actual ordered
arrays plus absent-event and present-empty-array cases. Only the attribute
getters and external apply/refresh callees are supplied as explicit dependencies;
the original loop/index/order/null branching remains unchanged. Writes are
limited to the original stack frame and instruction budgets reject escapes.

**86 original entry-prefix cases** pass for each export:82 actual source IDs plus
exact e3demo, uppercase, empty and trailing-space edges. The event ID getter and
reset/apply callees are supplied; original strcmp and conditional branches run.
The reference verifies local order and the special reset condition, not full
race-start animations, scripts, collision refresh implementation or scheduler.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/build_race_activation.py \
 --catalog /workspace/port-research/race-story/catalog.json \
 --groups /workspace/port-research/event-activation/recovered-group-members.json \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
 --base-plan /workspace/port-research/free-roam-activation/bin1.json \
 --verify-original \
 --output /workspace/port-research/race-activation/exploration-base
```

Add `--event 00c6bc71` for one course or use the exact full source collection name.
Use the bin15 base and separate output directory to preserve career locks.
No native race is started, no SDK build is run and no commit is made by this task.
