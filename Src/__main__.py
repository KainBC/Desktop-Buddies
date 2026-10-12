import os
import sys
from collections.abc import Mapping

DEFAULT_RELAY_URL = "wss://desktop-buddies-relay.fly.dev"


def relay_url(env: Mapping[str, str]) -> str:
    """`BUDDIES_URL` overrides the hosted relay (self-hosting, local dev)."""
    return env.get("BUDDIES_URL") or DEFAULT_RELAY_URL


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--smoke-test" in argv:
        from Src.smoke import run_smoke_test
        return run_smoke_test()
    from Src.app import AppController
    return AppController(relay_url(os.environ)).run()


if __name__ == "__main__":
    raise SystemExit(main())
