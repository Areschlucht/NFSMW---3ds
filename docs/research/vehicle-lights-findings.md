# BMW lamp bindings and vehicle-wide integration seam

2026-11-03. Read-only recovery; no runtime, shader, scene or packaged build was
changed. This adds a concrete binding export to the earlier original selector
research, rather than claiming a finished lighting implementation.

## Newly checked against the actual playable scene and hero preset

`tools/vehicle_lights_recovery.py` pins the USA DOL and decoded original
GLOBALB_VM_NGC preset source, checks the current NFM schema/CRC, and verifies
source texture dimensions and decoded RGBA SHA-256 values against their manifests.
It selects the actual `M3GTRCAREERSTART` record, not a guessed BMW configuration.
Its original part slots 64/65 are named HEADLIGHT/BRAKELIGHT in the DOL enum
and both selected keys are zero. Therefore the original default
`BMWM3GTRE46_KIT00_HEADLIGHT` and `BMWM3GTRE46_KIT00_BRAKELIGHT` prefix paths
are justified for this preset. Another preset or replacement kit can select
nonzero parts with TEXTURE_NAME overrides; do not generalize these BMW hashes.

All six gray lamp references belong to existing NFM batches 10–15, covering
1,434 vertices / 478 triangles. There is no need to invent missing lamp meshes.
The targets below are produced by original selector 802CAA44, with the current
WINDOW_FRONT target explicitly supplied by the caller:

| Alias | Alias key | Intact target |
| --- | --- | --- |
| HEADLIGHT_LEFT | a7e6ea53 | e626da6d, original headlamp ON |
| HEADLIGHT_RIGHT | a532fc46 | e626da6d, original headlamp ON |
| HEADLIGHT_GLASS_LEFT | 267d188c | current resolved WINDOW_FRONT |
| HEADLIGHT_GLASS_RIGHT | f68ef19f | current resolved WINDOW_FRONT |
| BRAKELIGHT_LEFT | d947f346 | 051ae6de OFF / 938c73a0 ON |
| BRAKELIGHT_RIGHT | 02b52399 | 051ae6de OFF / 938c73a0 ON |

All three head/brake source pixel payloads are present in the supplied BMW
textures. Unmodified global WINDOW_FRONT 7b220ddf is also available, but is only
an explicit test context here, not proof of the live window/tint state. The
original glass override at 802CABE8–802CAC48 is why the available headlamp
GLASS_ON ea977c66 must not simply replace both glass aliases.

Three concrete states were compared with bounded execution of the original
PowerPC selector: enable/suppress words (0,0), (24,0), (24,24), all with side-light
override zero and explicit WINDOW_FRONT 7b220ddf. Every target key matched.
Existing selector research additionally covers all 128 enable/suppress/force
combinations. These comparisons verify consumers; they do not prove that a port
produces the original brake, damage or force-side state.

## State producer seam narrowed further

The earlier known transfer 802D60C0–802D60CC copies update-input words +60/+64
to CarRenderInfo+1608/+160C. Following its direct caller identifies:

- 802D6964 builds an update-input structure at stack+8. It initializes +60/+64
  to zero at 802D6A7C/80.
- 802D6AA8 passes that structure through 8027EBD0 before the transfer routine.
- 8027EBD0 is a virtual-provider thunk: it loads the object's +4 pointer,
  then an adjustment and function target from its provider table +10/+14,
  adjusts the receiver and invokes that target.
- On success, 802D6ACC calls 802D6074 with the same update-input structure.

Thus the port should consume the provider's original fields rather than infer
all states from the render object. The actual concrete provider implementation,
original damage mask generation and state transitions are still unresolved.
The export records SHA-256 checksums of these exact original code ranges.
Do not label an arbitrary +60 store elsewhere as a brake producer without proving
its object type and call path. Reverse and police light states/effects are not
established by this intact BMW selector.

## Material fidelity matters after binding

The existing source material-run snapshot shows the six NFM batches currently
merge several original materials. Headlamp mesh strips use HEADLIGHTREFLECTOR
b51b3acf, CHROME 54949afd and MOLDINGS 12c9453c; brake meshes use BRAKELIGHT
05bc3a3c and MOLDINGS; headlamp glass uses HEADLIGHTGLASS a6348ee3. A single
opaque or uniformly emissive lamp shader would paint metal and trim incorrectly.

Restore original material/alpha semantics using the preserved source strip runs
and original material-cache evidence. Do not infer the whole blend mode merely
from PNG alpha or add shadowed spotlights without original consumer evidence.
The binding fix can retain the existing six alias slots and swap resolved texture
handles when vehicle state changes. That does not inherently require extra
geometry or additional batch subdivision; recovering distinct original materials
is a separate batching/performance decision.

## Reproduce

From the project root, using original/private inputs:

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/vehicle_lights_recovery.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --presets /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
  --scene /workspace/port-research/bmw/scene-v0.18-source-normals \
  --texture-dir /workspace/port-research/bmw/textures \
  --texture-dir /workspace/port-research/shared-textures/globalb \
  --window-front-target 7b220ddf --verify-original \
  --output /workspace/port-research/vehicle-lights-recovery/bmw-bindings.json
```

Result: six alias batches, three state maps, all three original comparisons
matched. Eight existing `test_material_recovery_vehicle.py` tests pass. Raw
textures and game data remain private; the report is hashes, bindings and source
provenance. This tool intentionally refuses a hero preset with nonzero lamp
part keys until its actual TEXTURE_NAME attributes are resolved.
