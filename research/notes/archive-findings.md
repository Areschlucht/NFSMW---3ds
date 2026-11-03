# Additional game files: inspection findings

## Files successfully inspected

- `opening.bnr`: 6,496 bytes, `BNR1` signature. Banner metadata names “Need for Speed™ Most Wanted” and Electronic Arts. This is a console-menu banner, not game code.
- `speed.ddf`: 4,587 bytes, text disc-layout configuration. Its DiskID section declares `GameName=GOWE`, `Company=69`, and `GameVersion=0`. This supports the supplied USA identification but is not independent verification of the actual disc header or executable revision. It refers to `speed.dol` as the boot file. Its settings describe the original disc workflow; they are not instructions executed during this analysis.
- `ZDIR.BIN`: 32,712 bytes. A candidate layout of 1,363 little-endian records of six 32-bit words fits the entire file. The first word is nondecreasing, consistent with a hash lookup table. The second word is always 0–3, consistent with four archive selectors.

| Candidate archive | Records | Constant word3 minus word2 |
| --- | ---: | ---: |
| 0 | 29 | 0 |
| 1 | 1,324 | 153,933 |
| 2 | 6 | 320,066 |
| 3 | 4 | 481,678 |

The two location-like fields may represent archive-relative and combined offsets in sectors. Their units are unverified; do not use them for extraction yet. Word4 is plausibly a byte size. Word5 is unclassified. There are duplicate first-word values, so treating them as unique filenames would be unsafe.

`Speed.dol` contains references to `NFS\\ZDIR.BIN`, `NFS\\ZZDATA`, and `NFS\\ZZDATA%d.BIN`. These directly connect the supplied directory and archive naming to the executable. Nearby strings include `JLZHash` and `HuffEncodeContext`; their proximity alone does not establish any particular entry's compression format.

## Transfer blocker

All four `ZZDATA0.BIN` through `ZZDATA3.BIN` uploads exceeded the workspace download tool's 32 MiB per-file limit. Their bytes have not been inspected. A filename in the upload list is not evidence of successful local access. Repository access also remains blocked by refusal of connections to the configured proxy at port 8080.

For the next investigation, obtain each archive's exact byte length and a small sample of its first 64 KiB. Samples must retain the archive index in the filename. These will help test signatures and offset units without transferring the full archives. If full archive access becomes necessary, split each original into numbered chunks of at most 16 MiB using a local file splitter, preserving byte order and providing sizes and SHA-256 checksums. Merely renaming a large file will not avoid the limit.

## Repeatable output

`python3 /workspace/port-research/inspect_zdir.py /path/to/ZDIR.BIN` produces CSV without executing game code or modifying files. The current result is `zdir-records.csv`. Labels deliberately distinguish hypotheses from raw words. This is an inspection helper, not a validated extractor or a 3DS port.

No `.3dsx` has been built. The next meaningful milestone is a validated asset lookup/extraction path, followed by a minimal native 3DS rendering experiment. Neither a complete engine reconstruction nor hardware performance has been established.
