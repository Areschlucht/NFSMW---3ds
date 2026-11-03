# Fidelity and integration checkpoints

The target is faithful Most Wanted (USA, GameCube) behaviour on 3DS hardware.
The current v0.17 build is an asset-based prototype with provisional driving,
partial scenery and road-render-mesh support. Full original physics, collision,
materials, streaming and game systems are unfinished.

## Evidence required for a recovered system

Keep original input hashes, directory/file offsets, executable addresses and
section mappings with each recovery. Field names locate candidates; original
consumers establish units, frames and state transitions. Preserve unresolved
flags and distinguish an observed data layout from a working runtime system.

Compare portable mathematical components against bounded original executable
references. Record exact input/output cases, rounding behaviour and any omitted
ABI instructions. An exact component comparison does not establish full vehicle
or game fidelity. For motion, retain initial conditions, surface, controls and
timestamps; define tolerances from reference precision before judging results.

Renderer changes must preserve source attributes and ordered triangles or
document an explicit quality difference. Buffer-size and cache-model results
are separate from measured hardware FPS. Compare stock and boosted hardware
under the same scene, camera and input conditions, retaining CPU/GPU timings.

## Specialist workstreams

| System | Recovered evidence | Runtime gap |
| --- | --- | --- |
| Driving | Original attribute database, engine torque interpolation, physical tire dimensions and original-code reference checks | Gearbox, wheel forces, suspension, braking/handbrake and assists still need complete consumer recovery and integration |
| Map/collision | Complete stream; original ground/wall queries and contact normals verified against executable | Runtime activation/material resolution and body response remain incomplete |
| World streaming | Original activation polygons, dependency lists and contained-region selector verified | Nearest-region fallback, readiness and load/unload scheduling remain unported |
| UI | Portable dual-screen dashboard, touch menus and drive-preserving help/stats panels | v0.17 integrated and emulator-tested; original frontend remains absent |
| Materials | Original light-alias hashing/selectors and visual-unit consumers | Canonical paint composition and state producers remain incomplete |
| Hardware | Exact world vertex packing/indexing, SDK inspection and independent failure-path review | Indexed hardware speed/cache behaviour and further compact GPU formats require measured validation |

These workstreams own separate research modules. The coordinator reviews shared
runtime changes and their tests before integration. Reviewed build artifacts
remain separate from experimental candidates. v0.17 integrates the reviewed 36-byte indexed-world path, retaining expanded
vertices on encoding/allocation failure. `NFS_DISABLE_WORLD_INDEX` builds the
expanded reference path. The isolated 20/24/32-byte experiments remain excluded.
The portable dual-screen UI is integrated; HELP/STATS preserve driving state.

## Received original inputs

The complete `STREAML2RA.BUN` is 109,279,744 bytes, SHA-256
`58fdd0adb8bdf1ebc3545ee679076c768acb3c52308c4b916ca960b4a0ac5552`.
It validates against all four earlier high/low samples at their original offsets.
The `L2RA.BUN` index contains 997 sections. Possessing the full stream does not
mean those sections are all converted, streamed or collidable in the app.

The original `ATTRIBUTES.BIN` is 694,976 bytes, SHA-256
`5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c`.
Recovered visual attachment values and physical tire/chassis values have distinct
consumers; coordinate frames must be proven before replacing the provisional rig.

## Further systems

Track remaining work explicitly: input, engine/transmission, wheel/tire forces,
suspension, chassis response, surface interaction, collision activation,
streaming/LOD, camera, paint/materials/lighting, audio, traffic/police, races and
progression. Foundations recovered by one specialist should be shared with the
others, especially collision material keys and vehicle surface parameters.
Only systems with sufficient source evidence and comparison coverage should be
described as recovered or faithful. Full-game 1:1 behaviour remains a long-term
acceptance target.
