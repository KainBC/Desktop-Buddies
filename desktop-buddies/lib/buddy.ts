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
