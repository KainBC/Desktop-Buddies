# Desktop Buddies — Web Frontend

## Summary

A small marketing site for Desktop Buddies: a landing page that explains what
the product is and shows it off with live, pokeable sprites, plus a download
page that is honest about the fact that packaged installers do not exist yet.

The site lives in `desktop-buddies/` — a Next.js 16 / React 19 / Tailwind 4 app
created by `create-next-app` and currently untracked. Today it holds two
placeholder pages (`<h1>Header</h1>` and `<h1>Download</h1>`). This spec covers
turning that scaffold into the real thing.

The site is a **separate deliverable from the desktop client**. It shares the
client's sprite art and copies its animation feel, but imports no Python, talks
to no relay, and has no build-time dependency on the rest of the repo.

## Goals

- Explain Desktop Buddies to someone who has never seen it, in one scroll.
- Demonstrate the product rather than describe it: real sprite frames idling,
  walking, and hopping when clicked, using the same easing as the app.
- Give visitors a download page structured for real installers, so shipping a
  build later is a URL swap rather than a redesign.
- Keep the page usable and complete before JavaScript hydrates.
- Keep the animation simulation pure and headless-testable, mirroring the
  client-side convention of separating logic from rendering.
- Stay honest: no invented download counts, testimonials, or user numbers.

## Non-Goals

- No login, accounts, analytics, or any backend. The site is static.
- No waitlist or email capture — that would require a form backend.
- No browser-based buddy that joins a real room over the relay. The hero is a
  local simulation and never opens a WebSocket.
- No documentation site (relay hosting, protocol, troubleshooting). Deferred.
- No new sprite art. The site uses the existing placeholder characters.
- No blog, changelog, or release-notes page.

## Design Decisions

Four choices shape the rest.

**The page is framed as a desktop window.** The hero sits inside faux window
chrome — a title bar with three traffic-light dots — and the buddies wander
along a floor line at its bottom edge. The product is a translucent
always-on-top window with sprites pinned to the floor, so the site's chrome is a
picture of the thing itself rather than decoration.

**The simulation is pure TypeScript, separate from React.** `lib/buddy.ts`
contains no React and touches no DOM, exactly as `Src/world.py` and
`Src/poke.py` contain no Qt. This is what makes the animation unit-testable
headless, and it keeps the two codebases legible to each other — someone who has
read `OwnController` can read `Stage`.

**Buddies are DOM nodes, not canvas.** Three or four 64px sprites is far below
the point where canvas earns its cost, and DOM gives real click targets,
keyboard focus, `aria-label`s, and Tailwind styling for free. Canvas would mean
hand-rolling hit testing and accessibility for no gain at this scale.

**The download page is built for installers that do not exist yet.** The primary
button is present, OS-labelled, and visibly marked coming soon; the run-from-
source path underneath is what actually works today. This is the honest version
of a real download page rather than a placeholder that has to be rebuilt.

## Scaffold Fixes

The generated scaffold has two defects that this work corrects rather than
builds on top of.

`app/layout.tsx` renders `<nav>` as a sibling of `<body>` inside `<html>`, which
is invalid HTML; imports `Metadata`, both Geist fonts, and `Welcome` without
using any of them; and omits `lang` on `<html>`. It is rewritten to a correct
root layout with real `metadata`, the fonts wired to the CSS variables that
`globals.css` already references (`--font-geist-sans`, `--font-geist-mono`), and
all markup inside `<body>`.

`app/page.tsx` imports `RootLayout` and wraps its own content in it. Next
applies the root layout automatically, so this nests a second `<html>` document
inside the first. The page is rewritten to return only its own content.

The palette in `globals.css` is kept: teal `#568889` on white, inverting to
white on `#222f34` in dark mode. It is extended with the tokens the design needs
(surface, border, muted text, accent) rather than replaced.

Both themes are supported, following the visitor's `prefers-color-scheme` as the
scaffold already does. There is no theme toggle. Every colour is defined as a
token in `:root` and redefined in the dark media query, so no element gets its
only definition inside one theme.

## Page Structure

### `/` — landing

One scrolling page. Bands are full-width; content is capped at `max-w-5xl`.

1. **Window chrome + hero.** Title bar with traffic-light dots and the wordmark.
   Headline, one-line subhead, and two buttons — *Download* (to `/download`) and
   *GitHub* (`https://github.com/KainBC/Desktop-Buddies`, the repository's
   `origin`, used for every GitHub link and the clone instructions). Along the
   bottom of the frame, a floor line with three buddies wandering on it and a
   quiet hint to click one.
2. **What it is.** Two sentences, no jargon.
3. **Feature cards.** Three cards — walks around, chat bubbles, pokes — each
   with a sprite motif. Chat and pokes are described as they behave today.
4. **How it works.** Three steps: install, share a room code, they show up.
5. **Closing CTA.** A single download button.
6. **Footer.** GitHub link and attribution.

### `/download`

Same window chrome, much shorter.

1. **Primary button**, labelled for the visitor's platform (*Download for
   macOS*), visibly marked coming soon and non-functional.
2. **All platforms** — macOS `.dmg`, Windows `.exe`, Linux `AppImage` — at
   placeholder URLs collected in one constant, so shipping real builds is a
   single-file edit.
3. **Run from source**, the path that works today: Python 3.11+, `git clone`,
   `./run.sh setup`, `./run.sh client`, and pointing `BUDDIES_URL` at a relay.
4. **Notes.** The global hotkey (⌘⇧B / Ctrl+Shift+B) and `BUDDIES_NO_HOTKEY=1`.

## Architecture

```
desktop-buddies/
  app/
    layout.tsx          root layout (rewritten)
    page.tsx            landing            — server component
    download/page.tsx   download           — server component
    globals.css         palette tokens + pixelated rendering
  components/
    WindowFrame.tsx     title bar + traffic lights          (server)
    BuddyStage.tsx      rAF loop, renders and pokes buddies (client)
    DownloadButton.tsx  OS-labelled primary CTA             (client)
    FeatureCard.tsx     one feature card                    (server)
    Steps.tsx           how-it-works list                   (server)
    Footer.tsx          footer                              (server)
  lib/
    buddy.ts            pure simulation — no React, no DOM
    characters.ts       character manifest (frames, fps)
    os.ts               pure userAgent -> platform
  public/sprites/<character>/{idle,walk}/<n>.png
```

Only `BuddyStage` and `DownloadButton` are client components. Every other piece
of the page is static server-rendered markup.

### `lib/buddy.ts` — the pure core

Ported from `Src/world.py` and `Src/poke.py`, keeping the same names and the
same units.

- **`FrameCycler(count, fps)`** — `advance(dt)` accumulates time; `frame`
  returns the current index, wrapping at `count`.
- **`Hop(height, duration)`** — `advance(dt)`, `offset()` returning
  `height * Math.sin(Math.PI * elapsed / duration)`, `done` once `duration`
  elapses, and `reset()`. `offset()` clamps to `0` past `duration` rather than
  letting sine go negative. This is a direct port of `Src/poke.py`, arc and
  defaults included.
- **`Buddy`** — `{ id, character, x, facing, state }`, where `x` is fractional
  `0.0`–`1.0`, `facing` is `1` or `-1`, and `state` is `"idle"` or `"walk"`.
- **`Stage`** — owns the buddies and the hops. `tick(dt)` runs the same decision
  loop as `OwnController`: hold a state for a randomised beat, then pick again;
  while walking, advance `x` at a fixed fractional speed and flip `facing` at
  the edges. It also advances every frame cycler and hop, dropping hops that
  report `done`. `poke(id)` creates a hop for a known id or resets the existing
  one so a second poke restarts the arc instead of stacking; unknown ids are
  ignored. `hopOffset(id)` returns `0` when there is no active hop.

`Stage` takes an injectable rng (defaulting to `Math.random`) so tests are
deterministic rather than flaky.

Coordinates are fractional on purpose, matching the wire and world conventions
of the desktop client. Pixels appear only at render time.

### Rendering and data flow

`BuddyStage` constructs a `Stage` on mount and drives it from
`requestAnimationFrame`. Each tick it computes `dt`, calls `stage.tick(dt)`,
then writes each buddy's `transform` and frame `src` directly onto its node
through a ref.

React renders the buddy list exactly once. Per-frame updates never touch React
state — sixty re-renders a second to move three sprites would be absurd — so the
animation is DOM writes against stable nodes.

Fractional coordinates become pixels against the stage element's measured box:
horizontal position from `x`, and the hop subtracted from the vertical so that
hopping up is a smaller `y`, exactly as `AppController._tick` does it.

Each buddy renders as a `<button>` with an `aria-label`, so poking works by
click and by Enter/Space, and the sprite is announced rather than being a
decorative div.

### Assets

The sprite frames live in `Sprites/` at the repository root, outside the Next
app, and Next serves static files only from `desktop-buddies/public/`. The three
placeholder characters are copied to `public/sprites/` and committed. They are
six small PNGs per character and the art is a placeholder anyway, so a sync
script would be more machinery than the problem deserves. When real art lands,
the copy is refreshed in the same commit.

`characters.ts` records each character's frame counts and fps — `idle` 2 frames,
`walk` 4 frames, 6 fps, read off `sprite.json` — so the loader never guesses at
what exists on disk. Frames are preloaded on mount so the first walk cycle does
not flicker. `image-rendering: pixelated` in `globals.css` keeps the 64px art
crisp when scaled up.

## Module Map

| File | Change |
|------|--------|
| `app/layout.tsx` | Rewrite: valid document, `lang`, real metadata, fonts wired. |
| `app/page.tsx` | Rewrite: landing page, no self-wrapped layout. |
| `app/download/page.tsx` | Rewrite: download page. |
| `app/globals.css` | Extend palette tokens; pixelated image rendering. |
| `components/WindowFrame.tsx` | New — faux window chrome. |
| `components/BuddyStage.tsx` | New — rAF loop, buddy rendering, poke handling. |
| `components/DownloadButton.tsx` | New — OS-labelled CTA. |
| `components/FeatureCard.tsx` | New — one feature card. |
| `components/Steps.tsx` | New — how-it-works list. |
| `components/Footer.tsx` | New — footer. |
| `lib/buddy.ts` | New — `FrameCycler`, `Hop`, `Buddy`, `Stage`. |
| `lib/characters.ts` | New — character manifest. |
| `lib/os.ts` | New — userAgent to platform. |
| `public/sprites/**` | New — copied placeholder frames. |
| `package.json` | Add `vitest` dev dependency and a `test` script. |

One new dev dependency: `vitest`. Nothing new at runtime.

## Error Handling & Edge Cases

- **Stage not yet measured.** Buddies stay hidden until the first layout tick,
  so nothing flashes at the left edge before positions are known.
- **Backgrounded tab.** `dt` is clamped to a maximum (~0.1s), so returning to a
  tab after a minute advances one ordinary frame instead of teleporting every
  buddy across the stage.
- **Missing sprite file.** A buddy whose image fails to load removes itself via
  `onError` rather than rendering a broken image.
- **`prefers-reduced-motion`.** No wandering and no idle cycling; buddies stand
  still. They still hop when poked, because that is a direct response to the
  visitor's own click rather than ambient motion.
- **No JavaScript, or before hydration.** The headline, copy, and buttons are
  server-rendered and complete. The stage is progressive enhancement, and the
  hero reserves its height either way so nothing shifts when it appears.
- **OS detection fails**, or the visitor is on a phone: the primary button falls
  back to a neutral "Download" label, and the full platform list below is
  unaffected. Detection runs after hydration and the button server-renders in
  its neutral state, so there is no hydration mismatch and no flash of the wrong
  platform.
- **Window resize.** The stage remeasures and positions recompute from the
  fractional coordinates, so buddies stay proportionally placed rather than
  drifting off the edge.

## Testing

**Unit tests (Vitest, node environment — `lib/` touches no DOM):**

- `Hop` — ground at both ends, peak at `height` midway, symmetric, clamped to
  `0` past `duration`, `reset()` restarts. Mirrors the assertions in
  `tests/test_poke.py` so the two ports cannot drift apart silently.
- `FrameCycler` — advances at `fps`, wraps at `count`, holds frame 0 before the
  first interval elapses.
- `Stage` — buddies stay within `0.0`–`1.0`; `facing` flips at the edges; state
  transitions occur under a seeded rng; `poke` creates a hop for a known id,
  resets rather than stacks on a second poke, and ignores unknown ids; `tick`
  expires a hop after `duration`; `hopOffset` returns `0` with no active hop.
- `os.ts` — a table of representative user-agent strings mapping to the right
  platform, and unknown strings mapping to `null`.

Components are not unit tested. Their verification is `npm run lint`,
`npm run build`, and looking at the pages in a browser — a snapshot test of
marketing markup asserts nothing worth breaking the build over.

Written test-first, as the Python side is.

## Open Considerations (not blocking)

- **Deployment** is unresolved. The site has no server needs, so Vercel or a
  static export to any host both work. Worth settling before the first real
  release, not before the first commit.
- **Real installer URLs** are collected in one constant specifically so that
  shipping builds is a single-file edit.
- **Sprite art.** The site inherits whatever `Sprites/` holds. When the real
  characters replace the placeholders, `public/sprites/` and `characters.ts`
  are refreshed together.
- **Docs.** Relay hosting, room codes, and troubleshooting have no home yet. A
  `/docs` section is the natural next addition once someone other than the
  author needs to run a relay.
- **Buddy count** in the hero starts at three and is a tuning knob, not a
  constraint of the design.
