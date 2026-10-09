from __future__ import annotations

import json
from pathlib import Path

import pytest

from ars_workbench.store import WorkbenchStore

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/ars_workbench/static"
FORBIDDEN = {"meaning", "translation", "semantic_gloss", "english_gloss"}


def _walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_decipherment_service_supports_bounded_filters_and_pagination():
    store = WorkbenchStore()
    all_rows = store.events_list(dataset_id="D0018", limit=250)
    assert all_rows["total"] >= 2
    first = store.events_list(dataset_id="D0018", limit=1, offset=0)
    second = store.events_list(dataset_id="D0018", limit=1, offset=1)
    assert first["items"][0]["event_id"] != second["items"][0]["event_id"]

    row = all_rows["items"][0]
    population = row.get("population_or_group_id")
    split = row.get("split")
    if population:
        filtered = store.events_list(dataset_id="D0018", population=population, limit=250)
        assert filtered["items"] and all(x.get("population_or_group_id") == population for x in filtered["items"])
    if split:
        filtered = store.events_list(dataset_id="D0018", split=split, limit=250)
        assert filtered["items"] and all(x.get("split") == split for x in filtered["items"])


def test_alignment_inputs_remain_canonical_and_semantics_free():
    store = WorkbenchStore()
    rows = store.events_list(limit=250)["items"]
    assert rows
    for row in rows:
        assert not (set(_walk(row)) & FORBIDDEN)
        assert row["provenance_ids"]
        assert row["dataset_id"]
        assert row["event_id"]


def test_experiment_workspace_can_deterministically_join_runs_to_datasets():
    store = WorkbenchStore()
    datasets = {row["dataset_id"]: row for row in store.dataset_list()}
    for run in store.run_list():
        assert run["dataset_id"] in datasets
        assert run["run_id"]
        assert run["state"]
        assert run["provenance_ids"]

    for suffix in ("005", "006"):
        mixed = store.run_get(f"RUN-PT-RQ0001-{suffix}")
        assert mixed["state"] == "CLOSED"
        assert mixed["disposition"] == "MIXED"
        assert "no replicated H0001 support" in mixed["interpretation_ceiling"]
    transfer = store.run_get("RUN-PT-RQ0001-006")
    assert transfer["model_refit"] is transfer["preprocessing_refit"] is False
    closed = store.run_get("RUN-PT-RQ0001-004")
    assert closed["state"] == "CLOSED"
    assert closed["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"


def test_workspace_chrome_and_contract_preserve_scientific_firewalls():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    en = json.loads((STATIC / "locales/en.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "contracts/workbench_research_workspaces_contract.json").read_text())

    for token in (
        "data-event-filter-form", "data-event-select", "data-compare-events",
        "renderEventComparison", "renderRunInspector", "data-inspect-run",
        "data-dataset-events", "data-dataset-runs",
    ):
        assert token in js

    for key in (
        "heading.events", "heading.runs", "events.compare_boundary",
        "runs.boundary", "runs.optional_fields",
    ):
        assert key in en

    assert contract["scientific_effect"] == "NONE"
    assert contract["biological_evidence"] is False
    assert "meaning or translation generation" in contract["decipherment_workspace"]["forbidden"]


def test_event_service_bounds_are_unchanged():
    store = WorkbenchStore()
    with pytest.raises(ValueError):
        store.events_list(limit=0)
    with pytest.raises(ValueError):
        store.events_list(limit=251)
    with pytest.raises(ValueError):
        store.events_list(offset=-1)
