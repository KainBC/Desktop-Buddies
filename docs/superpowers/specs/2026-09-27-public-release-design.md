# Public Release — Design

**Date:** 2026-09-27
**Status:** Approved in brainstorming, pending written-spec review

## Goal

A stranger can visit the website, download an installer for their OS, get
past the unsigned-app warning using on-page instructions, launch Desktop
Buddies, and join a room with friends through a hosted relay — with no
Python, no terminal, and no relay of their own.

## Decisions

| Question | Decision |
|---|---|
| Code signing | **None** for v1 (macOS and Windows ship unsigned). The pipeline leaves a slot per platform to add signing later. |
| Relay host | **Fly.io**, free `*.fly.dev` hostname. |
| Website host | **Vercel**, free `*.vercel.app` hostname. |
| Stale clients | **Update notice** in the launch menu, from GitHub Releases. No relay-enforced minimum version. |
| Packager | **PyInstaller** (one-dir), built per-OS on a GitHub Actions matrix. |
| First version | **`1.0.0`**. |

Out of scope: code signing/notarization, auto-update/self-install, client
reconnect after a relay restart, custom domains, CI-driven relay deploys,
the encounters and room-ownership features (their specs ride along as docs).

## Rollout order

Each stage depends on an address produced by the one before it.

1. **Baseline** — fast-forward `main` to the current branch and push.
2. **Relay** — deploy to Fly.io; this fixes the `wss://` URL.
3. **Client changes** — version, resources, default relay URL, hardening,
   update check, smoke test, packaging spec, CI workflow.
4. **Site** — downloads, first-launch instructions, Vercel deploy; this fixes
   the site URL, which is written into `Src/updates.py`.
5. **Tag `v1.0.0`** — CI builds and publishes the release; the site's
   `latest/download` links go live.

## 1. Release baseline and versioning

- `main` is fast-forwarded to the current branch (it has nothing unique) and
  pushed to `origin`. Releases are cut from `main` only. Stale local branches
  (`pokes`, `room-hosting`, `backup/encounters-prerebase`) are left untouched.
- The empty top-level `website/` directory is removed.
- **`Src/version.py`** holds `VERSION = "1.0.0"` — the single source of truth.
  - `pyproject.toml` keeps a static `version = "1.0.0"` (it declares no build
    backend, so dynamic versions are unavailable); a unit test asserts it
    equals `VERSION`, so the two cannot drift silently.
  - The launch menu shows `v{VERSION}` in small muted text.
  - A module constant, not `importlib.metadata`, because PyInstaller bundles
    do not reliably carry dist metadata.
- **Release process:** bump `VERSION`, commit, tag `vX.Y.Z`, push the tag. CI
  fails immediately if the tag does not equal `v` + `VERSION`.
- Semver-ish: patch = fixes, minor = features. A wire-format change that
  breaks older clients bumps minor and is called out in the release notes.

## 2. Hosted relay (Fly.io)

### Deploy

- `relay/Dockerfile`: `python:3.11-slim`, installs only `websockets`, copies
  `relay/` and `shared/`, runs `python -m relay`.
- `fly.toml` at repo root: internal port 8765, HTTP service with TLS
  terminated by Fly's proxy, served at `wss://<app>.fly.dev` (app name chosen
  at `fly launch`; the plan uses `desktop-buddies-relay`). A TCP health check
  on 8765.
- **Exactly one machine, always on:** `min_machines_running = 1`,
  `auto_stop_machines = "off"`, `auto_start_machines = true`, and the app is
  scaled to a count of 1. Rooms are in-memory, so a second machine would
  split rooms. `shared-cpu-1x` / 256 MB.
- Deploy is a manual `fly deploy` from the repo root; not wired into CI.

### Restart behaviour (accepted)

A deploy or crash drops every connection and forgets every room. The client
does not reconnect today (`NetClient` emits `disconnected`). For v1 this is
accepted; reconnect-and-restore is a future feature.

### Hardening (`relay/server.py`, `relay/room.py`, TDD)

- **Frame size cap:** `websockets.serve(..., max_size=64 * 1024)`.
- **Room size cap:** `MAX_MEMBERS = 16`. Joining a full room returns the
  existing `ERROR` message with `reason="Room is full"`; the client already
  surfaces `ERROR` reasons on join, so no client change is needed. The
  registry distinguishes "not found" from "full" (e.g. `join_room` returns a
  result the handler can map to either reason).
- **Logging** (stdout, visible via `fly logs`): connection open/close, room
  created, room joined, room emptied. Room codes and member ids are logged;
  names, appearances, and chat text are not.
- `BUDDIES_HOST` / `BUDDIES_PORT` env vars are unchanged.

### Client default URL

- `Src/__main__.py` defaults `BUDDIES_URL` to `wss://<app>.fly.dev` (a
  `DEFAULT_RELAY_URL` constant). The env var still overrides it.
- `run.sh client` sets `BUDDIES_URL` to `ws://localhost:8765` when unset, so
  local development never silently targets production. It also sets
  `BUDDIES_NO_UPDATE_CHECK=1`.
- `CLAUDE.md`'s "run a client" command already sets `BUDDIES_URL`; no change.

## 3. Build pipeline

### PyInstaller

- **`packaging/launch.py`** — entry script: imports and calls `Src.__main__`'s
  `main()`. (PyInstaller needs a script, not `-m`.)
- **`packaging/buddies.spec`** — one spec for all OSes, one-dir mode, windowed
  (no console). Branches on `sys.platform` for icon and platform-only hidden
  imports.
  - Data: `Sprites/` (including `manifest.json`), bundled at `Sprites/`.
    `Menu/` is not referenced by any code and is not bundled.
  - Hidden imports: `pynput`'s Linux backends (`pynput.keyboard._xorg`,
    `pynput.mouse._xorg`) on Linux; anything `Src/_hotkey_darwin.py` loads
    dynamically on macOS.
  - macOS: produces `Desktop Buddies.app` with bundle id
    `io.github.kainbc.desktopbuddies`, `CFBundleShortVersionString` from
    `VERSION`.
- **`Src/resources.py`** — `sprites_dir() -> Path`: returns
  `Path(sys._MEIPASS) / "Sprites"` when frozen, else the repo's `Sprites/`.
  `Src/app.py`'s `SPRITES_DIR` uses it. Profile storage already goes through
  `QStandardPaths.AppConfigLocation` and needs no change.
- **Icons** — `tools/make_icons.py` renders the default buddy's idle frame to
  `packaging/icons/buddy.icns`, `buddy.ico`, and `buddy.png` (256 px). The
  generated files are committed so CI does not need the icon toolchain.

### Linux launcher

The AppImage's `AppRun` sets `QT_QPA_PLATFORM=xcb` unless the user already
set it. Wayland forbids the always-on-top and absolute window positioning
the sprites rely on; XWayland provides them.

### Artifacts

Filenames carry no version, so GitHub's
`/releases/latest/download/<file>` URLs are stable across releases.

| Target | Runner | Packaging | Artifact |
|---|---|---|---|
| macOS arm64 | `macos-14` | `create-dmg` | `DesktopBuddies-mac-arm64.dmg` |
| macOS x64 | `macos-15-intel` | `create-dmg` | `DesktopBuddies-mac-x64.dmg` |
| Windows x64 | `windows-latest` | Inno Setup (`packaging/windows.iss`): per-user install, no UAC, Start Menu shortcut, uninstaller | `DesktopBuddies-windows-setup.exe` |
| Linux x86_64 | `ubuntu-22.04` | `appimagetool` + `packaging/linux/` (`AppRun`, `.desktop`, icon) | `DesktopBuddies-linux-x86_64.AppImage` |

Separate macOS builds instead of `universal2`: `actions/setup-python`'s
interpreters are single-arch, making a universal PyInstaller build fragile.

### Smoke test

`python -m Src --smoke-test` (and the frozen binary with the same flag):
sets `QT_QPA_PLATFORM=offscreen` if unset, loads the manifest, resolves and
composites the default appearance's frames, constructs the launch menu,
prints `desktop-buddies {VERSION} ok`, exits 0. Any exception exits non-zero.
It skips networking and the update check. CI runs it against the **built**
binary (inside the `.app` on macOS, the one-dir output on Windows, the
extracted AppImage on Linux), so a missing data file or hidden import fails
the build.

### Workflow — `.github/workflows/release.yml`

- Triggers: push of a `v*` tag; `workflow_dispatch` (manual).
- Jobs:
  1. `check` — verifies `github.ref_name == "v" + VERSION` (tag runs only);
     runs `python -m pytest` on Ubuntu with `QT_QPA_PLATFORM=offscreen`.
  2. `build` — matrix of the four targets: install deps + PyInstaller, build,
     package, smoke-test, upload the artifact.
  3. `release` (tag runs only) — downloads all artifacts, writes
     `SHA256SUMS.txt`, creates the GitHub Release titled `Desktop Buddies
     vX.Y.Z` marked latest, attaching the four artifacts and checksums.
- Manual runs stop after `build`; artifacts are downloadable from the run.
- Signing slot: each packaging step is its own named step so a future
  `codesign`/`notarytool` or `signtool` step slots in after it.

## 4. Update check

### Pure logic — `Src/updates.py`

- `parse_version(tag: str) -> tuple[int, int, int] | None` — tolerates a
  leading `v`; returns `None` for anything not `X.Y.Z` integers.
- `is_newer(latest: str, current: str) -> bool` — numeric tuple comparison;
  `False` if either side fails to parse.
- Constants: `RELEASES_API =
  "https://api.github.com/repos/KainBC/Desktop-Buddies/releases/latest"`,
  `DOWNLOAD_PAGE = "https://<site>.vercel.app/download"` (filled in at rollout
  stage 4).

### Fetch — Qt side

- On menu show, one `QNetworkAccessManager` GET to `RELEASES_API` with a
  5 s transfer timeout. Reads `tag_name` from the JSON body. Asynchronous; no
  thread, and create/join never wait on it.
- Skipped when `--smoke-test` is active or `BUDDIES_NO_UPDATE_CHECK=1`.
- Every failure (network, timeout, non-200, rate limit, bad JSON, missing
  `tag_name`, unparsable tag, no releases yet) silently shows nothing.

### UI

When `is_newer(tag, VERSION)`, a muted line under the version label:
**"Update available: vX.Y.Z — Download"**, where "Download" opens
`DOWNLOAD_PAGE` via `QDesktopServices.openUrl`. Shown only in the launch
menu; never mid-session.

### Tests

- `parse_version` / `is_newer`: `v` prefix, no prefix, malformed tags,
  multi-digit components (`1.10.0 > 1.9.0`), equal versions, older latest.
- Menu: a method that accepts a tag string (the seam the network callback
  calls) — asserts the line is hidden for equal/older/garbage tags and shown
  for a newer one. No real network in tests.

## 5. Website

### `lib/downloads.ts`

```ts
export interface Build {
  platform: Platform;
  label: string;         // "macOS", "Windows", "Linux"
  variant?: string;      // "Apple Silicon" | "Intel"
  file: string;          // ".dmg", ".exe", "AppImage"
  url: string | null;
  steps: string[];       // first-launch instructions for this build
}
```

- `RELEASE_BASE = "https://github.com/KainBC/Desktop-Buddies/releases/latest/download"`;
  each `url` is `${RELEASE_BASE}/<artifact filename from §3>`.
- Two macOS entries, Apple Silicon first.
- `primaryBuild(platform: Platform | null): Build | undefined` — first build
  for the platform (so Apple Silicon for macOS).
- `CHECKSUMS_URL = ${RELEASE_BASE}/SHA256SUMS.txt`.
- First-launch steps:
  - macOS: open the app; when macOS blocks it, open System Settings →
    Privacy & Security and click **Open Anyway**; confirm.
  - Windows: when SmartScreen shows "Windows protected your PC", click
    **More info → Run anyway**.
  - Linux: `chmod +x DesktopBuddies-linux-x86_64.AppImage`, then run it;
    needs a desktop with a compositor (transparent windows).

### `components/DownloadButton.tsx`

- Renders an `<a>` using `primaryBuild(platform)`: `href` is the build's URL
  once the platform is known; before hydration (server snapshot `null`) it is
  `#all-platforms` with the neutral "Download" label — the existing
  `useSyncExternalStore` pattern is kept, so no hydration mismatch.
- The helper line becomes a platform hint ("Unsigned app — first launch
  needs one extra click. See below.") and, on macOS, an "Intel Mac?" link to
  the Intel build.

### `app/download/page.tsx`

- "All platforms" list (`id="all-platforms"`): one row per build including
  the variant, a real Download link.
- New **"First launch"** section: one sentence on why the apps are unsigned
  (signing certificates cost money; the source is public), then each
  platform's `steps`, then a link to `SHA256SUMS.txt`.
- "Run from source": notes the client uses the hosted relay by default and
  `BUDDIES_URL` is for self-hosting a relay.
- Metadata description drops "installers are coming".

### Vercel

Import the GitHub repo in the Vercel dashboard with **Root Directory =
`desktop-buddies`**, framework Next.js (auto-detected), production branch
`main`. No `vercel.json`. The plan lists the exact clicks; the user performs
them once.

### Tests (vitest)

- Every build has a non-null `url` starting with `RELEASE_BASE`.
- The set of artifact filenames in `downloads.ts` equals the set CI produces
  (both sides reference the list in §3; the test hard-codes that list).
- `primaryBuild("macos")` is Apple Silicon; `primaryBuild(null)` is
  `undefined`.
- Every build has at least one step.
- Existing `os` and component tests keep passing.

## Documentation

`CLAUDE.md` gains a **Release** section (cut a release; deploy the relay;
where the site deploys from) and module-map rows for `Src/version.py`,
`Src/resources.py`, `Src/updates.py`, and `packaging/`. The client's
"Commands" block notes the hosted default relay.

## Risks

- **Antivirus false positives** on the unsigned Windows build are likely for
  some users. Mitigation: one-dir (not one-file) build, checksums published;
  signing is the real fix, deferred.
- **macOS Gatekeeper** UX for unsigned apps is deliberately awkward and may
  get worse in future macOS releases; the site's instructions must be kept
  current.
- **Single relay machine** is a single point of failure and a restart wipes
  all rooms. Accepted for v1.
- **Linux desktops** without a compositor, or pure-Wayland sessions without
  XWayland, cannot show the sprites correctly. Documented on the site.
