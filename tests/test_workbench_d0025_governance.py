from __future__ import annotations

import json
from pathlib import Path

from ars_workbench.store import WorkbenchStore


D0025_CURRENT_STATE = (
    "D0025_V1_H1_SHA256_VERIFIED_H2_ROW3_HEADERS_LOCATED_"
    "H3_PR0006_FULL_PRIMARY_SCHEMA_NOT_DEMONSTRATED_HELD"
)


def test_d0025_static_workbench_matches_current_h1_h2_governance_state():
    d0025 = WorkbenchStore().dataset_get("D0025")
    assert d0025 is not None
    assert d0025["availability"] == "GATED_METADATA_ONLY"
    assert d0025["empirical_state"] == D0025_CURRENT_STATE
    assert "CC BY 4.0" in d0025["rights_state"]
    assert "not blanket rights adjudication" in d0025["rights_state"].lower()
    assert "H1 source identity/checksums" in d0025["gate"]
    assert "H2 located" in d0025["gate"]
    assert "H3 remains HELD_SCHEMA" in d0025["gate"]
    assert "original unfiltered event-level extract" in d0025["gate"]
    assert "PREBYTE" not in d0025["empirical_state"]
    assert "ITEM_LEVEL_LICENSE_UNVERIFIED" not in d0025["rights_state"]


def test_d0025_license_metadata_verification_does_not_become_rights_adjudication():
    manifest = json.loads(
        Path("contracts/d0025_v1_verified_source_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    d0025 = WorkbenchStore().dataset_get("D0025")
    assert manifest["status"] == "IMMUTABLE_H1_VERIFICATION_SNAPSHOT_NOT_RIGHTS_ADJUDICATION"
    assert manifest["license_as_reported"]["name"] == "CC BY 4.0"
    assert manifest["verification"]["raw_files_persisted"] is False
    assert manifest["verification"]["rows_inspected"] is False
    assert "verified" in d0025["rights_state"].lower()
    assert "not blanket rights adjudication" in d0025["rights_state"].lower()


def test_d0025_governance_reconciliation_does_not_promote_scientific_state():
    store = WorkbenchStore()
    d0025 = store.dataset_get("D0025")
    species = store.species_get("SP001")
    assert d0025["semantic_authority"] == "NONE"
    assert "HELD" in d0025["empirical_state"]
    assert species["comparison_readiness"]["CRG-C"] == "NOT_PASS"
    assert species["comparison_readiness"]["overall"] == "NOT_COMPARISON_READY"
    assert "PR0006 is not blind discovery" in d0025["known_exposure"]
