from __future__ import annotations

from copy import deepcopy

import pytest

from ars_workbench.canonical import (
    CANONICAL_READ_CONTRACT,
    CanonicalReadError,
    canonical_bundle_to_snapshot,
)
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
        "software_verification": {
            "semantic_owner": "software",
            "source": "software",
        },
        "provenance": {"semantic_owner": "provenance", "source": "provenance"},
    }


def _bundle():
    return {
        "adapter_contract": CANONICAL_READ_CONTRACT,
        "authority_state": "CURRENT",
        "captured_at_utc": "2026-10-03T16:15:00Z",
        "bindings": _bindings(),
        "snapshot": WorkbenchStore().snapshot(),
    }


def _all_display_records(snapshot):
    yield snapshot["species"]
    yield snapshot["question"]
    for key in (
        "hypotheses",
        "datasets",
        "runs",
        "software_verification",
        "events",
        "evidence_items",
        "corrections",
        "disagreements",
        "media_placeholders",
    ):
        for row in snapshot.get(key, []):
            yield row
            if key == "evidence_items":
                yield from row.get("evidence_links", [])


def test_fixture_current_pilot_stale_state_invariants_remain_bounded():
    store = WorkbenchStore()
    species = store.species_get("SP001")
    d0019 = store.dataset_get("D0019")
    run005 = store.run_get("RUN-PT-RQ0001-005")
    run006 = store.run_get("RUN-PT-RQ0001-006")

    assert species["comparison_readiness"]["overall"] == "NOT_COMPARISON_READY"
    assert species["comparison_readiness"]["CRG-C"] == "PASS"
    assert species["comparison_readiness"]["CRG-D"] == "PARTIAL"
    assert species["comparison_readiness"]["controlling_criterion"] == "CRG-D"
    assert species["comparison_readiness"]["bonobo_activation"] == "DEFERRED"
    assert species["receiver_harness"]["empirical_exercise_state"] == "UNEARNED"

    assert d0019["availability"] == "GATED_METADATA_ONLY"
    assert (
        d0019["empirical_state"]
        == "D0019_PR0005_EMPIRICAL_CLOSED_MIXED"
    )
    assert (
        d0019["rights_state"]
        == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"
    )
    assert "access-controlled" in d0019["gate"]

    for run in (run005, run006):
        assert run["state"] == "CLOSED"
        assert run["disposition"] == "MIXED"
        assert "no replicated H0001 support" in run["interpretation_ceiling"]
    assert run006["model_refit"] is False
    assert run006["preprocessing_refit"] is False


def test_all_fixture_display_records_have_resolvable_provenance():
    store = WorkbenchStore()
    snapshot = store.snapshot()
    for record in _all_display_records(snapshot):
        refs = record.get("provenance_ids")
        assert refs, record
        for provenance_id in refs:
            assert store.provenance_get(provenance_id) is not None


def test_adapter_rejects_display_record_without_provenance():
    bundle = _bundle()
    bundle["snapshot"]["hypotheses"][0]["provenance_ids"] = []
    with pytest.raises(CanonicalReadError, match="lacks nonempty provenance_ids"):
        canonical_bundle_to_snapshot(bundle)


def test_adapter_rejects_nested_semantic_gloss_leakage():
    bundle = _bundle()
    bundle["snapshot"]["events"][0]["context"]["semantic_gloss"] = "forbidden"
    with pytest.raises(CanonicalReadError, match="forbidden semantic fields"):
        canonical_bundle_to_snapshot(bundle)

    bundle = _bundle()
    bundle["snapshot"]["evidence_items"][0]["evidence_links"][0][
        "translation"
    ] = "forbidden"
    with pytest.raises(CanonicalReadError, match="forbidden semantic fields"):
        canonical_bundle_to_snapshot(bundle)


def test_adapter_rejects_provenance_namespace_collision():
    bundle = _bundle()
    collision_id = next(iter(bundle["snapshot"]["event_provenance"]))
    bundle["snapshot"]["evidence_provenance"][collision_id] = {
        "authority": "collision",
        "source": "collision",
    }
    with pytest.raises(CanonicalReadError, match="provenance namespace collision"):
        canonical_bundle_to_snapshot(bundle)


def test_adapter_rejects_stale_unknown_or_conflicted_authority():
    for state in (
        "STALE_OR_CONFLICTED_AUTHORITY",
        "UNKNOWN_VERSION",
        "STALE",
        "",
        None,
    ):
        bundle = _bundle()
        bundle["authority_state"] = state
        with pytest.raises(CanonicalReadError, match="fail closed"):
            canonical_bundle_to_snapshot(bundle)


def test_adapter_rejects_unknown_contract_and_missing_semantic_owner():
    bundle = _bundle()
    bundle["adapter_contract"] = "WORKBENCH-CANONICAL-READ-v999"
    with pytest.raises(CanonicalReadError, match="contract mismatch"):
        canonical_bundle_to_snapshot(bundle)

    bundle = _bundle()
    bundle["bindings"]["datasets"]["semantic_owner"] = ""
    with pytest.raises(CanonicalReadError, match="lacks semantic_owner"):
        canonical_bundle_to_snapshot(bundle)


def test_zero_synthetic_cannot_become_empirical_or_biological_evidence():
    store = WorkbenchStore()
    evidence = store.evidence_get("RQ0001")
    empirical_run_ids = {r["run_id"] for r in evidence["empirical_runs"]}
    verification_ids = {
        v["verification_id"] for v in evidence["software_verification"]
    }
    assert empirical_run_ids.isdisjoint(verification_ids)
    assert all(
        v["class"] == "ZERO_SYNTHETIC" and v["biological_evidence"] is False
        for v in evidence["software_verification"]
    )

    bundle = _bundle()
    bundle["snapshot"]["software_verification"][0]["biological_evidence"] = True
    with pytest.raises(CanonicalReadError, match="cannot carry biological evidence"):
        canonical_bundle_to_snapshot(bundle)


def test_d0020_null_remains_scoped_and_anonymization_is_preserved():
    store = WorkbenchStore()
    run004 = store.run_get("RUN-PT-RQ0001-004")
    assert run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    assert "Waibira" in run004["interpretation_ceiling"]
    assert "only" in run004["interpretation_ceiling"].lower()

    d0020_events = store.events_list(dataset_id="D0020", limit=10)["items"]
    assert d0020_events
    for event in d0020_events:
        assert "GOAL_LABEL_ANONYMIZED" in event["missingness_codes"]
        assert event["signal"]["gesture_form"] == "NOT_RELEASED_IN_ANON_CSV"
        assert "meaning" not in event
        assert "translation" not in event
        assert "semantic_gloss" not in event
        assert "english_gloss" not in event


def test_rights_media_firewall_and_empty_registry_rule_remain_active():
    store = WorkbenchStore()
    evidence = store.evidence_get("RQ0001")
    assert "not evidence" in evidence["registry_status"]["absence_rule"].lower()
    for media in evidence["media_placeholders"]:
        assert media["bytes_available"] is False
        assert media["preview_allowed"] is False
        assert all(
            field not in media
            for field in ("media_url", "preview_url", "image_url", "bytes")
        )


def test_same_fixture_snapshot_is_deterministic():
    store = WorkbenchStore()
    assert store.overview() == store.overview()
    assert store.evidence_get("RQ0001") == store.evidence_get("RQ0001")
    assert store.events_list(dataset_id="D0018", limit=50) == store.events_list(
        dataset_id="D0018", limit=50
    )
