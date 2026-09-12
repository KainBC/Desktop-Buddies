"use client";

import { useSyncExternalStore } from "react";
import { BUILDS } from "@/lib/downloads";
import { detectPlatform, type Platform } from "@/lib/os";

/**
 * The userAgent never changes for the life of a page, so there is nothing to
 * subscribe to and the snapshot is computed once and cached. Caching is not
 * an optimisation here: useSyncExternalStore re-reads the snapshot on every
 * render and requires a stable value, so recomputing would be wasteful at
 * best.
 */
const subscribe = () => () => {};

let cached: Platform | null | undefined;
function clientPlatform(): Platform | null {
  if (cached === undefined) cached = detectPlatform(navigator.userAgent);
  return cached;
}

/** The server cannot know the platform, so it renders the neutral label. */
const serverPlatform = (): Platform | null => null;

/**
 * The OS-labelled primary CTA.
 *
 * `useSyncExternalStore`'s `getServerSnapshot` returns the neutral value
 * during SSR and hydration and `getSnapshot` returns the real one
 * afterwards, so the button server-renders in its neutral state by
 * construction: no hydration mismatch, and no flash of the wrong platform.
 */
export default function DownloadButton() {
  const platform = useSyncExternalStore(
    subscribe,
    clientPlatform,
    serverPlatform,
  );

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
