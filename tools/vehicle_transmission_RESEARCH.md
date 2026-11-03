# Original EngineRacer drivetrain checkpoint

The new portable module is `include/mw_physics_transmission.h` and
`source_bmw/mw_physics_transmission.c`. It is isolated from the live prototype.
The initial foundation described below has since expanded into six modules and
a bounded coherent EngineStep; see the current continuation sections below.
A complete 1:1 vehicle simulation is not yet established.

Source identities:

- Speed.dol SHA256 `33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`.
- ATTRIBUTES.BIN SHA256 `5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c`.

Every executable address is mapped through actual DOL sections. Large positive
small-data displacements must not be read from the preceding data segment.

## Implemented and compared

| Stage | Original range | Cases | What is established |
| --- | --- | ---: | --- |
| Output torque | 8025546C..802554F4, calls802240AC | 5616 | Raw torque curve ×1.3558 ×(1+state9C), then state100 unless Vehicle callback returns6 |
| Engine braking | 802557E8..80255A0C | 1872 | ENGINE_BRAKING interpolation and negative torque multiplication |
| Reported RPM | 80256B8C..80256C38 | 480 | Original bounded falling rate and45/55 smoothing, distinct from actual/requested RPM |
| Gear commit | 8025607C..8025617C | 11250 | Accepted gear changes, shift delay and clutch-state mutation |
| Engine inertia | 80223AFC..80223B3C | 312 | FLYWHEEL_MASS consumer and neutral/in-gear multiplier |
| Clutch numerical core | 80257CC8..80257EF8 | 1592 | Locked/slipping/disengaged wheel torque, engine reaction, slip memory and torque sign |

Total **21122** exact float-bit/integer-state comparisons. Torque/braking/inertia
cases use78 original engine collections. Gear commit cases use every nonempty
original transmission collection and valid current slots, including invalid
requested slots and all three supported clutch states.

The independent original reference is `tools/vehicle_transmission_verify.py`.
It preserves nested scalar PSQ ABI values through checked original instructions.
The torque wrapper's external Vehicle callback response is explicitly supplied;
that callback's producer is not claimed to be emulated. Other instructions in
these functions execute unchanged. The clutch test supplies documented live-in
registers and the preceding gear==neutral CR0 result, checks the original cmpwi
word at80257CBC, and stops before the surrounding engine update. It compares
all permitted state writes and rejects mutations outside108/10C for that slice.
No original executable code is run natively or linked into the 3DS module.

## Input/state contract

The original raw engine torque convention is supported by the separate torque×RPM
horsepower accessor using1/5252. The output wrapper applies the original
1.3558000326156616 factor, consistent with pound-foot to newton-metre conversion.
State9C boost and state100 scale remain explicit; Vehicle mode6 is the exact
observed bypass branch, with no guessed label such as traction-control setting.

ENGINE_BRAKING samples are uniformly interpolated across IDLE..MAX_RPM after
clamping RPM toIDLE..RED_LINE, retaining the original fused interpolation. More
than one sample is clamped to[0,1]; exactly one sample is used without that clamp.
Empty curves are rejected rather than calling original default-memory helpers.
The returned torque has the same input units as its torque argument.

Original engine inertia is:

```
inertia = fmaf(FLYWHEEL_MASS, 0.02500000037252903, 0.25)
inertia *= (gear_slot == 1 ? 0.3499999940395355 : 1)
```

For BMWM3GTRE46 FLYWHEEL_MASS10 this is0.5 in gear and0.175 in neutral. Engine
update80257818 supplies selectorgear!=neutral;80258258 divides net engine torque
by this inertia before angular integration. Do not substitute wheel inertia10
from the suspension calibration globals.

Reported-RPM stage is an output filter, not an engine RPM constraint. It limits
falling target RPM at−(2.5 or15)×1000/inertia, with15 selected when neutral or
when its caller predicate is true in a forward slot above2. It then returns
`fmaf(target,0.55,previous*0.45)`. This stage still smooths when dt==0, exactly as
its original branch does. The caller predicate's broader producer remains open.

Gear slots are0 reverse,1 neutral,2 first forward. An accepted shift writes
SHIFT_SPEED×requested_ratio; a downshift additionally multiplies by0.25. Clutch
state0 becomes2. The larger event/request wrapper8025617C and automatic
choice logic are separate from this commit function.

The clutch core takes angular engine/shaft speed, shaft acceleration, actual
engine inertia, net engine torque, signed driveline ratio, TORQUE_SPLIT, contact
fraction, shift-coupling factor and previous slip RPM. Its calibration arguments
are original initialized maxomega difference300 at8041F684 and coupling20 at
8041F658. They are writable original globals, so the API keeps them explicit.
Locked/slipping/disengaged describe only this numerical core's observed states.
The slipping state halves its coupling after a slip-sign reversal only when
both old and new slip magnitudes exceed2000RPM, not a tiny generic epsilon.
Neutral skips clutch-force calculations and retains prior slip memory.

The locked branch's shaft-acceleration correction adds only its NEGATIVE part
to wheel torque, while the full correction affects engine reaction. Both original
operation order and this asymmetric branch are retained. The core does not
perform subsequent wheel synchronization, final differential distribution,
gear-efficiency multiplication, power limiter, angular integration or state
transitions from the rest of8025762C..802584A8.

## Vehicle interface identity recovered for producer research

BehaviourBase8021CA50 queries token80042A2C into behaviour+4C. Vehicle constructor
80211D10 registers that token at80211D88 with interfaceVehicle+0xB4 and installs
vtable803F8728 at80211E44. The vtable's signed adjustment is−0xB4.

- Slot68 →8022E0E4 →Vehicle+14C. This is the mutable value copied to common
  contact stateC8. It initializes to0 at80211F14, changes through80210374, and
  is set to1 by8021551C when Vehicle+160 is null. Its enum label and actual
  player/BMW runtime selection remain unproven; do not choose a default by name.
- SlotB8 →8022E0DC →Vehicle+148. This is the torque wrapper's mode callback;
  constructor80211F10 supplies its original r4 parameter. Its enum labels remain
  unproven. Mode6's torque-scale bypass is independently established.

## Reproduce

```
PYTHONPATH=/workspace/toolchains/python-deps:tools python3 tools/vehicle_transmission_verify.py \
  --dol /local/Speed.dol --attributes /local/ATTRIBUTES.BIN
python3 -m unittest discover -s tests -p test_mw_transmission.py -v
```

The actual source report is
`/workspace/port-research/drivetrain/original-transmission-verification.json`.
Strict host C and ASan/UBSan checks cover standalone state/curve boundaries.
Strict pinned devkitARM ARMv6K hard-float compilation passes; no physical3DS
performance or whole-game behavioral equivalence is claimed.

The later continuation sections supersede this initial integration-gate list.
Root owns live controller integration and shared build/package files.

## Recovered continuation, 2026-11-03

The earlier checkpoint/table above is retained as historical detail. It is
superseded by the following complete current inventory. The portable sources
remain isolated from the live controller; no full engine pipeline or 1:1 handling
claim follows from numerical equivalence of these stages.

| Additional stage | Original range | Exact cases |
| --- | --- | ---: |
| Clutch countdown and engagement policy | 802578A8..80257988, 80257AF0..80257BA8 | 2916 |
| Differential ratios | 80249EA4..8024A00C | 23040 |
| Effective wheel speed | 802479A0..80247A0C | 4096 |
| Driven axle speed selection | 8025625C..80256484 | 1024 |
| Induction leaf | 80223DA8 | 2025 |
| Startup shift tables | 80224CB8 | 45 complete executions |
| Shift request classification | 80255DE0 | 9639 |
| Complete wheel torque/grip distribution | 8024A00C..8024A568 | 11520 |
| Actual shaft angular update | 8025817C..80258298 | 3904 |
| Startup peak-torque sample/RPM | 802247EC | 284 |
| Original EngineRacer speed-limit selector | 802577A8..80257808 | 80 |
| Powered-wheel synchronization | 802565C0..802568A0 | 4096 |
| Airborne powered-wheel speed cap | 80256A08..80256B8C | 4096 |

The initial core report now contains 52198 cases; the policy report contains
11709 cases. Full distribution executes across80 transmission collections,
including221 original quantized-angle calls. These reports are independent of
host synthetic boundary tests and all enforce bounded original execution and
allowed state writes. New reproducible verification tools are
`vehicle_transmission_shaft_verify.py`, `vehicle_transmission_peak_verify.py`,
`vehicle_transmission_sync_verify.py`, `vehicle_transmission_profile.py`, alongside
the earlier policy/distribution tools. Exact source hashes and current report
identities are in `/workspace/port-research/drivetrain/validation.json`.

### Canonical visual preset selects a different physical profile

Original decoded GLOBAL-GLOBALB_VM_NGC.BUN SHA256
`da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b`
contains M3GTRCAREERSTART at fileoffset385560. Its serialized64-bit field+50 is
`0000000039DAE0F8`, the VLT collection key for `pvehicle/m3gtre46careerstart`.
The independent field+48 is frontend key23CC4A4E; its visual model is BMWM3GTRE46.

This interpretation is established by executing original loader802DB494, then
both original consumers801651E0..801651EC and actual spawn prefix801A2004..801A205C.
The loader swaps the64-bit field; the consumers load runtime+54 and call
800F2EF0 (literal pvehicle class4A97EC8F), then prepare collection lookup80057FC8
with39DAE0F8. This is an executed source binding, not a name resemblance.

The resulting original pvehicle engine/transmission/chassis/tires/brakes RefSpecs
all select careerstart; induction selects default. Upgrade-index consumers remain
separate. Do not replace this physical profile with bmwm3gtre46 merely because
both refer to BMWM3GTRE46 geometry: original careerstart peak raw torque239 differs
from bmwm3gtre46 peak467. Both peak torque RPMs are5150. The default-induction
startup scan selects maximum sample torque, **not peak horsepower**. Ties retain
the first sample, negative-only curves retain zero and idle RPM, and the final
selected RPM is clamped toIDLE..RED_LINE.

### Actual shaft and wheel speed stages

Shaft step exposes the earlier engine RPM sample, net engine torque, clutch
reaction torque, inertia, timestep, gear/clutch state, throttle, CLUTCH_SLIP,
IDLE/selected peak-torque RPM, and minimum/maximum angular speed. It includes the
original first/reverse locked-clutch attenuation when net and reaction torque
oppose, then acceleration=(net+reaction)/inertia and fused integration with
native angular speed limits. It returns acceleration even when speed is clamped.
The upper-limit source is now proven: EngineRacer installs vtable803FDFC8;
slot70→80269F0C returns1. Original802577C0 therefore selects RED_LINE, not MAX_RPM.
For both BMW physical profiles the initialized limits are83.77581024169922 and
890.1179809570312 rad/s (800 and8500RPM). Other subclass selectors must be proven
separately rather than assumed to share this implementation.

Effective wheel speed returns zero when locked; loaded wheels with traction>=1
use previous contact forward velocity/radius, otherwise raw spin. Driven axle
selection uses powered axle averages: absolute largest signed value normally;
with direction filtering, max forward or min reverse constrained relative zero.
These are separate from requested RPM and smoothed reported RPM.

Powered-wheel synchronization first takes target minus selected driven omega.
On each powered axle, speeds average before adding that delta if original Vehicle
speed+128 times2.23699 is below40, or both wheels are airborne; otherwise axle
speed differences remain. Tests execute actual Racer vtable803FE938 and signed
this adjustments. The Vehicle callback is original803F8728.slot138→8022E1D0;
it returns Vehicle+128. The wider producer of that scalar remains a gate.
Airborne cap processes only powered airborne wheels: opposing angular direction
becomes zero; matching direction is capped to the signed limit. Grounded wheels
are retained.

### Ordering and remaining whole-engine gates

Original RacerUpdate80247A2C prepares all wheels at47CA8, calls mechanical
802455E0 at47D08, distributes at47D14, then calls8024A568 at47D20. That latter
stage updates steering, current brake/input routing, queries springs and contact.
Thus distribution reads **previous** compression, lock and slip state. Reordering
it after current contact changes the simulation. Current contact agent owns
these producers; this module must receive their explicit previous-state values.

Clutch countdown expires1→0 and computes coupling before this frame's new
engagement transition. New2→1 engagement uses.05s in first/reverse,.25s in other
forward gears, with the new frame retaining prior disengaged coupling.25.
Neutral disengages locked state. Countdown and accepted-shift delay are different
state values and must not be merged. Original auto wrapper additionally requires
all four wheels compressed and each longitudinal slip<4m/s (signed comparison,
not abs) before upshift; the classifier itself does not enforce that gate.

Still open before a complete source-faithful high-level engine update: torque
boost/state-scale timed producers; event/manual/automatic caller wrappers;
80257EF8..802580F8 launch-reaction stabilization and original8048A0EC curve;
engine/suspension top-level callback order and actual timer cadence; optional
rev modulation+1AC and optional tuned induction; exact pvehicle upgrade-index
selection. Existing shaft/sync primitives do not silently supply defaults for
these. All engine steps must receive actual dt; a guessed60Hz tick is not proven
by a60FPS render counter. Root owns runtime integration and packaging.

## Coherent EngineStep continuation, 2026-11-03

`include/mw_physics_transmission_engine.h` now supplies persistent parameters,
state and input/output contracts, rather than requiring root to assemble the
numerical leaves. `mw_physics_transmission_engine_step` follows original order:

1. Raw input throttle or zero when original rev-block boolean+1A8 is active.
2. Timed NOS state and original torque multiplier+100.
3. Disabled-induction class resets amount+94, display+98 and boost+9C.
4. Automatic policy/accepted gear commit and post-input timers.
5. Converter/shaft target, clutch countdown/engagement, torque and engine braking,
   clutch numerical core, launch stabilization, actual shaft update, wheel
   sync/cap, final torque/efficiency, reported RPM and next shift classification.

The independent `vehicle_transmission_step_verify.py` executes **the whole
original EngineRacer8025762C..802584A8**, including its actual nested call graph,
and compares all owned persistent state and wheel spin writes with this API.
**1536 complete cases pass, including512 persistent continuation steps**, across
both BMW physical collections. This is broader than comparing a sequence of
separately recovered leaves. External raw input/automatic-enabled, optional
entity recharge gate, tuningNULL, event-dispatch gate and boost scalar are
explicit; they are not claimed to be the wider game/scheduler implementation.

The API supports the canonical careerstart/default-induction/empty-SPEED_LIMITER
subset. Positive induction boost, nonempty RPM limiter and active rev-modulation
deadline reject transactionally. The source raw rev-block boolean is supported;
the timed sine modulation/event branch is not. Unsupported input does not quietly
fall through to approximated behavior. Source physical upgrade selection and
actual spawn/reset initialization must still be closed before deploying it as a
complete original controller.

### Mechanical continuation

`mw_physics_transmission_engine_mechanical_step` is also usable separately when
the caller already supplies the original preceding timed/input stage outputs.
It matches **2560 complete original802577A8..8025845C state cases**, including512
persistent continuation steps. This includes the full launch-reaction branch.
The curve object's correct address is **8048A0EC**; an earlier research checkpoint
mistyped it as8049A0EC. Executing startup80265EB0..80265EE4 establishes its pointer
to five original pairs at8041F65C:

```
(-10,1), (-7.5,0.96), (-3.5,0.925), (-0.3,0.875), (-0.05,0)
```

The original samples retain their exact binary32 source values in code. The
argument is `(net torque + reaction)*1000`, not a guessed normalization. The
launch branch adds curve*total*CLUTCH_SLIP to reaction. At the upper shaft limit,
original positive drive torque is cleared while negative reaction/braking torque
is retained; this distinction is covered by whole-phase comparisons.

### Timed NOS and automatic policy

`mw_physics_transmission_nos.h/.c` ports complete80256D9C..802571FC:
**2304 original full-state cases across all6 NOS collections pass**, including768
persistent continuation steps. It covers original activation hysteresis (start
at10mph, continue at5mph), charge drain by dt/NOS_CAPACITY, mode6/unlimited drain
bypass, disengage timer, speed-interpolated recharge time, optional boost effects
and optional source tuning. Schema FLOW_RATE is not substituted for the actual
NOS_CAPACITY denominator. Raw request, recharge inhibit, tuning/global values
and physical NOS upgrade choice remain explicit.

`mw_physics_transmission_auto.h/.c` ports80255AD4, accepted commit state from
8025617C, and post-input timers8025750C: **4096 complete original cases pass**,
including17 accepted shifts. It retains neutral1→first2 direct assignment,
source multi-downshift RPM prediction against the original current gear, signed
four-wheel slip<4 upshift gate, shift-delay inhibit and cooldown state. Cooldown
is `max(0,cooldown-dt*(2-raw input throttle))`, not dt*(1-throttle). Automatic
commits reset the pending request and set original committed state+188.

Optional original event allocation/dispatch is disabled in the reference; the
portable API returns accepted/previous/new/automatic event data for the caller.
Neutral's direct assignment produces no accepted-shift event. This does not send
messages or publish anything. Manual request wrapper/event-side integration
remains separate.

All six drivetrain C modules pass strict host tests, ASan/UBSan and pinned
ARMv6K hard-float compilation. `validation.json` records source/report/object
hashes and current totals. The live controller/build/package remain untouched.
