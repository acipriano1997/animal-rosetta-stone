"""Source-admitted PR0006 CLI; the direct analysis function is software-only."""
from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path

import pandas as pd

from .admission import AdmissionError, validate_admission
from .pr0006 import PR0006Config, run_pr0006


def _load_config(path: str) -> PR0006Config:
    raw = json.loads(Path(path).read_text())
    allowed = {f.name for f in fields(PR0006Config)}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Unknown PR0006 config fields: {unknown}")
    for key in ("baseline_numeric", "baseline_categorical"):
        if key in raw:
            raw[key] = tuple(raw[key])
    return PR0006Config(**raw)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Rights/provenance-admitted ARS PR0006 receiver run")
    ap.add_argument("csv", help="Reviewed and normalized, rights-cleared eligible receiver CSV")
    ap.add_argument("--source-file", required=True, help="Exact unmodified source bytes")
    ap.add_argument("--admission-manifest", required=True, help="Audited H0-H9 JSON declaration")
    ap.add_argument("--config", required=True, help="Frozen, source-approved PR0006 config JSON")
    ap.add_argument("--out", default="pr0006_candidate_result.json")
    args = ap.parse_args(argv)

    cfg = _load_config(args.config)
    manifest = json.loads(Path(args.admission_manifest).read_text())
    normalized = Path(args.csv)
    frame = pd.read_csv(normalized)
    try:
        run_cfg, receipt = validate_admission(
            frame, normalized, Path(args.source_file), manifest, cfg
        )
    except AdmissionError as exc:
        ap.error(str(exc))
    result = run_pr0006(frame, run_cfg)
    payload = {
        "admission": receipt,
        "registered_result": result.to_dict(),
        "scientific_claim_admissible": False,
        "crg_c_credit": "NOT_AUTOMATIC_REQUIRES_SEPARATE_ADJUDICATION",
        "evidence_weight": receipt["evidence_weight"],
    }
    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(args.out)


if __name__ == "__main__":
    main()
