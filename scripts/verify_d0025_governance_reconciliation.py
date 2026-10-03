from __future__ import annotations

import json
import os
from pathlib import Path

from ars_workbench.store import WorkbenchStore


EXPECTED_STATE = (
    "D0025_V1_H1_SHA256_VERIFIED_H2_ROW3_HEADERS_LOCATED_"
    "H3_PR0006_FULL_PRIMARY_SCHEMA_NOT_DEMONSTRATED_HELD"
)


def main() -> None:
    store = WorkbenchStore()
    d0025 = store.dataset_get("D0025")
    species = store.species_get("SP001")
    manifest = json.loads(
        Path("contracts/d0025_v1_verified_source_snapshot.json").read_text(
            encoding="utf-8"
        )
    )

    checks = {
        "h1_manifest_reports_cc_by_4": (
            manifest["license_as_reported"]["name"] == "CC BY 4.0"
        ),
        "h1_manifest_not_rights_adjudication": (
            manifest["status"]
            == "IMMUTABLE_H1_VERIFICATION_SNAPSHOT_NOT_RIGHTS_ADJUDICATION"
        ),
        "workbench_current_h1_h2_h3_state": d0025["empirical_state"] == EXPECTED_STATE,
        "item_license_metadata_reconciled": (
            "CC BY 4.0" in d0025["rights_state"]
            and "not blanket rights adjudication" in d0025["rights_state"].lower()
        ),
        "h3_schema_remains_held": (
            "H3 remains HELD_SCHEMA" in d0025["gate"]
            and "original unfiltered event-level extract" in d0025["gate"]
        ),
        "no_obsolete_prebyte_or_unverified_license_state": (
            "PREBYTE" not in d0025["empirical_state"]
            and "ITEM_LEVEL_LICENSE_UNVERIFIED" not in d0025["rights_state"]
        ),
        "no_scientific_promotion": (
            d0025["semantic_authority"] == "NONE"
            and species["comparison_readiness"]["CRG-C"] == "NOT_PASS"
            and species["comparison_readiness"]["overall"]
            == "NOT_COMPARISON_READY"
        ),
    }

    receipt = {
        "verification": "D0025 H1/H2 governance-state reconciliation",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks,
        "all_passed": all(checks.values()),
        "scientific_effect": "NONE",
        "biological_evidence": False,
        "empirical_execution": "NOT_RUN",
        "rights_boundary": (
            "source-reported item-level CC BY 4.0 metadata verified; not blanket rights adjudication"
        ),
    }
    out = Path("build/d0025_governance_reconciliation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
