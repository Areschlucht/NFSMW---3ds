# Remaining original inputs — bulk collection

The user requested as much missing data as possible before losing PC access.
The four original ZZDATA archives together contain 1,332,729,856 bytes. Earlier
whole-archive uploads exceed this workspace downloader's 32-MiB per-file limit.
Complete split archives avoid repeated requests for guessed internal names.

`tools/collect-remaining-game-files.ps1` creates 28-MiB-or-smaller pieces and a
SHA-256 manifest for each archive. It validates the known USA ZDIR SHA and archive
sizes first, reads originals through OpenRead, creates a new destination and
refuses to overwrite an existing folder. It requires about 1.25 GiB extra space.
Windows PowerShell 5.1 execution has not been verified here; sizes/boundaries,
source review and the consumer's reconstruction integrity tests were checked.

Upload priority is complete ZZDATA1 (12 pieces), then ZZDATA0 (11), ZZDATA2 (12),
and ZZDATA3 (12). Total 47 pieces and four manifests. Archive1 includes 305
currently matched car candidate entries plus global/gameplay/music metadata;
this does not make those 305 distinct playable vehicles. Complete collection
will allow identifying other assets without asking the user to locate each one.

Run beside the extracted script, substituting the original game folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\collect-remaining-game-files.ps1 -GameDirectory "C:\path\to\game"
```

Send the `.parts.json` manifests and `.bin` pieces in batches. Do not combine all
pieces into one oversized ZIP. If interrupted during collection, retain the
output/errors and choose a new Destination for another attempt; finished archive
manifests identify complete archive sets. Original files are never modified.

`tools/reassemble_game_archives.py` validates manifest identities, all piece names,
contiguous offsets and exact lengths, then checks each SHA and whole-archive SHA.
Only a fully verified result is linked to the final filename. A failed partial
is retained, and previous outputs are never overwritten. Five small deterministic
tests cover exact reconstruction, overwrite refusal, corrupted pieces, wrong whole
hash, parent-path injection and missing pieces (the first test covers two cases).
No full original archive has been reconstructed until its pieces actually arrive.

Original archives, segments, converted assets and decoded audio remain private;
only authored tools, findings and verification metadata are committed to GitHub.
