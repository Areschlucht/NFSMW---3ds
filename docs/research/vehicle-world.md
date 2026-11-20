# Physical vehicle geometry and world collision integration

`mw_vehicle_world` is the source physical primitive preparation/geometry stage.
It uses the existing verified compound decoder and shape dispatcher, followed
by original `RigidBody::Primitive::Prepare` 80231F14, `SetCollision` 80231F60 and
`Dynamics::Collision::Geometry` construction 80089398. It does not yet claim a
complete wall/ground intersection or body-world response pipeline.

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
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fsanitize=address,undefined -Iinclude tests/test_vehicle_world.c source_bmw/mw_vehicle_world.c source_bmw/mw_body_collision_shapes.c -lm -o /tmp/test-vehicle-world
/tmp/test-vehicle-world
```

Source box/sphere narrow phase remains the next gate. Original
`WCollisionMgr::Collide` 802F338C consumes cached **40-byte** barriers, constructs
a zero-thickness wall box and dispatches `Geometry::FindIntersection` 8008A630.
The dispatch table selects BoxVsBox 80089658, SphereVsBox 80089D50,
BoxVsSphere 8008A604 and SphereVsSphere 8008A4B8. Original wall orientation
rejection and callback packet assembly must also match.

`RigidBody::OnWCollide` 80238420 applies positive penetration along the original
packet normal and routes the actual contact to the existing 16-pass verified
body response core. Native NWC currently exposes nearest segment-wall queries;
a segment from the car center cannot reproduce these compound overlap
contacts. No centerline clamp or guessed wall impulse is introduced here.
