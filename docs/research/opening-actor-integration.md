# Opening race and police application bridge

`MwOpeningActors` composes the existing source-bound opening-opponent and police
trigger packs. The actor identities, explicit spawn positions and police Width
triggers come from the original game. Route following, driving policy, grid
fallbacks, ranking tie rules and the 30Hz NPC scheduler remain native adapters;
this is not the original racing or police AI.

## Application lifecycle

1. Keep the large state static or on the heap. `mw_opening_actors_begin` borrows
   the two opened packs, event catalog and original road network, then prepares
   the event's bounded source-curve routes. Failed preparation leaves an existing
   event intact. Temporary pathfinding allocation occurs only here.
2. Read `state.race.actors[i].spec.model`, load its real model and establish its
   physical collision/ground capability before admitting it. Authoritative
   post-NIS poses can use `mw_race_ai_place(&state.race, ...)` before start.
   Police events additionally require an admitted `COPMIDSIZE` render model and
   physical capability; otherwise start fails.
3. Start alongside the actual player's race clock after the countdown. Update
   only when the player's simulation is admitted. Supply actual controlled-player
   source position and the real physical drive callback, not a no-op callback.
   Public `race.actors` and `pursuit.actors` provide admitted rendering poses.
4. Pause/resume the wrapper with the player. Relocation resets the pursuit sweep
   and trail so a recovery teleport cannot cross police triggers artificially.
   Use reset on event cancellation and begin afresh on retries.
5. Query rank only after the player's verified ordered finish. The bridge refuses
   any rank before a successful actual NPC physical tick, after a failed racer
   or police callback, or if the existing race module rejects actor admission or
   route correspondence. It does not grant rewards or scripted career outcomes.

The original first partial and final sabotage event still belong to `MwCareer`'s
scripted outcomes. A geometric finish or this bridge's rank must not turn either
into an ordinary career win.

## Bounded work and failure behavior

Each update accepts at most100ms, processes the actual player's police trigger
sweep and accumulates an integer rational30Hz phase. There are at most three
physical ticks, nine racing drive callbacks and six police drive callbacks per
update. Normal60Hz rendering typically performs zero or one NPC tick per frame.
There is no allocation, pathfinding, nearest-node search or disk access in this
path. Each underlying controller commits its own successful tick; a later
failure does not rewind a different controller that already completed. Any such
failure disables rank and drops excess pending whole ticks rather than creating
an unbounded retry backlog. A later complete successful tick restores ranking.

## Validation

The strict C11 ASan/UBSan integration test uses all five genuine event records,
seven original opponent identities and both police events. It checks missing
model admission, no rank before physical simulation, racer and cop callback
failure, recovery, exact rational30Hz counts, bounded callbacks, no per-frame
planning, pause freezing, source-trigger spawning, teleport sweep reset and
transactional failed event preparation. These checks do not establish original
AI fidelity or hardware performance.

```sh
bash tools/test_opening_actors.sh \
 /workspace/port-research/opening-opponents/native-v1/opening-opponents.nro \
 /workspace/port-research/opening-pursuit/native-v1/opening-pursuit.npp \
 /workspace/port-research/race-story/events-v3.nre \
 /workspace/port-research/street-systems/native-v1/road-network.mwt
```
