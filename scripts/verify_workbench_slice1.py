from __future__ import annotations

import json
import os
from pathlib import Path

from ars_workbench.store import WorkbenchStore


def main() -> None:
    store = WorkbenchStore()
    s = store.snapshot()
    known = set(s["provenance"])

    refs = list(s["species"]["provenance_ids"]) + list(s["question"]["provenance_ids"])
    for row in s["hypotheses"] + s["datasets"] + s["runs"] + s["software_verification"]:
        refs.extend(row.get("provenance_ids", []))

    d0019 = store.dataset_get("D0019")
    d0025 = store.dataset_get("D0025")
    run004 = store.run_get("RUN-PT-RQ0001-004")
    d0019_runs = [r for r in store.run_list() if r["dataset_id"] == "D0019"]

    checks = {
        "all_provenance_resolves": bool(refs) and set(refs) <= known,
        "d0020_null_is_bounded": run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT" and "bounded" in run004["interpretation_ceiling"].lower(),
        "d0019_metadata_only": d0019["availability"] == "GATED_METADATA_ONLY" and all(r["state"] == "CLOSED" for r in d0019_runs),
        "d0019_empirical_closure_current": (
            d0019["empirical_state"] == "D0019_PR0005_EMPIRICAL_CLOSED_MIXED"
            and d0019["rights_state"] == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"
            and "access-controlled" in d0019["gate"]
            and all(r["disposition"] == "MIXED" for r in d0019_runs)
        ),
        "d0025_metadata_only": d0025["availability"] == "GATED_METADATA_ONLY" and not any(r["dataset_id"] == "D0025" for r in store.run_list()),
        "zero_synthetic_segregated": all(v["class"] == "ZERO_SYNTHETIC" and not v["biological_evidence"] for v in store.software_verification_list()),
        "no_semantic_authority_in_corpora": all(d["semantic_authority"] == "NONE" for d in s["datasets"]),
        "comparison_gate_not_promoted": s["species"]["comparison_readiness"]["overall"] == "NOT_COMPARISON_READY" and s["species"]["comparison_readiness"]["CRG-C"] == "PASS",
        "crg_d_controls": s["species"]["comparison_readiness"]["controlling_criterion"] == "CRG-D" and s["species"]["comparison_readiness"]["CRG-D"] == "PARTIAL",
        "bonobo_deferred": s["species"]["comparison_readiness"]["bonobo_activation"] == "DEFERRED",
    }
    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 1",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "snapshot_id": s["snapshot_id"],
        "mode": s["mode"],
        "checks": checks,
        "all_passed": all(checks.values()),
        "scientific_effect": "NONE",
        "biological_evidence": False,
    }
    out = Path("build/workbench_slice1_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
