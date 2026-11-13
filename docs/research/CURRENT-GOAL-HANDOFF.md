# Current opening-career integration handoff

The user wants original-style GC/DS combined two-screen menus: touchable bottom
icons, top current car in original garage environments and changing camera views.
The target milestone is the original opening career through purchasing a first
car, including movies, in-engine NIS, street traffic, police pursuit and breakable
props. Original handling/camera fidelity and performance are explicit priorities.
Make the deliverable build after this milestone is integrated; do not mistake
component exports/tests for a finished playable game. Commit/push source often.

## Surviving private assets

- All original archives: `/workspace/port-research/original-archives`.
- Original world/runtime inputs: `dist/v018-shipping-install/3ds/nfsmw-rockport`.
- Career: `opening-career/native-v3/opening-career.nfc` under port-research.
- Eight movie clips: `career-movies/native-v1/*.nvm`, approximately357MB, genuine
  frame counts retained. Native JPEG/PCM and three-buffer NDSP helpers tested.
- Starter cars and traffic: `starter-cars/native-v2/{COBALTSS,GTI,IS300,PUNTO,TRAFHA}`
  plus catalog.nvc. Original COPMIDSIZE: `opening-police-car/v1` separate catalog.
- Menus: `menu-reference/icons-v1/menu-icons.nmi`, original13icons.
- Five original environments: `menu-reference/platform-native-v1/*`, native NFM,
  T3X textures, source normalization in scene.json and placement.bin.
- Source camera: `menu-reference/source-camera-v1/camera.ncp` (five visual ecars).
- Street graph: `street-systems/native-v1/road-network.mwt`.
- Pursuit: `opening-pursuit/native-v1/opening-pursuit.npp`.
- Breakables: `breakable-instances/native-v1/breakables.nbp`.
- Race absolute states: `race-activation/native-{exploration,career-bin15,career-bin16}`.
- Source-bound dynamics profiles: `driving-runtime/*.ndp`.

## Proven opening flow

Original selector801A4CB0 chooses five event IDs in order:
42938ce2, d348f2cd,6ddd8383,9f60a40e,f7e4440a.
The intermediate04b06f54 is a NIS shell, not a sixth playable race. Every stage
uses M3GTRCAREERSTART. First partial uses Mia Width100 trigger40caf8c1, call start,
8-second fade/AI timer then3-second tail. Final stage uses Width160 sabotage
triggerf73bbbcb, engine-blown notification,1second, then JumpToCarLot. These are
not ordinary race wins. The middle three legitimate first-place career results
award original CashValue10000 each, exactly once. New wallet starts at zero.
Four first-car options and actual prices: Cobalt26000, Punto27000, IS30027000,
GTI35000. Do not invent a bonus to make the GTI affordable.

Original scripts enable/spawn two copmidsize units in third selector event
6ddd8383 (second full race after partial), and also final DDay; explicit bail and
911 events are exported. Native pursuit is a documented adapter, not original AI.

## Integration state

Main source contains partial menu icons/camera/garage loading, active-car loader,
cached traffic, lossless indexed vehicle draws, and race/career/movie globals and
helpers. It is NOT yet a completed or verified SDK build. Career main-loop glue,
movie/NIS phase dispatch, police/breakables rendering and car-choice purchase flow
remain to finish. Inspect compiler flags/source lists: new modules are not all
added yet. The last attempted patch failed before application when exec transport
closed: it would remove restore_exploration's hardcoded700-byte length, make
save_career accept transactional candidate state, add primary/backup read handling,
and restore BMW after choosing another car. Do not assume that patch applied.

NWS1/version2 now accepts event key at36 and0x400/0x10 source overrides. Renderer
stores effective flags per staged object, applies exact wrapped-Q13 reflection,
and has explicit state invalidation so unchanged-camera transitions restage.
`streamed_world_suspend` releases world GPU cache for menu memory handoff. Its
host state-switch/suspend/rollback test passed. Indexing preserves all48-byte
attributes/order and cuts BMW geometry memory60.8%, traffic48.8%. Full-frame FPS
has not been validated. Camera source direction/cubic components are compared;
placement/FOV/eye collision remain documented adapters.

## Remaining recovery, do not replace with guesses

- NIS source bundles were extracted to `opening-nis/raw`. IntroNisDDba42885e at
  ZZDATA1offset114737152, GenericStartc91e014b at114182144, IntroNis04234d6fba at
  114216960, IntroNis0572ac793b at114223104, IntroNis1021118357 at114268160,
  EndingNis0330185662 at113534976. Containers include ELF32LE animation banks.
  GLOBAL/INGAMEB_VM_NGC has exact scene paths0x80037050 and camera banks
  0x8003B200..203; camera0x3B210 records keyed original case-sensitive name hash.
  GenericStart camera has two tracks and duration6seconds. Decoder still needed;
  do not call a generic orbit original NIS.
- Opening opponent source identities are saved in `opening-opponents/source-actors.json`:
  RAZORMUSTANG→MUSTANGGT, DDAYSUPRA→SUPRA, BL2→SLR; circuit presets map to GTO,
  IMPREZAWRX,RX8 (OPM_MUSTANG_BOSS actuallyGTO). Actual NPC conversion/AI unfinished.
- Dynamics four-wheel orchestration exposes required mechanical/input hooks;
  do not supply no-ops and claim original handling. 802455E0 mechanical stage
  emits drag then downforce at most two forces. Original common state fields:
  world velocity+50,speed+BC,contact fraction+6C,local CG+70,throttle+4C;
  caller f3/f4 are physical front/rear mount Z. DRAG_COEFFICIENT chassis+70;
  aero80223ADC=2*speed*AERO_COEFFICIENT(+68)*1000; AERO_CG(+5C) interpolates axles.
  Optional effect/global fields and full native comparisons still needed.
- Normal player assist802484F8, body/inertia integration, timestep scheduling and
  full-camera providers remain unported. Existing helper matches are not1:1 car.
- Breakable exact static bindings/Width shape/proxy query are tested. Damage
  scalar units, fragment sequencing and debris motion remain unproved; no broad
  deletion or guessed source damage threshold.

## Backup workflow

Root repo branch work. Linked public backup worktree
`/workspace/nfsmw-github-checkpoint-20261103`, branch
`codex/v018-checkpoint-20261103`. Preserve its public main README (original8254124),
map root README.md to docs/DEVELOPMENT.md on export. Never push raw archives,
converted assets, binaries or caches. Original public preview backup was e50e666;
last complete playable exploration ZIP remains under dist. No new goal ZIP yet.
