# Native event catalog, tutorial selection and Alias persistence

This resumes the interrupted source pass. All prior inputs and uncommitted files
survived. The user still requests no new 3DS build; only portable host components
were compiled/tested, with no SDK build, emulator run or release package.

## Bounded source event data

`tools/build_event_catalog.py` creates private NRE1/version2 data from the recovered
catalog and pinned USA DOL. The135,218-byte pack contains277 source definitions,
2,462 spatial nodes and1,990 checkpoint references. It preserves source float32
values/bytes and original checkpoint ordering; missing spatial fields are explicit
presence bits. Definitions include templates/challenges, not277 playable races.
Private current pack: `/workspace/port-research/race-story/events-v2.nre`.
The older events.nre is retained as a previous version and is not current.

`mw_event_catalog.[ch]` supplies a bounded zero-copy reader with CRC, exact layout,
reserved fields, sorted unique keys, string boundaries, finite floats and resolved
node references checked before publishing a view. Failure leaves the output
unchanged. Caller-owned ordered key storage binds eligible data to the existing
race-progress core. Movie names are preserved as data, not automatically played.
The pack and borrowed view must remain immutable/alive while used.

The native end-to-end host test validates all277 definitions and2,462 nodes,
exercises216 source-bound routes through2,689 ordered checkpoint/lap events, and
rejects23 malformed variants including cases with recomputed valid CRCs.
No checkpoint sorting, generated test road or filename-based mode classification
is introduced. Actual driving/trigger detection and original finish/lap consumers
remain separate; this catalog/core is not yet called from the app's menu loop.

## Exact source event types and tutorials

Original getter801A7398 queries field0F6BCDE1, then compares its source string
case-sensitively against the11-entry table8041D31C using original strcmp80063034.
`event_type_reference.py` executes the unchanged lookup loop/table/strcmp with
only attribute access supplied synthetically. `mw_event_type.c` matches17 string
cases and all277 actual source definitions. Seven source definitions (empty
strings and multipoint) remain type -1; no unsupported mapping is invented.

The pack carries that exact original numeric type. The catalog's tutorial helper
feeds it into `mw_story_tutorial_select`: type2 drag/bit40, type5 speedtrap/bit80,
type4 tollbooth/bit100. Source once flags update at selection time, before playback.
113 source definitions select a tutorial with cleared once flags; each suppresses
repeat selection after the bit is set. This is not113 distinct tutorial movies.
Compiled portable selector output matches480 bounded original PPC cases.

The outer manager/player/event preconditions must still be established by callers.
This does not provide a movie decoder, original career transition or Alias-backed
career persistence. Source IntroMovie/OutroMovie fields do not yet have proven
execution conditions. The linked-event field's cleanup check does not prove an
automatic next race. See story-flow-consumers.md for exact evidence/limits.

## Alias fixes that survived the interruption

The app's source now distinguishes ENOENT from other save-open failures before
allowing writes, and gives controller input precedence over simultaneous menu
touch. Delete confirmation cannot have its touch selection moved by a D-pad
press in that frame. Existing corrupted-primary recovery remains read-only; a
repair UI is not implemented and damaged input is not overwritten silently.

NFA1/version2 preserves a monotonic last-issued Alias ID in its CRC-covered
header. Deleting the highest or every alias no longer permits future profiles to
reuse that ID. Exhausted IDs fail without mutation. Version1 saves migrate using
the maximum surviving ID; deleted historical IDs absent from an old version1
file cannot be reconstructed. No career files have been produced by this source
pass. Capacity/name restrictions remain3DS port choices, not verified GC limits.

Host ASan/UBSan checks cover CRUD, full save roundtrip,5,376 single-bit corruptions,
monotonic IDs after deleting/reloading an empty store, exhaustion and legacy
migration, plus ordered race progress. No SDK or physical SD test was performed.

## Trigger recovery boundary

The source trigger constructor and parameter permutations have original-execution
comparisons. Shape basis differs from render basis; data stays in source form.
The resumed narrowphase work recovers mixed-axis box half extents and concrete
OBB call sites. An unresolved overlap counterexample remains negative evidence.
Do not present a point/radius shortcut or generic SAT as the original detector.
See race-trigger-consumers.md and race-gate-containment.md for the exact scope.
