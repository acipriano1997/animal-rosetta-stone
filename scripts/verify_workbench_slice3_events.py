from __future__ import annotations

import json
import os
from pathlib import Path

from ars_workbench.store import WorkbenchStore


def main() -> None:
    store = WorkbenchStore()
    d0018 = store.events_list(dataset_id="D0018", limit=10)
    d0020 = store.events_list(dataset_id="D0020", limit=10)
    all_events = d0018["items"] + d0020["items"]

    checks = {
        "fixture_explicitly_sample_only": (
            d0018["inventory"]["D0018"]["coverage"] == "STATIC_SAMPLE_ONLY"
            and d0020["inventory"]["D0020"]["coverage"] == "STATIC_SAMPLE_ONLY"
        ),
        "canonical_inventory_counts_preserved": (
            d0018["inventory"]["D0018"]["canonical_total"] == 36
            and d0020["inventory"]["D0020"]["canonical_total"] == 4223
        ),
        "d0018_and_d0020_browsable": bool(d0018["items"]) and bool(d0020["items"]),
        "event_provenance_resolves": all(
            store.provenance_get(pid) is not None
            for event in all_events
            for pid in event["provenance_ids"]
        ),
        "missingness_visible": all(event.get("missingness_codes") for event in all_events),
        "no_semantic_gloss_fields": all(
            not ({"meaning", "translation", "semantic_gloss", "english_gloss"} & set(event))
            for event in all_events
        ),
        "d0020_goal_anonymization_preserved": all(
            "GOAL_LABEL_ANONYMIZED" in event["missingness_codes"]
            for event in d0020["items"]
        ),
        "overview_omits_bulk_events": (
            "events" not in store.overview()
            and "event_provenance" not in store.overview()
        ),
    }

    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 3 event/provenance exploration",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks,
        "all_passed": all(checks.values()),
        "fixture_scope": "four-event sample only; canonical producer owns full event rows",
        "scientific_effect": "NONE",
        "biological_evidence": False,
    }
    out = Path("build/workbench_slice3_event_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
