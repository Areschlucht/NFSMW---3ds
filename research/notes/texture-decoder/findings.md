# RGB5A3 decoding validated with an existing game asset

The supplied `opening.bnr` contains a standard 96×32, 16-bit GameCube RGB5A3 image from file offset 0x20 to 0x1820. The pixel stream is stored as big-endian words in 4×4 tiles, rather than linear scanlines. Its decoded PNG shows the recognizable NFS Most Wanted menu logo.

The reusable standard-library decoder is `/workspace/NFSMW---3ds/tools/gc_texture.py`. It handles both opaque RGB555 and three-bit-alpha RGB444 branches, expands channels by bit replication, reconstructs tiled pixels, and writes a PNG with CRCs. It checks banner magic/size and texture byte counts, and refuses to overwrite an existing output file.

Validation:

- Five unittest cases passed for known pixel vectors, all eight alpha levels, tile order using four colored quadrants, malformed/truncated inputs, and PNG CRC/decompressed-pixel integrity.
- The real banner was decoded and visually inspected.
- Independently reading the PNG with Pillow reproduced the exact 96×32 RGBA byte stream.
- Decoded RGBA SHA-256: `3ca072b64a2475bd4bc876a8dd105c0e53774c961147e4cb6eaf8f6dea7241b8`.

This validates one GameCube image format against a real uploaded asset. It does not prove the brake textures use that pixel format, establish their package format, or decode missing image data. The banner is console-menu artwork, not a recovered car/track texture.

Actual shared-texture candidates are still absent from local storage. Their extraction ranges and the reviewed Windows helper are recorded in the brake-material findings. Further image-package investigation depends on those small files becoming available. No new hardware viewer test is needed for this work.
