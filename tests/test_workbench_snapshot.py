from __future__ import annotations

from ars_workbench.store import WorkbenchStore


def _all_provenance_ids(snapshot):
    ids = []
    ids.extend(snapshot["species"]["provenance_ids"])
    ids.extend(snapshot["question"]["provenance_ids"])
    for row in snapshot["hypotheses"] + snapshot["datasets"] + snapshot["runs"] + snapshot["software_verification"]:
        ids.extend(row.get("provenance_ids", []))
    return ids


def test_all_displayed_records_have_resolvable_provenance():
    s = WorkbenchStore().snapshot()
    known = set(s["provenance"])
    refs = _all_provenance_ids(s)
    assert refs
    assert set(refs) <= known


def test_d0020_null_is_bounded_not_global():
    s = WorkbenchStore().snapshot()
    run = next(r for r in s["runs"] if r["run_id"] == "RUN-PT-RQ0001-004")
    assert run["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    ceiling = run["interpretation_ceiling"].lower()
    assert "bounded" in ceiling
    assert "only" in ceiling


def test_d0019_never_appears_empirically_executed():
    s = WorkbenchStore().snapshot()
    d = next(x for x in s["datasets"] if x["dataset_id"] == "D0019")
    assert d["availability"] == "GATED_METADATA_ONLY"
    assert d["empirical_state"] == "RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"
    assert d["rights_state"] == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"
    assert "READY_FOR_SECRET_BACKED_MATERIALIZATION" in d["gate"]
    runs = [r for r in s["runs"] if r["dataset_id"] == "D0019"]
    assert runs
    assert all(r["state"] == "EMPIRICAL_EXECUTION_HELD" for r in runs)
    assert all(r["disposition"] is None for r in runs)


def test_d0025_remains_metadata_only():
    s = WorkbenchStore().snapshot()
    d = next(x for x in s["datasets"] if x["dataset_id"] == "D0025")
    assert d["availability"] == "GATED_METADATA_ONLY"
    assert d["rights_state"] == "ITEM_LEVEL_LICENSE_UNVERIFIED"
    assert not any(r["dataset_id"] == "D0025" for r in s["runs"])


def test_zero_synthetic_is_segregated_from_empirical_runs():
    s = WorkbenchStore().snapshot()
    assert s["software_verification"]
    assert all(x["class"] == "ZERO_SYNTHETIC" for x in s["software_verification"])
    assert all(not x["biological_evidence"] for x in s["software_verification"])
    assert not any(r.get("evidence_class") == "ZERO_SYNTHETIC" for r in s["runs"])


def test_store_returns_stable_copies():
    store = WorkbenchStore()
    a = store.snapshot()
    b = store.snapshot()
    assert a == b
    a["species"]["activation_state"] = "MUTATED"
    assert store.snapshot()["species"]["activation_state"] == "ACTIVE"
