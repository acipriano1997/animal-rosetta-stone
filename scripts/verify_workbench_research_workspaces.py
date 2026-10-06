"""Verify the architecture-defined Workbench core research workspaces."""
from __future__ import annotations

import json
from pathlib import Path

from ars_workbench.store import WorkbenchStore

FORBIDDEN = {"meaning", "translation", "semantic_gloss", "english_gloss"}


def paths(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{prefix}.{key}" if prefix else key
            if key in FORBIDDEN:
                found.append(here)
            found.extend(paths(child, here))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(paths(child, f"{prefix}[{i}]"))
    return found


store = WorkbenchStore()
d0018 = store.events_list(dataset_id="D0018", limit=250)
d0020 = store.events_list(dataset_id="D0020", limit=250)
runs = store.run_list()
datasets = {x["dataset_id"] for x in store.dataset_list()}

checks = {
    "event_filter_pagination_service_operational": d0018["items"] and d0020["items"],
    "event_rows_semantics_free": not paths(d0018["items"]) and not paths(d0020["items"]),
    "event_provenance_visible": all(x.get("provenance_ids") for x in d0018["items"] + d0020["items"]),
    "run_dataset_joins_resolve": all(r.get("dataset_id") in datasets for r in runs),
    "held_runs_remain_held": store.run_get("RUN-PT-RQ0001-005")["state"] == "EMPIRICAL_EXECUTION_HELD",
    "held_run_disposition_unearned": store.run_get("RUN-PT-RQ0001-005")["disposition"] is None,
    "d0020_null_remains_bounded": store.run_get("RUN-PT-RQ0001-004")["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT",
    "zero_synthetic_separate": all(not x["biological_evidence"] for x in store.software_verification_list()),
}
receipt = {
    "verification": "Rosetta Research Workbench core research workspaces",
    "repository_sha": "LOCAL_UNCOMMITTED",
    "checks": {k: bool(v) for k, v in checks.items()},
    "all_passed": all(checks.values()),
    "scientific_effect": "NONE",
    "biological_evidence": False,
}
Path("build").mkdir(exist_ok=True)
Path("build/workbench_research_workspaces_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
if not receipt["all_passed"]:
    raise SystemExit(1)
