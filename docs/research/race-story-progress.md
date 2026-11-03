# Original race and story data checkpoint

2026-11-03. This is a read-only source-data export. No 3DS build, runtime event
logic, shared parser or original input was changed. It does not make a playable
race, implement progression or play cutscenes.

## Concrete export

`tools/race_story_export.py` loads the SHA-pinned USA DOL and original packed
GAMEPLAY plus ATTRIBUTES schema. It retains all original field values and source
provenance, resolves typed GCollectionKey references across packages, and exports
route nodes, start/finish associations, bin definitions and story movie strings.

Private output: `/workspace/port-research/race-story/catalog.json`, compact
`summary.json`, and `verification.json`. Original numerical positions/rotations
are unchanged. Raw game data and the full catalog should remain outside Git.

Measured source definitions:

- 277 collections contain NumLaps, including templates and challenge definitions.
  This is not a count of shipped playable races.
- 216 contain original ordered checkpoint arrays, with 1,990 references.
- 16 race_bin_NN collections include bin16 intro data as well as Blacklist bins.
- Six definitions contain explicit Storyfmv movie strings.
- 14,830 resolved typed-key observations and 2,654 null observations are retained;
  no nonzero key in the exported graph remains unresolved. Counts include repeat
  observations in route views, not that many unique objects.

The earlier attribute reader leaves GCollectionKey as four raw bytes. The new
export interprets that type only as its original big-endian32 collection key,
then resolves it against the existing gameplay collections. Every scalar/array
is compared independently against its preserved original bytes. The first run
checked all5,605 typed reference fields and preserved the checkpoint-order
counterexample below.

## Race route associations and ordering

Source field34aae3fc resolves to the ordered checkpoint nodes; e43b2ccc resolves
to startgrid nodes and b0a24adc to finishline nodes. Field916e0e78 resolves to
folder children. Field64273c71 links some event definitions to other events.
These associations are established by actual source references and node names;
full original gameplay consumers and transition conditions still require tracing.
Constant materialization xrefs are recorded in the compact summary without
invented function names.

Exact VLT hash-label matches were additionally checked:

| Candidate label | Original field hash |
| --- | --- |
| Checkpoint | 34aae3fc |
| Children | 916e0e78 |
| IntroMovie | f572ede8 |
| OutroMovie | b70268c0 |
| BossRaces | d5a174aa |

These label candidates do not prove when their consumers execute, whether a movie
is conditioned on success/failure, or which events are unlocked. The exporter
keeps original hashes/types/provenance instead of replacing unknown semantics.

Example race_bin_10/10_2_1_sprint has nine checkpoint references in original order,
original Position and Rotation per node, NumLaps1, Region coastal and
TrafficLevel20. Other scalar fields and source trigger-vector6d9e21ad are kept
without guessed physical units or collision interpretation.

Important counterexample: 16_2_1_d_day_intro's ordered route begins checkpoint1,
checkpoint3,checkpoint4; checkpoint2 is absent despite existing in its child
folder. Do not sort names or use all folder children as the race route.
Similarly 16_2_2_sprint's start and finish nodes use prefixed names, not literal
`startgrid`/`finishline`; the actual references select them correctly.

## Story source references

| Definition | Field f572ede8 | Field b70268c0 |
| --- | --- | --- |
| 16_2_1_d_day_intro | storyfmv_pin11 | storyfmv_bus12 |
| 16_1_0_partial_dday | storyfmv_rac01 | empty |
| 16_2_2_sprint | storyfmv_cro06_coh06a | empty |
| 16_2_3_sprint | storyfmv_raz08 | empty |
| race_bin_01/epic_pursuit | Storyfmv_her136 | empty |
| race_bin_01/1_5_2_speedtraprace | storyfmv_bla134 | empty |

Original field64273c71 links partial_dday ->16_2_2_sprint ->16_2_3_sprint ->
16_1_1_circuit. The graph is retained but is not labelled a proven automatic
success transition. Many root definitions also contain original IntroNis and
finish-scene names: in-engine NIS and pre-rendered movies are separate media
systems and must not be treated as interchangeable video filenames.

Bin15 contains original opponent, rewards, unlocks, ordinary race and boss-race
reference arrays. Bin01 contains its own opponent, race lists and epic_pursuit.
All lists and scalar values are preserved rather than reconstructing them from
remembered game rules. Numeric bounty/win/milestone thresholds must be bound to
original consumers before a faithful unlock engine can use them.

## Reproduce and integration gates

```sh
PYTHONPATH=tools python tools/race_story_export.py \
  --gameplay /workspace/port-research/whole-game-metadata-20261103/GLOBAL-GAMEPLAY-at267364352.BIN \
  --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/race-story/catalog.json \
  --summary /workspace/port-research/race-story/summary.json
```

Before claiming playable original races, recover checkpoint trigger orientation,
shape/vector units, lap/reset/wrong-way rules, AI course and opponent spawning,
event barrier activation plus collision, start/countdown/results and reward
consumers. Before story playback, verify media payloads/codecs, original movie
trigger ordering/skip/AV behaviour and state transitions. Alias/save persistence
must reference actual progression state rather than unlocking all source nodes.
No guessed career graph, hardcoded threshold, dummy movie or test-road event was
introduced in this checkpoint.

## Additional exact field-label matches: requirements and dimensions

The source schema hashes also exactly match Dimensions6d9e21ad,
RequiredBountyd3657d92, RequiredRacesWond617fedc and RequiredChallenges6dd4b98b.
This establishes concrete source fields for a requirements display. Original
unlock evaluation, event-win accounting and challenge completion producers still
need integration; no requirement value below is guessed or copied from memory.

| Bin | RequiredBounty | RequiredRacesWon | RequiredChallenges |
| --- | ---: | ---: | ---: |
| 15 | 20000 | 3 | 3 |
| 14 | 50000 | 4 | 3 |
| 13 | 100000 | 4 | 3 |
| 12 | 180000 | 4 | 3 |
| 11 | 300000 | 5 | 3 |
| 10 | 500000 | 5 | 4 |
| 09 | 790000 | 5 | 4 |
| 08 | 1180000 | 5 | 4 |
| 07 | 1680000 | 7 | 4 |
| 06 | 2300000 | 7 | 4 |
| 05 | 3050000 | 7 | 4 |
| 04 | 4050000 | 7 | 5 |
| 03 | 5550000 | 8 | 5 |
| 02 | 7550000 | 8 | 5 |
| 01 | 10000000 | 9 | 5 |
| 16 (intro) | 0 | 4 | 0 |

All16 bins, original scalar provenance and reference arrays are in the private
catalog. Dimensions names the vector previously retained as6d9e21ad; its exact
half/full extents, axis interpretation and trigger crossing consumer remain open.
