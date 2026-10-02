from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from urllib.parse import urlparse

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

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._static("index.html")
        if path in {"/app.js", "/styles.css"}:
            return self._static(path[1:])
        if path == "/api/authority-status":
            return self._json(self.store.authority_status())
        if path == "/api/snapshot":
            return self._json(self.store.snapshot())
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
        # Barebones local research app: keep stdout clean unless caller wraps logging.
        return


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), WorkbenchHandler)
    print(f"Rosetta Research Workbench Phase I: http://{host}:{port}")
    server.serve_forever()
