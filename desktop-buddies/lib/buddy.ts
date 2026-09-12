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
