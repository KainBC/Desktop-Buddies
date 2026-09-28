import sys
from pathlib import Path

from Src.resources import sprites_dir

ROOT = Path(__file__).resolve().parent.parent


def test_source_checkout_uses_repo_sprites(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert sprites_dir() == ROOT / "Sprites"
    assert (sprites_dir() / "manifest.json").is_file()


def test_frozen_bundle_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert sprites_dir() == tmp_path / "Sprites"
