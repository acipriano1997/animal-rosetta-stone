"""Execute locked D0019 PR0005 RUN-006 after an empirical RUN-005 freeze."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ars_receiver_harness.pr0005_transfer import run_d0019_group1_transfer


def main() -> None:
    ap=argparse.ArgumentParser(description="One-time locked PR0005 RUN-006 transfer")
    ap.add_argument("--run005-freeze-dir",required=True)
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--pins",default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk",default="contracts/d0019_rdc004_source_crosswalk_v0_2.json")
    ap.add_argument("--eligibility",default="contracts/d0019_group2_eligibility_rules_v0_1.json")
    ap.add_argument("--group1-procedure",default="contracts/d0019_group1_transfer_procedure_v0_1.json")
    args=ap.parse_args()

    secret=os.environ.get("ARS_D0019_HMAC_KEY","").encode()
    if len(secret)<32:
        raise SystemExit("ARS_D0019_HMAC_KEY must be configured with at least 32 bytes")

    freeze_dir=Path(args.run005_freeze_dir)
    freeze_manifest=json.loads((freeze_dir/"run005_freeze_manifest.json").read_text())
    pins=json.loads(Path(args.pins).read_text())
    crosswalk=json.loads(Path(args.crosswalk).read_text())
    eligibility=json.loads(Path(args.eligibility).read_text())
    group1=json.loads(Path(args.group1_procedure).read_text())

    try:
        from scripts.probe_d0019_source import public_item,fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item,fetch_source

    manifest=run_d0019_group1_transfer(
        item=public_item(),
        pins=pins,
        crosswalk=crosswalk,
        eligibility=eligibility,
        group1_procedure=group1,
        run005_freeze_manifest=freeze_manifest,
        run005_freeze_dir=freeze_dir,
        secret=secret,
        fetch=fetch_source,
        output_dir=Path(args.output_dir),
        evidence_weight="D0019_EMPIRICAL",
    )
    print(json.dumps({
        "status":"RUN006_LOCKED_TRANSFER_COMPLETE",
        "group1_eligible_rows":manifest["group1_eligible_rows"],
        "models_refit_on_group1":manifest["models_refit_on_group1"],
        "final_pr0005_disposition":manifest["final_pr0005_disposition"],
        "crg_c_credit":manifest["crg_c_credit"],
        "manifest":str(Path(args.output_dir)/"run006_transfer_manifest.json"),
    }))


if __name__=="__main__":
    main()
