# Integration checkpoint after complete archive collection

The four original archives are available privately. This checkpoint does not
publish another prototype ZIP or claim that the whole game is implemented.

## Runtime rendering consumer

`mw_lod_instance_visible` now implements original 802BEAA8..802BEAC4 in the
existing LOD module. `streamed_world.c` applies it before frustum/matrix decoding,
using the supplied original_context_flags (the same original Drawcontext+84 word
that feeds LOD). The compiled portable function matched 4,608 bounded original
PowerPC cases; see scenery-render-gate-verification.json.

The current prototype supplies zero as its explicit context, so its default
object activation stays unchanged. Original normal contexts set bit0x10, but
turning that on before collision/event ownership is recovered could create
invisible walls. The render consumer is integrated; the free-roam wall bug is
not yet fixed. Source group flags also drive transform changes and cannot be
replaced by filename-based object deletion.

## Car assets

`extract_original_entries.py` verified source archives against the receipts and
extracted all305 currently matched car candidate entries (135,806,976 bytes),
retaining every duplicate directory record. They are private under
`/workspace/port-research/all-car-candidates`. All83 geometry candidates passed
payload SHA checks. The existing strict B-LOD decoder fully accepts28, finds no
Bparts in28, and rejects27. The rejected cases remain rejected; triangle-header
statistics and other layouts need recovery rather than silently bypassing checks.
These are candidate/decoder counts, not a recovered playable roster.

The original BMW lamp bank now has native texture assets and state bindings;
see vehicle-light-bank.md. This remains a private asset candidate. Original
material distinctions, live WINDOW_FRONT context, brake/damage state producers
and runtime texture ownership still need integration.

## Audio

See full-music-validation.md: five complete music banks, all1,363 segments checked,
five representative complete clips decoded privately. Source timing uses integer
truncation, and four decoder tails differ by10–22 PCMframes; those discrepancies
are preserved as an integration gate. No3DS audio playback or engine/radio/menu
sound system is claimed by desktop decoding. The existing prefix inspector now
uses the proven truncated duration conversion.

Private complete test clip:
`/workspace/port-research/full-music/MW_MUSIC-first.wav` (30.016s).

## Validation for this checkpoint

The host ASan/UBSan integration suite passed, including section/provider failure
rollback, 40 changed-region fail/recover cycles, GPU-owned HUD texture conversion,
600 integrated driving frames, preserved source normals, and byte comparison of
all17,260 archived payloads. Driving remains the provisional controller.
Compiled C render-mask outputs matched bounded original PPC execution in4,608cases.
The streamed 3DS target compiled and linked successfully with the pinned devkitARM
image as `nfsmw-rockport-integration-check.3dsx`. This checks compilation; it is
not a new packaged release, hardware test, emulator performance result or proof
that the open activation/collision issue has been solved.
