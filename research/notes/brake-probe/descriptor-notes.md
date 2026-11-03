# Descriptor investigation: unresolved, do not promote the partial export

Further inspection finds a 36-byte metadata chunk (`0x134800`) and a descriptor-array chunk (`0x134801`) alongside each geometry blob. The first object's descriptor payload has eight leading bytes followed by six 16-byte records. The second object's has eight leading bytes followed by twelve 16-byte records. All four objects' metadata chunks are 36 bytes long.

The first object's metadata contains big-endian words 0x108, 0x220, 0x1A8, and 0x1AC, plausibly relative offsets into different arrays. The descriptor records include lengths/count-like values and endpoints 0x20, 0xA0, 0xE0, 0xF0, and 0xFC. These could explain more draw data, but the base address, record interpretation, and primitive generation rules have not been established.

The first object's outer header contains little-endian 16-bit values 27 and 37 at payload offsets 20 and 22. Other objects differ at those positions. They may be counts, but their relationship to the probe's 22 candidate positions is unresolved. Consequently the probe must remain experimental; the previous matching 22-value field is not enough evidence to establish the full position array size.

Words such as bytes `00 16 41 80` would resemble GameCube RAM addresses if read little endian. Do not treat them as sizes or flags without checking executable code that consumes the structure. Outer chunk byte order is not sufficient to select inner field byte order.

Next decisive evidence should come from tracing the executable's consumer of chunk IDs 0x134800–0x134802 and the GX attribute/array setup. This is preferable to guessing additional primitives solely from visually plausible raw coordinates. The current environment has no detected devkitARM compiler or devkitPro installation, and the configured proxy still refuses Git connections. A 3DS executable has not been built.
