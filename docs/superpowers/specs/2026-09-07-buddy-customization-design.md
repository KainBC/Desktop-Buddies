# Desktop Buddies — Buddy Customization

## Summary

Let people build their own buddy before joining a room, watching it animate in
a **live preview** as they choose. In this phase exactly two things are
customizable: the **body type** (shape) and the **skin color**.

The point of the phase is not the two controls. It is the **layer seam**
underneath them. Today a character is a folder of flat, pre-colored PNGs and
its color is baked into the art. This replaces that with a small compositor:
an appearance resolves to an ordered list of tinted layers, drawn back to
front. Body and skin are the first two. Hair, outfits, and shoes are added
later by appending to that list — no re-architecture, and no relay change at
all.

Appearance is chosen at the menu and locked in for the session.

## Goals

- Animated preview of your buddy in the launch menu, updating as you edit.
- Choose a body type and a skin color; see both immediately.
- Composite sprites from independently tinted layers at load time.
- Reserve the slots and draw order for hair, outfits, shoes, and faces now, so
  later art drops in without renumbering or restructuring.
- Discover the options for a slot by globbing the filesystem, so importing new
  art requires no code change.
- Remember name and appearance between launches.
- Degrade gracefully when an appearance carries fields this build doesn't know.
- Keep appearance logic pure and headless-testable, matching the existing split
  between logic and Qt.

## Non-Goals

- **No mid-session editing.** Appearance is fixed once you create or join a
  room. Changing it means leaving and rejoining. There is therefore no
  appearance message on the wire.
- **No hair, outfits, shoes, or face selection.** The slots, the draw order,
  and the discovery mechanism exist; the art and the controls do not.
- **No generic slot-driven UI.** The panel gets two concrete controls. A
  control factory for slots with no art yet would be speculative.
- No arbitrary color picking — skin is chosen from a fixed palette.
- No per-buddy naming, no accessories, no animations beyond the existing
  `idle` and `walk`.
- No syncing profiles across machines; the saved profile is local.

## Design Decisions

Four choices shape everything below.

**Color is a tint, not art.** Today `tools/make_placeholder_sprites.py` bakes
an orange cat and a blue dog into the PNGs, so color and shape are the same
axis and cannot vary independently. Instead, body art is authored as a white
silhouette and tinted at load. Skin color becomes data, and one body type
serves every skin tone.

**Today's fields are tomorrow's fields.** Shape becomes **body type** and color
becomes **skin color** — the base layer everything else is later drawn on top
of. Nothing chosen in this phase is discarded when feature sprites arrive.
Buddies are humanoid; the existing cat/dog/blob placeholders are retired.

**One function knows what a layer means.** `resolve_layers()` turns an
appearance into an ordered list of layer specs. The compositor, the preview,
and `SpriteWindow` consume that list without knowing whether a layer is a torso
or a hat. Adding hair later changes this function and nothing downstream.

**Unknown fields are ignored, missing fields default.** Applied identically to
the wire and to the saved profile. A future client that sends `hair` to an
un-upgraded peer renders a bald buddy rather than crashing, and an old profile
missing `skin` loads with the default tone.

## Appearance

A frozen dataclass in a new `Src/appearance.py`, with no Qt import:

```
Appearance:
    body: str    # body type id, e.g. "round"
    skin: str    # hex color, e.g. "#e8b48c"
```

Both fields have module-level defaults, so `Appearance()` is always a valid,
renderable buddy. `to_dict()` produces the wire and on-disk form. `from_dict()` drops keys it
does not recognize and substitutes defaults for keys that are absent; it never
raises on unexpected input. Every future slot is added here as an optional
field with a default, so the tolerance rule keeps holding.

`Src/User.py`'s `PlayerIdentity` swaps `character: str` for
`appearance: Appearance`.

## Sprite Layout

The tree reorganizes around slots, using the directories already stubbed out in
`Sprites/`:

```
Sprites/manifest.json
Sprites/Bodies/<body>/<anim>/<n>.png     white silhouette, tinted by skin
Sprites/Faces/<face>/<anim>/<n>.png      untinted; only "default" exists
Sprites/Hair/<style>/<anim>/<n>.png      empty this phase
Sprites/Outfits/<name>/<anim>/<n>.png    empty this phase
Sprites/Shoes/<name>/<anim>/<n>.png      empty this phase
```

`<anim>` is `idle` or `walk`, as today. The per-character `sprite.json` is
replaced by one `Sprites/manifest.json`, which carries the animation `fps` and
`scale` that `sprite.json` held — read once at startup rather than per
character, since a composited buddy has no single owning character folder — and
declares the slots:

| Slot | z | Directory | Tintable | Required |
|------|---|-----------|----------|----------|
| body | 0 | `Bodies` | yes | yes |
| shoes | 10 | `Shoes` | yes | no |
| outfit | 20 | `Outfits` | yes | no |
| face | 30 | `Faces` | no | yes |
| hair | 40 | `Hair` | yes | no |

Draw order is back to front by `z`. The gaps of ten leave room to insert slots
without renumbering. Faces are untinted for now; the manifest is where that
changes if faces later take their own color.

**Options are discovered, not declared.** The choices for a slot are the
subdirectories of its directory. Dropping in `Sprites/Hair/spiky/` creates that
style. This is what makes importing art later a content change rather than a
code change.

## Layers and Compositing

`Src/layers.py`, pure and headless:

```
LayerSpec:
    frames_dir: Path
    tint: str | None
    z: int

resolve_layers(appearance, sprites_dir) -> list[LayerSpec]
```

`load_manifest(sprites_dir)` parses the manifest once and is the sole reader of
it; `SpriteWindow` takes `fps` from there instead of from a per-character
`sprite.json` (`Src/sprite_window.py:53`).

`resolve_layers` reads the manifest, and for each slot resolves the appearance's
choice for it to a directory. A slot with no choice, or whose chosen directory
is absent, contributes no layer — which is why the three empty slots cost
nothing today. The result is sorted by `z`.

Compositing lives with the Qt code in `Src/sprite_window.py`, replacing
`load_frames`. For each frame index it starts from a transparent pixmap and
draws each layer in order. A tint is applied by filling the layer with the
color under `CompositionMode_SourceIn`, which preserves the alpha channel and
replaces RGB — correct for the flat art in this phase. Shaded art later would
switch to Multiply over a greyscale source; the manifest's `tintable` flag is
where that distinction would grow a mode.

Layers may differ in frame count. The body's count is canonical, and a shorter
layer indexes into its own frames modulo its length, so a two-frame accessory
rides a four-frame walk without special-casing.

Compositing happens once when a `SpriteWindow` is constructed, exactly as
`load_frames` does today — never per tick. The preview recomposites on each
edit, which is cheap at preview size.

## Interface

`Src/customizer.py` holds two widgets.

`PreviewWidget` draws the composited buddy playing its `idle` loop, reusing
`FrameCycler` so preview and sprite share one animation clock. `set_appearance()`
recomposites and restarts the cycler.

`CustomizerPanel` stacks the preview above a body-type selector and a row of
skin-tone swatches, and emits `appearance_changed(Appearance)`. Body types come
from slot discovery; swatches come from a fixed palette constant. Skin is a
preset palette rather than a free color picker so buddies stay visually
coherent, and so the control still makes sense when it is one of five slots.

`Src/menu.py` embeds the panel where the three character radio buttons are
today (`Src/menu.py:31`). The name field, the create button, the join row, and
the status label are unchanged. When a later phase adds hair and outfits, their
controls are added to this panel.

## Persistence

`Src/profile.py` reads and writes `{"name": ..., "appearance": {...}}` as JSON.
Load and save take an explicit path so they test without touching the real
config directory; `Src/app.py` supplies the platform path via Qt's
`AppConfigLocation`.

A missing file, unreadable file, or malformed JSON yields defaults rather than
an exception — a broken profile must never prevent the app from starting. The
appearance is parsed through `Appearance.from_dict`, so an old profile
inherits its unknown-key and missing-key tolerance for free.

The profile is saved when a room is created or joined, which is the moment the
appearance is locked in.

## Wire Format

`character` becomes `appearance` — a dict rather than a string — in
`create_room`, `join_room`, `member_joined`, and the member list returned by
`room_joined`.

The relay does not gain any logic. `Registry._public` copies the field opaquely
(`relay/room.py:31`), and that stays true when the dict grows hair and shoes.
This is the property worth protecting: **every future customization phase is a
client-only change.**

This is a breaking wire change with no compatibility shim. Client and relay
ship together and rooms hold no persisted state, so a coordinated deploy is
sufficient.

## Testing

Following the existing convention that logic tests run headless and Qt is
touched only in thin smoke tests:

- `tests/test_appearance.py` — dict round trip, unknown keys dropped, missing
  keys defaulted, malformed input yielding defaults.
- `tests/test_layers.py` — draw order sorted by `z`, tint applied only to
  tintable slots, a slot with no art contributing no layer, an absent chosen
  directory contributing no layer.
- `tests/test_profile.py` — save/load round trip, missing file, corrupt JSON,
  and a profile carrying an unknown appearance field.
- `tests/test_menu.py` — updated for the panel; editing emits
  `appearance_changed` and create/join carry the current appearance.
- `tests/test_sprite_frames.py` — extended with a compositing smoke test under
  the offscreen platform, asserting a tinted pixel and layer order.

Existing tests that pass `character` — `test_room.py`, `test_server.py`,
`test_connections.py`, `test_smoke.py`, `test_menu.py` — are updated to pass an
appearance dict.

## Tooling

`tools/make_placeholder_sprites.py` is rewritten to emit the new tree: white
body silhouettes under `Sprites/Bodies/` in three body types, and an untinted
eyes-only face under `Sprites/Faces/default/`. It keeps drawing procedurally
with QPainter, so the project still needs no external art. The old
`Sprites/placeholder_{cat,dog,blob}/` folders are deleted.

## Scope Note

This phase touches the wire format, the sprite tree, the placeholder
generator, and five existing test files. It is not a contained change. The
compensating benefit is that the phases after it are: adding hair, outfits, and
shoes means art, one function, and one panel — no protocol work and no relay
work.
