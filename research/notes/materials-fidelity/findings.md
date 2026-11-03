# Current checkpoint after v0.18 input upload

Canonical hero preset and original diffuse sources are now recovered. The earlier checkpoints below retain historical unresolved leads; this section supersedes them.

- Native GLOBALB_VM_NGC.BUN SHA256 da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b contains82original30220presets. M3GTRCAREERSTART at385560 selects BMWM3GTRE46, basepaint C7F288D1 and vinyl E9886D54. See canonical-bmw-preset.json.
- Original carparts container80034602/version6 resolves those to METAL_L1_COLOR41 (RED/GREEN/BLUE183,GLOSS128) and PSRTEST (TEXTURE PSRTEST, NUMCOLOURS64, REMAP0). Selected white/cream vinyl colors are unused by this no-remap branch. See canonical-bmw-parts.json;28selectedattribute lookups match original802D9B14.
- Actual hero source is BMWM3GTRE46_PSRTEST849FF2F5 with mask02C984A0. BMW_24 was only a candidate and is not selected by this preset.
- Original partial mask uses grayscale/128 with separate per-term truncation;>=128selects source.384originalPPCcases match. Source fourth byte is not used as opacity.
- Native CPU RGB5A3 adapter8026C080 and packback8026C130 are now closed: all65536halfwords match decode/encode reference loops and256arbitraryCPUwords match packback. Original expansion shifts fields, unlike display PNG bit replication. See paint-native-adapter-verification.json.
- Current isolated native-adapter-derived diffuse preview: canonical-skin-native-preview/de3ad3c6-logical-diffuse.png,512²opaque, RGBA SHA2560ce2e7aa06e152f438292cdd8d780f7ec4c1c9152152558548400de30d62886e. CPU fourthbyte, GXnormalized fourthbyte and linear native halfword plane are separate artifacts. Original indexed edge palette quantizer remains unresolved;41logicalwords/26nativehalfwords are observed, not proof quantization is lossless. No reflections/specular/lighting are baked into this preview.
- New original render/post-effect report shaders/original-visuallook-evidence.json and shaders/render-plan.md separate actual bloom/material recovery from optional artistic grading. include/mw_color_grade.h and source_bmw/mw_color_grade.c implement neutral-default, alpha-preserving one-stage warm grade. Mocked state tests and strict real devkitARM compile pass. The optional label is Piss filter; coefficients are honestly provisional, not original LUT data.
-18material recovery unit tests and syntax compilation pass. Shared root shaders/main/exporters remain untouched by this agent; root coordinates any cloned scene/runtime integration.

---

# Original BMW vehicle material recovery checkpoint

This checkpoint recovers original executable behavior and records its limits. It does not replace the reviewed v0.16 renderer, synthesize a BMW livery, or establish full visual fidelity.

## Provenance and verification

All executable addresses refer to the supplied USA GameCube Speed.dol, SHA256 `33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`. `vehicle_dol.DolImage` maps actual DOL sections; late data does not share the early text section's constant address delta.

`tools/material_recovery_vehicle.py` implements a bounded original light target selector and texture-key helpers. Eight unit tests pass. Its optional reference verifier executes the original PowerPC hash routines and integer light selector with Unicorn, checks the executable SHA256, and limits memory/instructions/time. `light-alias-evidence.json` records 26/26 hash reference matches and 128/128 selector matches, covering all combinations of three enable bits, three suppress bits, and the side-light override. These checks prove the transcribed target-key subset; they do not prove integration with the original flag producers or GPU.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -p 'test_material_recovery_vehicle.py'
PYTHONPATH=/workspace/toolchains/python-deps:tools python tools/material_recovery_vehicle.py /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol /workspace/port-research/materials-fidelity/light-alias-evidence.json --verify-original
```

## Six gray light references are runtime aliases

Six of the seven unresolved BMW texture references are generic runtime texture aliases: HEADLIGHT_LEFT/RIGHT, HEADLIGHT_GLASS_LEFT/RIGHT and BRAKELIGHT_LEFT/RIGHT. Their exact keys match the original case-sensitive multiply-by-33 hash at 0x80062ECC. They are not six independently missing painted textures.

The seventh reference, `BMWM3GTRE46_SKIN1` (`de3ad3c6`), is a generated skin output. The original compositor and canonical M3 paint/vinyl configuration remain unrecovered. No guessed colors or artwork were generated.

Original initializer 0x802DB7CC constructs SKIN1/SKIN1B/GLOBAL_SKIN1 keys and light source arrays. Default prefixes are BMWM3GTRE46_KIT00_HEADLIGHT and BMWM3GTRE46_KIT00_BRAKELIGHT. RideInfo part slots 0x40/0x41 can replace those prefixes using TEXTURE_NAME (`10c98090`); missing or zero attributes use the defaults.

The original light update 0x802CAA44 selects headlight_ON. Crucially, 0x802CABE8..0x802CAC48 then overrides both headlight glass targets with the resolved WINDOW_FRONT target at CarRenderInfo+0x2D0. Mapping glass straight to HEADLIGHT_GLASS_ON would miss this actual behavior. The helper therefore requires an explicit window target.

Brake targets use bits 8, 16 and 32 of CarRenderInfo+0x1608, suppressed by corresponding bits of +0x160C. Global 0x80437310 forces side lights on, but does not force the centre. Original flag producers, damage passes and live window/tint selection are still separate unresolved systems.

Original supplied sources exist for headlight_ON (`e626da6d`), headlight_GLASS_ON (`ea977c66`), brakelight_OFF (`051ae6de`) and brakelight_ON (`938c73a0`). Global WINDOW_FRONT (`7b220ddf`) is present, but its resolved live target need not always equal the unmodified global source.

## Exact additional paint inputs

`required-material-inputs.json` retains original ZDIR row numbers and all six raw words per entry. All offsets below are bytes within ZZDATA1.BIN:

| Original entry | Offset | Length |
|---|---:|---:|
| CARS\\BMWM3GTRE46\\PREVINYL.BIN | 128509952 | 8192 |
| CARS\\BMWM3GTRE46\\VINYLS.BIN | 128591872 | 2187392 |
| GLOBAL\\DYNTEX.BIN candidate A | 279683072 | 1274240 |
| GLOBAL\\DYNTEX.BIN candidate B | 299415552 | 1274240 |
| GLOBAL\\DYNTEX.BIN candidate C | 266086400 | 1274240 |

The three DYNTEX rows share a hash and final directory word. Content equality and active loader precedence have not been demonstrated. Preserve and compare all three, rather than silently choosing the first.

Original loader 0x802DEFC4..0x802DF028 skips vinyl loading for request byte7=0; byte7=2 or nonzero global 0x804388E4 selects PREVINYL; other nonzero byte7 selects VINYLS. Existence check is 0x802DF030 and load call is 0x802DF04C. The producer of byte7 and canonical BMW preset still require recovery, so these files are candidate dependencies, not a proven final paint recipe. Parent coordinates any user upload request.

## Original visual dimensions, kept separate from physics

`visual-values-evidence.json` contains the ATTRIBUTES.BIN SHA256, source collection/field keys, exact original field bytes, mapped constants and code-range hashes. Values use the driving specialist's strict shared `vehicle_attributes.py` parser rather than a second schema implementation.

BMW ecar TireOffsets are `[1.6,+.91,0,.33]`, `[1.6,-.91,0,.33]`, `[-1.13,-.91,0,.33]`, `[-1.13,+.91,0,.33]`. Original 0x802D3D54..0x802D3D88 copies these vectors without reordering xyz. Fourth components are clamped to at least 0.1 and stored separately at visual object+0xB8; vector fourth components are then cleared. 0x802D56BC..0x802D56D0 uses that radius as a divisor in rolling phase. The fourth component is therefore an artwork wheel rolling radius, not merely an arbitrary vector value.

The independent physical tire diameter helper 0x80224268 uses tire section width/aspect ratio/rim size. Caller 0x802D3DF0 halves this diameter. BMW 255/40R19 gives approximately 0.3433 m physical radius versus 0.33 m artwork radius. Driving specialist owns the bit-verified physical helper.

RideHeight is -3.25. Original visual consumer loads required layout+0xFC at 0x802D6648, then uses original float32 0.0254 in FMADD at 0x802D6650. This establishes an inches-to-metres conversion for this visual field. FECompressions are original [.27,.27], but their consumer and units are not established here. Neither value should be added directly to the current fitted wheel heights.

Final wheel matrices, hub versus mount origin, local mesh orientation, kit offsets and the full body height transform remain unresolved. Retain the existing fitted rig until those consumers establish a replacement. No rig/runtime edits were made.

## Remaining material fidelity work

Recover canonical BMW preset and generated paint compositor from original inputs/code; resolve duplicate DYNTEX precedence; establish light flag producers/window override state; trace final wheel/body transforms; recover original material composition and lighting only with evidence. Existing world baked RGB, reviewed 13-instruction shader and 36-byte GPU vertex format remain untouched. World fourth vertex byte/night lighting is still unresolved and is not invented here.


## Resumed checkpoint: supplied paint inputs

The files listed in received-inputs.json have arrived. All three DYNTEX copies are byte-identical (SHA256 519ef3ece5ed45ec28341982770cbb0f2cc254b10b325835f83a60eb193191fa), resolving content ambiguity for these observed archive extents. Active loader precedence remains immaterial to their current bytes. Decoded DYNTEX contains environments/UI rather than a paint-named texture. PREVINYL textures have nonconstant RGB but uniformly zero alpha; see previnyl-pixel-statistics.json. Their appearance as blank ordinary RGBA previews is not proof of an empty internal data role.

The full VINYLS catalog contains a BMW-specific pair outside UNIQUE01..12: BMWM3GTRE46_BMW_24 (7e19c0cb), decoded/179_7e19c0cb.png, and BMWM3GTRE46_BMW_24_MASK (f49b6836), decoded/265_f49b6836.png. Original source shows asymmetric blue/red race panels with a matching grayscale mask. This is a stronger candidate than generic UNIQUE patterns, but canonical preset selection and color transformation remain unproven. Do not substitute its source RGB directly as the finished hero livery.

Original code explicitly chooses preset M3GTRCAREERSTART (8015FF40 and 80165728). Preset loader802DB494 handles chunk00030220 with 0x290-byte records: model string+8, preset string+28 and139 part keys+60. Neither currently supplied GLOBALA nor GLOBALB includes that chunk/name. Applying a found preset via802DB684 explicitly sets RideInfo byte7=1 at802DB6B0 then resolves the139 part keys. This establishes an actual preset mode producer, but its original record remains missing.

New tools/material_recovery_presets.py preserves names, raw unknown fields,139 part keys and record hash, rejects malformed records and limits parsing to actual top-level30220 chunks. Three unit tests pass. Its bounded original PPC reference verifier matches endian transformations for1/2/5/32 synthetic records, comparing every byte except linked-list pointers. preset-loader-verification.json records these checks; they verify recovered schema handling, not canonical preset contents.

GLOBAL\FE_ATTRIB.BIN is directly loaded in801FF23C at801FF284 and parsed at801FF2E8. Global\GlobalMemoryFile.bin is loaded at801FF5BC, while GLOBAL\GLOBALB_VM_NGC.LZC is loaded at801FF66C. Their membership is not inferred from filenames. These are justified next small original containers to inspect for the missing frontend collection and/or30220 records; parent coordinates requests.

One producer of loader mode7 is a separate dummy-skin path802DB2D4: slots1..4 select mode1, slots5..12 mode2, others0, using DUMMY_SKIN%d/WHEEL%d/SPINNER%d. This does not identify the BMW hero preset. Additional light-state transfer evidence:802D60C0..CC copies update-input offsets60/64 into CarRenderInfo1608/160C. Main live flag generation remains unrecovered.


## Recovered paint-word operations and original slot names

Original enum/name table80438484 contains139 sequential (enum,pointer) pairs. The bounded pinned-DOL reader in material_recovery_presets.py exports original-part-slots.json. Paint-relevant slots are BASE_PAINT76, VINYL_LAYER0 77, PAINT_RIM78 and VINYL_COLOUR0_0..3 at79..82. These are original labels, not inferred from array position conventions.

Actual skin preparation802E1B64 obtains BASE_PAINT RED/GREEN/BLUE/GLOSS attributes and packs `RED | GREEN<<8 | BLUE<<16 | GLOSS<<24` at802E1C58..74. It obtains the selected vinyl part's TEXTURE string through802E19D0 and constructs car name + '_' + TEXTURE, or car name + '_PRECOM_' + TEXTURE when mode2/globaloverride applies. Ordinary texture mode also requests the matching '_MASK'. NUMCOLOURS and REMAP control additional recolor preparation with the four selected original vinyl color parts.

New tools/material_recovery_paint.py transcribes the original802E0A84→802E0890 recolor subset using original numeric word ordering. It retains float32 rounding, per-term truncation before summation, saturation, and maximum selection on the last native-memory byte.135/135 cases match bounded scalar original PPC execution (including128 seeded random cases), recorded in paint-remap-verification.json. Three unit tests pass;14 total material recovery tests pass. This interface deliberately does not equate native numeric word bytes with standard PNG RGBA or produce final skin images. The ABI-specific pixel adapter and canonical source palette still need proof.

The force-PREVINYL global804388E4 has original file offset4358E4 and static value0. Four original loads were identified at802D23B8,802DEFD8,802E1A34 and802E1D60. No direct non-SDA stores were found in the displacement scan; this is not proof that indirect/bulk runtime mutation is impossible. Presetbyte1 alone therefore does not prove the final file branch irrespective of the override.

previnyl-rgb-diagnostic.png plots original RGB with stored alpha ignored only for inspection: PRECOM_TEST contains flame/checker stripes, and both PRECOM_FLAM entries contain generic flames on colored backgrounds. TexInfo for each is alpha_test_mode2/blend_mode1. Their original bytes and decoded PNGs remain unchanged. No hero BMW livery selection was inferred from this diagnostic.


## Source normals and original car base-state checkpoint

Original GX VAT2 setup8010E458..46C explicitly uses NRM/XYZ/S8/6fractionalbits.80116D74..90 sets normal pointer to geometryblob+metadataoffset10;801170AC..BC binds it with4-byte stride. Candidate source normals are therefore actual original consumer data.

New material_recovery_car_render.py exports all23112expanded source normals with exact existingv0.9 position+UVbyte matches, batch/texture order checks and per-corner provenance. Fitted left wheels receive the same180degree source-Z rotation as their current positionfit; no normalization/smoothing is invented. normals-f32le.bin SHA c4d2909a448aa16666077964250cafad74cbff6aae267230d48d54f078eda499. The manifest pins source and referenceCRC/fullSHA. Root owns any cloned scene normal patch and wheelrig CRC update.

The same exporter now retains original raw material references and16-byte strip descriptors. shaders/original-car-material-runs.json contains1257source-strip/facecontinuous intersections with existingNFMbatches, covers every vertex exactly and preserves shader/referenceword1, geometryflags and original source offsets. This is provenance, not a recommendation for1257PICA drawcalls. Original-car-material-catalog.json retains all156materialrecords with raw bytes and numeric offsets. Basepaint originalattribute6BA02C05 selects METPAINTSILVER93C0EAF6; draw802CD2DC..2F0 substitutes that material for geometryCARSKIN D6D6080A.

Bounded original material cache capture80109C04..8010A364 yields all156record caches under original executable staticdefaults, without replacing arithmetic instructions. HEADLIGHTGLASS additionally reads runtime-context defaults8041B144/148/14C, retained explicitly. Other cache word meanings are not guessed. Scalar-region entry/exit omit only paired-single ABI save/restore context. This is original coefficient capture, not a completed TEVshader.

shaders/original-gc-car-base-state.json records original firstlit-channel/baseTEV facts: three-light mask7, diffuseCLAMP, attenuationNONE, registerambient/material, alpha lightingdisabled, baseTEVtexture×rasterRGB and texturealpha×constantalpha. Actual3light/ambient inputs come from runtime arrays filled by8010A788 and are not replaced by a new guessed sun direction. Gloss/reflection/environment coordinate routing and finalmaterial coefficient consumers remain open.21material tests pass.
