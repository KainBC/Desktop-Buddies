/**
 * userAgent -> desktop platform. Pure: no `navigator`, no DOM.
 *
 * The caller passes the string, so this is unit testable and so the
 * download button can server-render neutral and only narrow after
 * hydration. Phones and anything unrecognised map to null, which the button
 * renders as a plain "Download".
 */
export type Platform = "macos" | "windows" | "linux";

export function detectPlatform(ua: string): Platform | null {
  // Mobile first: an iPhone's UA contains "Mac OS X" and an Android's
  // contains "Linux", so checking desktops first would misreport both.
  if (/iPhone|iPad|iPod|Android/i.test(ua)) return null;
  if (/Macintosh|Mac OS X/i.test(ua)) return "macos";
  if (/Windows/i.test(ua)) return "windows";
  if (/Linux|X11/i.test(ua)) return "linux";
  return null;
}
