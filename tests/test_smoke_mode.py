import os
import subprocess
import sys
from pathlib import Path

from Src.version import VERSION

ROOT = Path(__file__).resolve().parent.parent


def test_smoke_test_passes_on_a_good_checkout(capsys):
    from Src.smoke import run_smoke_test
    assert run_smoke_test() == 0
    assert f"desktop-buddies {VERSION} ok" in capsys.readouterr().out


def test_smoke_test_fails_without_sprites(monkeypatch, tmp_path, capsys):
    import Src.resources
    from Src.smoke import run_smoke_test
    monkeypatch.setattr(Src.resources, "sprites_dir", lambda: tmp_path)
    assert run_smoke_test() == 1
    assert "FAILED" in capsys.readouterr().err


def test_module_entry_point_runs_smoke_test():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-m", "Src", "--smoke-test"],
                            cwd=ROOT, env=env, capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert f"desktop-buddies {VERSION} ok" in result.stdout
