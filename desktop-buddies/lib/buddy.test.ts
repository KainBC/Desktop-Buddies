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
