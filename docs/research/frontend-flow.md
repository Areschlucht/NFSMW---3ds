# Original frontend package and Alias flow inventory

2026-11-03. No SDK build, release, runtime edit or reconstructed FEng interpreter
is produced by this checkpoint. Decoded original layouts remain private.

## Concrete original layouts recovered

`tools/frontend_flow_inventory.py` reads the SHA-pinned supplied GameCube
FRONTEND-FRONTB_VM_NGC.BUN and decodes all **99 original FEng packages**: 98 JDLZ
and one HUFF. Each chunk, declared compressed/output size, FEng root and child
range, PkHd header and bounded package name is checked. Output filenames are
strict original leaf names, not executable paths. Existing differing outputs
are refused. Source inputs remain unchanged.

The original inventory includes:

- PressStart.fng: 17,384 bytes.
- MainMenu.fng: 46,912 bytes; MainMenu_Sub.fng: 48,420 bytes.
- MC_ProfileManager.fng: 32,996 bytes.
- MC_DeleteProfile.fng: 35,144 bytes.
- MC_Bootup_GC.fng, MC_Main_GC.fng and MC_List.fng.

The explicit GC memory-card packages matter. Their presence does not mean a 3DS
SD-card save should emulate GameCube memory-card hardware or reuse that binary
save format. It establishes original screens available to inspect for a port.

Private decoded files and inventory:
`/workspace/port-research/frontend-flow/`.

## Alias and main-flow evidence

The original USA executable contains these exact strings:

| Purpose | Original strings / addresses |
| --- | --- |
| Profile manager creator | CreateUIProfileManager at 803E1A04 |
| Profile operations | PMSave, PMPopDelete, PMCreateNew, PMLoad, PMDelete in 803E1A1C..803E1A50 region |
| Delete creator | CreateUIDeleteProfile at 803E1A54 |
| Menu intents | MainQuickRace, MainCustomize, MainOptions, MainCareer, MainProfileManager near 803DFA58..803DFAB0 |
| Main package references | MainMenu.fng at 803DF9A8; MC_ProfileManager.fng at 803DF9FC |

Original screen entry references to MC_ProfileManager are also materialized at
80118428 and 80137778 before the common 80133EA0 call. These are conservative
local observations; the whole menu state machine and callbacks are not recovered.
Create, load, save and delete Alias flows have original vocabulary and packages.

**Alias name length, character set, maximum simultaneous profiles, original
button order, first selection and confirmation/cancellation transitions remain
unproved.** A port may choose bounded storage/input limits as implementation
choices, but must not label guessed limits as original-game facts. No Xbox manual
or PC menu screenshot is used to establish GameCube-specific behaviour here.

## Original art actually referenced by those layouts

MainMenu references MW_Logo.tga, FONT_MW_BODY.ffn, FONT_MW_TITLE.ffn, BasePoly,
BaseStripe, GRAF_04, ROGER_TAG_3, MW_GRIT_01, TAG_1, ARROW_SKINNIER,
Main_Icon_Car_Select, Splatter_01 and Crosshair_Corner. PressStart additionally
references Start.tga and GRIT_VINETTE_02. Profile/Delete share the original body
and title fonts, stripe/poly panels, graffiti, arrow and crosshair resources.

The optional SHA-pinned `--art` source validates matching texture RGBA hashes and
dimensions. Concrete supplied FRONTB art includes:

| Texture | Original hash | Dimensions |
| --- | --- | --- |
| TAG_1 | 03bfc0cb | 64 x 64 |
| MW_GRIT_01 | 128fdcb8 | 128 x 128 |
| GRAF_04 | 312c3e02 | 64 x 64 |
| ROGER_TAG_3 | 4e19a58b | 64 x 64 |
| GRIT_VINETTE_02 | 7f1b63b4 | 128 x 32 |
| FONT_MW_TITLE | e0463afa | 512 x 512 |
| SPLATTER_01 | ec2dcaee | 64 x 64 |

Existing `ui_build_assets.py` already verifies the original GLOBALA body font,
237 glyph metrics and MW_LOGO, and converts selected original title glyphs.
Its prototype composition is not the original screen layout. The new FNG
inventory gives the actual package/resource evidence needed to replace it.

**PC_key_* resources occur inside this GameCube frontend archive too.** Their
presence does not establish that PC buttons are visible in the target flow.
Resource inventories are not proof of original animation, layout, visibility,
localized menu labels or platform-specific selection behaviour.

## Decoder detail and validation

Some frontend JDLZ packets finish with three nonzero unused bytes. The shared
`nfs_jdlz` helper rejects such trailers; this tool leaves it unchanged and uses a
bounded local decoder that retains and reports up to three trailer bytes. It
checks every back-reference and declared output size. This does not assign
unproven meaning to individual trailer bits. The one HUFF package is
LS_THXMovie.fng, decoded with the existing SHA-pinned bounded reference emulator.

The existing decoder's accepted packets are compared byte-for-byte. Invalid
magic and truncated-header cases are rejected for each JDLZ packet. All99 FEng
roots/child ranges and eight required menu package identities are checked.
Private verification.json records exact measured counts. Original scripts and
resource payloads are never committed by this tool.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/frontend_flow_inventory.py \
  --frontend /workspace/port-research/v018-decoded/FRONTEND-FRONTB_VM_NGC.BUN \
  --art /workspace/port-research/v018-decoded/FRONTEND-FRONTB.BUN \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --decoded-directory /workspace/port-research/frontend-flow \
  --output /workspace/port-research/frontend-flow/inventory.json
```

Next: decode actual object/script/layout and language-key consumers, recover
Alias limits and memory-card profile selection logic, then adapt original menu
flows and art to 3DS inputs/two displays without claiming exact layout parity
from a resource-name list.
