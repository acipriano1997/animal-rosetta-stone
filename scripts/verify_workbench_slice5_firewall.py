from __future__ import annotations

import json
import os
from pathlib import Path

from ars_workbench.canonical import CANONICAL_READ_CONTRACT, canonical_bundle_to_snapshot
from ars_workbench.store import WorkbenchStore


def _bindings():
    return {
        "species": {"semantic_owner": "species", "source": "species"},
        "question": {"semantic_owner": "question", "source": "question"},
        "hypotheses": {"semantic_owner": "hypotheses", "source": "hypotheses"},
        "datasets": {"semantic_owner": "datasets", "source": "datasets"},
        "events": {"semantic_owner": "events", "source": "events"},
        "evidence": {"semantic_owner": "evidence", "source": "evidence"},
        "media": {"semantic_owner": "media", "source": "media"},
        "runs": {"semantic_owner": "runs", "source": "runs"},
        "software_verification": {"semantic_owner": "software", "source": "software"},
        "provenance": {"semantic_owner": "provenance", "source": "provenance"},
    }


def main() -> None:
    store = WorkbenchStore()
    snapshot = store.snapshot()
    adapted, status = canonical_bundle_to_snapshot(
        {
            "adapter_contract": CANONICAL_READ_CONTRACT,
            "authority_state": "CURRENT",
            "captured_at_utc": "STATIC_VERIFICATION_FIXTURE",
            "bindings": _bindings(),
            "snapshot": snapshot,
        },
        source="<memory>",
    )

    d0019 = store.dataset_get("D0019")
    run005 = store.run_get("RUN-PT-RQ0001-005")
    run006 = store.run_get("RUN-PT-RQ0001-006")
    species = store.species_get("SP001")
    evidence = store.evidence_get("RQ0001")
    d0020_events = store.events_list(dataset_id="D0020", limit=50)["items"]

    all_refs = []
    for record in [snapshot["species"], snapshot["question"]]:
        all_refs.extend(record["provenance_ids"])
    for key in (
        "hypotheses",
        "datasets",
        "runs",
        "software_verification",
        "events",
        "evidence_items",
        "media_placeholders",
    ):
        for record in snapshot.get(key, []):
            all_refs.extend(record["provenance_ids"])
            if key == "evidence_items":
                for link in record.get("evidence_links", []):
                    all_refs.extend(link["provenance_ids"])

    checks = {
        "adapter_accepts_complete_current_snapshot": (
            status["authority_state"] == "CURRENT"
            and adapted["mode"] == "CANONICAL_READ_ADAPTER"
        ),
        "all_displayed_provenance_resolves": all(
            store.provenance_get(provenance_id) is not None
            for provenance_id in all_refs
        ),
        "d0019_current_readiness_not_stale": (
            d0019["availability"] == "GATED_METADATA_ONLY"
            and d0019["empirical_state"]
            == "RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"
            and d0019["rights_state"]
            == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"
        ),
        "d0019_empirical_runs_still_held": all(
            run["state"] == "EMPIRICAL_EXECUTION_HELD"
            and run["disposition"] is None
            for run in (run005, run006)
        ),
        "comparison_gate_not_promoted": (
            species["comparison_readiness"]["overall"] == "NOT_COMPARISON_READY"
            and species["comparison_readiness"]["CRG-C"] == "NOT_PASS"
        ),
        "synthetic_stays_nonevidentiary": all(
            item["class"] == "ZERO_SYNTHETIC"
            and item["biological_evidence"] is False
            for item in evidence["software_verification"]
        ),
        "d0020_null_remains_bounded": (
            store.run_get("RUN-PT-RQ0001-004")["disposition"]
            == "NULL_OR_CONTEXT_SUFFICIENT"
            and "only"
            in store.run_get("RUN-PT-RQ0001-004")["interpretation_ceiling"].lower()
        ),
        "d0020_anonymization_and_missing_form_preserved": all(
            "GOAL_LABEL_ANONYMIZED" in event["missingness_codes"]
            and event["signal"]["gesture_form"] == "NOT_RELEASED_IN_ANON_CSV"
            for event in d0020_events
        ),
        "registry_absence_not_evidence": (
            "not evidence" in evidence["registry_status"]["absence_rule"].lower()
        ),
        "media_firewall_active": all(
            media["bytes_available"] is False
            and media["preview_allowed"] is False
            and all(
                field not in media
                for field in ("media_url", "preview_url", "image_url", "bytes")
            )
            for media in evidence["media_placeholders"]
        ),
        "same_snapshot_deterministic": (
            store.overview() == store.overview()
            and store.evidence_get("RQ0001") == store.evidence_get("RQ0001")
        ),
    }

    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 5 provenance-completeness / stale-state / semantic-firewall verification",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks,
        "all_passed": all(checks.values()),
        "live_authenticated_producer_exercised": False,
        "completion_boundary": (
            "Workbench software firewall verification only; the separate Slice 2 live-auth canonical-producer execution gate remains open."
        ),
        "scientific_effect": "NONE",
        "biological_evidence": False,
    }
    out = Path("build/workbench_slice5_firewall_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
