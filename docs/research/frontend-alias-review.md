# Frontend/Alias correctness and original-evidence review

2026-11-03. Source review only: no SDK build, save-file mutation, original callback
execution or runtime change. Owned helper `tools/frontend_alias_reference.py`
records a reproducible source snapshot and verifies six decoded original layouts
against the existing inventory. Private output:
`/workspace/port-research/frontend-flow/alias-review.json`.

## Original fidelity evidence

The SHA-pinned USA DOL contains CreateUIProfileManager, PMCreateNew, PMLoad,
PMDelete, PMPopDelete, PMSave, CreateUIDeleteProfile and MainProfileManager.
Original decoded Profile Manager, Delete Profile, GC boot/main, main menu and
Press Start layouts all match their recorded decoded-byte SHA and length.

No additional original capacity, name-length, character-set, name-comparison or
menu-order rule was recovered in this review. Conservative materialized-address
and direct pointer-word scans for the selected callback-name strings yielded no
new callable consumer. This is not proof that the original callbacks are absent
or unreachable. Callback names may be retained vocabulary rather than direct
runtime string users.

The decoded profile/delete layout printable strings primarily identify resources
and the original source package path. They do not expose a proven maximum name
length or slot count. There is no proved original rename callback in this pass.
The current 16 slots, 31-character ASCII names, case-insensitive uniqueness and
rename action are port choices until original consumers are established. They
must not be described as GameCube limits or complete original Alias behaviour.

## Actionable current source findings

These observations refer to the source hashes in the private review snapshot;
parent fixes can supersede them without changing the original evidence above.

1. **An unreadable save is treated as missing.** `load_aliases` skips every failed
   `fopen`, and the previous-file probe in `save_aliases` also treats every failure
   as absence. A primary save that exists but is unreadable (EACCES/EIO and similar)
   can therefore leave writes enabled. Directory-level rename permissions may
   still permit replacing it. Distinguish ENOENT from other errors, latch a write
   block on unexpected access/read errors, and avoid destructive recovery until
   a valid candidate is verified. Do not equate a failed open with nonexistence.

2. **Touch and controller selection can disagree in one input frame.** The MENU
   branch resolves a touch row, then independently processes D-pad movement before
   dispatching the accepted selection. On Delete confirmation this can turn a
   touched Cancel into Delete, or vice versa, if another navigation key went down
   simultaneously. Give controller navigation or touch exclusive precedence and
   apply it consistently. Test a simultaneous touch plus navigation event on both
   confirmation rows. Adjacent two-pixel row gaps also currently accept touches;
   this is a minor hit-box choice, separate from the confirmation bug.

3. **IDs can be reused after deletion.** New IDs are derived from the maximum ID
   among currently present aliases. Deleting the highest alias, or deleting all
   aliases, allows that identifier to be reused. This is harmless for the current
   aliases-only file but becomes a progression isolation bug if upcoming career
   saves use the alias ID as their namespace. Before binding career state, retain
   a persistent monotonic next-ID/generation, or explicitly invalidate the deleted
   namespace. Handle exhaustion and save-version migration rather than wrapping.

4. **Backup recovery has no write-recovery flow.** A corrupt primary followed by a
   valid backup restores the displayed aliases but intentionally keeps writes
   blocked. This preserves the corrupt primary and is documented current policy,
   not a decoder defect. The user cannot resolve that condition from the current
   Alias UI. Before calling profile recovery complete, provide a deliberate
   recovery choice that preserves the bad file and safely promotes verified data.

The app's pending/backup promotion uses fflush/fclose and rename. This review
has not validated SD/FAT rename-replacement behaviour, fsync/power-loss durability
or software-keyboard lifecycle on actual 3DS. No stronger durability guarantee
should be inferred from host codec corruption checks.

## Things that are already sound in the reviewed source

- NFA1 CRC covers header selection/count and the full record region, not names
  alone. Decode rejects malformed data before assigning the destination.
- Rename copies its input before clearing the old name, so self-aliasing calls
  do not erase their source string.
- Delete confirmation defaults to Cancel and records the chosen stable ID.
  Its displayed target name points into the persistent global store.
- State is assigned only after successful save promotion. Invalid/duplicate
  names and failed persistence do not commit the in-memory candidate.
- Original game assets are not deleted by Alias removal. Career progression is
  not saved or loaded by this format yet, which must remain explicit.

## Reproduce

```sh
PYTHONPATH=tools python tools/frontend_alias_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --frontend /workspace/port-research/frontend-flow \
  --output /workspace/port-research/frontend-flow/alias-review.json
```

The helper inventories exact original evidence and source constructs. It does
not execute original callbacks or claim that static pattern matches are runtime
regression tests. Original save/menu/profile consumer recovery remains separate
from the 3DS-specific persistence and input fixes above.

## Subsequent root fixes

The source now blocks writes after non-ENOENT open failures, gives controller
keys precedence over simultaneous menu touch, and persists monotonic issued IDs
in NFA1/version2. Host tests include legacy v1 migration, delete/reload/create
without ID reuse, ID exhaustion and full-file corruption rejection. The original
GC limits/order/rename evidence and the missing explicit recovery UI remain open.
