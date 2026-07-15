import os

from Src.app import AppController

if __name__ == "__main__":
    url = os.environ.get("BUDDIES_URL", "ws://localhost:8765")
    raise SystemExit(AppController(url).run())
