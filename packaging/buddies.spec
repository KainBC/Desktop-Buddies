# PyInstaller spec for Desktop Buddies. Build from the repo root:
#   pyinstaller --noconfirm --clean packaging/buddies.spec
# One-dir (not one-file): faster start, fewer antivirus false positives,
# and required for a macOS .app bundle.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent            # noqa: F821 (SPECPATH is injected)
sys.path.insert(0, str(ROOT))
from Src.version import VERSION        # noqa: E402

hidden = []
if sys.platform.startswith("linux"):
    hidden += ["pynput.keyboard._xorg", "pynput.mouse._xorg"]
elif sys.platform == "win32":
    hidden += ["pynput.keyboard._win32", "pynput.mouse._win32"]

icon = str(ROOT / "packaging" / "icons" / "buddy.png")

a = Analysis(                           # noqa: F821
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "Sprites"), "Sprites")],
    hiddenimports=hidden,
    excludes=["pytest", "tkinter"],
)
pyz = PYZ(a.pure)                       # noqa: F821
exe = EXE(                              # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="DesktopBuddies",
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DesktopBuddies")  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(                       # noqa: F821
        coll,
        name="Desktop Buddies.app",
        icon=icon,
        bundle_identifier="io.github.kainbc.desktopbuddies",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
        },
    )
