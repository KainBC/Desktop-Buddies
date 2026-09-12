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
        const x = buddy.x * Math.max(0, width - SPRITE_PX);
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
              // A broken image is worse than a missing buddy, but the node
              // is React-owned -- we don't rip it out of the DOM (that's
              // only safe because this list happens never to re-render,
              // and nothing enforces that invariant). Instead we hide the
              // button and drop this buddy's entries from the ref maps so
              // the rAF loop stops writing transforms to a node it can no
              // longer see.
              const button = e.currentTarget.closest("button");
              if (button) button.hidden = true;
              nodes.current.delete(spec.id);
              images.current.delete(spec.id);
            }}
          />
        </button>
      ))}
    </div>
  );
}
