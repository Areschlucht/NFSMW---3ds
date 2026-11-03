# Native GPU prototype v0.3

Update after delivery: the user reports v0.3 runs as well as the earlier viewers on the available New 3DS. This establishes a successful device run; individual control checks and measured performance were not separately logged. The build-time validation notes below retain their original distinction between native tests and GPU execution.

## Implementation

The runtime uses Citro3D to render the four decoded brake meshes into a 400×240 top-screen target with a depth buffer. A PICA200 vertex shader applies the model-view and tilted perspective matrices, transforms generated flat normals, and computes simple two-sided inspection lighting. The fragment stage passes the resulting vertex color through. No original texture images or game materials are used.

The GPU upload is an expanded vertex list prepared only at initialization or when switching model/mode. Each filled triangle uses three vertices. Edge mode uses 18 vertices per original triangle: six vertices for each of three narrow triangle ribbons, since the PICA200 has no line primitive. Both modes issue native triangle draws. Per-frame updates send matrices and lighting uniforms rather than rebuilding positions on the CPU.

The default build still targets ARMv6K and does not request the New 3DS clock or L2 cache. Old 3DS support remains untested. Performance on a small model does not predict full-game feasibility.

## Synchronization and error handling

The VBO resides in linear memory. It is explicitly cache-flushed after updates. Runtime updates occur after a synchronized frame begins and the prior graphics queue is drained. Dirty state persists if a frame cannot begin. Shutdown calls Citro3D finalization, which drains queued GPU work and destroys render targets, before freeing shader/VBO resources. Failure paths free any resources that were allocated successfully.

The bottom text console uses a single framebuffer and is flushed while Citro3D manages the top-screen frame transfers. Allocation, shader/program creation, uniform lookup, buffer configuration and asset loading failures display an error or abort initialization cleanly. These paths are code-reviewed; only the portable buffer preparation and asset decoding have runtime tests here.

## Evidence and limits

- The PICA200 shader assembles successfully.
- A complete build with the official pinned devkitPro image passes GCC `-Wall -Wextra -Werror`.
- Native tests pass ASan/UBSan for all four decoded models in filled and edge-buffer modes; expanded vertices stay finite and within normalized bounds, generated normals have unit length, and capacity canaries remain intact.
- A known XY triangle produces the expected positions and +Z normals; null, short-capacity, non-finite, invalid-index and degenerate inputs are rejected.
- Earlier decoder mutation tests and 48 CPU reference-render cases still pass. They do not execute PICA200 commands.
- v0.1/v0.2 have user-reported successful New 3DS runs. **v0.3 hardware execution has not yet been verified.**

The reference Citro3D examples and current upstream render-queue implementation were consulted for initialization, projection and resource lifetime. This does not substitute for a GPU/device test. The next useful check is that v0.3 displays a model, that X/Y and SELECT work, and that START exits cleanly on the available New 3DS.

The prior v0.2 ZIP is preserved. No environment configuration was reapplied and nothing was pushed or published remotely.
