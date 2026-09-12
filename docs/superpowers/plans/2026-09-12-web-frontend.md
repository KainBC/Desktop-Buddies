# Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the untracked `create-next-app` scaffold in `desktop-buddies/` into the real Desktop Buddies marketing site — a landing page with live, pokeable sprites and a download page honest about installers not existing yet.

**Architecture:** Two static server-rendered routes (`/` and `/download`) built from small server components, with exactly two client components (`BuddyStage`, `DownloadButton`). All animation logic lives in a pure, React-free, DOM-free `lib/buddy.ts` ported from `Src/world.py` and `Src/poke.py`, unit-tested headless with Vitest — mirroring the desktop client's convention of separating logic from rendering. Sprite art is baked from the repo's layered `Sprites/` system into flat PNG sequences under `public/sprites/` by a Python tool that reuses the client's own compositor.

**Tech Stack:** Next 16.3 (App Router), React 19.2, TypeScript 5 (strict), Tailwind 4, Vitest (node environment). Python 3.11+ / PySide6 for the sprite bake tool only.

**Spec:** `docs/superpowers/specs/2026-08-29-web-frontend-design.md`

## Note on Assets (amendment withdrawn)

An earlier revision of this plan amended the spec's **Assets** section,
claiming it was stale because the desktop client had moved to a layered,
tinted sprite system. That amendment was wrong **for this branch** and has
been withdrawn.

`web-frontend` forks from `main` at `1019bd3`. The layered sprite system
(`Src/layers.py`, `Src/appearance.py`, `composite_frames()`, and a
manifest-driven `Sprites/` tree) exists only on the unmerged `pokes`
branch. What `Sprites/` actually holds here is exactly what the spec
describes: three flat characters — `placeholder_blob`, `placeholder_cat`,
`placeholder_dog` — each with `sprite.json` (`fps: 6`), 2 idle frames, 4
walk frames, authored at 64x64.

So the spec stands unamended, and Task 5 is the straight copy it always
described. There is no bake tool.

When the layered system does reach `main`, the flat placeholders are
retired and this copy goes stale. At that point the right move is a small
`tools/bake_web_sprites.py` that reuses the client's own `resolve_layers()`
and `composite_frames()` to flatten a fixed set of looks — reusing the
client's compositor rather than porting the layer stack to TypeScript for
three static buddies. That is a follow-up, recorded under **Deferred**.

## Global Constraints

- **Next 16.3.0, React 19.2.8, Tailwind 4, TypeScript 5 strict.** Pin nothing new at runtime; `vitest` is the only new dependency and it is a devDependency.
- **All work happens in `desktop-buddies/`** inside the `web-frontend` worktree at `/Users/kaincorkeron/Desktop-Buddies-web-frontend`. Run every `npm` command from `desktop-buddies/`; run every `python`/`pytest` command from the repository root.
- **Sprite coordinates are fractional floats `0.0`–`1.0`**, never pixels. Pixels appear only at render time. This matches `Src/world.py` and the wire format.
- **`facing` is `1` (right) or `-1` (left).**
- **`lib/` is pure**: no React import, no DOM access, no `window`, no `document`. That is what makes it testable in Vitest's node environment.
- **Only `BuddyStage` and `DownloadButton` carry `"use client"`.** Everything else is a server component.
- **Every colour is a CSS custom property defined in `:root` and redefined in the `prefers-color-scheme: dark` media query.** No element gets its only definition inside one theme. There is no theme toggle.
- **GitHub URL is `https://github.com/KainBC/Desktop-Buddies`** — the repository's `origin` — everywhere it appears.
- **Honesty rule:** no invented download counts, testimonials, user numbers, or working installer links. Installers are marked coming soon.
- **Animation constants copied verbatim from the Python:** `WALK_SPEED = 0.12` (fraction of screen width per second), idle beat `rng.uniform(2.0, 5.0)`, walk targets `rng.uniform(0.05, 0.95)`, `Hop` defaults `height = 0.04` and `duration = 0.45`, sprite `fps = 6`.
- **TDD.** Write the failing test, watch it fail, implement minimally, watch it pass, commit. Components are exempt: their verification is `npm run lint` and `npm run build`.
- Commit messages end with the repository's attribution lines:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
  ```

---

### Task 1: Track the scaffold and repair the root document

The scaffold is untracked and two of its files are invalid. `app/layout.tsx`
renders `<nav>` as a sibling of `<body>` inside `<html>` (invalid HTML),
imports `Metadata`, `Geist`, `Geist_Mono` and `Welcome` without using any of
them, and omits `lang`. `app/page.tsx` imports `RootLayout` and wraps itself
in it — Next applies the root layout automatically, so this nests a second
`<html>` document inside the first. Nothing else can be built on top of
this, so it is fixed before anything is added.

**Files:**
- Create: `desktop-buddies/.gitignore` already exists in the scaffold — verify it, do not regenerate
- Modify: `desktop-buddies/app/layout.tsx` (full rewrite, 10 lines)
- Modify: `desktop-buddies/app/page.tsx` (full rewrite, 9 lines)
- Modify: `desktop-buddies/app/download/page.tsx` (full rewrite, 5 lines)
- Delete: `desktop-buddies/public/{file,globe,next,vercel,window}.svg` (create-next-app boilerplate, unused)

**Interfaces:**
- Consumes: nothing.
- Produces: a valid root layout exporting `metadata: Metadata` and applying the `.variable` classes of `Geist` and `Geist_Mono` to `<body>`, so `globals.css`'s existing `--font-geist-sans` / `--font-geist-mono` references resolve. Every later task's page content renders inside this layout.

- [ ] **Step 1: Confirm the working tree and the toolchain**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git status --short --branch
node -v    # expect v26.x
ls desktop-buddies/node_modules > /dev/null && echo "deps present"
```

Expected: on branch `web-frontend`; `desktop-buddies/` shows as untracked
(`?? desktop-buddies/`); deps present. If `node_modules` is missing, run
`cd desktop-buddies && npm install` before continuing.

- [ ] **Step 2: Delete the create-next-app boilerplate SVGs**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
rm -f public/file.svg public/globe.svg public/next.svg public/vercel.svg public/window.svg
```

- [ ] **Step 3: Rewrite the root layout**

Replace the entire contents of `desktop-buddies/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Desktop Buddies",
  description:
    "Friends as animated pets on your desktop. Share a room code and " +
    "everyone's buddy walks around on everyone's screen.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
```

The `<nav>` is gone on purpose: a two-page site navigates from the hero
buttons and the footer, so a nav bar would be chrome with nothing in it.

- [ ] **Step 4: Rewrite the landing page to a placeholder that does not self-wrap**

Replace the entire contents of `desktop-buddies/app/page.tsx` with:

```tsx
export default function Home() {
  return (
    <main>
      <h1>Desktop Buddies</h1>
    </main>
  );
}
```

Task 8 replaces this body. What matters now is that it no longer imports
`RootLayout`.

- [ ] **Step 5: Rewrite the download page placeholder**

Replace the entire contents of `desktop-buddies/app/download/page.tsx` with:

```tsx
export default function Download() {
  return (
    <main>
      <h1>Download</h1>
    </main>
  );
}
```

- [ ] **Step 6: Verify lint and build both pass**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint
npm run build
```

Expected: lint reports no errors (the four unused imports are gone), and the
build succeeds with `/` and `/download` both listed as static. If the build
prints a hydration or nested-`<html>` warning, Step 4 or Step 5 was not
applied.

- [ ] **Step 7: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies
git status --short   # confirm node_modules and .next are NOT staged
git commit -m "$(cat <<'EOF'
feat: track the web scaffold and repair the root document

The generated layout rendered <nav> outside <body>, omitted lang, and
imported four things it never used; the page wrapped itself in RootLayout,
nesting a second <html> inside the one Next already applies.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

If `node_modules/` or `.next/` appear in `git status --short`, stop: the
scaffold's `.gitignore` is not being honoured. Confirm
`desktop-buddies/.gitignore` exists and contains `/node_modules` and
`/.next/` before committing.

---

### Task 2: Vitest, and the pure `FrameCycler` and `Hop`

Ports of `FrameCycler` from `Src/sprite_window.py` and `Hop` from
`Src/poke.py`. The `Hop` tests deliberately mirror the assertions in
`tests/test_poke.py` so the two ports cannot drift apart silently.

**Files:**
- Modify: `desktop-buddies/package.json` (add `vitest` devDependency and a `test` script)
- Create: `desktop-buddies/vitest.config.ts`
- Create: `desktop-buddies/lib/buddy.ts`
- Test: `desktop-buddies/lib/buddy.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class FrameCycler { constructor(frameCount: number, fps: number); index: number; advance(dt: number): number; reset(): void; }`
  - `class Hop { constructor(height?: number, duration?: number); readonly height: number; readonly duration: number; advance(dt: number): void; offset(): number; get done(): boolean; reset(): void; }`
  - Both are used by `Stage` in Task 3.

- [ ] **Step 1: Install Vitest and add the test script**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm install --save-dev vitest
npm pkg set scripts.test="vitest run"
npm pkg set scripts.test:watch="vitest"
```

No `jsdom` and no React plugin: `lib/` touches no DOM, so the default node
environment is the correct one and anything more is unused machinery.

- [ ] **Step 2: Add the Vitest config**

Create `desktop-buddies/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
```

`include` is narrowed to `lib/` on purpose. Components are not unit tested —
a snapshot test of marketing markup asserts nothing worth breaking the build
over — and this makes that a property of the config rather than a habit.

- [ ] **Step 3: Write the failing tests**

Create `desktop-buddies/lib/buddy.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { FrameCycler, Hop } from "./buddy";

describe("FrameCycler", () => {
  it("advances at fps", () => {
    const c = new FrameCycler(4, 10);        // 0.1s per frame
    expect(c.advance(0)).toBe(0);
    expect(c.advance(0.1)).toBe(1);
    expect(c.advance(0.25)).toBe(3);         // 0.35s total -> frame 3
  });

  it("wraps around", () => {
    const c = new FrameCycler(2, 10);
    c.advance(0.1);                          // -> 1
    expect(c.advance(0.1)).toBe(0);
  });

  it("holds frame 0 before the first interval elapses", () => {
    const c = new FrameCycler(4, 10);
    expect(c.advance(0.09)).toBe(0);
  });

  it("stays at zero for a single frame", () => {
    const c = new FrameCycler(1, 10);
    expect(c.advance(5)).toBe(0);
  });

  it("stays at zero for a non-positive fps", () => {
    const c = new FrameCycler(4, 0);
    expect(c.advance(5)).toBe(0);
  });

  it("resets", () => {
    const c = new FrameCycler(4, 10);
    c.advance(0.3);
    c.reset();
    expect(c.advance(0)).toBe(0);
  });
});

describe("Hop", () => {
  it("starts on the ground", () => {
    const h = new Hop(0.04, 0.45);
    expect(h.offset()).toBe(0);
    expect(h.done).toBe(false);
  });

  it("peaks at height midway", () => {
    const h = new Hop(0.04, 0.45);
    h.advance(0.225);
    expect(Math.abs(h.offset() - 0.04)).toBeLessThan(1e-6);
  });

  it("returns to the ground at the end", () => {
    const h = new Hop(0.04, 0.45);
    h.advance(0.45);
    expect(Math.abs(h.offset())).toBeLessThan(1e-6);
    expect(h.done).toBe(true);
  });

  it("has a symmetric arc", () => {
    const rising = new Hop(0.04, 0.4);
    rising.advance(0.1);
    const falling = new Hop(0.04, 0.4);
    falling.advance(0.3);
    expect(Math.abs(rising.offset() - falling.offset())).toBeLessThan(1e-6);
    expect(rising.offset()).toBeGreaterThan(0);
  });

  it("never sinks below the ground", () => {
    const h = new Hop(0.04, 0.45);
    h.advance(10);                           // long past the end
    expect(h.offset()).toBe(0);
  });

  it("accumulates across advances", () => {
    const h = new Hop(0.04, 0.4);
    h.advance(0.1);
    h.advance(0.1);
    expect(Math.abs(h.offset() - 0.04)).toBeLessThan(1e-6);
  });

  it("does not mutate its configuration when read", () => {
    const h = new Hop(0.04, 0.45);
    h.advance(0.225);
    const first = h.offset();
    const second = h.offset();
    expect(first).toBe(second);
    expect(h.height).toBe(0.04);
    expect(h.duration).toBe(0.45);
  });

  it("restarts the arc on reset", () => {
    const h = new Hop(0.04, 0.45);
    h.advance(1);
    expect(h.done).toBe(true);
    h.reset();
    expect(h.done).toBe(false);
    expect(h.offset()).toBe(0);
  });

  it("defaults to the client's hop", () => {
    const h = new Hop();
    expect(h.height).toBe(0.04);
    expect(h.duration).toBe(0.45);
  });
});
```

- [ ] **Step 4: Run the tests to verify they fail**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: FAIL — `Failed to resolve import "./buddy"`.

- [ ] **Step 5: Write the minimal implementation**

Create `desktop-buddies/lib/buddy.ts`:

```ts
/**
 * The site's buddy simulation. Pure TypeScript: no React, no DOM.
 *
 * Ported from the desktop client's `Src/world.py`, `Src/poke.py` and the
 * `FrameCycler` in `Src/sprite_window.py`, keeping the same names and the
 * same units so the two codebases stay legible to each other. Positions are
 * fractional (0.0-1.0) exactly as they are on the wire; pixels appear only
 * at render time.
 */

/** Cycles an animation's frames at a fixed rate. */
export class FrameCycler {
  index = 0;
  private elapsed = 0;

  constructor(
    readonly frameCount: number,
    readonly fps: number,
  ) {}

  advance(dt: number): number {
    if (this.frameCount <= 1 || this.fps <= 0) {
      this.index = 0;
      return 0;
    }
    this.elapsed += dt;
    const frameTime = 1 / this.fps;
    while (this.elapsed >= frameTime) {
      this.elapsed -= frameTime;
      this.index = (this.index + 1) % this.frameCount;
    }
    return this.index;
  }

  reset(): void {
    this.index = 0;
    this.elapsed = 0;
  }
}

/**
 * A short vertical hop: one arc up from the ground and back down.
 *
 * `offset()` is a fraction of the stage's height, applied at render time so
 * a hopping buddy keeps walking underneath it. Past `duration` it clamps to
 * 0 rather than letting sine go negative and sink the buddy through the
 * floor.
 */
export class Hop {
  private elapsed = 0;

  constructor(
    readonly height = 0.04,
    readonly duration = 0.45,
  ) {}

  advance(dt: number): void {
    this.elapsed += dt;
  }

  offset(): number {
    if (this.done) return 0;
    return this.height * Math.sin((Math.PI * this.elapsed) / this.duration);
  }

  get done(): boolean {
    return this.elapsed >= this.duration;
  }

  reset(): void {
    this.elapsed = 0;
  }
}
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: PASS — 16 tests.

- [ ] **Step 7: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/package.json desktop-buddies/package-lock.json \
        desktop-buddies/vitest.config.ts desktop-buddies/lib
git commit -m "$(cat <<'EOF'
feat: vitest, and pure FrameCycler and Hop ports

Hop's tests mirror tests/test_poke.py assertion for assertion so the port
and the original cannot drift apart silently.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 3: `Stage` — the wander loop and poke handling

Ports `OwnController` and the hop bookkeeping from `World` in
`Src/world.py`. `Stage` owns the buddies, their frame cyclers, and their
hops; it is driven entirely by `tick(dt)` and takes an injectable rng so
tests are deterministic rather than flaky.

**Files:**
- Modify: `desktop-buddies/lib/buddy.ts` (append)
- Test: `desktop-buddies/lib/buddy.test.ts` (append)

**Interfaces:**
- Consumes: `FrameCycler`, `Hop` from Task 2.
- Produces:
  - `type AnimState = "idle" | "walk"`
  - `type Facing = 1 | -1`
  - `type Rng = () => number`
  - `interface CharacterFrames { idle: number; walk: number; fps: number }`
  - `interface BuddySpec { id: string; character: string; x: number }`
  - `interface Buddy { id: string; character: string; x: number; facing: Facing; state: AnimState }`
  - `class Stage { constructor(specs: readonly BuddySpec[], frames: Record<string, CharacterFrames>, rng?: Rng); readonly buddies: Buddy[]; tick(dt: number): void; poke(id: string): void; hopOffset(id: string): number; frame(id: string): number; }`
  - Constants `WALK_SPEED`, `IDLE_MIN`, `IDLE_MAX`, `MIN_X`, `MAX_X`, `MAX_DT`, and `function clampDt(dt: number): number`.
  - `Stage`, `Buddy`, `CharacterFrames` and `BuddySpec` are consumed by `BuddyStage` in Task 7; `CharacterFrames` and `BuddySpec` are also what `lib/characters.ts` produces in Task 5.

- [ ] **Step 1: Write the failing tests**

Append to `desktop-buddies/lib/buddy.test.ts`:

```ts
import {
  clampDt,
  MAX_DT,
  MAX_X,
  MIN_X,
  Stage,
  WALK_SPEED,
  type BuddySpec,
  type CharacterFrames,
} from "./buddy";

const FRAMES: Record<string, CharacterFrames> = {
  round: { idle: 2, walk: 4, fps: 6 },
};

const SPECS: BuddySpec[] = [{ id: "a", character: "round", x: 0.5 }];

/** Deterministic rng cycling through fixed values, for seeded tests. */
function seeded(values: number[]): () => number {
  let i = 0;
  return () => values[i++ % values.length];
}

describe("Stage", () => {
  it("exposes its buddies with client defaults", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    expect(s.buddies).toHaveLength(1);
    expect(s.buddies[0]).toMatchObject({
      id: "a",
      character: "round",
      x: 0.5,
      facing: 1,
      state: "idle",
    });
  });

  it("starts walking once the idle beat elapses", () => {
    // rng 0 -> idle beat of IDLE_MIN (2.0s), then target 0.05 (MIN_X)
    const s = new Stage(SPECS, FRAMES, seeded([0]));
    s.tick(0.1);
    expect(s.buddies[0].state).toBe("idle");
    s.tick(2.0);
    expect(s.buddies[0].state).toBe("walk");
    expect(s.buddies[0].facing).toBe(-1);   // target 0.05 is left of 0.5
  });

  it("walks at WALK_SPEED toward its target", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0]));
    s.tick(2.0);                             // -> walk, target 0.05
    s.tick(1.0);
    expect(s.buddies[0].x).toBeCloseTo(0.5 - WALK_SPEED, 6);
  });

  it("faces right when the target is to the right", () => {
    // rng 1 -> idle beat of IDLE_MAX, then target 0.95 (MAX_X)
    const s = new Stage(SPECS, FRAMES, seeded([1]));
    s.tick(5.0);
    expect(s.buddies[0].state).toBe("walk");
    expect(s.buddies[0].facing).toBe(1);
  });

  it("settles on the target and returns to idle", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0]));
    s.tick(2.0);                             // -> walk, target 0.05
    s.tick(10.0);                            // far more than enough
    expect(s.buddies[0].x).toBeCloseTo(MIN_X, 6);
    expect(s.buddies[0].state).toBe("idle");
  });

  it("keeps every buddy inside the stage over a long run", () => {
    const s = new Stage(SPECS, FRAMES, Math.random);
    for (let i = 0; i < 5000; i++) s.tick(0.016);
    expect(s.buddies[0].x).toBeGreaterThanOrEqual(MIN_X);
    expect(s.buddies[0].x).toBeLessThanOrEqual(MAX_X);
  });

  it("advances the frame cycler for the current state", () => {
    const s = new Stage(SPECS, FRAMES, seeded([1]));
    expect(s.frame("a")).toBe(0);
    s.tick(1 / 6);                           // one idle frame at 6fps
    expect(s.frame("a")).toBe(1);
  });

  it("returns frame 0 for an unknown id", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    expect(s.frame("nobody")).toBe(0);
  });

  it("hops a known buddy when poked", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    expect(s.hopOffset("a")).toBe(0);
    s.poke("a");
    s.tick(0.225);                           // midway through a 0.45s hop
    expect(s.hopOffset("a")).toBeCloseTo(0.04, 6);
  });

  it("restarts rather than stacks on a second poke", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    s.poke("a");
    s.tick(0.4);
    s.poke("a");                             // resets the arc
    expect(s.hopOffset("a")).toBe(0);
    s.tick(0.225);
    expect(s.hopOffset("a")).toBeCloseTo(0.04, 6);
  });

  it("ignores a poke for an unknown id", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    s.poke("nobody");
    expect(s.hopOffset("nobody")).toBe(0);
  });

  it("expires a hop once its duration elapses", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0.5]));
    s.poke("a");
    s.tick(0.5);                             // past the 0.45s duration
    expect(s.hopOffset("a")).toBe(0);
  });

  it("integrates the dt it is handed, without clamping", () => {
    // Clamping is the render loop's job, not the simulation's: Stage stays
    // a plain integrator so tests can advance it in whole seconds.
    const s = new Stage(SPECS, FRAMES, seeded([0]));
    s.tick(2.0);                             // -> walk, target 0.05
    s.tick(1.0);
    expect(s.buddies[0].x).toBeCloseTo(0.5 - WALK_SPEED, 6);
  });

  it("holds still when motion is frozen, but still hops", () => {
    const s = new Stage(SPECS, FRAMES, seeded([0]));
    s.frozen = true;
    s.tick(5.0);
    expect(s.buddies[0].state).toBe("idle");
    expect(s.buddies[0].x).toBe(0.5);
    expect(s.frame("a")).toBe(0);
    s.poke("a");
    s.tick(0.225);
    expect(s.hopOffset("a")).toBeCloseTo(0.04, 6);
  });
});

describe("clampDt", () => {
  it("passes an ordinary frame through untouched", () => {
    expect(clampDt(0.016)).toBe(0.016);
  });

  it("caps the enormous dt a backgrounded tab hands back", () => {
    expect(clampDt(60)).toBe(MAX_DT);
  });

  it("floors a negative dt at zero", () => {
    // Some clocks step backwards. Never rewind the simulation.
    expect(clampDt(-1)).toBe(0);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: FAIL — `"Stage" is not exported by "lib/buddy.ts"`.

- [ ] **Step 3: Write the minimal implementation**

Append to `desktop-buddies/lib/buddy.ts`:

```ts
export type AnimState = "idle" | "walk";
export type Facing = 1 | -1;
export type Rng = () => number;

/** Fraction of the stage's width per second. Matches Src/world.py. */
export const WALK_SPEED = 0.12;
/** The idle beat is drawn uniformly from this range, as OwnController does. */
export const IDLE_MIN = 2.0;
export const IDLE_MAX = 5.0;
/** Walk targets stay off the very edges so no buddy half-leaves the stage. */
export const MIN_X = 0.05;
export const MAX_X = 0.95;
/**
 * Longest step the render loop may hand the simulation. A backgrounded tab
 * gives rAF one enormous dt on return; without this, every buddy teleports.
 */
export const MAX_DT = 0.1;

/**
 * Clamp a frame delta into a sane range.
 *
 * This lives at the render-loop boundary rather than inside `Stage.tick`:
 * the oversized dt is an artifact of how the browser schedules frames, not
 * a property of the simulation, and a `Stage` that quietly rewrote the time
 * it was given could not be driven in whole seconds by a test.
 */
export function clampDt(dt: number): number {
  if (!(dt > 0)) return 0;        // also catches NaN
  return Math.min(dt, MAX_DT);
}

export interface CharacterFrames {
  idle: number;
  walk: number;
  fps: number;
}

export interface BuddySpec {
  id: string;
  character: string;
  x: number;
}

export interface Buddy {
  id: string;
  character: string;
  x: number;
  facing: Facing;
  state: AnimState;
}

interface Runtime {
  target: number;
  idleTimer: number;
  cyclers: Record<AnimState, FrameCycler>;
}

/**
 * Owns the buddies, their animation state, and their hops.
 *
 * The decision loop is `OwnController.update` from Src/world.py: hold idle
 * for a randomised beat, pick a target, walk to it, idle again. The hop
 * bookkeeping is `World.poke` / `World.hop_offset` / the hop half of
 * `World.tick`. The rng is injectable so tests are deterministic.
 */
export class Stage {
  readonly buddies: Buddy[];
  /** When true, ambient motion stops but pokes still land. */
  frozen = false;

  private readonly runtimes = new Map<string, Runtime>();
  private readonly hops = new Map<string, Hop>();

  constructor(
    specs: readonly BuddySpec[],
    frames: Record<string, CharacterFrames>,
    private readonly rng: Rng = Math.random,
  ) {
    this.buddies = specs.map((spec) => ({
      id: spec.id,
      character: spec.character,
      x: spec.x,
      facing: 1 as Facing,
      state: "idle" as AnimState,
    }));
    for (const spec of specs) {
      const f = frames[spec.character];
      this.runtimes.set(spec.id, {
        target: spec.x,
        idleTimer: this.idleTime(),
        cyclers: {
          idle: new FrameCycler(f.idle, f.fps),
          walk: new FrameCycler(f.walk, f.fps),
        },
      });
    }
  }

  private idleTime(): number {
    return IDLE_MIN + this.rng() * (IDLE_MAX - IDLE_MIN);
  }

  /** Advance by `dt` seconds. Callers clamp first; see `clampDt`. */
  tick(dt: number): void {
    if (!this.frozen) {
      for (const buddy of this.buddies) {
        const rt = this.runtimes.get(buddy.id);
        if (!rt) continue;
        this.wander(buddy, rt, dt);
        rt.cyclers[buddy.state].advance(dt);
      }
    }

    // Hops run even when frozen: a poke is a direct response to the
    // visitor's own click, not ambient motion they did not ask for.
    for (const [id, hop] of this.hops) {
      hop.advance(dt);
      if (hop.done) this.hops.delete(id);
    }
  }

  private wander(buddy: Buddy, rt: Runtime, dt: number): void {
    if (buddy.state === "idle") {
      rt.idleTimer -= dt;
      if (rt.idleTimer <= 0) {
        rt.target = MIN_X + this.rng() * (MAX_X - MIN_X);
        buddy.state = "walk";
        buddy.facing = rt.target >= buddy.x ? 1 : -1;
      }
      return;
    }

    const step = WALK_SPEED * dt;
    const remaining = rt.target - buddy.x;
    if (Math.abs(remaining) <= step) {
      buddy.x = rt.target;
      buddy.state = "idle";
      rt.idleTimer = this.idleTime();
      rt.cyclers.walk.reset();
    } else {
      buddy.x += remaining > 0 ? step : -step;
      buddy.facing = remaining > 0 ? 1 : -1;
    }
  }

  /** Start, or restart, a hop on a known buddy. Unknown ids are ignored. */
  poke(id: string): void {
    if (!this.runtimes.has(id)) return;
    const hop = this.hops.get(id);
    if (hop === undefined) this.hops.set(id, new Hop());
    else hop.reset();
  }

  /** Vertical offset as a fraction of stage height; 0 when not hopping. */
  hopOffset(id: string): number {
    return this.hops.get(id)?.offset() ?? 0;
  }

  /** Current frame index for a buddy's current animation. */
  frame(id: string): number {
    const rt = this.runtimes.get(id);
    if (!rt) return 0;
    const buddy = this.buddies.find((b) => b.id === id);
    if (!buddy) return 0;
    return rt.cyclers[buddy.state].index;
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: PASS — 33 tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/lib
git commit -m "$(cat <<'EOF'
feat: Stage, the wander loop and poke handling

A port of OwnController plus World's hop bookkeeping, with an injectable
rng so the tests are deterministic instead of flaky.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 4: `lib/os.ts` — platform detection

A pure userAgent-to-platform function. It runs after hydration only, so the
download button server-renders neutral and there is no hydration mismatch
and no flash of the wrong platform.

**Files:**
- Create: `desktop-buddies/lib/os.ts`
- Test: `desktop-buddies/lib/os.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `type Platform = "macos" | "windows" | "linux"` and `function detectPlatform(ua: string): Platform | null`. Both are consumed by `lib/downloads.ts` and `DownloadButton` in Task 9.

- [ ] **Step 1: Write the failing tests**

Create `desktop-buddies/lib/os.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { detectPlatform, type Platform } from "./os";

const CASES: Array<[string, Platform | null]> = [
  [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "macos",
  ],
  [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 " +
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "macos",
  ],
  [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "windows",
  ],
  [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "linux",
  ],
  [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 " +
      "Firefox/121.0",
    "linux",
  ],
  // Phones get the neutral label: there is nothing here they can install.
  [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) " +
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148",
    null,
  ],
  [
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 " +
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148",
    null,
  ],
  [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    null,
  ],
  ["", null],
  ["some unknown agent", null],
];

describe("detectPlatform", () => {
  it.each(CASES)("maps %s", (ua, expected) => {
    expect(detectPlatform(ua)).toBe(expected);
  });
});
```

Note the iPhone and iPad cases: both contain the literal string
`Mac OS X`, so a naive `includes("Mac OS X")` check would report macOS for a
phone. The mobile checks must come first.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: FAIL — `Failed to resolve import "./os"`.

- [ ] **Step 3: Write the minimal implementation**

Create `desktop-buddies/lib/os.ts`:

```ts
/**
 * userAgent -> desktop platform. Pure: no `navigator`, no DOM.
 *
 * The caller passes the string, so this is unit testable and so the
 * download button can server-render neutral and only narrow after
 * hydration. Phones and anything unrecognised map to null, which the button
 * renders as a plain "Download".
 */
export type Platform = "macos" | "windows" | "linux";

export function detectPlatform(ua: string): Platform | null {
  // Mobile first: an iPhone's UA contains "Mac OS X" and an Android's
  // contains "Linux", so checking desktops first would misreport both.
  if (/iPhone|iPad|iPod|Android/i.test(ua)) return null;
  if (/Macintosh|Mac OS X/i.test(ua)) return "macos";
  if (/Windows/i.test(ua)) return "windows";
  if (/Linux|X11/i.test(ua)) return "linux";
  return null;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: PASS — 43 tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/lib
git commit -m "$(cat <<'EOF'
feat: pure userAgent -> platform detection

Mobile is checked first: an iPhone's UA contains "Mac OS X" and an
Android's contains "Linux".

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 5: Copy the sprite frames and write the character manifest

The site needs the sprite art under `public/`, because Next serves static
files only from `desktop-buddies/public/` and `Sprites/` lives outside the
Next app. Six small PNGs per character and the art is a placeholder anyway,
so a sync script would be more machinery than the problem deserves — the
files are copied and committed, and refreshed in the same commit whenever
the art changes.

**Files:**
- Create: `desktop-buddies/public/sprites/<character>/{idle,walk}/*.png` (copied, committed — 18 files)
- Create: `desktop-buddies/lib/characters.ts`
- Test: `desktop-buddies/lib/characters.test.ts`

**Interfaces:**
- Consumes: `AnimState`, `BuddySpec`, `CharacterFrames` from `lib/buddy.ts` (Task 3).
- Produces: `interface Character { id: string; label: string }`, `CHARACTERS: Record<string, Character>`, `CHARACTER_FRAMES: Record<string, CharacterFrames>`, `HERO_BUDDIES: BuddySpec[]`, and `framePath(character: string, state: AnimState, index: number): string`. All consumed by `BuddyStage` in Task 7; Task 8 also references three baked frame URLs directly.

- [ ] **Step 1: Confirm what the art actually is**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
for d in Sprites/*/; do
  echo "$d idle=$(ls "$d"idle | wc -l) walk=$(ls "$d"walk | wc -l)"; cat "$d"sprite.json; echo
done
```

Expected: three characters — `placeholder_blob`, `placeholder_cat`,
`placeholder_dog` — each `idle=2 walk=4` with `{"fps": 6, "scale": 1}`. If
what you see differs, STOP and report it rather than adapting the numbers
below: the manifest in Step 3 hard-codes these counts and a silent
mismatch would only surface as a missing sprite in the browser.

- [ ] **Step 2: Copy the frames into the Next app**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
mkdir -p desktop-buddies/public/sprites
for c in placeholder_blob placeholder_cat placeholder_dog; do
  for a in idle walk; do
    mkdir -p "desktop-buddies/public/sprites/$c/$a"
    cp Sprites/$c/$a/*.png "desktop-buddies/public/sprites/$c/$a/"
  done
done
find desktop-buddies/public/sprites -name '*.png' | sort
```

Expected: 18 files. `sprite.json` is deliberately NOT copied — the site
records frame counts in `characters.ts` instead, and Step 4's test is what
keeps that record honest.

- [ ] **Step 3: Write the character manifest**

Create `desktop-buddies/lib/characters.ts`:

```ts
import type { AnimState, BuddySpec, CharacterFrames } from "./buddy";

/**
 * The sprite art copied into public/sprites by Task 5.
 *
 * Frame counts are recorded rather than discovered, so the loader never
 * guesses at what exists on disk. They come from `Sprites/<c>/sprite.json`
 * and the frame files themselves; `characters.test.ts` asserts this record
 * still matches what is actually there, so the two cannot drift silently.
 */
export interface Character {
  id: string;
  /** Used as each buddy's aria-label, so a poke target is announced. */
  label: string;
}

export const CHARACTERS: Record<string, Character> = {
  placeholder_blob: { id: "placeholder_blob", label: "the blob buddy" },
  placeholder_cat: { id: "placeholder_cat", label: "the cat buddy" },
  placeholder_dog: { id: "placeholder_dog", label: "the dog buddy" },
};

export const CHARACTER_FRAMES: Record<string, CharacterFrames> = {
  placeholder_blob: { idle: 2, walk: 4, fps: 6 },
  placeholder_cat: { idle: 2, walk: 4, fps: 6 },
  placeholder_dog: { idle: 2, walk: 4, fps: 6 },
};

/** Who wanders in the hero. Count is a tuning knob, not a constraint. */
export const HERO_BUDDIES: BuddySpec[] = [
  { id: "buddy-1", character: "placeholder_blob", x: 0.22 },
  { id: "buddy-2", character: "placeholder_cat", x: 0.5 },
  { id: "buddy-3", character: "placeholder_dog", x: 0.78 },
];

export function framePath(
  character: string,
  state: AnimState,
  index: number,
): string {
  return `/sprites/${character}/${state}/${index}.png`;
}
```

- [ ] **Step 4: Write the failing test**

Create `desktop-buddies/lib/characters.test.ts`:

```ts
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CHARACTERS,
  CHARACTER_FRAMES,
  HERO_BUDDIES,
  framePath,
} from "./characters";

const PUBLIC_SPRITES = join(import.meta.dirname, "..", "public", "sprites");

describe("framePath", () => {
  it("builds a root-relative url", () => {
    expect(framePath("placeholder_cat", "walk", 2)).toBe(
      "/sprites/placeholder_cat/walk/2.png",
    );
  });
});

describe("the character manifest", () => {
  it("describes the same characters in both maps", () => {
    expect(Object.keys(CHARACTER_FRAMES).sort()).toEqual(
      Object.keys(CHARACTERS).sort(),
    );
  });

  it("gives every hero buddy a known character and a distinct id", () => {
    const ids = HERO_BUDDIES.map((b) => b.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const buddy of HERO_BUDDIES) {
      expect(CHARACTERS[buddy.character]).toBeDefined();
      expect(CHARACTER_FRAMES[buddy.character]).toBeDefined();
      expect(buddy.x).toBeGreaterThanOrEqual(0);
      expect(buddy.x).toBeLessThanOrEqual(1);
    }
  });

  // The manifest records frame counts instead of discovering them, so this
  // is the test that catches the record and the art drifting apart.
  it.each(Object.entries(CHARACTER_FRAMES))(
    "matches the frames actually on disk for %s",
    (character, frames) => {
      for (const state of ["idle", "walk"] as const) {
        const dir = join(PUBLIC_SPRITES, character, state);
        expect(existsSync(dir)).toBe(true);
        const pngs = readdirSync(dir).filter((f) => f.endsWith(".png"));
        expect(pngs).toHaveLength(frames[state]);
        for (let i = 0; i < frames[state]; i++) {
          expect(pngs).toContain(`${i}.png`);
        }
      }
    },
  );
});
```

This test file reads the filesystem, which `lib/` production code never
does. That is fine and deliberate: the rule keeps `lib/`'s shipped modules
pure so they run anywhere, and a node-environment test asserting that a
hand-written manifest matches real files is exactly the drift guard the
recorded counts need.

- [ ] **Step 5: Run the test to verify it fails**

Temporarily rename one frame so the drift guard has something to catch:

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
mv public/sprites/placeholder_cat/walk/3.png public/sprites/placeholder_cat/walk/3.png.bak
npm test
```

Expected: FAIL — the `placeholder_cat` case reports 3 PNGs where 4 were
expected. Then restore it:

```bash
mv public/sprites/placeholder_cat/walk/3.png.bak public/sprites/placeholder_cat/walk/3.png
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm test
```

Expected: PASS — 48 tests (42 existing + 6 new).

- [ ] **Step 7: Verify lint and build**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint && npm run build
```

Expected: both pass. `characters.ts` is not imported by a page yet, which
is fine — it is typed against Task 3's exports, so a mismatch in
`BuddySpec` or `CharacterFrames` surfaces here as a type error.

- [ ] **Step 8: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/public/sprites desktop-buddies/lib/characters.ts \
        desktop-buddies/lib/characters.test.ts
git commit -m "$(cat <<'EOF'
feat: sprite frames and the character manifest

Frame counts are recorded rather than discovered, and a test asserts the
record still matches the files on disk so the two cannot drift silently.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 6: Palette tokens and the window frame

The page is framed as a desktop window: the product *is* a translucent
always-on-top window with sprites pinned to the floor, so the chrome is a
picture of the thing itself rather than decoration.

**Files:**
- Modify: `desktop-buddies/app/globals.css` (extend, do not replace)
- Create: `desktop-buddies/components/WindowFrame.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `WindowFrame({ title, children }: { title?: string; children: React.ReactNode })` — a server component rendering a title bar with three traffic-light dots above its children. Consumed by both pages (Tasks 8 and 9). Also produces the CSS custom properties `--surface`, `--surface-2`, `--border`, `--muted`, `--accent`, `--accent-contrast`, `--floor`, available as Tailwind utilities (`bg-surface`, `text-muted`, `border-border`, …) via `@theme inline`.

- [ ] **Step 1: Extend the palette**

Replace the entire contents of `desktop-buddies/app/globals.css` with:

```css
@import "tailwindcss";

/*
 * The scaffold's teal-on-white / white-on-slate palette is kept and
 * extended. Every colour is defined here in :root and redefined in the dark
 * block below -- no element gets its only definition inside one theme.
 * There is no toggle; the site follows prefers-color-scheme.
 */
:root {
  --background: #ffffff;
  --foreground: #223033;
  --surface: #f4f7f7;
  --surface-2: #e7eded;
  --border: #d2dedd;
  --muted: #5f7274;
  --accent: #568889;
  --accent-contrast: #ffffff;
  --floor: #c3d3d3;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #222f34;
    --foreground: #ffffff;
    --surface: #2b3a40;
    --surface-2: #35464d;
    --border: #3f535a;
    --muted: #a8bdc0;
    --accent: #7fb3b4;
    --accent-contrast: #142024;
    --floor: #47606a;
  }
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-surface: var(--surface);
  --color-surface-2: var(--surface-2);
  --color-border: var(--border);
  --color-muted: var(--muted);
  --color-accent: var(--accent);
  --color-accent-contrast: var(--accent-contrast);
  --color-floor: var(--floor);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: var(--font-geist-sans), system-ui, -apple-system, sans-serif;
}

/* The art is 64px and gets scaled up; keep it crisp rather than smeared. */
.pixelated {
  image-rendering: pixelated;
}
```

`--accent-contrast` inverts between themes on purpose: white ink on the
teal accent in light mode, near-black ink on the lighter accent in dark
mode. Both are legible; a single value would fail one of them.

- [ ] **Step 2: Write the window frame**

Create `desktop-buddies/components/WindowFrame.tsx`:

```tsx
/**
 * Faux desktop-window chrome.
 *
 * Desktop Buddies is a translucent, always-on-top window with sprites
 * pinned to its floor, so framing the page this way is a picture of the
 * product rather than ornament.
 */
export default function WindowFrame({
  title = "Desktop Buddies",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-lg">
      <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-4 py-3">
        {/*
          The macOS traffic-light colours, and the one deliberate exemption
          from the token palette: real window chrome keeps these identical in
          light and dark, so they cannot fail the "readable in both themes"
          rule the tokens exist to enforce, and tokenising them would mean
          three properties whose two definitions are byte-identical.
        */}
        <span aria-hidden className="flex gap-1.5">
          <span className="size-3 rounded-full bg-[#ff5f57]" />
          <span className="size-3 rounded-full bg-[#febc2e]" />
          <span className="size-3 rounded-full bg-[#28c840]" />
        </span>
        <span className="flex-1 text-center text-sm font-medium text-muted">
          {title}
        </span>
        {/* Balances the dots so the title sits centred. */}
        <span aria-hidden className="w-[52px]" />
      </div>
      {children}
    </div>
  );
}
```

- [ ] **Step 3: Verify lint and build**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint && npm run build
```

Expected: both pass. `WindowFrame` is unused so far; Tailwind 4 compiles
`@theme inline` tokens regardless of use.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/app/globals.css desktop-buddies/components
git commit -m "$(cat <<'EOF'
feat: palette tokens and faux window chrome

Every colour is defined in :root and redefined for dark, so nothing gets
its only definition inside one theme.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 7: `BuddyStage` — the animated, pokeable hero

The only genuinely interactive part of the site. It constructs a `Stage` on
mount and drives it from `requestAnimationFrame`, writing each buddy's
`transform` and frame `src` straight onto its DOM node through a ref. React
renders the buddy list exactly once — sixty re-renders a second to move
three sprites would be absurd.

**Files:**
- Create: `desktop-buddies/components/BuddyStage.tsx`

**Interfaces:**
- Consumes: `Stage`, `clampDt` and the type `BuddySpec` from `lib/buddy.ts`; `CHARACTERS`, `CHARACTER_FRAMES`, `HERO_BUDDIES`, `framePath` from `lib/characters.ts`.
- Produces: `BuddyStage({ buddies }: { buddies?: BuddySpec[] })` — a client component rendering a fixed-height stage with a floor line. Consumed by the landing page in Task 8.

- [ ] **Step 1: Write the component**

Create `desktop-buddies/components/BuddyStage.tsx`:

```tsx
"use client";

import { useEffect, useRef } from "react";
import { clampDt, Stage, type BuddySpec } from "@/lib/buddy";
import {
  CHARACTERS,
  CHARACTER_FRAMES,
  HERO_BUDDIES,
  framePath,
} from "@/lib/characters";

const SPRITE_PX = 72;
/** Stage height in px. Reserved server-side so nothing shifts on hydration. */
const STAGE_PX = 200;

export default function BuddyStage({
  buddies = HERO_BUDDIES,
}: {
  buddies?: BuddySpec[];
}) {
  const stageRef = useRef<HTMLDivElement>(null);
  const nodes = useRef(new Map<string, HTMLButtonElement>());
  const images = useRef(new Map<string, HTMLImageElement>());
  const sim = useRef<Stage | null>(null);

  useEffect(() => {
    const stage = new Stage(buddies, CHARACTER_FRAMES);
    sim.current = stage;

    // Ambient motion is a distraction for anyone who has asked for less of
    // it. Pokes still work: those are a direct response to a click, not
    // motion the visitor did not ask for.
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const applyMotion = () => {
      stage.frozen = motion.matches;
    };
    applyMotion();
    motion.addEventListener("change", applyMotion);

    // Preload every frame so the first walk cycle does not flicker.
    for (const spec of buddies) {
      const frames = CHARACTER_FRAMES[spec.character];
      for (const [state, count] of [
        ["idle", frames.idle],
        ["walk", frames.walk],
      ] as const) {
        for (let i = 0; i < count; i++) {
          const img = new Image();
          img.src = framePath(spec.character, state, i);
        }
      }
    }

    let raf = 0;
    let last = performance.now();

    const frame = (now: number) => {
      const dt = clampDt((now - last) / 1000);
      last = now;
      stage.tick(dt);

      const height = stageRef.current?.clientHeight ?? STAGE_PX;
      const width = stageRef.current?.clientWidth ?? 0;

      for (const buddy of stage.buddies) {
        const node = nodes.current.get(buddy.id);
        if (!node) continue;

        // Fractional coordinates become pixels against the measured box.
        // The hop is subtracted so hopping up is a smaller y, exactly as
        // AppController._tick does it.
        const x = buddy.x * width - SPRITE_PX / 2;
        const y = -stage.hopOffset(buddy.id) * height;
        node.style.transform =
          `translate(${x}px, ${y}px) scaleX(${buddy.facing})`;
        node.style.visibility = width > 0 ? "visible" : "hidden";

        const img = images.current.get(buddy.id);
        if (img) {
          const src = framePath(
            buddy.character,
            buddy.state,
            stage.frame(buddy.id),
          );
          // Assigning an unchanged src is a no-op in every browser, but
          // skipping it keeps the per-frame work to one string compare.
          if (!img.src.endsWith(src)) img.src = src;
        }
      }

      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      motion.removeEventListener("change", applyMotion);
      sim.current = null;
    };
  }, [buddies]);

  return (
    <div
      ref={stageRef}
      className="relative w-full overflow-hidden"
      style={{ height: STAGE_PX }}
    >
      {/* The floor the buddies stand on -- the bottom edge of the window. */}
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-px bg-floor"
      />
      {buddies.map((spec) => (
        <button
          key={spec.id}
          type="button"
          ref={(node) => {
            if (node) nodes.current.set(spec.id, node);
            else nodes.current.delete(spec.id);
          }}
          onClick={() => sim.current?.poke(spec.id)}
          aria-label={`Poke ${CHARACTERS[spec.character].label}`}
          className="absolute bottom-0 left-0 cursor-pointer border-0 bg-transparent p-0"
          style={{ width: SPRITE_PX, height: SPRITE_PX, visibility: "hidden" }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={(node) => {
              if (node) images.current.set(spec.id, node);
              else images.current.delete(spec.id);
            }}
            src={framePath(spec.character, "idle", 0)}
            alt=""
            width={SPRITE_PX}
            height={SPRITE_PX}
            className="pixelated size-full select-none"
            draggable={false}
            onError={(e) => {
              // A broken image is worse than a missing buddy.
              e.currentTarget.closest("button")?.remove();
            }}
          />
        </button>
      ))}
    </div>
  );
}
```

Three things worth understanding before changing this:

- **`<img>`, not `next/image`.** The frame `src` is swapped six times a
  second by direct DOM write. `next/image` exists to manage loading and
  layout for images React controls; here React deliberately does not control
  them after the first render. The eslint disable is the honest annotation
  of that choice, not a workaround.
- **Buddies start `visibility: hidden`** and only become visible once the
  stage has a measured width, so nothing flashes at the left edge before
  positions are known.
- **Resize needs no listener.** Positions recompute from fractional
  coordinates against `clientWidth` on every frame, so a resized window is
  already handled.

- [ ] **Step 2: Verify lint, build, and tests**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint && npm run build && npm test
```

Expected: all pass.

- [ ] **Step 3: Look at it in a browser**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run dev
```

`BuddyStage` is not on a page yet, so this step only confirms the dev server
starts clean. The real visual check is Step 3 of Task 8. Stop the server
with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/components/BuddyStage.tsx
git commit -m "$(cat <<'EOF'
feat: BuddyStage, the animated and pokeable hero

React renders the buddy list once; the rAF loop writes transforms and frame
srcs straight to the nodes. Sixty re-renders a second to move three sprites
would be absurd.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 8: The landing page

One scrolling page. Bands are full-width; content is capped at `max-w-5xl`.
The small server components it needs (`FeatureCard`, `Steps`, `Footer`) are
folded into this task because the landing page is their only consumer and
there is nothing to review in them independently.

**Files:**
- Create: `desktop-buddies/components/FeatureCard.tsx`
- Create: `desktop-buddies/components/Steps.tsx`
- Create: `desktop-buddies/components/Footer.tsx`
- Create: `desktop-buddies/lib/links.ts`
- Modify: `desktop-buddies/app/page.tsx` (full rewrite)

**Interfaces:**
- Consumes: `WindowFrame` (Task 6), `BuddyStage` (Task 7).
- Produces: `GITHUB_URL` from `lib/links.ts`, consumed by `Footer` here and by the download page in Task 9.

- [ ] **Step 1: Write the shared link constant**

Create `desktop-buddies/lib/links.ts`:

```ts
/** The repository's origin. Every GitHub link on the site resolves here. */
export const GITHUB_URL = "https://github.com/KainBC/Desktop-Buddies";
```

- [ ] **Step 2: Write the three server components**

Create `desktop-buddies/components/FeatureCard.tsx`:

```tsx
export default function FeatureCard({
  sprite,
  title,
  children,
}: {
  sprite: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={sprite}
        alt=""
        width={48}
        height={48}
        className="pixelated mb-4"
      />
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}
```

Create `desktop-buddies/components/Steps.tsx`:

```tsx
const STEPS = [
  {
    title: "Install it",
    body: "Run it from source today; packaged installers are on the way.",
  },
  {
    title: "Share a room code",
    body: "One person creates a room and sends the short code to friends.",
  },
  {
    title: "They show up",
    body: "Everyone's buddy appears and wanders on everyone else's screen.",
  },
];

export default function Steps() {
  return (
    <ol className="grid gap-6 sm:grid-cols-3">
      {STEPS.map((step, i) => (
        <li key={step.title}>
          <span className="mb-3 flex size-8 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-contrast">
            {i + 1}
          </span>
          <h3 className="mb-1 font-semibold">{step.title}</h3>
          <p className="text-sm leading-relaxed text-muted">{step.body}</p>
        </li>
      ))}
    </ol>
  );
}
```

Create `desktop-buddies/components/Footer.tsx`:

```tsx
import { GITHUB_URL } from "@/lib/links";

export default function Footer() {
  return (
    <footer className="border-t border-border py-8 text-sm text-muted">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6">
        <span>Desktop Buddies — an open-source desktop pet for friends.</span>
        <a href={GITHUB_URL} className="underline hover:text-foreground">
          GitHub
        </a>
      </div>
    </footer>
  );
}
```

- [ ] **Step 3: Write the landing page**

Replace the entire contents of `desktop-buddies/app/page.tsx` with:

```tsx
import Link from "next/link";
import BuddyStage from "@/components/BuddyStage";
import FeatureCard from "@/components/FeatureCard";
import Footer from "@/components/Footer";
import Steps from "@/components/Steps";
import WindowFrame from "@/components/WindowFrame";
import { GITHUB_URL } from "@/lib/links";

export default function Home() {
  return (
    <>
      <main>
        <section className="mx-auto max-w-5xl px-6 pt-12 pb-16">
          <WindowFrame>
            <div className="px-6 pt-12 text-center sm:px-12">
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
                Your friends live on your desktop
              </h1>
              <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
                Share a room code and everyone&apos;s buddy walks around on
                everyone&apos;s screen.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Link
                  href="/download"
                  className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-contrast hover:opacity-90"
                >
                  Download
                </Link>
                <a
                  href={GITHUB_URL}
                  className="rounded-md border border-border px-5 py-2.5 font-medium hover:bg-surface-2"
                >
                  GitHub
                </a>
              </div>
              <p className="mt-10 text-sm text-muted">Click a buddy.</p>
            </div>
            <BuddyStage />
          </WindowFrame>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <h2 className="mb-4 text-2xl font-semibold">What it is</h2>
          <p className="max-w-2xl text-lg leading-relaxed text-muted">
            Desktop Buddies puts a small animated character on your desktop
            that wanders around while you work. Join a room with friends and
            their characters appear on your screen too, moving in real time.
          </p>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <div className="grid gap-6 sm:grid-cols-3">
            <FeatureCard sprite="/sprites/placeholder_blob/walk/0.png" title="They wander">
              Each buddy idles and walks along the bottom of the screen on its
              own, in a frameless always-on-top window that never steals your
              clicks.
            </FeatureCard>
            <FeatureCard sprite="/sprites/placeholder_cat/idle/0.png" title="Chat bubbles">
              Press the global hotkey or click your buddy to type; what you
              send appears as a bubble over your character on everyone&apos;s
              desktop.
            </FeatureCard>
            <FeatureCard sprite="/sprites/placeholder_dog/walk/2.png" title="Pokes">
              Click someone else&apos;s buddy and it hops on their screen and
              on everyone else&apos;s.
            </FeatureCard>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <h2 className="mb-6 text-2xl font-semibold">How it works</h2>
          <Steps />
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-20 text-center">
          <Link
            href="/download"
            className="inline-block rounded-md bg-accent px-6 py-3 font-medium text-accent-contrast hover:opacity-90"
          >
            Get Desktop Buddies
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
```

The feature copy describes chat and pokes as they behave today. Do not add
download counts, testimonials, or user numbers — there are none.

- [ ] **Step 4: Verify lint, build, and tests**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint && npm run build && npm test
```

Expected: all pass, and the build lists `/` as static.

- [ ] **Step 5: Look at the page in a browser**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run dev
```

Open `http://localhost:3000` and confirm, before moving on:

1. Three buddies wander along the floor line at the bottom of the window
   frame, turning around at the edges rather than walking off.
2. Clicking a buddy makes it hop; clicking again mid-hop restarts the arc
   rather than stacking a second one.
3. The sprites are crisp, not blurry (that is `.pixelated` working).
4. Narrowing the window to phone width keeps the layout readable, with the
   feature cards stacking to one column.
5. Switching the OS to dark mode recolours everything, with no element left
   unreadable.
6. With reduced motion on
   (macOS: System Settings → Accessibility → Display → Reduce motion), the
   buddies stand still but still hop when clicked.

Stop the server with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/app/page.tsx desktop-buddies/components \
        desktop-buddies/lib/links.ts
git commit -m "$(cat <<'EOF'
feat: the landing page

Hero inside the window frame with live pokeable buddies, then what it is,
features, how it works, and a closing CTA.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 9: The download page

Built for installers that do not exist yet. The primary button is present,
OS-labelled, and visibly marked coming soon; the run-from-source path
underneath is what actually works today. Shipping a real build later is a
one-line edit to `lib/downloads.ts`, not a redesign.

**Files:**
- Create: `desktop-buddies/lib/downloads.ts`
- Create: `desktop-buddies/components/DownloadButton.tsx`
- Modify: `desktop-buddies/app/download/page.tsx` (full rewrite)

**Interfaces:**
- Consumes: `detectPlatform`, `Platform` (Task 4); `WindowFrame` (Task 6); `Footer`, `GITHUB_URL` (Task 8).
- Produces: `interface Build { platform: Platform; label: string; file: string; url: string | null }` and `BUILDS: Build[]` — the single place a real installer URL is filled in.

- [ ] **Step 1: Write the builds constant**

Create `desktop-buddies/lib/downloads.ts`:

```ts
import type { Platform } from "./os";

/**
 * Every build the site offers.
 *
 * `url: null` means "not shipped yet" and renders as a disabled, coming-soon
 * control. Shipping a real installer is filling in one string here -- that
 * is the whole point of collecting them in one file.
 */
export interface Build {
  platform: Platform;
  label: string;
  file: string;
  url: string | null;
}

export const BUILDS: Build[] = [
  { platform: "macos", label: "macOS", file: ".dmg", url: null },
  { platform: "windows", label: "Windows", file: ".exe", url: null },
  { platform: "linux", label: "Linux", file: "AppImage", url: null },
];
```

- [ ] **Step 2: Write the download button**

Create `desktop-buddies/components/DownloadButton.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { BUILDS } from "@/lib/downloads";
import { detectPlatform, type Platform } from "@/lib/os";

/**
 * The OS-labelled primary CTA.
 *
 * Detection runs after hydration, so the button server-renders in its
 * neutral state: no hydration mismatch, and no flash of the wrong platform.
 */
export default function DownloadButton() {
  const [platform, setPlatform] = useState<Platform | null>(null);

  useEffect(() => {
    setPlatform(detectPlatform(navigator.userAgent));
  }, []);

  const build = BUILDS.find((b) => b.platform === platform);
  const label = build ? `Download for ${build.label}` : "Download";

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        disabled
        aria-disabled="true"
        className="cursor-not-allowed rounded-md bg-accent px-6 py-3 font-medium text-accent-contrast opacity-60"
      >
        {label}
      </button>
      <span className="text-sm text-muted">
        Packaged builds aren&apos;t ready yet — run it from source below.
      </span>
    </div>
  );
}
```

- [ ] **Step 3: Write the download page**

Replace the entire contents of `desktop-buddies/app/download/page.tsx` with:

```tsx
import type { Metadata } from "next";
import Link from "next/link";
import DownloadButton from "@/components/DownloadButton";
import Footer from "@/components/Footer";
import WindowFrame from "@/components/WindowFrame";
import { BUILDS } from "@/lib/downloads";
import { GITHUB_URL } from "@/lib/links";

export const metadata: Metadata = {
  title: "Download — Desktop Buddies",
  description:
    "Get Desktop Buddies. Packaged installers are coming; running from " +
    "source works today.",
};

const SETUP = `git clone ${GITHUB_URL}.git
cd Desktop-Buddies
./run.sh setup
./run.sh client`;

export default function Download() {
  return (
    <>
      <main className="mx-auto max-w-5xl px-6 pt-12 pb-16">
        <WindowFrame title="Download">
          <div className="px-6 py-12 text-center sm:px-12">
            <h1 className="mb-8 text-3xl font-bold tracking-tight">
              Get Desktop Buddies
            </h1>
            <DownloadButton />
          </div>
        </WindowFrame>

        <section className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">All platforms</h2>
          <ul className="divide-y divide-border rounded-lg border border-border">
            {BUILDS.map((build) => (
              <li
                key={build.platform}
                className="flex items-center justify-between gap-4 px-5 py-4"
              >
                <span>
                  <span className="font-medium">{build.label}</span>{" "}
                  <span className="text-sm text-muted">{build.file}</span>
                </span>
                {build.url ? (
                  <a
                    href={build.url}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-contrast hover:opacity-90"
                  >
                    Download
                  </a>
                ) : (
                  <span className="text-sm text-muted">Coming soon</span>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">Run from source</h2>
          <p className="mb-4 text-muted">
            This is the path that works today. You need Python 3.11 or newer.
          </p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-surface p-5 font-mono text-sm">
            <code>{SETUP}</code>
          </pre>
          <p className="mt-4 text-muted">
            The client talks to a relay you host yourself. Point it at one
            with <code className="font-mono text-sm">BUDDIES_URL</code>, for
            example{" "}
            <code className="font-mono text-sm">
              BUDDIES_URL=ws://localhost:8765 ./run.sh client
            </code>
            , and start the relay with{" "}
            <code className="font-mono text-sm">./run.sh relay</code>.
          </p>
        </section>

        <section className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">Notes</h2>
          <ul className="list-disc space-y-2 pl-5 text-muted">
            <li>
              The global hotkey is ⌘⇧B on macOS and Ctrl+Shift+B elsewhere. It
              opens the chat input for your buddy; clicking your own buddy does
              the same.
            </li>
            <li>
              Set <code className="font-mono text-sm">BUDDIES_NO_HOTKEY=1</code>{" "}
              to opt out of the global hotkey.
            </li>
            <li>
              Source and issues live on{" "}
              <a href={GITHUB_URL} className="underline hover:text-foreground">
                GitHub
              </a>
              .
            </li>
          </ul>
        </section>

        <p className="pt-12">
          <Link href="/" className="text-muted underline hover:text-foreground">
            ← Back to the landing page
          </Link>
        </p>
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 4: Verify lint, build, and tests**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run lint && npm run build && npm test
```

Expected: all pass, and the build lists both `/` and `/download` as static.

- [ ] **Step 5: Look at the page in a browser**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend/desktop-buddies
npm run dev
```

Open `http://localhost:3000/download` and confirm:

1. The primary button reads "Download for macOS" (on a Mac) and is visibly
   disabled, with the coming-soon line beneath it.
2. There is no flash of a wrong platform label on load.
3. All three platforms are listed, each marked Coming soon.
4. The clone/setup block is correct and horizontally scrollable rather than
   overflowing on a narrow window.
5. Both links to `/` and to GitHub work.
6. Dark mode and phone width both hold up.

Stop the server with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add desktop-buddies/app/download/page.tsx \
        desktop-buddies/components/DownloadButton.tsx \
        desktop-buddies/lib/downloads.ts
git commit -m "$(cat <<'EOF'
feat: the download page

Built for installers that do not exist yet: the OS-labelled button is
present and marked coming soon, and the run-from-source path underneath is
what actually works today.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

### Task 10: Document the site and close out

**Files:**
- Modify: `CLAUDE.md` (architecture and module map)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Add the site to the architecture section**

In `CLAUDE.md`, in the **Architecture** section, add a fourth bullet after
the `shared/` one:

```markdown
- **`desktop-buddies/`** — the marketing site (Next 16 / React 19 / Tailwind
  4). A separate deliverable from the desktop client: it shares the sprite
  art and copies the client's animation feel, but imports no Python, talks
  to no relay, and has no build-time dependency on the rest of the repo.
  Its animation logic lives in a pure, React-free `lib/buddy.ts` ported from
  `Src/world.py` and `Src/poke.py`; its sprite frames are copies of the
  placeholder art in `Sprites/`, refreshed whenever that art changes.
```

- [ ] **Step 2: Add the site's modules to the key module map**

In `CLAUDE.md`, append these rows to the **Key module map** table:

```markdown
| `desktop-buddies/lib/buddy.ts` | `FrameCycler`, `Hop`, `Stage` — the site's pure simulation. No React, no DOM. |
| `desktop-buddies/lib/characters.ts` | Which characters the site ships, their frame counts, and who wanders in the hero. |
| `desktop-buddies/lib/os.ts` | userAgent → platform, for the OS-labelled download button. |
| `desktop-buddies/lib/downloads.ts` | `BUILDS` — the one place a real installer URL gets filled in. |
| `desktop-buddies/components/BuddyStage.tsx` | The rAF loop: renders and pokes the hero's buddies. |
```

- [ ] **Step 3: Add the site's commands**

In `CLAUDE.md`, in the **Commands** block, append:

```bash
cd desktop-buddies && npm install       # install website deps
cd desktop-buddies && npm run dev       # website at http://localhost:3000
cd desktop-buddies && npm test          # website unit tests (vitest)
```

- [ ] **Step 4: Run the whole verification suite one last time**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
python -m pytest -q
cd desktop-buddies
npm run lint && npm test && npm run build
```

Expected: the Python suite passes, lint is clean, 48 Vitest tests pass, and
the build reports `/` and `/download` as static. Paste the actual output
when reporting completion — do not claim it passed without it.

- [ ] **Step 5: Commit**

```bash
cd /Users/kaincorkeron/Desktop-Buddies-web-frontend
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: document the website in CLAUDE.md

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014RoHVmgdKTnC2EcTmBHqMr
EOF
)"
```

---

## Deferred

Carried from the spec's Open Considerations, deliberately not in this plan:

- **Deployment.** The site has no server needs, so Vercel or a static export
  to any host both work. Worth settling before the first real release.
- **A `/docs` section** for relay hosting, room codes, and troubleshooting —
  the natural next addition once someone other than the author needs to run
  a relay.
- **Real installer URLs**, which are a one-line edit to `lib/downloads.ts`
  when builds exist.
- **Real sprite art, and the layered sprite system.** Both land when the
  `pokes` branch reaches `main`. That retires the flat placeholders this
  site copies, so `public/sprites/` and `lib/characters.ts` are refreshed
  together at that point — and the right mechanism then is a small
  `tools/bake_web_sprites.py` reusing the client's own `resolve_layers()`
  and `composite_frames()`, rather than porting the layer stack to
  TypeScript for three static buddies.
