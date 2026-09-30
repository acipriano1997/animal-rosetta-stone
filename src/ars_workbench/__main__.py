from __future__ import annotations

import argparse

from .app import serve


def main() -> None:
    ap = argparse.ArgumentParser(description="Run Rosetta Research Workbench Phase I Slice 1")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
