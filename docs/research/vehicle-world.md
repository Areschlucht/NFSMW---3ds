# Physical vehicle geometry and world collision integration

`mw_vehicle_world` is the source physical primitive preparation/geometry stage.
It uses the existing verified compound decoder and shape dispatcher, followed
by original `RigidBody::Primitive::Prepare` 80231F14, `SetCollision` 80231F60 and
`Dynamics::Collision::Geometry` construction 80089398. It also supplies the original box/sphere versus box narrow phase, one-barrier
wall contact construction, and vehicle static-contact modifier. It does not yet
claim the complete wall/ground body-world response pipeline.

The initial verification passes **2,048 unchanged original calls** (1,024 preparation and 1,024 complete geometry cases) with zero float-bit differences. C synthetic tests pass ASan/UBSan.

The actor borrows an original unfixed `.bnd` package and actual source
COLLISION_BOX_PAD. `actor_open` selects the original detailed child path and
retains source flags, quaternion, center, physical dimensions, radius, material
and tokens. Unsupported root-only dispatch fails explicitly. BMW static-world
primitives are the original two boxes and six spheres; the separate convex
mesh is not replaced by renderer bounds.

Call `mw_vehicle_world_prepare` **before** integration in SimStart. It stores
each primitive's previous world center. After integration,
`mw_vehicle_world_geometry` composes the body and primitive quaternion, produces
world center/axes/extent vectors and the original swept delta. Spheres use the
original identity directions and maximum source dimension. Shapes remain in
native Y-up world coordinates. The original geometry layout is 176 bytes and
its exact member offsets are confirmed by matching debug DWARF.

`tools/build_vehicle_world.py` exports physical compounds for both BMW profiles,
Cobalt SS, GTI, IS300 and Punto from SHA-pinned source GLOBALB_VM_NGC.BUN and
ATTRIBUTES.BIN. Its private manifest records source model hash, package offset,
SHA, rigidbodyspecs binding, padding, source friction and moment scales. Source
assets remain outside Git. The tool also compares complete native geometry and
previous-center output with unchanged original PPC calls, using the existing
bounded Gekko model and independent pinned Dolphin estimate reference.

Example verification:

```
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/build_vehicle_world.py --dol /path/Speed.dol --dolphin-reference /path/pinned-dolphin-reference --output /tmp/vehicle-world --cases 1024
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fsanitize=address,undefined -Iinclude tests/test_vehicle_world.c source_bmw/mw_vehicle_world.c source_bmw/mw_vehicle_world_intersection.c source_bmw/mw_body_collision_shapes.c source_bmw/mw_gekko_math.c -lm -o /tmp/test-vehicle-world
/tmp/test-vehicle-world
```

## Original wall contact and vehicle modifier

The fixed native narrow phase implements original BoxVsBox80089658 and
SphereVsBox80089D50, including swept face/edge clipping and output-alias normal
orientation. `generate_vehicle_world_intersection.py` reproducibly lowers the
SHA-pinned functions into fixed native C control flow; no original executable,
instruction decoder or asset code is used at runtime. The separate vector leaves
preserve original fused operations and the Gekko square-root estimate/Newton
helper. A resumed **1,024-case comparison has zero float-bit/hit differences**:
320 box/box,704 sphere/box,251 hits,773 misses,256 actual physical source
primitives and61 tangent/swept edge cases. The earlier18 differences were already
resolved in the surviving implementation; they were not current failures.

`mw_vehicle_world_wall_contact` reproduces one iteration of
`WCollisionMgr::Collide`802F338C. It accepts an actual transformed native-world
barrier from NWC. The source cached record is40bytes, not a raw32-byte CARP wall.
It builds the original zero-thickness oriented box, preserves signed-zero cross
products, dispatches the compound intersection with input/output identity,
applies source exclusion flags and one-sided orientation rejection, and returns
the original callback normal, negative overlap/penetration and contact point.
The point receives normal×penetration only when mPenetratesOther is set. An
orientation-rejected contact still retains the original geometry's intersection
writes. Callback acceptance/geometry translation remains the caller's operation.

**1,024 unmodified original wall calls compare exactly**, including192 admitted
contacts, source flag0x10 orientation bypass, force-orientation testing, exclusion
mask, box/sphere primitives, rotations and swept motion. The final suite includes
source-sized world coordinates, rotated/reversed barriers, nonunit transformed
normals and reversed top/bottom order; the initial local suite also passed1,024
calls including218 contacts. Comparison covers all
176 bytes of resulting geometry and the10 contact/translation float components.

`mw_vehicle_world_modify_collision` implements
`RBVehicle::ModifyCollision(SimSurface,Plane,Moment)`8023C33C. Explicit player,
forward and velocity inputs represent the original interface getters. The base
operation loads actual WORLD_MOMENT_SCALE. Player contacts use original clamped
approach speed and forward-normal terms to scale diagonal inertiaY, clear wall
elasticity, and then zero local CG Y. The nonplayer path only zeroes local CG Y
in addition to base scales. **2,048 standalone original calls and1,024 cases in
the checked-in reproduction tool have zero float-bit mismatches**. Source
OBJ_ELASTICITY must not replace this wall branch. Exact debug identifies the
existing response core's state+10C as mElasticity.

Reproduce both new comparisons:

```
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/vehicle_world_contact_reference.py --dol /path/Speed.dol --dolphin-reference /path/pinned-dolphin-reference --output /tmp/contact-verification.json --cases 1024
```

ASan/UBSan synthetic tests cover compound preparation, wall contact admission,
actual player/nonplayer modifier branches, masks and transactional invalid-input
rejection. These checks execute an original PPC functional model, not console
traces; FPSCR/subnormal modes and rare binary64 FMA ties remain outside it.

## Remaining integration boundary

`RigidBody::OnWCollide`80238420 first applies positive penetration along the
original packet normal, then routes the actual contact to the existing compared
16-pass response core. Source material resolution/SimSurface friction, callback
collision-event dispatch, accepted-contact geometry translation, complete ground
body constraints and original barrier-cache broadphase/order still require full
integration and comparison. The NWC AABB API supplies conservative source-ordered
wall candidates, not the original GetBarrierList cache producer. Its callbacks
must preserve group activation and original identity. No nearest-centerline wall
clamp, guessed wall impulse or SAT stand-in has been enabled. The recovered
components do not by themselves establish whole-car1:1 handling.
