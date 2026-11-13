# Original opening career: source scripts, prizes and native lifecycle

This pass adds a bounded source-bound opening-career packet and portable
controller. It does not itself implement the renderer, a full Lua VM, phone
audio, NIS animation, pursuit AI, vehicle physics or the entire career. The
parent application supplies those consumers and must distinguish playable
integration from the host verification reported here. All original bytecode,
catalogs and media remain private.

## The actual original opening order

The original selector801A4CB0..801A4D2C iterates five eight-byte source IDs at
803EC79C in original order, resolves each through801A42F4/801A7710 and tests its
completion bit2 through801A4B8C. It returns the first unfinished source ID. This
is direct consumer evidence, superseding guesses from names or linked fields.

| Stage | Original ID | Original key | Role | CashValue |
| --- | --- | --- | --- | ---: |
| 0 |16.1.0|42938ce2|Partial D-day; scripted phone/fade exit|0|
| 1 |16.2.2|d348f2cd|Competitive sprint|10000|
| 2 |16.2.3|6ddd8383|Competitive sprint with source police triggers|10000|
| 3 |16.1.1|9f60a40e|Competitive circuit|10000|
| 4 |16.2.1|f7e4440a|Razor D-day; scripted engine failure|0|

Every source event selects M3GTRCAREERSTART. The linked04B06F54 collection is
an intermediate NIS shell, not a sixth playable race: its source NISShell is
true and its OutroNIS is EndingNis03. It links the circuit's PostRaceActivity
to the final D-day event. Exact case-sensitive VLT label matches are
PostRaceActivity64273C71, IntroNISDEC18D3E, OutroNIS54932966 and NISShell4C17FE41.

## The scripts were present in the supplied assets

The GAMEPLAY handler field9A4A020A is an Attrib::Blob descriptor. Its relocated
pointer/size select compressed original Lua5.0 chunks in the same package BIN,
not a missing external script file. The exporter reconstructs all258 observed
handlers:253 HUFF and five JDLZ. The 29 short HUFF chunks decode to165–183 bytes;
the previous texture-era184-byte minimum in nfs_huff_reference was therefore
relaxed to1 without changing its pinned reference decoder or output/write guards.

The strict Lua reader checks the observed little-endian float32 header,
prototype/count/string bounds, nesting and exact end of input. JDLZ's up-to-three
unused tail bytes are retained in provenance. Native game code is not executed
by the Lua inspection helper: it interprets a bounded subset of Lua5.0
instructions with supplied mock dictionaries/functions. Unsupported instructions
fail. No file access, network access, eval or Python environment is available to
the inspected bytecode.

Nineteen instruction-path fixtures verify actual conditional calls, including
empty/nonempty movie selection, player-only police spawn/bail/911, player-only
engine sabotage, the partial race timers and final car-lot dispatch. This is
a source bytecode interpretation check, not execution of the original native
Lua VM or complete stategraph scheduler.

## Movies and NIS remain separate

The actual intromovie handler tests IntroMovie against an empty string. A
nonempty value calls EPlayRaceMovie; empty advances to intronis. Its movie-finished
handler also advances to intronis. The intronis handler selects IntroNIS and
dispatches NIS.Play, and the NISShell override advances to outronis instead of a
race. The outromovie handler similarly chooses actual playback or done.

| Stage | IntroMovie | IntroNIS | Relevant post-media |
| --- | --- | --- | --- |
|0|storyfmv_rac01|IntroNisDD|Next source event|
|1|storyfmv_cro06_coh06a|GenericStart|Next source event|
|2|storyfmv_raz08|IntroNis05|Next source event|
|3|empty|IntroNis10|Linked shell's EndingNis03|
|4|storyfmv_pin11|IntroNis04|OutroMovie storyfmv_bus12|

`mw_career_media` returns the exact asset for the current movie or NIS phase.
Only successful playback or an explicitly accepted caller skip may invoke
media_finished. A decoder failure must not silently finish the media. The
portable controller collapses the source's empty message/shell bookkeeping into
explicit media phases; it is an authored native integration, not the entire
original script machine. Rendering a NIS as a generic rotating car is not an
original NIS implementation and must not be claimed as one.

## Partial race and Razor loss are not normal wins

The first partial event's original player-only call_from_mia trigger is
40CAF8C1. Its script requests ECellCall(10), with once-only DoMiaCellCall and
WaitForCallLoad state. The actual cell-call-start handler sets fade to8 seconds.
That timer forces AI control and begins a3-second killrace tail. The final
timer clears AI control, ends the fade and changes to postrace. The native
controller models those timing states; phone audio and actual AI handoff remain
caller-owned. Starting the timer immediately without a call-start notification
is a documented caller adaptation, not original phone playback.

The final event's player-only kill_engine trigger F73BBBCB kills backup and
calls SabotageEngine(GetPlayerElement(0),5). The second argument5 is preserved
as source evidence; it is not relabelled as a proven five-second delay.
NotifyEngineBlown sets eblown to1 second; that timer fades and changes to
postrace. The final done override calls JumpToCarLot. The native controller
requires the trigger and engine-blown notification, then waits the actual
one-second timer. A normal geometric finish cannot award a final story win.

Both special triggers use original Width, not Radius or Dimensions:

- Mia: Position(2541.7261,52.23893,104.1328), Rotation106.8593, Width100.
- Engine: Position(2953.1489,282.24249,34.95509), Rotation-99.85694, Width160.

Original Width construction is kind1 with internal half-extents
(Width/2,50,0.5); see playable-race documentation and the verified width_sweep
helper. NFC retains Width separately with present bit16 and a float at trigger
record+40. It must never be treated as an arbitrary spherical radius.

## Original opening pursuit actions

The stage2 handler first rejects non-player actors. On cop_spawn_trigger it
calls SetCopsEnabled(true), then SpawnCop(cop_spawn_1,"copmidsize",false,false)
and SpawnCop(cop_spawn_2,"copmidsize",false,false). bail_pursuit invokes
EBailPursuit(1,1), then NoNewPursuitsOrCops. trigger_911 invokes E911Call.
The final D-day event has its own corresponding spawn and bail triggers.

Private opening_police_nodes retain every source position, rotation, Width and
field byte range. Stage2 source keys are8760F956 spawn trigger, C55B4CBA911,
04045A5C bail,993840EA first spawn and0A54490F second spawn. Final D-day keys
areB14F35BA spawn trigger,A2568789 bail,52D38E96/5D691CB3 spawns. Original police
driving, heat escalation, bust/cooldown and speech are separate systems; a
bounded new chaser controller must be labelled a native adapter.

## Wallet and own-car choice

Read career-wallet.md for164 bounded original PPC comparisons and exact caller
bindings. The actual new-career reset clears the wallet at profile+F0 to0 and
sets intro bin16. CashValue is the exact D8BAA07B prize field, and the career
award branch requires local identity,1-based rank1, mode2 and a clear per-event
cash latch. Three legitimate source10000-prize wins produce30000 from this zero
reset. No30000 starting grant is invented, and an optional10000 bonus must not
be granted without its actual detection producer.

The supplied FE_ATTRIB database has exactly four positive-cost car rows with
UnlockedAt16 (exact hash60F99F57); Cost exactly hashes toE61673E9:

| Source car | Frontend key | Cost |
| --- | --- | ---: |
|gti|79054B53|35000|
|is300|5BFF2FB0|27000|
|cobaltss|5A784095|26000|
|punto|A6EE7A11|27000|

The native flow separately records pending selection and actual ownership.
Purchases require a known sufficient wallet and debit once. With only the three
verified wins, GTI remains unaffordable. This does not establish every possible
original callback/bonus after Razor's loss; no extra currency is synthesized.
The complete original car-lot list ordering and all later unlock rules remain
outside this opening controller.

## Packet, persistence and verification

Private packet: `/workspace/port-research/opening-career/native-v3/opening-career.nfc`,
1058 bytes, SHA256
e831b3424a21fc228f0ad31e14c75d914364188ac27229ad822cc5d9936c12e6.

NFC1 header160 stores exact counts/offsets, CRC and GAMEPLAY/FE/DOL identities.
Five64-byte stage records include source CashValue at+36; four64-byte car
records and two64-byte special triggers precede bounded ASCII strings. Open
checks all source event IDs/flags, expected special keys, reserved bytes and
finite geometry before publishing a borrowed view. Failed reads leave the old
view untouched. Generated original data is not committed.

NCS1 is a new128-byte 3DS career save, not a GameCube memory-card format.
It binds Alias ID, packet CRC/source identity, stage, phase, scripted timer,
wallet, pending car and ownership. CRC covers the whole state payload; rejected
input leaves state unchanged. The application owns atomic SD promotion/backup.
Media and timer notifications cannot double-pay or turn the scripted final loss
into a win. Future full-career progress is not falsely marked completed.

Host ASan/UBSan tests cover all five phases, separate movie/NIS completion,
partial8+3 timers, final1-second story loss, rejected wrong/duplicate finishes,
three once-only source prizes, unaffordable GTI and real Cobalt purchase leaving
4000, mid-timer save/resume, Alias mismatch and all1024 single-bit save
corruptions. Guard tests reject impossible timer/flag combinations and CRC-valid
phase corruption. Source tests verify19 actual Lua subset paths, all29 short
HUFF scripts and eleven malformed HUFF/Lua inputs. No SDK or emulator validation
is claimed by this subtask.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/build_opening_career.py \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --gameplay /workspace/port-research/whole-game-metadata-20261103/GLOBAL-GAMEPLAY-at267364352.BIN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --frontend /workspace/attachments/430e54cf-3f7e-4284-81a1-67743e30a796/GLOBAL-FE_ATTRIB.BIN \
 --output /workspace/port-research/opening-career/native-v3
```
