# Original trigger constructor and notification consumers

This is read-only recovery of the supplied USA GameCube DOL. No SDK build,
3DSX, runtime change or original input edit was made. The evidence below does
not yet justify a complete checkpoint hit detector.

## Proven constructor chain

Original constructor `8019A8D8` reads source Position (`9f743a0e`), Rotation
(`5a6a57c6`), Dimensions (`6d9e21ad`), Radius (`39bf8002`) and Width (`5816c1fc`).
These labels match the exact schema hashes, and the matching immediates occur in
this constructor's attribute reads through `80057250`.

- Rotation is negated and multiplied by the float32 constant `1/360` at
  `803EC3B0`, then passed to matrix routine `80191A50`. Its trigonometric helper
  `80191774` multiplies by float32 `2*pi` from `803EB2F0` before sin/cos calls.
  Thus the source Rotation is in degrees; the internal rotation operand is
  negative turns. Do not use raw degrees as radians.
- Position `(x,y,z)` becomes the internal shape position `(-y,z,x)` in
  `8019AB18..8019ABA0`.
- Dimensions `(dx,dy,dz)` become shape parameters `(dy,dz,dx)` in that window.
  The Dimensions path computes a square-root operand equivalent to
  `0.25*(dx*dx + dy*dy)` with the original single-precision operation order at
  `8019AC68..8019AC98`. This is a broad-phase radius calculation, not a recovered
  box containment inequality.
- Later `8019ADA0..8019ADD8` doubles the middle parameter into object+3C.
  Since that is `2*dz`, while the horizontal broad-phase uses quarters of
  squared horizontal dimensions, do **not** label all three source Dimensions
  uniformly as half extents or full extents without the narrow-phase consumer.
- The Radius path takes precedence over Dimensions at `8019AC34..8019AC60`.
  It doubles Radius into all three shape parameters and sets another shape-kind
  code. Width is a further fallback when Radius and Dimensions are absent.
  A universal dimensions-only box is not justified for every trigger definition.

The internal shape basis differs from the existing renderer's VIEWER basis
`(sourceX,sourceZ,-sourceY)`. Preserve source coordinates in the route pack.
Applying the internal permutation directly to render coordinates would introduce
another rotation and move trigger positions incorrectly.

## Bounded original execution

`tools/race_trigger_reference.py` executes three unchanged scalar constructor
windows with bounded instruction and write ranges. It compares float32 bits for
position/dimension permutations, degree scaling and the box square-root operand.
All **1,948 cases match**: **1,944** distinct spatial inputs from actual checkpoint,
start/finish nodes plus four synthetic signed/axis/zero cases. The referenced
catalog was separately verified by `race_story_export.py`; these checks validate
constructor arithmetic rather than the entire attribute lookup or race consumer.

The reference does not execute the square-root function, complete matrix/trig
path, shape registration or actual collision query. No approximation is called
an original point/segment gate detector.

## Membership and notification flow

`8019B964` treats incoming notification code1 and code2 separately. The exact
code predicates at `8019B980..8019B99C` were checked against **260** inputs.

- Code2 calls `8019BD78`, which finds and removes the supplied object pointer
  from the trigger's membership list at +78/+7C.
- Code1 tests previous membership through `8019BDF0`; when absent, it calls
  `8019BC08`, which inserts that pointer. Additional event messages are posted
  in `8019BA68..8019BB10`.
- The code2 path can also post a message when an additional source Boolean is
  enabled. Do not discard exit notifications or turn every per-frame overlap
  into a new enter event.

The exact physical detector producing these notification codes, message IDs,
vehicle shape, direction requirements and race checkpoint/lap accounting are
still unrecovered. Code1/2 are membership add/remove paths here, not proof that a
particular geometric plane crossing and its normal should generate them.

## Actual start positions already in the catalog

For every catalog candidate that has an ordered checkpoint array and a nonempty
startgrid reference, the rich `startgrid_ref.nodes[0].spatial_fields` includes
Position. The generic reference graph can omit rich spatial fields; use the rich
route node rather than treating that omission as a missing source position.

Examples:

- `race_bin_10/10_2_1_sprint/startgrid`, key `97135115`: Position
  `(1511.823974609375,4404.865234375,209.60450744628906)`, Rotation
  `-198.91690063476562` degrees. Position file offset11392.
- `16_2_1_d_day_intro/startgrid`, key `8508a067`: Position
  `(917.4359741210938,-634.517578125,109.80670166015625)`.

These are source startgrid transforms, not a proven player/opponent slot layout.
Vehicle offsets within the grid and the actual spawn consumer remain a separate
integration gate. Do not invent child positions or assume every racer occupies
exactly the source grid origin.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/race_trigger_reference.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --catalog /workspace/port-research/race-story/catalog.json \
  --output /workspace/port-research/race-triggers/constructor-verification.json
```

Unicorn executes unchanged whitelisted original bytes; instruction budgets and
CPU-write guards reject escapes. Source game data and private catalog remain
outside Git. Before claiming playable original races, recover actual narrow-phase
shape queries, notification production, course direction, event activation,
vehicle grid placement and original lap/finish transition conditions.
