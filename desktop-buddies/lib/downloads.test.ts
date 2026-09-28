import { describe, expect, it } from "vitest";
import {
  BUILDS,
  CHECKSUMS_URL,
  RELEASE_BASE,
  buildName,
  primaryBuild,
} from "./downloads";

// Must equal ARTIFACTS in tests/test_packaging.py and the `artifact:` names
// in .github/workflows/release.yml.
const ARTIFACTS = [
  "DesktopBuddies-mac-arm64.dmg",
  "DesktopBuddies-mac-x64.dmg",
  "DesktopBuddies-windows-setup.exe",
  "DesktopBuddies-linux-x86_64.AppImage",
];

describe("BUILDS", () => {
  it("downloads every build from the latest release", () => {
    for (const build of BUILDS) {
      expect(build.url).not.toBeNull();
      expect(build.url!.startsWith(`${RELEASE_BASE}/`)).toBe(true);
    }
  });

  it("ships exactly the artifacts CI produces", () => {
    const files = BUILDS.map((b) => b.url!.slice(RELEASE_BASE.length + 1));
    expect([...files].sort()).toEqual([...ARTIFACTS].sort());
  });

  it("gives every build first-launch steps", () => {
    for (const build of BUILDS) expect(build.steps.length).toBeGreaterThan(0);
  });

  it("tells Linux users the AppImage is x86_64 only", () => {
    const linux = primaryBuild("linux")!;
    expect(linux.steps.join(" ")).toMatch(/x86_64/);
  });

  it("links the checksums", () => {
    expect(CHECKSUMS_URL).toBe(`${RELEASE_BASE}/SHA256SUMS.txt`);
  });
});

describe("primaryBuild", () => {
  it("offers Apple Silicon to macOS (userAgent can't tell the chip)", () => {
    expect(primaryBuild("macos")?.variant).toBe("Apple Silicon");
  });

  it("finds Windows and Linux", () => {
    expect(primaryBuild("windows")?.file).toBe(".exe");
    expect(primaryBuild("linux")?.file).toBe("AppImage");
  });

  it("offers nothing for an unknown platform", () => {
    expect(primaryBuild(null)).toBeUndefined();
  });
});

describe("buildName", () => {
  it("includes the variant when there is one", () => {
    const intel = BUILDS.find((b) => b.variant === "Intel")!;
    expect(buildName(intel)).toBe("macOS (Intel)");
    expect(buildName(primaryBuild("windows")!)).toBe("Windows");
  });
});
