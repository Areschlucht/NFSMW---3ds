# Rockport prototype v0.18

Extract the complete ZIP to your SD card root, replacing the previous prototype
files when Windows asks. Launch **NFS MW Rockport Prototype v0.18** from the
Homebrew Launcher and choose **DRIVE ROCKPORT**. Keep all files together under
`/3ds/nfsmw-rockport/`; the larger `world.mwp` is required. Old `world.nfm` and
`world-textures` files from v0.17 are unused and may be retained.

This is a playable native 3DS prototype, not a completed 1:1 port. It does not
enable 804 MHz or L2 cache. Old 3DS hardware performance is unverified.

## Changes

- Original region/dependency selection now drives bounded map streaming. The
  archive contains all 997 converted source sections, 13,556 model hashes and
  original boot-global texture providers. Only the active view is uploaded.
  Original normal-view LOD components replace the slot-0 diagnostic selection.
- Original collision banks now provide ground queries beyond the old road
  sample. A centreline sweep stops movement through detected original walls.
  Render/collision source identities must match; failed loading pauses driving
  rather than repeating blocking SD reads every frame. X resets, or use MENU.
- The bottom screen is rendered off-screen and double buffered. Completed HUD
  images are swapped at VBlank; the visible image is never cleared/repainted.
- Original frontend fonts, logo and artwork, BMW career-start diffuse preview,
  original car normals and rolling/steering wheels are included.
- Neutral colours are the default. DISPLAY includes optional **Piss filter**.
- Immutable material spans and resource-slot hints reduce CPU work while
  retaining original ordered geometry. Unchanged views reuse their draw plan.
- One world archive replaces thousands of loose SD files. ZIP/payload checksums
  are checked during packaging; runtime checks each newly loaded payload.

## Controls

| Control | Driving |
| --- | --- |
| A | Accelerate |
| B | Brake |
| Y | Reverse |
| Circle Pad / left-right D-pad | Steer |
| R | Handbrake; steer and tap at speed to initiate a provisional slide |
| X | Reset to the Colonial starting position; retry failed map loading |
| START / SELECT | Menu; driving pauses |

Bottom-screen MENU, HELP and STATS also support touch. HELP/STATS change the HUD
panel without pausing driving. In the garage A rolls wheels, Circle Pad steers,
Y toggles orbit and X resets the view. B/START returns to the menu. DISPLAY uses
A or touch to toggle the warm grade. START exits from the main menu.

## Current limits

Handling and chase-camera motion still use the provisional prototype controller.
Recovered original drivetrain, tire, suspension, body-response and camera
components are preserved in the source repository but are not a complete live
vehicle simulation in this build. There is no claim of 1:1 driving or full-body
wall collision. The centreline wall guard does not model the car's width or
original impact impulses. Ground-following has no jumping/falling suspension.

The full supplied stream is packaged, but every district/transition has not been
validated as playable. The ordinary contained-region path is supported; an
unimplemented nearest-region case, missing asset or exceeded resident budget
pauses loading. Original asynchronous preload, special view contexts and dynamic
render targets remain incomplete. The Colonial minimap still covers the earlier
road sample; it is not a full-city navigation system. Original sky, reflections,
layered materials, bloom and complete original menu behaviour remain unfinished.
There is no traffic, police, race progression, original audio or save system.

The larger streamed view may cost more than the small v0.17 scene. STATS shows
actual application FPS and GPU/draw/logic timings. Emulator checks do not certify
console FPS or physical LCD behaviour. The flicker fix addresses framebuffer
ownership and presentation; hardware confirmation is still useful when available.

`manifest.json` identifies every installed file and the source stream. Do not
mix world archive, collision and metadata from different builds.
