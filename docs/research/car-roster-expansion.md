# Original car roster expansion

`tools/build_all_cars.py` covers all83geometry packages reconstructed from the
supplied USA archives. The validated private output is
`/workspace/port-research/all-native-cars/v3`. It contains69complete native stock
mesh adapters,318144triangles and1213real texture bindings. Every native NFM/NWA
and catalog entry passed the production readers under ASan/UBSan; every indexed
vertex reconstructs its original48bytes exactly, including after the renderer's
UV flip. Every converted texture pixel was compared with Tex3DS output.

The unchanged root BMW preview is deliberately retained separately by staging:
its current reconstructed livery is more complete than the stock flat-paint
adapter in this exporter. The expanded69include35source PlayerUsable models.
Together with that root BMW,36player models are available as render assets.
This does not imply original per-car physics, saved preset customization,
engine sounds, damage, career unlocks or ownership are complete.

Original source pvehicle.MODEL and PlayerUsable fields, with offset/raw-byte/
SHA256 provenance, are exported in `coverage.json`. NVC1/version2 retains the
160byte record and uses recordoffset20 bit0 for this verified PlayerUsable fact;
all other bits are zero. This is separate from frontend pricing keys and from
career ownership. Version1 remains byte-compatible when no flags are emitted.
For example CARRERAGT is genuinely PlayerUsable even though its model/pvehicle
name does not match the original frontend `carrera_gt` name. The exporter does
not invent a frontend key to make it appear purchasable.

Geometry uses the previously original-emitter-checked B/C offline LOD exports,
rechecks each chosen descriptor against original package bytes, and selects
intact KIT00 parts. Police packages use actual DAMAGE0 exteriors. Rejected
nonempty exterior parts fail the whole candidate; explicitly listed rejected
*driver-only* parts are outside the static-exterior scope. No replacement car,
hole hidden as successful exterior, or placeholder texture is emitted. The
original front tire mesh is still instanced at source mounts and documented as
an assembly adapter; exact rim/kit consumers remain separate.

The native artwork normalizer accepts an explicit16metre halfextent limit for
large vehicles, while the actual largest accepted model is6.636474609375metres.
Five large SEMI/firetruck/trailer assets are now accepted in addition to the
first64. An outlying mesh is not automatically treated as a large legitimate
car: source CAYMANS rear side windows lie at lateral±9.22metres, so its original
part transform/admission must be recovered before that vehicle can be accepted.

Fourteen source candidates remain blocked:

- BMWM3GTRE46 stock conversion has an unresolved material; the existing root BMW
  remains available, so this is not a missing player model in the staged app.
- CAYMANS: two source rear side window transforms/admission remain unresolved.
- DB9: source B-LOD front-right window has inverted model bounds and was rejected
  by the strict exporter. No window is silently omitted.
- COPHELI: no four-wheel ground-vehicle rig; requires a helicopter renderer.
- COPMIDSIZEINT: separate interior package has unresolved material binding.
- TRAF4DSEDB,TRAFAMB,TRAFCAMPER,TRAFDMPTR,TRAFMINIVAN,TRAFPIZZA,TRAILERA,
  TRAILERB,TRAILERLOG: unresolved material aliases. Several are exact CAR_TIRE
  aliases without that texture in their local banks; the original default tire
  binding must be recovered rather than borrowing another car's artwork.

Thus only CAYMANS and DB9 are missing source PlayerUsable model conversions after
preserving the existing BMW. The coverage manifest records exact failure reasons
and every original source fingerprint, including non-player vehicles.

Reproduce using a NEW output directory (native cache reuse checks body/rig hashes
and each texture's original RGBA hash; original inputs are never overwritten):

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python3 tools/build_all_cars.py \
 --meshes /workspace/port-research/car-model-expansion-v2 \
 --candidates /workspace/port-research/all-car-candidates \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --carparts /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
 --frontend /workspace/attachments/430e54cf-3f7e-4284-81a1-67743e30a796/GLOBAL-FE_ATTRIB.BIN \
 --shared-textures /workspace/port-research/bmw/shared \
 --shared-textures /workspace/port-research/bmw/wheels \
 --shared-textures /workspace/port-research/shared-textures/globalb \
 --output /workspace/port-research/all-native-cars/fresh-output \
 --reuse-native /workspace/port-research/all-native-cars/v3 --native-textures
bash tools/test_car_roster.sh /workspace/port-research/all-native-cars/fresh-output
```

Source-palette flat paint and stock part selection remain explicitly native
preview policies. This work does not claim the whole original vehicle/material
renderer is complete, nor that all packages are converted. Original/converted
payloads and decoded mesh caches remain private; only authored tools/tests/notes
belong in Git.
