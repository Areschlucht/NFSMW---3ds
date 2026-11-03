# Original gameplay/scenery activation recovery

2026-11-03; read-only recovery for the supplied USA GameCube executable.
No runtime renderer, collision filter or event logic is changed here.

## Recovered source records

Original code establishes the previously unknown L2RA chunk purposes:

- `802BD5D4` handles chunk `00034108`. It divides payload size by six, sets the
  record base and byte-swaps three halfwords per record. `802BCCC4` indexes this
  table by `member_id * 6`. The supplied file has **14,313 records**, plus two
  zero alignment bytes. Records contain logical scenery-section number, instance
  index, and the original low flag halfword.
- `802BD234` handles chunk `00034109`. It links variable records, swaps the hash
  at +8, signed group ID at +12, signed member count at +14, and member IDs at
  +20. The stride is `align4(20 + 2*member_count)`. The supplied payload contains
  **754 groups**, IDs 1 through 754, and **14,313 memberships**. All member IDs
  fit the six-byte table. Linked-list words and +16 state bytes are retained
  without invented interpretation.
- `802BD374` looks up loaded group records by hash. Source literal candidates
  recover **736 of the 754 group hashes**, primarily `BARRIER_SPLINE_*`. A hash
  match is a candidate name until consumer/context checks; unmatched groups are
  preserved and must not be discarded.

These counts are source-table sizes, not simultaneously active barriers or
visible draw calls. The large first group remains unnamed in current literal
matching. Do not assume it is FREE_ROAM.

## Direct gameplay-to-group consumer chain

Gameplay field **`e244f26b`** is a text array. The earlier scalar-only search
missed it. The original executable provides a complete local chain:

1. `801A9960` iterates the array.
2. `801A98A8` gets an entry and removes one leading `*`, if present.
3. `801A9900` separately returns whether the unmodified entry starts with `*`.
4. `801A99A4` calls `801FE9AC(stripped_name, leading_star_flag)`.
5. `801FE9AC` validates a recognized prefix using `802C117C`, hashes the
   stripped string using the case-sensitive original hash `80062ECC`, and
   calls `802BD3A8(hash, leading_star_flag)`.

Thus `*` is an actual original state argument, not decorative punctuation.
The exporter preserves both the literal and star state. Array inheritance also
matters: event definitions can inherit bin-level groups. Example inherited
references include `BARRIER_LOCKED_15`, `_14`, `_11`, `_13`, `_12` in the later
bin definitions. They cannot all be suppressed simply because they are barriers.
The human-readable name of field `e244f26b` is not guessed here.

Original table `8043707C` contains five case-insensitive classifier prefixes:
`BARRIER_`, `BARRIERS_`, `PLAYER_BARRIERS_`, `SCENERY_GROUP_`, `FREE_ROAM`.
The first four table entries have a second word of one, and FREE_ROAM zero.
The traced caller uses the classifier's non-null result; it does not consume
that second word. No additional meaning is assigned to it.

## Original state operations and important limits

`802BD3A8` walks a group's member IDs, then performs:

```
member.flags = (member.flags & 0xFBEF) | (argument != 0 ? 0x0400 : 0)
```

`802BD48C` and reset path `802BD50C` OR `0x0010` into member flags, then propagate
state to a loaded scenery section via `802BD040` -> `802BCCD8`.
`802BCCD8` addresses the original instance using `instance_index * 64`, updates
its flag word at +24 preserving the high halfword, and conditionally mutates
its transform when flag `0x400` changes on eligible instances. Therefore the
star flag cannot honestly be reduced to a simple visible/hidden Boolean.

The downstream meanings of `0x10` for render/collision/navigation, complete
load/reset ordering, bin/career producer selection, and the transform mutation
must be integrated together. This pass recovers the original state producer and
membership schema; it does not yet fix the free-roam walls in the playable build.

## Logical identity versus streaming directory identity

An indexed stream entry can contain multiple `80034100` scenery containers,
each with its own `34101` header. That header's word at +12 is the logical
scenery-section number used by the group member records. For example stream
entry 141 contains logical scenery sections 141 and 101. Using only the indexed
entry ID loses membership for secondary scenery containers.

Full-stream mapping also finds repeated logical section/instance identities in
different provider occurrences. The exporter keeps every original source-offset
candidate and its instance-byte hash; it never silently chooses the first.
Resolve original provider activation/remap behaviour before applying membership
to the flattened 3DS scene. The existing WSI records retain original absolute
instance offsets, which can support a precise mapping after provider resolution.

## Tool and validation

`tools/gameplay_activation_recovery.py` reads the original index, supplied packed
gameplay database, schema, DOL and optional complete stream. It exports all group
memberships, field reference provenance, leading-star state and candidate source
instance offsets into private research output. `--summary` writes a compact
count/evidence report. No raw game payloads should be added to Git.

Validated all original group bounds, IDs, member indices and trailing padding.
Four deliberately corrupted count, group ID, member index and padding inputs
were rejected. Python syntax compilation passes. The DOL SHA is pinned, and the
five-entry classifier table is verified against the actual loaded addresses.

Next integration gate: trace group-flag consumers and provider selection;
recover exact event/free-roam/bin state transitions; then use one activation state
for rendering and collision with original career locks preserved. Compare the
same camera/route before and after and measure transparent overdraw separately
from CPU submission. No filename-based global removal is supported by this work.

## Completed export measurements

The full export resolves all **14,313 logical member records** to original stream
instances. **3,514** have two provider occurrences; those repeated candidates have
identical 64-byte instance bytes. All **17,827 distinct original source offsets**
are present in the current WSI scene. Of these, **8,763** bind one of the six
specific XO_TRACKBARRIER models. Membership also covers other scenery; a global
model-name filter would lose the original grouping and state transitions.

The recursive field walk finds **7,390 distinct text-array references**, all in
field e244f26b and all matching a source group. **3,577** carry a leading star.
These are exported field references, not concurrently active groups. Remaining
provider ambiguity is preserved even where instance bytes happen to agree.

Private full output: `/workspace/port-research/event-activation/recovered-group-members.json`.
Private compact output: `/workspace/port-research/event-activation/summary.json`.
