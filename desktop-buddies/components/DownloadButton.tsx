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
    // Intentional one-shot: `navigator` only exists post-hydration, so this
    // read (and the state it narrows) cannot happen during render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
