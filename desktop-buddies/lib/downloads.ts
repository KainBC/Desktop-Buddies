import type { Platform } from "./os";

/**
 * Every build the site offers.
 *
 * `url: null` means "not shipped yet" and renders as a disabled, coming-soon
 * control. Shipping a real installer is filling in one string here -- that
 * is the whole point of collecting them in one file.
 */
export interface Build {
  platform: Platform;
  label: string;
  file: string;
  url: string | null;
}

export const BUILDS: Build[] = [
  { platform: "macos", label: "macOS", file: ".dmg", url: null },
  { platform: "windows", label: "Windows", file: ".exe", url: null },
  { platform: "linux", label: "Linux", file: "AppImage", url: null },
];
