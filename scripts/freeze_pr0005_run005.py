"""Freeze PR0005 RUN-005 OOF and full-Group-2 B1/B2 artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ars_receiver_harness.pr0005_artifacts import freeze_run005_package


def main() -> None:
    ap = argparse.ArgumentParser(description="Freeze manifest-bound PR0005 RUN-005 artifacts")
    ap.add_argument("--normalized-csv", required=True)
    ap.add_argument("--materialization-manifest", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument(
        "--evidence-weight",
        required=True,
        choices=("ZERO_SYNTHETIC", "D0019_EMPIRICAL"),
    )
    args = ap.parse_args()

    manifest = freeze_run005_package(
        Path(args.normalized_csv),
        Path(args.materialization_manifest),
        Path(args.output_dir),
        evidence_weight=args.evidence_weight,
    )
    print(json.dumps({
        "status": "RUN005_FROZEN",
        "evidence_weight": manifest["evidence_weight"],
        "development_rows": manifest["development_rows"],
        "primary_unordered_dyads": manifest["primary_unordered_dyads"],
        "group1_accessed": manifest["group1_accessed"],
        "scientific_claim_admissible": manifest["scientific_claim_admissible"],
        "manifest": str(Path(args.output_dir) / "run005_freeze_manifest.json"),
    }))


if __name__ == "__main__":
    main()
