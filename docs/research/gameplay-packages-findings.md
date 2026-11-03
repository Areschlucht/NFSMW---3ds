# Supplied gameplay packages — 2026-11-03

The new metadata bundle passed ZIP CRC, extraction-manifest SHA-256/size and
known USA directory-range verification for all eight payloads (4,294,123 bytes).
Both GAMEPLAY records are byte-identical, SHA-256
`7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6`.
They remain separate source records; identical observed content does not establish
which directory record the original loader selects.

## Recovered container structure

This VPAK is a packed directory, not the single-database ATTRIBUTES envelope.
The little-endian header is magic, package count, name-region offset and size.
Each 20-byte entry contains name offset, BIN size, VLT size, BIN file offset and
VLT file offset. There are 272 entries, with bounded NUL-terminated names and
64-byte-aligned disjoint stream ranges. Embedded big-endian BIN/VLT streams use
the existing strict Attrib layout/relocation/type reader.

`tools/gameplay_packages.py` adapts each pair into a bounded in-memory envelope
and resolves inheritance against the original ATTRIBUTES schema and other packed
packages. Twenty packages can load first; their definitions allow the remaining
252 to resolve. Original inputs are unchanged. All returned field provenance
refers to the original gameplay/schema SHA and file offsets, not the adapter.

There are 6,287 gameplay collections across the 272 packages. These are not 6,287
races. Package names include event packages, challenge packages, gpcore, race_bin
packages and epic_pursuit. Exact event ownership and unlock behaviour still need
original consumer traces. Do not infer shipped mode availability from a name.

The gameplay class contains 220 fields. Whole-identifier DOL string hashes resolve
12 field labels: NumLaps, CatchUp, Radius, Name, Rotation, MilestoneName,
CollectionName, Position, TrafficLevel, Region, engagetrigger and ZoneType. Other
fields retain their hashes/types; no guessed label or runtime meaning is assigned.

## Verification

`tools/verify_gameplay_packages.py` decoded 89,251 fields, checking each original
byte range against its original source SHA. It rejected eight malformed variants:
empty/oversized directory, out-of-bounds names, name offset inside a string,
out-of-bounds BIN, header overlap, overlapping BIN/VLT and truncated payload.
See gameplay-packages-verification.json. These checks establish layout/provenance,
not matching gameplay execution or original physics integration.

`tools/import_whole_game_metadata.py` validates the archive paths, manifests,
source entries, directory offsets, archive offsets, sizes and payload hashes before
writing private files. Existing inputs must match byte-for-byte; source archives
are never edited. See metadata-received-verification.json.

The supplied disc listing contains only eight root disc files, with no expanded
media folders. This is normal for the supplied packed disc extraction and does not
prove that movies or audio are absent inside the archives. Their actual archive
entries still need targeted name/hash/header recovery.

No new playable build is produced by these read-only tools. Next work is original
scenery-group/event activation, recovered vehicle lamp binding and music metadata
consumers; their separate reports must distinguish proven consumers from leads.
