# Native driving integration bridge

`mw_driving_backend.[ch]` provides a stable-address asset/runtime/actor owner,
bounded source60Hz scheduling and an explicit per-tick transaction boundary.
It is not enabled as the app's live driving backend while original world/body
callback phases and dynamic gameplay producers remain unclosed.

The loader checks NVR source identity/CRC, exact embedded NDP/MMP correspondence,
actual BND model key and matching physical collision-root extents. NVR/NDP/MMP
scalars are copied; BND is borrowed by `open`. `open_files` instead reads all four
files once and owns BND storage until `close`. An open backend must not be copied:
its curve pointers reference its own parameter arrays. No simulation tick reads
files or allocates memory.

`engine_construct` implements the scalar subset of original EngineRacer
constructor802545F4/Reset802553CC: first gear slot2, idle omega via original
float constant0.10471976548433304, reported idle RPM, zero shaft/output/timers,
closed clutch and multiplier1. Constructor NOS charge is1 only for positive
NOS_CAPACITY. Shift/peak tables were already computed from source-bound NVR.
This scalar initialization follows original instruction inspection; full engine
steps have their separate4608-case comparison. It does not reproduce original
owner/interface registration or select physical upgrades.

`start` requires the actual source initial body pose, velocity, angular velocity,
flags/status and force accumulators, with matching physical inertia/local CG.
It does not infer spawn orientation from the viewer, replace body forces with
zero, or choose ground contacts. Existing runtime initialization supplies the
source wheel scalar constructors, steering histories and assist constructor
state. Actual ground/material queries are still required on subsequent ticks.

Supply `MwDrivingCallbacks` with all three transaction callbacks and all four
required runtime callbacks. `begin` receives a private actor copy, allowing the
application's `after_body_tick` to generate source geometries after integration.
The bridge invokes source primitive preparation after `before_body_tick`, before
integration. The application must implement original remaining OnBeginFrame and
collision/OnEndFrame effects; it must not supply empty callbacks merely to pass
the gate. A failed begin/runtime step invokes `abort`, retains body/actor/clock,
and leaves the admitted elapsed time as unconsumed debt. Only successful ticks
publish body/actor, advance clock and invoke `commit` with real output commands.
Callbacks must stage external collision/event state until this commit.

Every normal-speed source step uses float0.01666666753590107. Maximum work per
advance is8 ticks. Remaining debt is retained; a debt exceeding1second rejects
before admission rather than silently skipping source simulation. Successful
ticks commit individually, so a later failure cannot roll back earlier ticks.
Pausing and source simulation-speed changes are caller scheduling concerns.

The viewer adapter converts successful native Y-up body state by swapping X/Z
and subtracting the actual world origin. It returns the full native pose matrix
as well as planar DriveState. Heading and velocity are derived from the actual
body basis, with reflected lateral/yaw signs. DriveState.drift has no equivalent
authoritative source field and stays0; the adapter never feeds viewer state back
into physics.

Strict C11 `-Wall -Wextra -Werror -pedantic`, ASan and UBSan contract tests verify
source asset loading/pointer binding, mismatched model/profile rejection,
native/viewer conversion, required-callback refusal, bounded scheduler/debt gates,
and body/actor/clock rollback after real integration and a rejecting producer.
The tests deliberately stop before wheel queries; they do not fabricate a world
provider and are not whole-frame trajectory parity evidence.

Remaining activation gates are concrete: original body/world callback ordering,
material/friction and full contact/constraint response with actual collision
events; source cached vehicle interface/tuning/settings providers; source input
policies; and whole-vehicle trajectory comparisons. The original wall-contact and
ModifyCollision components are callable through `mw_vehicle_world`, but their
existence alone does not close these application phases.
