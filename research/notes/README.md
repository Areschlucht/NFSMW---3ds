# NFS Most Wanted GameCube → Nintendo 3DS: initial inspection

## Verified from the supplied file

- Input: `Speed.dol`, 4,541,888 bytes.
- SHA-256: `33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`.
- Big-endian DOL header: two text sections and five data sections. All populated sections fit the file and their file and address ranges do not overlap.
- Entry point: `0x80003100`, inside the first text section.
- BSS: address `0x80456560`, size `0xA99D8` (zero-initialized memory, not stored in the file).
- Source-path strings identify GameCube `ecstasy/EcstasyE.cpp`, `EcstasyEx.cpp`, frontend `feng/FEPackage.cpp`, and other engine components. These are clues for analysis, not recovered source code or function symbols.
- 7,533 printable strings of eight or more characters; 88 asset string candidates. Candidate extraction is heuristic and is not a complete dependency inventory.
- External filenames include tracks, frontend packages, language files, HUD data, and sound data. The executable alone is insufficient for a functional port.

The DOL format has no standard symbol-table field. This inspection has not established whether useful embedded function metadata exists. It has not verified the region/revision independently of the supplied filename and user description, decompiled functions, executed the game, or measured performance.

## Repeat inspection

Use the existing checkout in this isolated cloud environment; no worktree is needed.
This helper requires only Python 3 and does not execute the input:

```sh
python3 /workspace/port-research/inspect_dol.py /path/to/Speed.dol
```

The current output is in `speed-dol-inspection.json`. Keep the executable and game assets out of public source control.

## Next milestones

1. Restore repository/network access and inspect the repository before choosing its tools or changing its code. The current checkout has no commits or source files. Git and curl both fail to connect to the configured proxy at port 8080.
2. Obtain a filename-and-size inventory of the extracted disc, plus its game ID/revision. Look for an existing `.map` or `.elf` file; do not assume one is present. No additional game binaries are needed for this inventory.
3. Import the DOL into a PowerPC-aware reverse-engineering tool with DOL support, or map its sections explicitly using the JSON addresses. Trace startup, file I/O, allocation, and rendering boundaries. Validate any recovered function signatures against disassembly.
4. Prepare the devkitARM/libctru 3DS workflow and build a minimal homebrew program on a real device. This is a separate hardware/toolchain milestone, not evidence of game compatibility.
5. Investigate one asset format and render a small scene before attempting gameplay. A port requires substantial recovered/reimplemented engine behavior and replacement of GameCube graphics, audio, input, and OS interfaces.

Start performance experiments on New 3DS, then assess Old 3DS with measured CPU, memory, and rendering budgets. Neither device's feasibility or frame rate can be inferred from this executable's size. Full-game emulation is not the assumed porting strategy.

No game source code, dependency declarations, or tests were modified. No game build or execution has been validated.
