from __future__ import annotations

import json
from copy import deepcopy

import pytest

from ars_workbench.canonical import CANONICAL_READ_CONTRACT, CanonicalReadError
from ars_workbench.store import WorkbenchStore


def _bundle():
    snapshot = WorkbenchStore().snapshot()
    return {
        "adapter_contract": CANONICAL_READ_CONTRACT,
        "authority_state": "CURRENT",
        "captured_at_utc": "2026-10-02T18:00:00Z",
        "bindings": {
            "species": {
                "semantic_owner": "Chimpanzee — Species Activation Record v0.1",
                "drive_id": "1KYlWfx-aD39DledKlF8xZdHOEKBdrMyXcQJwhHqAbic",
            },
            "question": {
                "semantic_owner": "ACEB Research Questions",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Research Questions:RQ0001",
            },
            "hypotheses": {
                "semantic_owner": "ACEB Hypotheses",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Hypotheses:H0001..H0003",
            },
            "datasets": {
                "semantic_owner": "ACEB Datasets",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Datasets:D0018,D0019,D0020,D0025",
            },
            "runs": {
                "semantic_owner": "RQ0001 frozen run authorities",
                "source": "per-record provenance pointers",
            },
            "software_verification": {
                "semantic_owner": "ARS executable verification records",
                "github_repo": "acipriano1997/animal-rosetta-stone",
            },
            "provenance": {
                "semantic_owner": "record-specific canonical provenance authorities",
                "source": "snapshot provenance index",
            },
        },
        "snapshot": snapshot,
    }


def test_fixture_mode_is_explicit():
    status = WorkbenchStore().authority_status()
    assert status["source_mode"] == "STATIC_FIXTURE"
    assert status["authoritative_live_read"] is False


def test_canonical_bundle_replaces_fixture_through_adapter(tmp_path):
    bundle = _bundle()
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")

    store = WorkbenchStore(canonical_source=str(path))
    status = store.authority_status()
    assert status["source_mode"] == "CANONICAL_READ_ADAPTER"
    assert status["authority_state"] == "CURRENT"
    assert status["authoritative_live_read"] is True
    assert store.snapshot()["mode"] == "CANONICAL_READ_ADAPTER"
    assert store.species_get("SP001")["taxon"] == "Pan troglodytes"
    assert store.dataset_get("D0019")["semantic_authority"] == "NONE"


def test_noncurrent_authority_fails_closed(tmp_path):
    bundle = _bundle()
    bundle["authority_state"] = "STALE_OR_CONFLICTED_AUTHORITY"
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(CanonicalReadError, match="fail closed"):
        WorkbenchStore(canonical_source=str(path))


def test_missing_binding_fails_closed(tmp_path):
    bundle = _bundle()
    del bundle["bindings"]["runs"]
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(CanonicalReadError, match="missing authority bindings"):
        WorkbenchStore(canonical_source=str(path))


def test_unresolved_provenance_fails_closed(tmp_path):
    bundle = _bundle()
    bundle = deepcopy(bundle)
    bundle["snapshot"]["species"]["provenance_ids"].append("PROV-NOT-REAL")
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(CanonicalReadError, match="unresolved provenance ids"):
        WorkbenchStore(canonical_source=str(path))
