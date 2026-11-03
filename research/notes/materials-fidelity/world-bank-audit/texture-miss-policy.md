# Original GameCube model texture misses

The original USA DOL registers the original GLOBAL/DEFAULTALPHA resource (hash
`66994f4a`) as its final texture-lookup fallback. This is an actual original
texture and policy, not a synthesized replacement or a new alias for a missing
hash. The requested hash and returned/effective resource identity must remain
separate in the port.

## Exact consumer and precedence

- Model loader `800F824C` calls fixup `800F6E10`; the latter passes each hash to
  `800FD4A0` with fallback enabled (`r4=1`, `r5=0`) at `800F6E58..6C` and stores
  the returned resource pointer into reference word1. The source word1 alone is
  therefore not a permanent source texture identity.
- Lookup first checks fast cache `8046B20C` (validating TexInfo key at+24),
  then ordinary texture-bank list `8046284C`, then the 17 standard render-target
  descriptors (`800FFC1C`/`800FFEAC`/`800FFC04`), then streaming aliases
  `800F4CCC` (`8041A5E0` count, `8046A6E8` keys, `8046A670` resources).
- Only a final miss reaches `800FD584..598`: fallback enabled returns global
  `8041AB74`; disabled returns NULL. Resource registration `800FC670..688`
  populates that global on the exact key `66994F4A`.

## Exact source provider

Original file: `/workspace/attachments/85875135-c339-4aea-9553-be7e652717b8/GLOBAL-GLOBALB.BUN`.
SHA256 `b1329f35739503b13cff4838766f511b1f5e8fec28d37112da9efbc63cb0438a`.
Complete GLOBAL TPK offset0, length174464; keytable entry offset548, source
reference word1=0. DEFAULTALPHA is8×8 C4, native image offset111232,
32 image bytes and512 palette bytes. Its decoded64 pixels are allRGBA(0,0,0,0).
Original TexInfo alpha_test_mode=2 and blend_mode=2 (SRCALPHA/ONE). Preserve the
original material state; this is not an opaque white/gray replacement and does
not justify dropping its model or its other material runs.

Canonical unmodified RGBA: `defaultalpha/66994f4a.rgba`, SHA256
`5341e6b2646979a70e57653007a1f310169421ec9bdd9f1a5648f75ade005af1`.
`defaultalpha/manifest.json` records the original source metadata.

## Bounded execution and limits

`tools/material_recovery_texture_lookup.py` executes the unmodified original
lookup, fixup, standard-render-target scan and empty-streaming scan, with checked
code/write bounds. It neither patches code nor stubs the scanner. The explicit
fixture has9 actual Tireshop keys in the original cache, no ordinary banks,
no matching render-target keys, zero streaming aliases, fixup guard0 and the
registered original default pointer. All11 Tireshop fixup results match;
14 direct cases include both fallback modes for all6 currently unresolved
hashes plus a cache-hit control. See `original-texture-lookup-reference.json`.

This proves final-miss behavior under that explicit registry state. It does not
prove that the original live game never generates the requested resources.
Original render targets or streaming aliases, when recovered, must take
precedence. The port's missing render-target generation remains a visual
fidelity limitation; a successful original-policy fallback does not close it.

Reproduce from the repository with Unicorn available:

```sh
PYTHONPATH=/workspace/toolchains/python-deps:tools python tools/material_recovery_texture_lookup.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --requested 8de70662 6dc61680 7e2734a8 7e2734a9 8b335c76 61a56b42 c904085c \
  --known c904085c c95fe138 9ebb788a 764dea79 438cc032 d85a1224 b72aa8d3 c567bac7 fd8270ee \
  --model-keys c904085c c95fe138 9ebb788a 764dea79 438cc032 d85a1224 b72aa8d3 c567bac7 7e2734a8 7e2734a9 fd8270ee \
  --output /tmp/original-texture-lookup-reference.json
```
