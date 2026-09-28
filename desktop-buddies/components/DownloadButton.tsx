"use client";

import { useSyncExternalStore } from "react";
import { BUILDS, primaryBuild } from "@/lib/downloads";
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
 * The OS-labelled primary download link.
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

  const build = primaryBuild(platform);
  const href = build?.url ?? "#all-platforms";
  const label = build ? `Download for ${build.label}` : "Download";
  const intel =
    platform === "macos"
      ? BUILDS.find((b) => b.platform === "macos" && b.variant === "Intel")
      : undefined;

  return (
    <div className="flex flex-col items-center gap-2">
      <a
        href={href}
        className="rounded-md bg-accent px-6 py-3 font-medium text-accent-contrast hover:opacity-90"
      >
        {label}
      </a>
      <span className="text-sm text-muted">
        {build ? (
          <>
            Unsigned app — the first launch needs one extra click.{" "}
            <a href="#first-launch" className="underline hover:text-foreground">
              How?
            </a>
          </>
        ) : (
          "macOS, Windows and Linux — pick yours below."
        )}
      </span>
      {intel?.url ? (
        <a
          href={intel.url}
          className="text-sm text-muted underline hover:text-foreground"
        >
          Intel Mac?
        </a>
      ) : null}
    </div>
  );
}
