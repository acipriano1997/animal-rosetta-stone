from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from urllib.parse import parse_qs, urlparse

from .store import WorkbenchStore


STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class WorkbenchHandler(BaseHTTPRequestHandler):
    store = WorkbenchStore()

    def _json(self, obj, status=HTTPStatus.OK):
        payload = json.dumps(obj, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, name: str):
        root = files("ars_workbench").joinpath("static")
        path = root.joinpath(name)
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = path.read_bytes()
        suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", STATIC_TYPES.get(suffix, "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def _int_query(query: dict[str, list[str]], key: str, default: int) -> int:
        raw = query.get(key, [str(default)])[0]
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"{key} must be an integer") from exc

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            return self._static("index.html")
        if path in {"/app.js", "/styles.css"}:
            return self._static(path[1:])
        if path == "/api/authority-status":
            return self._json(self.store.authority_status())
        if path == "/api/snapshot":
            return self._json(self.store.overview())
        if path == "/api/species":
            return self._json(self.store.species_list())
        if path.startswith("/api/species/"):
            item = self.store.species_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path.startswith("/api/questions/"):
            item = self.store.question_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path == "/api/datasets":
            return self._json(self.store.dataset_list())
        if path.startswith("/api/datasets/"):
            item = self.store.dataset_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path == "/api/event-inventory":
            return self._json(self.store.event_inventory())
        if path == "/api/events":
            try:
                result = self.store.events_list(
                    dataset_id=query.get("dataset_id", [None])[0],
                    population=query.get("population", [None])[0],
                    split=query.get("split", [None])[0],
                    limit=self._int_query(query, "limit", 50),
                    offset=self._int_query(query, "offset", 0),
                )
            except ValueError as exc:
                return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return self._json(result)
        if path.startswith("/api/events/"):
            item = self.store.event_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path == "/api/claims":
            return self._json(self.store.claims_list())
        if path.startswith("/api/claims/"):
            item = self.store.claim_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path == "/api/media-placeholders":
            return self._json(self.store.media_placeholders())
        if path == "/api/runs":
            return self._json(self.store.run_list())
        if path.startswith("/api/runs/"):
            item = self.store.run_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path.startswith("/api/evidence/"):
            item = self.store.evidence_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path.startswith("/api/provenance/"):
            item = self.store.provenance_get(path.split("/")[-1])
            return self._json(item, HTTPStatus.OK if item else HTTPStatus.NOT_FOUND)
        if path == "/api/software-verification":
            return self._json(self.store.software_verification_list())
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        return


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), WorkbenchHandler)
    print(f"Rosetta Research Workbench Phase I: http://{host}:{port}")
    server.serve_forever()
