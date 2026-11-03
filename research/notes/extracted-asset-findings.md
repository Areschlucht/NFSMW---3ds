# Extracted asset validation

Both supplied files have exactly the sizes predicted by the directory: 212,136 bytes for English text and 6,080 bytes for brake geometry.

## English text

The file consists of one little-endian chunk, ID `0x00039000`, payload size 212,128 bytes. Its header declares 4,464 entries. The hash/offset table begins at file offset 6,172; string storage begins at file offset 41,884. Both offsets are relative to the eight-byte chunk header in the stored header fields.

All 4,464 keys are unique and sorted. All 4,464 offsets fall within the string storage, point to a string boundary, and have an in-bounds null terminator. Readable strings include `ACCELERATION`, `Accept`, and `LAP`. Encoding beyond ASCII has not been established. The presence of online-related text does not prove that this platform implements those features; shared localization data may include unused entries.

This independently supports the filename-hash lookup and sector-based extraction path, rather than merely detecting plausible filenames in the executable.

## Brake geometry

The main container ID is `0x80134000`, with 5,632 payload bytes. The complete file, including trailing zero-ID chunks, parses exactly under a nested little-endian ID/length interpretation. Every nested chunk fits its parent.

Four child containers with ID `0x80134010` contain names:

- `EBRAKE_KIT00_B`
- `EBRAKE_STYLE01_B`
- `EBRAKE_STYLE02_B`
- `EBRAKE_STYLE03_B`

Each has nested `0x80134100` data with child IDs `0x00134800`, `0x00134801`, and `0x00134802`. Their payloads have not yet been decoded into vertex attributes, primitive commands, or triangles. The outer little-endian chunk headers do not establish the byte order of every platform-specific structure inside them.

The sample supports the identification as a brake-geometry package. It is not yet a renderable mesh. No model conversion, game execution, or 3DS build has occurred.

## Repeat validation

Run `python3 /workspace/port-research/inspect_asset.py /path/to/asset.bin`. Generated reports are `english-inspection.json` and `geometry-inspection.json`. The helper validates chunk bounds and language table/string boundaries, and reports geometry name candidates. It does not execute input binaries.

Next: decode one object's vertex layout and primitive stream, verify index bounds and geometry plausibility, and then attempt a minimal native rendering experiment. These samples are sufficient for that next investigation; no additional uploads are currently requested. Repository/tool installation remains a separate outstanding network issue.
