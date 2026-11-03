# Archive sample analysis

User-supplied archive sizes: 315254784, 340240384, 330981376, and 346253312 bytes for archives 0–3 respectively. These sizes have not been measured against full local archives because transfers exceed the download limit.

All 1,363 directory records fit their reported archive sizes when word2 is multiplied by 2048 and word4 is interpreted as byte length. Excluding zero-length entries, adjacent entry ranges do not overlap and have gaps between 0 and 2047 bytes. End padding is also under 2048 bytes for every archive. The word3-minus-word2 constants equal the cumulative preceding archive sizes in 2048-byte sectors. This provides strong structural support for archive-relative and concatenated sector offsets.

Archive 0 and 1 samples begin with `MVhd` and contain `SCHl` and `MV0K` tags, consistent with EA multimedia streams. Archive 2 begins with `SCHl`, followed by `SCCl` and `SCDl` chunks, consistent with EA audio streams. This classifies only their initial entries, not the entire archives. Archive 3's first entry has an unclassified binary header. No codecs have been decoded or played.

A candidate filename hash starts at 0xffffffff, uppercases ASCII characters, and accumulates `hash = (hash * 33 + character) modulo 2^32`. Matching path strings from Speed.dol yields 67 distinct path candidates mapping to 73 directory records. This is strong evidence for a useful lookup algorithm, but neither names nor duplicate resolution are proven by hash equality alone. `GLOBAL\\GAMEPLAY.BIN`, for example, maps to multiple entries. No rule for choosing among those entries is assumed.

`map_assets.py` repeats the matching analysis and writes `named-assets.csv`. The helper uses only the Python standard library. Its output was generated successfully against the current uploaded DOL and ZDIR.

Next validation: copy the 6080-byte candidate brake geometry entry and 212136-byte candidate English text entry from ZZDATA1.BIN, then inspect their structures. `extract-samples.ps1` contains the corresponding read-only source operations, archive-length check, exact-length read loop, and non-overwriting destination creation. PowerShell is unavailable here, so that helper has been reviewed but not executed on Windows. It does not decode or convert either asset, nor create a 3DS executable.
