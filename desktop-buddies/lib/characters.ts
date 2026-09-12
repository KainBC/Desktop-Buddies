import type { AnimState, BuddySpec, CharacterFrames } from "./buddy";

/**
 * The sprite art copied into public/sprites by Task 5.
 *
 * Frame counts are recorded rather than discovered, so the loader never
 * guesses at what exists on disk. They come from `Sprites/<c>/sprite.json`
 * and the frame files themselves; `characters.test.ts` asserts this record
 * still matches what is actually there in both directions — a listed
 * character's frame count matches its files, and no character folder
 * exists on disk that this record omits — so the two cannot drift
 * silently in either direction.
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
