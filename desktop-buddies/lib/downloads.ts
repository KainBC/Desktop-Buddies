import type { Platform } from "./os";

/**
 * Every build the site offers.
 *
 * URLs use GitHub's `releases/latest/download/<file>` redirect and the
 * artifact names carry no version, so these never change per release. The
 * names are a contract with .github/workflows/release.yml, checked by
 * downloads.test.ts and tests/test_packaging.py.
 */
export const RELEASE_BASE =
  "https://github.com/KainBC/Desktop-Buddies/releases/latest/download";

export const CHECKSUMS_URL = `${RELEASE_BASE}/SHA256SUMS.txt`;

export interface Build {
  platform: Platform;
  label: string;
  /** Distinguishes builds that share a platform, e.g. the two Macs. */
  variant?: string;
  file: string;
  /** `null` renders as a disabled "Coming soon" row. */
  url: string | null;
  /** First-launch instructions: the builds are unsigned. */
  steps: string[];
}

const MAC_STEPS = [
  "Open the .dmg and drag Desktop Buddies into Applications.",
  "Open Desktop Buddies. macOS says it can't verify the app — click Done.",
  "Open System Settings → Privacy & Security, scroll down, and click Open Anyway next to Desktop Buddies.",
  "Confirm with Open Anyway and your password. After this it opens normally.",
];

const WINDOWS_STEPS = [
  "Run DesktopBuddies-windows-setup.exe.",
  "If SmartScreen says “Windows protected your PC”, click More info, then Run anyway.",
  "Finish the installer. Desktop Buddies is in your Start menu.",
];

const LINUX_STEPS = [
  "This AppImage is for x86_64 PCs only (not ARM).",
  "Make it executable: chmod +x DesktopBuddies-linux-x86_64.AppImage",
  "Run it: ./DesktopBuddies-linux-x86_64.AppImage",
  "Needs a desktop with a compositor so buddies can be transparent. On Wayland it runs through XWayland.",
];

export const BUILDS: Build[] = [
  {
    platform: "macos",
    label: "macOS",
    variant: "Apple Silicon",
    file: ".dmg",
    url: `${RELEASE_BASE}/DesktopBuddies-mac-arm64.dmg`,
    steps: MAC_STEPS,
  },
  {
    platform: "macos",
    label: "macOS",
    variant: "Intel",
    file: ".dmg",
    url: `${RELEASE_BASE}/DesktopBuddies-mac-x64.dmg`,
    steps: MAC_STEPS,
  },
  {
    platform: "windows",
    label: "Windows",
    file: ".exe",
    url: `${RELEASE_BASE}/DesktopBuddies-windows-setup.exe`,
    steps: WINDOWS_STEPS,
  },
  {
    platform: "linux",
    label: "Linux",
    file: "AppImage",
    url: `${RELEASE_BASE}/DesktopBuddies-linux-x86_64.AppImage`,
    steps: LINUX_STEPS,
  },
];

/** The build the big button offers: the first one listed for the platform. */
export function primaryBuild(platform: Platform | null): Build | undefined {
  if (platform === null) return undefined;
  return BUILDS.find((b) => b.platform === platform);
}

export function buildName(build: Build): string {
  return build.variant ? `${build.label} (${build.variant})` : build.label;
}
