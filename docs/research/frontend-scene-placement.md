# Original frontend placement and camera records

The prototype's car-centred model rotations are not the original garage scene
consumer. `tools/frontend_scene_reference.py` reads the supplied FE attribute
vault with its original dependency, checks its field offsets against the matching
debug ELF, then executes the original static camera matrix constructor. The
private report is `/workspace/port-research/menu-reference/frontend-source-placement.json`.
It contains 18 camera cases and 11 screen-to-camera references, with input hashes,
field provenance, exact source eye/target/up, FOV and resulting view matrices.
No original executable, debug data or converted asset is committed.

Original functions: `GarageMainScreen::UpdateCurrentCameraView` 803a54ac;
`SelectCarCameraMover::CreateCameraMatrix` 800787ac;
`GarageMainScreen::UpdateRenderingCarParameters` 803a59b0;
`GarageMainScreen::HandleRender` 803a5e54. Actual camera matrix construction,
angle quantization, rotation, banked-up and look-at callees run unmodified in the
bounded Gekko reference harness. No eye/target/terrain provider is substituted.
This is emulator-reference evidence, not a hardware trace or complete native
frontend camera port.

`Attrib::Gen::frontend::_LayoutStruct` confirms the values are spherical camera
parameters, not eye coordinates: vertical angle at 3c, horizontal angle at 54,
radius at 50; look-at XYZ at 2c/30/34, roll at 44, FOV at 24, animation speed at
20, damping at 1c and periods at 48. `SetCurrentOrientation` receives the original
vertical/horizontal/radius triplet. `mainmenu` references `angle3`.

For that actual main-menu record, original source XYZ outputs are:

- Eye `(0.2851859331, -5.4429936409, 0.7365367413)`.
- Target `(1.2000000477, -0.3000000119, 0.3000000119)`.
- Up `(-0.1246977597, 0.0214985497, 0.9919632077)`; FOV 55 degrees.

Map all three vectors with the same source-to-viewer `(X,Z,-Y)` basis. These are
world metre coordinates; dividing camera distance by arbitrary model scale or
using an extra scene-centred orbit changes the original composition.

The original geometry parent transform and car transform are independent:

| Garage | Geometry source-Z rotation | Geometry source translation | Car source XYZ rotation |
| --- | ---: | --- | --- |
| Main FE | 134.4125061 degrees | `(0,0,0)` | `(0,0,304.9697876)` degrees |
| Career safehouse | 302.8530884 degrees | `(0,0,0)` | `(0,0,304.9697876)` degrees |
| Customization shop | 0 degrees | `(0,0,0)` | `(0,0,304.9697876)` degrees |
| Backroom | 134.4125061 degrees | `(0,0,0)` | `(0,0,304.9697876)` degrees |
| Car lot | 0 degrees | `(0,0.075000003,0)` | `(-0.379623,-0.000193,340)` degrees |

Do **not** add the geometry rotation to the car BodyMatrix rotation. The original
code rotates the car position by the geometry rotation, while building the body
matrix separately from GetCarRotationXYZ. Source `carPosX/carPosY` are both zero.
Car source height is the original ordered sum of four tire radii times .25 minus
the ordered sum of wheel mount Z times .25, then bias `-0.02500000037`; actual
currently selected car providers must supply the tire radius and mounts.
Grounding from the artwork's lowest vertex changes this original placement.

Remaining boundaries: animation/oscillation and user-orbit update, actual current
ride tire providers, geometry header matrix handling, shadow/reflection and
particle passes, and source menu-specific camera switching. The report provides
original static poses and placement evidence; it does not establish that the
current two-screen app already matches the GameCube menu.
