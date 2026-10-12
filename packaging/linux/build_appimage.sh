#!/usr/bin/env bash
# Assemble dist/DesktopBuddies (PyInstaller one-dir) into an AppImage.
# Run from anywhere after `pyinstaller packaging/buddies.spec` on Linux.
set -euo pipefail
cd "$(dirname "$0")/../.."

APPDIR=build/AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr" out
cp -R dist/DesktopBuddies/. "$APPDIR/usr/"
install -m 755 packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/desktop-buddies.desktop "$APPDIR/"
cp packaging/icons/buddy.png "$APPDIR/desktop-buddies.png"

TOOL=build/appimagetool-x86_64.AppImage
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
# CI runners have no FUSE; extract-and-run avoids needing it.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" \
  out/DesktopBuddies-linux-x86_64.AppImage
