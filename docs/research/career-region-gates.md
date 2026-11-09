# Original career-bin region gate plans

Read-only recovery from the supplied USA GameCube data and executable. No SDK
build, runtime activation change, shared file edit or commit is performed by this
tool. The user's observation that career progression restricts the city is
supported by concrete original bin-to-scenery-group consumers.

## Exact original per-bin plans

`tools/career_region_gates.py` exports all16 source bin definitions, original
array order, original leading-star argument, full field provenance and matching
scenery-group membership. The current plans refer to six `BARRIER_LOCKED_*`
groups containing32 logical member records. Every referenced member's original
stream-instance bytes are checked against the previously recovered SHA256.
Source positions are exported only as coordinates, without guessed district names.

| Source BinIndex | Ordered group literals from field E244F26B |
| --- | --- |
| 16 | LOCKED_15, LOCKED_14, LOCKED_11, LOCKED_13, LOCKED_12 |
| 15 | LOCKED_15, LOCKED_14, LOCKED_11, LOCKED_13, LOCKED_12 |
| 14 | LOCKED_12, LOCKED_13, LOCKED_11, LOCKED_15, LOCKED_14 |
| 13 | LOCKED_15, LOCKED_14, LOCKED_11, LOCKED_13, LOCKED_12 |
| 12 | LOCKED_12, LOCKED_13, LOCKED_10 |
| 11 | LOCKED_10, LOCKED_13, LOCKED_12 |
| 10 | LOCKED_12, LOCKED_13, LOCKED_10 |
| 09 | LOCKED_10, LOCKED_13, LOCKED_12 |
| 08 through01 | No group field in the resolved inherited source definition |

Each table shorthand has the literal prefix `BARRIER_`; e.g. `LOCKED_15` is
`BARRIER_LOCKED_15`. All of these literals have **no leading star**, hence original
state argument zero. This argument is preserved, not renamed a visible/hidden
Boolean: bit0400 can cause transform changes in the shared group consumer.
Every source member here has initial low flags8070; the full source instance
flags/provider occurrences remain preserved separately.

Ignoring only array order, plan sets change at source transitions13→12 and09→08:

- 13→12 removes LOCKED_11/14/15, retains LOCKED_12/13 and adds LOCKED_10.
- 09→08 removes LOCKED_10/12/13, adding none.

This is not simply a steadily shrinking group set: the first boundary adds a
new gate group as others are removed. Group suffixes are object labels, not
proof that a group is named for its Blacklist rival. Exact Rosewood/Camden/
Downtown ownership is not established from coordinate envelopes alone.

## Original current-bin and group consumer chain

The script registration's two-word callback descriptor at803EDE7C is
`0000FFFF,8019DDFC`, tied to the original `EnableBinBarriers` name. Its callback
8019DDFC loads the current bin object from manager+1AB0 and, if non-null, calls
the existing source group-apply loop801A9960. This call alone reapplies the
current plan; it does not reset all groups first.

The separate bin-replacement routine8019DE34:

1. Loads the old object at manager+1AB0. If non-null, calls801A99E4.
2. Resolves the requested bin through801A43EC and stores the result at+1AB0.
3. If the new object is non-null, applies its group array through801A9960.

801A43EC searches original28-byte bin records using getter801A9558. That getter
reads field6CE23062, exactly the VLT hash of **BinIndex**. All16 actual catalog
values match their original source bin numbers and big-endian source bytes.

The update path8019E1EC..8019E21C performs the replacement when manager+1AA4 is
zero and its request flag+1AE4 is nonzero. It obtains the profile through global
8041C484, follows pointer+20, then reads **profile byte+EC** as the bin argument.
This establishes a concrete profile/bin input, without assigning guessed names
to every manager state or reconstructing how wins update that profile byte.

## Reset matters, including the empty later plans

801A99E4 calls801FEB00. That reset calls801FEABC, which reaches802BD50C to reset
source member/group flags, then801FEA44. The latter explicitly checks and applies
**SCENERY_GROUP_DOOR with argument zero** when the group exists. The default is
not a guessed FREE_ROAM group. Its original literal is803F57C0; source group71
has hash87DE8337 and five members.

Consequently replacing a bin must not be implemented by merely enabling the
new plan's names and leaving previous groups active. The reset precedes applying
the replacement plan, including a later source definition with no group entries.
Additional collision-system refresh calls in801A99E4/801A9960 remain part of the
original integration contract. This tool does not replace them with the current
independent NWC wall mask or claim rendering/collision ownership is solved.

Race-specific group overlays are separate from legitimate bin locks. Do not
remove every barrier, and do not treat these bin arrays as all event activation.
Profile progression, event cleanup/reset ordering, original collision refresh,
provider selection and conditional transform updates must be integrated together.

## Verification and reproduction

The strict export produced16 plans, six referenced groups and32 logical members.
The full ordered arrays, source offsets, provider candidates, source placements
and provenance remain private at:
`/workspace/port-research/career-region-gates/plans.json`.

A bounded original execution of8019DE34..8019DE7C checks38 cases: old pointer
present/absent crossed with valid bin arguments1..16 and invalid0/17/255.
Only reset, lookup and apply callees are explicitly stubbed. The real original
branch/order/store instructions run unchanged; write guards and instruction
budgets reject escapes. Every case matches reset→lookup→store→apply ordering and
null-new-object handling. This verifies the local prefix, not complete original
reset side effects, database lookup, scheduler, progression or collision execution.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/career_region_gates.py \
  --catalog /workspace/port-research/race-story/catalog.json \
  --groups /workspace/port-research/event-activation/recovered-group-members.json \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --stream /workspace/port-research/rockport/samples/STREAML2RA-full.BUN \
  --verify-original \
  --output /workspace/port-research/career-region-gates/plans.json
```

The tool pins DOL/gameplay provenance, verifies BinIndex source bytes, source-array
counts, unique complete bin coverage, group hashes/membership bounds and each
mapped source instance. No source data is rewritten and no fictional geographic
unlock threshold or unlock save is added.
