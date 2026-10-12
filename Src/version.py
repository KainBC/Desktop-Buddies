"""The client's version. The single source of truth.

Bump this, commit, then tag `v<VERSION>`; CI refuses a tag that doesn't
match. A module constant rather than package metadata because PyInstaller
bundles don't reliably carry dist-info.
"""
VERSION = "1.0.0"
