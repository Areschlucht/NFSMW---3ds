# Original free-roam destinations and event entry points

This is a strict source-data export and bounded original dispatcher reference.
No shared runtime source, SDK build, shop economy or teleport was implemented by
this subtask. Original inputs remain unchanged/private.

## Concrete source locations

`tools/free_roam_destinations.py` reloads the pinned original packed GAMEPLAY
through GameplayPackages and the strict original ATTRIBUTES schema. It does not
trust destination coordinates or strings from an edited cached JSON file.
Every selected field's original byte range is independently matched to the
pinned gameplay file; spatial scalars/vectors and collection references are also
checked against their big-endian typed bytes.

There are three menu-gate owner definitions with actual `ZoneType` values:

- `customshop`: eight concrete zones.
- `safehouse`: four concrete zones (source names1,2,4,5).
- `carlot`: three concrete zones.

These classifications are typed source values, not substring guesses. Owner
field64893DA8 selects the original ordered zone keys; concrete children retain
ZoneType, Position, Radius, BinIndex and scalar reference2241F4CD. That reference
selects an explicit respawn Position/Rotation. The exporter resolves every key
without synthesizing a fifth safehouse or choosing a nearest coordinate.

Example: safehouse1 (DAA53BEF) has source Position
(1777.094970703125,2503.468017578125,147.7935028076172), Radius7 and BinIndex16.
Its explicit respawn ED80F668 has Position
(1762.761962890625,2508.818115234375,147.2841033935547), Rotation-115.41580200195312.
All values retain original source units and basis. For the existing renderer,
source(X,Y,Z) becomes viewer-world(X,Z,-Y) before local-origin subtraction; do
not treat raw sourceY as vertical or label Radius as a proved meter distance.
Original radius/actor overlap, interaction acceptance and pursuit gates remain
separate from a native proximity preview.

## Original frontend action consumers

8014BF68..8014C064 compares object+3C with exact source type strings using the
original case-sensitive strcmp80063034:

| Type | Frontend mode | Actual package |
| --- | ---: | --- |
| safehouse | 2 | MainMenu_Sub.fng |
| carlot | 5 | Car_Select.fng |
| customshop | 3 | CustomizeMain.fng |

The customshop branch additionally obtains the current ride through801645F8
and requires its byte+10 not equal FF before opening the frontend. The table
does not implement inventory, prices, purchases, performance installation,
cosmetic customization or a valid-ride producer by itself.

The bounded ActionReference executes unchanged comparison/branch instructions
against nine source/synthetic strings. It stops at the customshop ride check,
which remains a real precondition rather than being patched away. No emulator
or game state is substituted for that check. Unknown/case-mismatched strings do
not select an action. The original icon selector80162B14 returns carlot4EAEE18B,
safehouse0ED39F69 and customshop0CF07089; these are exact source constants.

Respawn reference2241F4CD is consumed at801C5184..801C51B4 and stored in manager
+114. A conditional safehouse path801C5208..801C522C can also store it at+118.
This is not a complete teleport or safehouse persistence implementation.

## Jump to safehouse is not an arbitrary nearest warp

Script registration801C0098..801C00B0 binds original string JumpToSafeHouse at
803EDF10 to callback801C5F00. That callback obtains the frontend interface through
801EB8D0 and calls801E1170 with mode2 and MainMenu_Sub.fng. There is no position
copy or nearest-safehouse search in that callback.

Thus the directly proved first step is opening the original safehouse frontend.
Saved/selected respawn handling and the later world-return path are separate.
Do not label a guessed nearest-point teleport as recovered original behaviour.
A native frontend shell can preserve this action while remaining explicit that
world transition, career save and respawn integration are not complete.

## Original race-entry hotspots

Fifteen source bin/engage owner definitions have actual RaceTriggers field
58DC14C0 (exact VLT label hash). Its arrays select146 concrete entry triggers.
Each has Position, positive Radius and scalar key277566F3 resolving an original
NumLaps event definition. The exporter retains the source array order, not the
folder's Children order (the orders differ).

Each owner is directly referenced by a source bin's Children916E0E78 array; that
bin's typed BinIndex6CE23062 supplies its original owner index. This uses source
references and values rather than parsing a bin number from a filename. This
ownership alone does not prove an unlock comparison such as <= or >=.

Original trigger initialization8019AF14..8019AF4C reads field277566F3 and resolves
the referenced event through801A4364. Other entry conditions, available-race
sets, event acceptance, actor geometry, source activation and actual race logic
remain integration work. A proximity preview is not an original gate detector.

## Native-ready private format

`/workspace/port-research/free-roam-destinations/catalog.json` contains:

- `destinations`:15 flat records. Keys: key, kind, owner_key, position_source,
  radius_source, bin_index, respawn (key/position_source/rotation_source_degrees),
  original_frontend_mode, original_frontend_package and original field provenance.
- `race_entries`:146 flat records. Keys: key, kind, owner_key, bin_index,
  position_source, radius_source, event_key, event_type_source,
  event_display_source_id and original field provenance.
- `menu_gate_owners` / `race_owners`: authoritative original ordered child arrays.
- Source SHA256, actual consumer addresses and code-window SHA256 values.

No placeholder coordinates, guessed race names, invented unlock threshold or
fabricated shop/safehouse inventory is included. Parent runtime may consume these
records into a bounded native sidecar while retaining the stated limitations.

## Reproduce and checks

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/free_roam_destinations.py \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --gameplay /workspace/port-research/whole-game-metadata-20261103/GLOBAL-GAMEPLAY-at267364352.BIN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --output /workspace/port-research/free-roam-destinations/catalog.json \
 --verify-original --check-rejections
```

Checks cover source SHA/bytes, every selected finite spatial scalar, every typed
key, all direct owner associations, nine original action branches and six rejected
corruptions: changed position, wrong radius bytes, changed respawn/race keys and
wrong GAMEPLAY/DOL sources. Python syntax and scoped whitespace checks pass.
