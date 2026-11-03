# v0.18 prototype build and verification

The private complete ZIP is `/workspace/NFSMW---3ds/dist/nfsmw-rockport-prototype-v0.18.zip`.
It contains all required runtime assets and a per-file SHA256 manifest. Extract
the complete ZIP to the SD root. See ROCKPORT-PROTOTYPE.md for controls and limits.
Original whole-car physics, original chase-camera assembly, complete material
shading and full-city traversal validation remain unfinished.

Build:

```sh
bash tools/build_streamed_rockport.sh TARGET=nfsmw-rockport-v0.18 BUILD=build-v018-release \
 'APP_TITLE=NFS MW Rockport Prototype v0.18' \
 'APP_DESCRIPTION=Streamed Rockport and original collision'
```

Reproduce host checks with `tools/test_streamed_integration.sh`: supply the
private converted scene folder, WST metadata, NWC collision, NRD road/spawn,
source-normal BMW body and MWP scene archive, in that order. Every source file
is compiled with strict warnings, ASan/UBSan and explicit floating-point fusion
control. Archive format tests also cover corruption, range/key errors and the
boot-global provider bank. The full archive reader compares all 17,260 payloads
against their original converted files.

The HUD uses GPU-owned presentation of the complete rasterized canvas. Its
pass clears colour/depth and disables inherited 3D alpha/depth tests. Acceptance
measures actual label pixels across repeated resets and mode transitions;
small screenshot previews alone are insufficient. The mandatory-bank CRC test
checks that loading fails visibly and START returns to the menu.

`v018-validation.json` records identities and check results. These are emulator
and component tests, not physical-console FPS/LCD certification or proof of a
complete original-game simulation. Original game data and the generated ZIP
remain private; Git contains source, tools, tests and authored evidence.
