from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen

from ars_workbench.app import WorkbenchHandler


def _get(base: str, path: str):
    with urlopen(base + path, timeout=5) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def test_workbench_http_surface_smoke():
    server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        status, ctype, body = _get(base, "/")
        assert status == 200
        assert "text/html" in ctype
        assert b"Rosetta Research Workbench" in body

        status, _, body = _get(base, "/api/authority-status")
        assert status == 200
        authority = json.loads(body)
        assert authority["source_mode"] == "STATIC_FIXTURE"
        assert authority["authoritative_live_read"] is False

        status, ctype, body = _get(base, "/api/species/SP001")
        assert status == 200
        species = json.loads(body)
        assert species["activation_state"] == "ACTIVE"
        assert species["comparison_readiness"]["CRG-C"] == "PASS"
        assert species["comparison_readiness"]["CRG-D"] == "PARTIAL"
        assert species["comparison_readiness"]["controlling_criterion"] == "CRG-D"
        assert species["comparison_readiness"]["overall"] == "NOT_COMPARISON_READY"
        assert species["comparison_readiness"]["bonobo_activation"] == "DEFERRED"

        status, _, body = _get(base, "/api/questions/RQ0001")
        assert status == 200
        question = json.loads(body)
        assert {h["hypothesis_id"] for h in question["hypotheses"]} == {"H0001","H0002","H0003"}

        status, _, body = _get(base, "/api/datasets/D0019")
        assert status == 200
        d0019 = json.loads(body)
        assert d0019["availability"] == "GATED_METADATA_ONLY"
        assert d0019["empirical_state"] == "D0019_PR0005_EMPIRICAL_CLOSED_MIXED"
        assert d0019["rights_state"] == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"

        for suffix in ("005", "006"):
            status, _, body = _get(base, f"/api/runs/RUN-PT-RQ0001-{suffix}")
            assert status == 200
            run = json.loads(body)
            assert run["state"] == "CLOSED"
            assert run["disposition"] == "MIXED"
            assert "no replicated H0001 support" in run["interpretation_ceiling"]
        assert run["model_refit"] is run["preprocessing_refit"] is False

        status, _, body = _get(base, "/api/software-verification")
        assert status == 200
        software = json.loads(body)
        assert software and all(not x["biological_evidence"] for x in software)

        status, ctype, body = _get(base, "/app.js")
        assert status == 200
        assert "javascript" in ctype
        assert b"software.only" in body

        status, ctype, body = _get(base, "/locales/en.json")
        assert status == 200
        assert "application/json" in ctype
        assert json.loads(body)["software.only"] == "software verification only"

        status, ctype, body = _get(base, "/i18n.js")
        assert status == 200
        assert "javascript" in ctype
        assert b"export async function initializeLocale" in body

        status, ctype, body = _get(base, "/locales/en-XA.json")
        assert status == 200
        assert "application/json" in ctype
        assert "testing only" in json.loads(body)["locale.pseudo"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
