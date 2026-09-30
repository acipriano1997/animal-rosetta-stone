from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path

import pandas as pd

from .pr0006 import PR0006Config, run_pr0006


def _load_config(path: str | None) -> PR0006Config:
    if path is None:
        return PR0006Config()
    raw = json.loads(Path(path).read_text())
    allowed = {f.name for f in fields(PR0006Config)}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Unknown PR0006 config fields: {unknown}")
    for key in ("baseline_numeric", "baseline_categorical"):
        if key in raw:
            raw[key] = tuple(raw[key])
    return PR0006Config(**raw)


def main() -> None:
    ap = argparse.ArgumentParser(description="ARS PR0006 receiver runner")
    ap.add_argument("csv", help="Normalized, rights-cleared receiver CSV")
    ap.add_argument("--config", help="JSON config overriding PR0006Config fields")
    ap.add_argument("--out", default="pr0006_result.json")
    args = ap.parse_args()
    cfg = _load_config(args.config)
    df = pd.read_csv(args.csv)
    result = run_pr0006(df, cfg)
    Path(args.out).write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    print(args.out)


if __name__ == "__main__":
    main()
