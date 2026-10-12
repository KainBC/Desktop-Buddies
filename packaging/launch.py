"""PyInstaller entry point: PyInstaller needs a script, not `python -m`."""
from Src.__main__ import main

raise SystemExit(main())
