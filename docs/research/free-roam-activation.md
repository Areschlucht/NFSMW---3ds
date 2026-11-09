# Materialized original cold free-roam activation

`tools/build_free_roam_activation.py` reads verified source group/member data,
original stream-instance bytes, source career plans and every converted WSI
section. It writes a private source-offset flag plan, not runtime policy by
model filename. No renderer or collision source is edited by this tool.

## Cold reset is not blanket suppression

The original group loader reset at802BD304 zeros the4096-byte active-group array
except its sentinel entry0. Import802BD234 does not activate imported groups.
Reset802BD50C tests each group's active-array byte before visiting its members;
it only ORs0x10 into members of previously active groups. Therefore a cold reset
visits no imported groups, and must NOT mark all14,313 members inactive. The large
unnamed first group includes ordinary scenery, not only race arrows.

All17,827 mapped original instance occurrences have low flags EXACTLY matching
their source member table's initial flags. The tool preserves this cold source
state, applies SCENERY_GROUP_DOOR with argument0, then the exact selected bin's
ordered operations. Warm replacement additionally needs the previous active-group
set reset before applying the new plan; this export is explicitly cold-state.

## Concrete native lookup inputs

Private outputs:

- `/workspace/port-research/free-roam-activation/bin15.json`
- `/workspace/port-research/free-roam-activation/bin15-summary.json`
- Corresponding bin16 and bin1 outputs in the same directory.

Each full output includes sorted `overrides` records with
`source_instance_offset`, `expected_source_flags`, `effective_flags`. These keys
are the original source offsets already retained in WSI records. Every source
instance SHA and every WSI manifest SHA is checked before output. No source
geometry or original file is removed or rewritten.

| Original selected source state | Changed source occurrences | Four-triangle track-barrier occurrences suppressed by normal mask0x10 | Retained barrier occurrences |
| --- | ---: | ---: | ---: |
| Bin15 (early career) | 58 | 8,710 | 53 |
| Bin16 (intro, equivalent lock set) | 58 | 8,710 | 53 |
| Bin1 (late/open-area source state) | 5 | 8,763 | 0 |

Bin15 and16 override arrays are byte-identical. The five non-barrier changes are
DOOR group members. Bin15's other53 changes retain original career lock provider
occurrences. Counts refer to the complete stream, not simultaneous visible walls.

Every selected plan has ZERO original0x400 transform transitions, so these static
flag plans do not substitute guessed matrix changes. A future star-state plan
that needs an eligible transform change is refused by the exporter.

Normal render rejection is the separately proved original predicate:
`(((effective_flags & 0xff) ^ 0x60) & 0x10) != 0`.
The tool compares its distinct source flag pairs with original unchanged flag-copy
and render-predicate windows when `--verify-original` is passed.

Choosing bin1 for an explicitly labelled prototype full-city exploration shortcut
would use an actual source open-area plan without fabricating a saved career.
Choosing bin15/16 preserves early-career locks. The caller must state its selected
state; this exporter does not alter Alias/career progression or decide which user
flow should offer whole-city exploration.

## Coherent collision group admission

The parallel collision audit has now traced original query windows802F2000 and
802F2700: CI+24 decimal (0x18) is a scenery-group ID, and a nonzero ID is skipped
when the same original active-group array entry is zero. This is distinct from
the scene-instance0x10 render bit and from per-wall0xC0 flags.

The exporter now supplies `active_group_ids`: [71] for bin1, and
[71,200,356,389,495,496] for bin15/16. Group0 is unconditionally admitted, matching
the original bypass. A caller must share this exact plan with render overrides
and collision group admission; it must not use all-wall masking or geometry
proximity. Original per-wall material/exclusion flags stay unchanged.

The collision audit also checked that ordinary source ground/static walls use
group0 (38,347 ground nodes/37,454 walls across unique packages). The large unnamed
scene group1 has no CI entries, so cold group1 state does not remove ordinary road
collision. Nonzero group754 contains five ground nodes and remains inactive in
these exact plans unless another original producer is recovered. This is a cold
source-state policy, not a claim that all career/free-roam scheduling is ported.
See the root collision agent's report for exact contact provenance and execution
comparisons. No collision implementation was edited by this exporter task.

## Reproduce

```
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/build_free_roam_activation.py \
 --catalog /workspace/port-research/race-story/catalog.json \
 --groups /workspace/port-research/event-activation/recovered-group-members.json \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
 --scene /workspace/port-research/world-streaming/scene-native \
 --bin 15 --verify-original \
 --output /workspace/port-research/free-roam-activation/bin15.json \
 --summary /workspace/port-research/free-roam-activation/bin15-summary.json
```

Use `--bin 1` or16 with distinct output names for the alternate original plans.
Original data and full generated flag/instance records remain private.
