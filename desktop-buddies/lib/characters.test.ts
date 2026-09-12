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

  // The manifest records frame counts instead of discovering them. This
  // catches the record and a manifest entry's art drifting apart in one
  // direction: a listed character whose on-disk frames no longer match.
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

  // The test above only walks characters the manifest already knows about,
  // so it can't catch the other direction: a character folder dropped
  // under public/sprites/ but never added to the manifest, or a manifest
  // entry with no art on disk at all. This closes that gap with equality,
  // not a subset check, since either omission is a defect worth catching.
  it("has no character on disk that the manifest omits", () => {
    const onDisk = readdirSync(PUBLIC_SPRITES, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
      .sort();
    expect(onDisk).toEqual(Object.keys(CHARACTER_FRAMES).sort());
  });
});
