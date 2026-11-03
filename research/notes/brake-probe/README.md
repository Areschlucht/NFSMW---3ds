# Experimental partial brake mesh

The probe decodes the supplied 6,080-byte geometry sample only. It is deliberately not a general asset converter.

- The first object's header contains a 16-bit value of 22. At file offset 0x428 there are 22 plausible big-endian signed-16 XYZ triples, ending at 0x4AC.
- At offsets 0x340 and 0x3C0, candidate GX opcode 0x9A is followed by big-endian counts of 22 and 7 respectively. Interpreting the following records as five byte-sized attribute indices yields in-range position indices in their first byte.
- Expanding these two candidate triangle strips with alternating winding yields 25 triangle slots: 21 nondegenerate triangles and four repeated-index or zero-area triangles. All indices are checked before export.
- The result forms a thin, contiguous curved strip in orthographic projections. That is compatible with a portion of a brake object; it is not proof of a complete or correctly decoded model. The first four candidate positions are unused by these strips.

`brake-partial.obj` is a partial mesh in **raw integer units**, with no textures or normals. `brake-partial.svg` and `brake-partial.png` show orthographic projections, not a running game. `brake-probe.json` records the input hash, primitive attribute indices, counts, and bounds.

Unknowns include the remaining draw data, platform vertex descriptors, other attributes, coordinate scaling, winding relative to the game's render state, and object/material transforms. The original header's floating-point bounding box does not exactly match these raw coordinates under an assumed power-of-two scale; no guessed scale is applied.

Repeat with:

```sh
python3 /workspace/port-research/decode_brake_probe.py /path/to/brakes-geometry.bin /path/to/output-directory
```

The decoder and its OBJ/SVG/JSON generation require only Python 3. The PNG was generated separately with matplotlib and visually inspected. No 3DS compilation or hardware validation was performed.

Next milestone: resolve the platform vertex descriptors and position scale, decode the remaining primitives, and compare their extrema to the object's stored bounding box. A 3DS renderer must follow those checks; this partial export does not establish port feasibility.
