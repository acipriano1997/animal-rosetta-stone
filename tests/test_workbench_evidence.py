from __future__ import annotations

from copy import deepcopy
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
import json

import pytest

from ars_workbench.app import WorkbenchHandler
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
        "captured_at_utc": "2026-10-02T19:45:00Z",
        "bindings": _bindings(),
        "snapshot": WorkbenchStore().snapshot(),
    }


def _get_json(base, path):
    with urlopen(base + path, timeout=5) as response:
        return response.status, json.loads(response.read())


def test_fixture_claim_set_is_bounded_and_nonranking():
    store = WorkbenchStore()
    claims = store.claims_list()
    assert {c["claim_id"] for c in claims} == {
        "C0062",
        "C0083",
        "C0084",
        "C0085",
        "C0086",
    }
    assert store.claim_get("C0085")["status"] == "methodological_challenge"
    assert all(c["do_not_overclaim"] for c in claims)
    assert all("score" not in c and "rank" not in c for c in claims)


def test_empty_registry_state_is_not_interpreted_as_absence():
    evidence = WorkbenchStore().evidence_get("RQ0001")
    assert evidence["corrections"] == []
    assert evidence["disagreements"] == []
    status = evidence["registry_status"]
    assert status["contradictions_registry_checked"] is True
    assert status["disagreement_registry_checked"] is True
    assert "not evidence" in status["absence_rule"].lower()
    assert "does not exist" in status["absence_rule"].lower()


def test_media_placeholders_are_rights_aware_and_never_preview():
    store = WorkbenchStore()
    media = store.media_placeholders()
    assert {m["dataset_id"] for m in media} == {"D0018", "D0020"}
    assert all(m["availability_status"] == "NOT_INGESTED" for m in media)
    assert all(m["bytes_available"] is False for m in media)
    assert all(m["preview_allowed"] is False for m in media)
    assert all("preview" in m["placeholder_message"].lower() for m in media)
    for item in media:
        for provenance_id in item["provenance_ids"]:
            assert store.provenance_get(provenance_id) is not None


def test_adapter_rejects_semantic_claim_field():
    bundle = _bundle()
    bundle["snapshot"]["evidence_items"][0]["semantic_gloss"] = "forbidden"
    with pytest.raises(CanonicalReadError, match="forbidden semantic fields"):
        canonical_bundle_to_snapshot(bundle)


def test_adapter_rejects_media_preview_or_bytes():
    bundle = _bundle()
    bundle["snapshot"]["media_placeholders"][0]["preview_allowed"] = True
    with pytest.raises(CanonicalReadError, match="cannot enable preview"):
        canonical_bundle_to_snapshot(bundle)

    bundle = _bundle()
    bundle["snapshot"]["media_placeholders"][0]["bytes_available"] = True
    with pytest.raises(CanonicalReadError, match="cannot expose bytes"):
        canonical_bundle_to_snapshot(bundle)


def test_adapter_requires_absence_rule_for_zero_registry_rows():
    bundle = _bundle()
    bundle["snapshot"]["evidence_registry_status"]["absence_rule"] = ""
    with pytest.raises(CanonicalReadError, match="requires explicit absence_rule"):
        canonical_bundle_to_snapshot(bundle)


def test_http_claim_and_evidence_navigation():
    server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        status, claims = _get_json(base, "/api/claims")
        assert status == 200
        assert len(claims) == 5

        status, claim = _get_json(base, "/api/claims/C0086")
        assert status == 200
        assert claim["claim_id"] == "C0086"
        assert claim["evidence_links"][0]["link_id"] == "L0078"

        status, evidence = _get_json(base, "/api/evidence/RQ0001")
        assert status == 200
        assert evidence["registry_status"]["matching_disagreement_rows"] == 0
        assert "not evidence" in evidence["registry_status"]["absence_rule"].lower()

        status, media = _get_json(base, "/api/media-placeholders")
        assert status == 200
        assert all(m["preview_allowed"] is False for m in media)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
