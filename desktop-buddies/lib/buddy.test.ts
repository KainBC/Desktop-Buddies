import { describe, expect, it } from "vitest";
import {
  clampDt,
  FrameCycler,
  Hop,
  MAX_DT,
  MAX_X,
  MIN_X,
  Stage,
  WALK_SPEED,
  type BuddySpec,
  type CharacterFrames,
} from "./buddy";

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
