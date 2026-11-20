# Source engine RPM provider for audio

`mw_engine_audio_driver.[ch]` composes the existing recovered EngineRacer engine,
NOS, induction, clutch and automatic-transmission state machine into a bounded
60Hz scalar provider. It reads no files or audio, performs no sound synthesis,
and changes no chassis state. The engine implementation already has its separate
original-executable comparison; this wrapper does not extend that claim to a
whole vehicle or a GIN granular synthesizer.

The driver borrows one self-bound `MwVehicleRuntimeParams` loaded from the actual
NVRv2 for the selected physical car. Keep that parameter object at a stable
address. Initialization repeats the original scalar constructor/reset values
already used by `mw_driving_backend`: gear slot2, idle omega using original
float0.10471976548433304, reported idle RPM, closed clutch, zero timers, multiplier1
and source NOS charge eligibility. Initialization alone does not publish an audio
sample. Nonempty original RPM limiter arrays remain explicitly unsupported.

Each successful tick invokes the complete source engine API, including original
induction spool timing and automatic shift policy. `sample.rpm` comes directly
from EngineRacer's reported-RPM state, not a guessed linear conversion of car
speed. `applied_throttle` and `gear_slot` are engine outputs. Applied throttle is
not claimed to be the original audio mixer's complete load/acceleration signal.
The optional source sabotage deadline is processed at the correct engine stage.
A committed tick can report gear events, modified wheel angular speeds and an
actual engine-blown transition to its caller.

The producer callback is deliberately mandatory and called separately for every
catch-up tick. It supplies the actual source-equivalent wheel/contact/owner,
settings and NOS/tuning providers. A producer mask makes absent groups fail
explicitly. In particular, visual WheelMotion alone does not supply:

- Original axle-first wheel order, spring compression, traction factor, prior
  longitudinal contact velocity, radius, lock state and longitudinal slip.
- Previous contact count consumed before the source suspension task.
- Vehicle mode, gate, scalar/speed and optional boost-interface outputs.
- Input-present, automatic-enabled and rev-gate results.
- NOS recharge inhibition, unlimited/tuning state and induction tuning.

The wrapper never fills those with convenient zeros or assumes four contacts.
A source pointer being genuinely absent may produce zero values, but the caller
must establish that absence. Current bicycle motion, handbrake flags and wheel
animation are not evidence that those original interfaces have been reproduced.
A separately documented native wheel/owner producer can be supplied for an
experimental audio preview; it must not be described as full original handling.
The main app should not set an audio `rpm_valid` flag just because it knows speed.

Calls admit at most100ms and at most6 source ticks. Extra elapsed debt is retained
rather than silently skipped; debt above1second rejects before admission. Pause
by not calling, not by submitting more time with zero input. A failed producer or
engine tick retains numerical state/clock and invalidates audio-sample readiness.
Already successful earlier ticks stay committed. `commit` is called only after
success; producer callbacks must not mutate external state speculatively.

The strict C11 ASan/UBSan contract test runs all six current physical NVR profiles.
It compares1200 continuation ticks per profile against direct invocations of the
already source-compared engine core (7200 primary comparisons total), including
all engine state bytes, wheel speeds, gear events and clock. Additional tests
cover missing-contact/provider refusal, no constructor-only sample, pause/debt
bounds, rejecting-tick rollback, recovery, source sabotage and reset. Test wheel
values are controlled numeric fixtures, not fabricated application providers or
claims about actual driving trajectories. Run:

```
python3 tests/test_engine_audio_driver.py /workspace/port-research/driving-runtime-v2
```

This module is ready for source-backed producer integration. It is not wired into
the main application until those producers and the actual audio-bank consumer are
admitted. No original executable, audio sample or debug data is included here.
