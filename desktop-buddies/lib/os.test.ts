import { describe, expect, it } from "vitest";
import { detectPlatform, type Platform } from "./os";

const CASES: Array<[string, Platform | null]> = [
  [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "macos",
  ],
  [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 " +
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "macos",
  ],
  [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "windows",
  ],
  [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "linux",
  ],
  [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 " +
      "Firefox/121.0",
    "linux",
  ],
  // Phones get the neutral label: there is nothing here they can install.
  [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) " +
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148",
    null,
  ],
  [
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 " +
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148",
    null,
  ],
  [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    null,
  ],
  ["", null],
  ["some unknown agent", null],
];

describe("detectPlatform", () => {
  it.each(CASES)("maps %s", (ua, expected) => {
    expect(detectPlatform(ua)).toBe(expected);
  });
});
