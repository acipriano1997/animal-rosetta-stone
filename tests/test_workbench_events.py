from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from ars_workbench.app import WorkbenchHandler
from ars_workbench.store import WorkbenchStore


def _get(base: str, path: str):
    with urlopen(base + path, timeout=5) as response:
        return response.status, json.loads(response.read())


def test_fixture_event_sample_is_explicitly_bounded():
    store = WorkbenchStore()
    inventory = store.event_inventory()
    assert inventory["D0018"]["canonical_total"] == 36
    assert inventory["D0018"]["available_in_fixture"] == 2
    assert inventory["D0018"]["coverage"] == "STATIC_SAMPLE_ONLY"
    assert inventory["D0020"]["canonical_total"] == 4223
    assert inventory["D0020"]["available_in_fixture"] == 2


def test_event_list_filters_without_reinterpreting_fields():
    store = WorkbenchStore()
    result = store.events_list(dataset_id="D0020", limit=10)
    assert result["total"] == 2
    assert all(e["dataset_id"] == "D0020" for e in result["items"])
    assert all(e["signal"]["gesture_form"] == "NOT_RELEASED_IN_ANON_CSV" for e in result["items"])
    assert all("GOAL_LABEL_ANONYMIZED" in e["missingness_codes"] for e in result["items"])
    assert all("semantic_gloss" not in e for e in result["items"])


def test_event_provenance_resolves_and_overview_stays_lightweight():
    store = WorkbenchStore()
    event = store.event_get("EVT-PT-RQ0001-D0018-SNK-001")
    assert event is not None
    for provenance_id in event["provenance_ids"]:
        assert store.provenance_get(provenance_id) is not None

    overview = store.overview()
    assert "events" not in overview
    assert "event_provenance" not in overview
    assert overview["event_inventory"]["D0018"]["coverage"] == "STATIC_SAMPLE_ONLY"


def test_event_pagination_bounds_are_fail_closed():
    store = WorkbenchStore()
    try:
        store.events_list(limit=251)
    except ValueError as exc:
        assert "between 1 and 250" in str(exc)
    else:
        raise AssertionError("limit >250 should fail")


def test_event_http_surface_and_provenance_navigation():
    server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        status, result = _get(base, "/api/events?dataset_id=D0018&limit=1")
        assert status == 200
        assert result["total"] == 2
        assert len(result["items"]) == 1

        event_id = result["items"][0]["event_id"]
        status, event = _get(base, f"/api/events/{event_id}")
        assert status == 200
        assert event["dataset_id"] == "D0018"

        provenance_id = event["provenance_ids"][0]
        status, provenance = _get(base, f"/api/provenance/{provenance_id}")
        assert status == 200
        assert provenance["provenance_id"] == provenance_id

        try:
            urlopen(base + "/api/events?limit=999", timeout=5)
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("invalid limit should return HTTP 400")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
