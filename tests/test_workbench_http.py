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

        status, ctype, body = _get(base, "/api/species/SP001")
        assert status == 200
        species = json.loads(body)
        assert species["activation_state"] == "ACTIVE"
        assert species["comparison_readiness"]["CRG-C"] == "NOT_PASS"

        status, _, body = _get(base, "/api/questions/RQ0001")
        assert status == 200
        question = json.loads(body)
        assert {h["hypothesis_id"] for h in question["hypotheses"]} == {"H0001","H0002","H0003"}

        status, _, body = _get(base, "/api/datasets/D0019")
        assert status == 200
        d0019 = json.loads(body)
        assert d0019["availability"] == "GATED_METADATA_ONLY"
        assert d0019["empirical_state"] == "RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"
        assert d0019["rights_state"] == "APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"

        status, _, body = _get(base, "/api/software-verification")
        assert status == 200
        software = json.loads(body)
        assert software and all(not x["biological_evidence"] for x in software)

        status, ctype, body = _get(base, "/app.js")
        assert status == 200
        assert "javascript" in ctype
        assert b"software verification" in body.lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
