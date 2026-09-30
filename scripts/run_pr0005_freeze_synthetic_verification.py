"""ZERO_SYNTHETIC verification of the PR0005 RUN-005 freeze package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ars_receiver_harness.pr0005_artifacts import freeze_run005_package
try:
    from scripts.run_pr0005_synthetic_verification import synthetic_group2
except ModuleNotFoundError:
    from run_pr0005_synthetic_verification import synthetic_group2


def main() -> None:
    ap=argparse.ArgumentParser(description="Verify RUN-005 artifact freeze on synthetic data only")
    ap.add_argument("--out-dir",default="build/pr0005_freeze_synthetic")
    args=ap.parse_args()
    out=Path(args.out_dir)
    out.mkdir(parents=True,exist_ok=True)

    frame=synthetic_group2()
    csv_path=out/"synthetic_group2_normalized.csv"
    frame.to_csv(csv_path,index=False)
    csv_sha=hashlib.sha256(csv_path.read_bytes()).hexdigest()

    input_manifest={
        "dataset_id":"ZERO_SYNTHETIC",
        "evidence_weight":"ZERO_SYNTHETIC",
        "normalized_rows":104,
        "normalized_csv_sha256":csv_sha,
        "raw_source_identities_in_normalized_csv":False,
        "group1_rows_materialized":False,
        "pr0005_executed":False,
        "source_sha256":"ZERO_SYNTHETIC",
        "eligible_source_row_set_sha256":"ZERO_SYNTHETIC",
        "identity_namespace_fingerprint":"ZERO_SYNTHETIC",
    }
    manifest_path=out/"synthetic_materialization_manifest.json"
    manifest_path.write_text(json.dumps(input_manifest,indent=2,sort_keys=True)+"\n")

    freeze_dir=out/"run005_freeze"
    manifest=freeze_run005_package(
        csv_path,manifest_path,freeze_dir,evidence_weight="ZERO_SYNTHETIC"
    )
    print(json.dumps({
        "status":"PASS_ZERO_SYNTHETIC_RUN005_FREEZE",
        "rows":manifest["development_rows"],
        "dyads":manifest["primary_unordered_dyads"],
        "full_group2_models_frozen":manifest["full_group2_b1_b2_fitted_and_frozen"],
        "group1_accessed":False,
        "scientific_claim_admissible":False,
        "output":str(freeze_dir/"run005_freeze_manifest.json"),
    }))


if __name__=="__main__":
    main()
