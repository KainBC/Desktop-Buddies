"""The artifact names are a contract between CI, the packaging scripts, and
the website's download links. These tests fail if any side drifts."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARTIFACTS = [
    "DesktopBuddies-mac-arm64.dmg",
    "DesktopBuddies-mac-x64.dmg",
    "DesktopBuddies-windows-setup.exe",
    "DesktopBuddies-linux-x86_64.AppImage",
]


def test_inno_setup_output_name():
    iss = (ROOT / "packaging" / "windows.iss").read_text()
    assert "OutputBaseFilename=DesktopBuddies-windows-setup" in iss
    assert "PrivilegesRequired=lowest" in iss


def test_appimage_output_name_and_x11_default():
    script = (ROOT / "packaging" / "linux" / "build_appimage.sh").read_text()
    assert "out/DesktopBuddies-linux-x86_64.AppImage" in script
    apprun = ROOT / "packaging" / "linux" / "AppRun"
    assert 'QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"' in apprun.read_text()
    assert os.access(apprun, os.X_OK)


def test_workflow_builds_every_artifact():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    for name in ARTIFACTS:
        assert f"artifact: {name}" in workflow, name
    assert "--smoke-test" in workflow
    assert "SHA256SUMS.txt" in workflow
