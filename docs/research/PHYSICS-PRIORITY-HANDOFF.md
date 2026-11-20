# Active priority: original complete driving physics

The user explicitly says finish original driving physics before sound and other
features. Audio/roster work is paused and preserved. Do not imply that recovered
engine code, the native audio adapter, car imports, or isolated numerical parity
mean the currently playable planar driving controller is original handling.

## Current source-backed core

mw_vehicle_runtime composes original rigidbody, engine/automatic/induction,
mechanical aero, steering/assists, four-wheel forces and chassis accumulation.
mw_driving_backend owns source parameters/BND actor and fixed60Hz transactions.
They intentionally require actual world/producer callbacks and initialization.
The app still calls streamed_drive_step/drive_step until these complete.

NVRv2 source profiles63, including every represented player model, are private in
/workspace/port-research/roster-physics/native-v1. All63 reader/engine continuation
checks pass; this is not whole-car original trajectory parity. Matching original
DEBUG ELF /workspace/port-research/opening-story-services/original-debug.elf has
verified byteidentical initialized sections to Speed.dol; tools/mw_debug_info.py
reads source DWARF1/symbols. No original C++ source is available or claimed.

## Active ownership

- Root: integration, current runtime dispatch fixes, real-world harness, SDK/app
  activation only after actual callbacks are ready; source backups.
- physics_world_pipeline: original OnBeginFrame/integration/reset/gravity/
  OnEndFrame; source collider caches, walls/OBBs/contact response/events/materials.
- engine_audio_driver(retasked): ORIGINAL wheel query WWorldPos/Wheel::UpdatePosition,
  source cached triangle queries and actual SimSurface/material coefficients.
  The native visual audio tyre proxy is NOT used for this physics callback.
- physics_producers: original owner/settings/common-state/engine/input/assist/
  transmission distribution fields; InputPlayer reverse/brake/steering policies.
- physics_initialization: true constructor/PlaceObject/PlaceOnGround spawn/body
  flags/status/forces/quaternion/CG and physical collision padding/source settings.

## Source ordering and concrete corrections

OnBeginFrame80234A44 setsflag0x400. State2 skips BOTH PrimitivePrepare and
DoIntegration. State1 prepares then integrator clearsvelocity. Force and torque
clear afterintegration; state0 seeds gravity for nextinterval unlessflag2.
OnEndFrame8023487C updatescollider, clearsflag4, resolvesworldcontacts, drag/sleep,
andclears0x400. Current root fixes runtime's unconditionalintegrate forstate2;
worldagent guards backend's preparation too. Do not place force reset before
integration or erase previous-frame forces needed by the source scheduler.

Source normal fixedtick0.01666666753590107. Source Physics task follows SimStart,
so engine/suspension forces affect NEXT body integration. Driver input and source
world/controller time must pause with admission/simulation. Do not drop debt or
substitute direct position/yaw edits and call it source physics.

## Validation required before fidelity claims

Use original functions/reference calls plus actual NVR/BND/NWC surfaces, compare
complete sequential body/wheel/engine state under fixed inputs and normal source
settings. Cover acceleration, gear changes, reverse/braking, steering transitions,
handbrake/slip/traction, sloped/uneven surfaces, airborne/landing, impacts and
sleep/wake; preserve contact/material order. Component tests alone do not prove
whole-car1:1 driving. Then SDK/emulator smoke checks and performance profiling.
Source gaps remain explicit; no empty callback or guessed constant is a fix.

Audio and roster handoffs retain completed work under game-audio and all-native-
cars/v7:80converted+rootBMW81roadpackages/all38PlayerUsable, original53music
segments/5verifiedUIcues/Ginsu sourcegraincore. Do not continue audio features
until the driving priority is handled or the user changes it.
