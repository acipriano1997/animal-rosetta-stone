"""Presentation contracts, real JS execution and HTTP dispatch without bind()."""
from __future__ import annotations

import ast
from html.parser import HTMLParser
from importlib.resources import files
from io import BytesIO
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tomllib

import pytest

from ars_workbench.app import WorkbenchHandler
from ars_workbench import presentation
from ars_workbench.store import WorkbenchStore

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/ars_workbench/static"
GENERATOR = ROOT / "scripts/generate_workbench_pseudolocale.py"
PLACEHOLDER = re.compile(r"\{[a-zA-Z_]+\}")


class Markup(HTMLParser):
    """Inspect actual shell/rendered markup using Python's HTML parser."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.unowned_text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "parents": list(self.stack)}
        self.nodes.append(node)
        if tag not in {"meta", "link", "br", "hr", "input"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack:
            assert self.stack[-1]["tag"] == tag, f"Malformed markup closing {tag}"
            self.stack.pop()

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data
        if re.search(r"[A-Za-z]", data) and not any(
            {"data-canonical", "data-i18n", "data-number"} & node["attrs"].keys()
            for node in self.stack
        ):
            self.unowned_text.append(data)

    def by_id(self, node_id):
        return next(node for node in self.nodes if node["attrs"].get("id") == node_id)


def _catalog(name):
    return json.loads((STATIC / f"locales/{name}.json").read_text(encoding="utf-8"))


def test_catalog_completeness_and_placeholders():
    def unique(pairs):
        assert len(pairs) == len(dict(pairs)), "Duplicate catalog key"
        return dict(pairs)

    en, xa = [json.loads((STATIC / f"locales/{name}.json").read_text(encoding="utf-8"), object_pairs_hook=unique)
              for name in ("en", "en-XA")]
    assert set(en) == set(xa)
    for key, source in en.items():
        assert isinstance(source, str) and source.strip()
        assert isinstance(xa[key], str) and xa[key].strip()
        assert sorted(PLACEHOLDER.findall(source)) == sorted(PLACEHOLDER.findall(xa[key]))
    code = "\n".join(path.read_text(encoding="utf-8") for path in (
        STATIC / "app.js", STATIC / "i18n.js", ROOT / "src/ars_workbench/presentation.py",
    ))
    references = set(re.findall(r"['\"]([a-z]+\.[a-z_0-9]+)['\"]", code))
    shell = (STATIC / "index.html").read_text(encoding="utf-8")
    references.update(re.findall(r"\{\{([a-z]+\.[a-z_]+)\}\}", shell))
    references.discard("index.html")
    assert references == set(en), {"missing": references - set(en), "unused": set(en) - references}


def test_pseudolocale_is_deterministic_and_test_only():
    generator = runpy.run_path(str(GENERATOR))
    en, xa = _catalog("en"), _catalog("en-XA")
    assert generator["generate"](en).encode("utf-8") == (STATIC / "locales/en-XA.json").read_bytes()
    for key, source in en.items():
        if key in generator["STABLE_LABELS"]:
            assert xa[key] == source
        else:
            assert xa[key].startswith("⟦") and xa[key].endswith("⟧")
            assert len(xa[key]) > len(source)
    assert "testing only" in xa["locale.pseudo"] and "en-XA" in xa["locale.pseudo"]
    assert "{shown}" in generator["pseudo"]("{shown} café 原文 e\u0301")
    subprocess.run([sys.executable, str(GENERATOR), "--check"], check=True, capture_output=True)


def test_pseudolocale_check_rejects_stale_bytes_without_writing(tmp_path):
    generator = tmp_path / "scripts/generate_workbench_pseudolocale.py"
    generator.parent.mkdir()
    generator.write_bytes(GENERATOR.read_bytes())
    locales = tmp_path / "src/ars_workbench/static/locales"
    locales.mkdir(parents=True)
    (locales / "en.json").write_text('{"app.title": "Workbench"}', encoding="utf-8")
    target = locales / "en-XA.json"
    target.write_bytes(b"{}\n")
    result = subprocess.run([sys.executable, str(generator), "--check"], capture_output=True)
    assert result.returncode == 1 and b"stale" in result.stderr
    assert target.read_bytes() == b"{}\n"


def test_english_shell_language_selector_and_keyboard_targets():
    html = presentation.render_shell((STATIC / "index.html").read_text(encoding="utf-8"))
    assert "{{" not in html
    markup = Markup(html)
    document = next(node for node in markup.nodes if node["tag"] == "html")
    assert document["attrs"]["lang"] == "en"
    assert document["attrs"]["dir"] == "ltr"
    assert next(node for node in markup.nodes if node["tag"] == "title")["text"] == _catalog("en")["app.title"]
    selector = markup.by_id("presentation-locale")
    assert selector["tag"] == "select"
    assert any(node["attrs"].get("for") == "presentation-locale" and node["text"] for node in markup.nodes)
    assert markup.by_id(selector["attrs"]["aria-describedby"])["text"]
    options = [node for node in markup.nodes if node["tag"] == "option"]
    assert [node["attrs"]["value"] for node in options] == ["en", "en-XA"]
    assert all(node["attrs"]["lang"] == "en" for node in options)
    assert "testing only" in options[1]["text"]
    assert markup.by_id("locale-status")["attrs"]["role"] == "status"
    for node in markup.nodes:
        if "data-target" in node["attrs"]:
            assert markup.by_id(node["attrs"]["data-target"])["attrs"]["tabindex"] == "-1"
    skip = next(node for node in markup.nodes if node["attrs"].get("class") == "skip-link")
    assert markup.by_id(skip["attrs"]["href"][1:])["attrs"]["tabindex"] == "-1"


def test_shell_escapes_catalog_content_without_script_injection(monkeypatch):
    dangerous = '</script><img src=x onerror="x"> & “原文”\u2028'
    en = {**_catalog("en"), "app.title": dangerous}
    monkeypatch.setattr(presentation, "english_messages", lambda: en)
    markup = Markup(presentation.render_shell((STATIC / "index.html").read_text(encoding="utf-8")))
    assert not any(node["tag"] == "img" for node in markup.nodes)
    assert next(node for node in markup.nodes if node["tag"] == "title")["text"] == dangerous
    assert json.loads(markup.by_id("presentation-messages")["text"])["app.title"] == dangerous


def test_package_data_contains_all_presentation_assets():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["ars_workbench"]
    package = ROOT / "src/ars_workbench"
    included = {path.relative_to(package).as_posix() for pattern in patterns for path in package.glob(pattern)}
    for asset in ("index.html", "app.js", "i18n.js", "styles.css", "locales/en.json", "locales/en-XA.json"):
        assert f"static/{asset}" in included
        assert files("ars_workbench").joinpath(f"static/{asset}").read_bytes()


def test_presentation_is_not_imported_by_scientific_code():
    for path in (ROOT / "src").rglob("*.py"):
        if path.name in {"app.py", "presentation.py"}:
            continue
        imports = [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, (ast.Import, ast.ImportFrom))]
        for node in imports:
            names = [alias.name for alias in node.names] + [getattr(node, "module", "") or ""]
            assert not any(name.split(".")[-1] in {"presentation", "i18n"} for name in names), path


class MemoryConnection:
    def __init__(self, request):
        self.request = request
        self.output = BytesIO()

    def makefile(self, mode, *args):
        assert mode == "rb"
        return BytesIO(self.request)

    def sendall(self, data):
        self.output.write(data)


def _request(path, language="en", method="GET"):
    class Handler(WorkbenchHandler):
        def date_time_string(self, timestamp=None):
            return "Mon, 05 Oct 2026 00:00:00 GMT"

    wire = (f"{method} {path} HTTP/1.0\r\nHost: localhost\r\n"
            f"Accept-Language: {language}\r\nCookie: ars.workbench.presentationLocale={language}\r\n\r\n")
    connection = MemoryConnection(wire.encode("ascii"))
    Handler(connection, ("127.0.0.1", 0), None)
    return connection.output.getvalue()


def test_all_api_routes_are_byte_invariant_across_locale_inputs():
    store = WorkbenchStore()
    before = store.snapshot()
    paths = [
        "/api/authority-status", "/api/snapshot", "/api/species", "/api/species/SP001",
        "/api/questions/RQ0001", "/api/datasets", "/api/event-inventory",
        "/api/events", "/api/events?dataset_id=D0020&limit=1&offset=1",
        "/api/events?limit=999", "/api/events?limit=invalid", "/api/events?offset=-1",
        "/api/claims", "/api/media-placeholders", "/api/runs", "/api/evidence/RQ0001",
        "/api/software-verification", "/api/not-found",
    ]
    paths += [f"/api/datasets/{row['dataset_id']}" for row in store.dataset_list()]
    paths += [f"/api/runs/{row['run_id']}" for row in store.run_list()]
    paths += [f"/api/events/{row['event_id']}" for row in store.events_list()["items"]]
    paths += [f"/api/claims/{row['claim_id']}" for row in store.claims_list()]
    paths += [f"/api/provenance/{pid}" for key in ("provenance", "event_provenance", "evidence_provenance") for pid in before[key]]
    paths += [f"/api/{resource}/UNKNOWN" for resource in ("species", "questions", "datasets", "runs", "events", "claims", "evidence", "provenance")]
    for path in paths:
        baseline = _request(path)
        for locale in ("en-XA", "ar", "unknown"):
            query = "&" if "?" in path else "?"
            assert _request(path + query + f"locale={locale}&lang={locale}", locale) == baseline, path
    assert _request("/api/snapshot", "en-XA", "POST") == _request("/api/snapshot", "en", "POST")
    assert store.snapshot() == before


@pytest.mark.parametrize("path,content_type", [
    ("/", "text/html"), ("/app.js", "text/javascript"), ("/i18n.js", "text/javascript"),
    ("/styles.css", "text/css"), ("/locales/en.json", "application/json"), ("/locales/en-XA.json", "application/json"),
])
def test_static_routes_are_served_without_language_negotiation(path, content_type):
    wire = _request(path)
    headers, body = wire.split(b"\r\n\r\n", 1)
    assert b"200 OK" in headers
    assert content_type.encode() in headers
    assert f"Content-Length: {len(body)}".encode() in headers
    assert _request(path + "?locale=en-XA", "en-XA") == wire


def test_unregistered_locale_files_fail_closed():
    for path in ("/locales/fr.json", "/locales/../en.json", "/locales/../../data/chimp_rq0001_snapshot.json"):
        headers, body = _request(path).split(b"\r\n\r\n", 1)
        assert b"404 Not Found" in headers
        assert b'<html lang="en" dir="ltr">' in body


@pytest.fixture(scope="module")
def js_result():
    node = shutil.which("node")
    assert node, "Node.js 22+ is required for presentation tests; put node on PATH (no npm packages needed)."
    store = WorkbenchStore()
    responses = {
        "/api/snapshot": store.overview(),
        "/api/events?dataset_id=D0018&limit=12": store.events_list(dataset_id="D0018", limit=12),
        "/api/events?dataset_id=D0020&limit=12": store.events_list(dataset_id="D0020", limit=12),
        "/api/evidence/RQ0001": store.evidence_get("RQ0001"),
        "/api/media-placeholders": store.media_placeholders(),
    }
    # Adversarial display text only; no empirical data or state is materialized.
    responses["/api/events?dataset_id=D0018&limit=12"]["items"][0]["notes"] = '“原文 e\u0301 العربية” <script> & DOI:10.0000/display-test'
    before = json.dumps(responses, ensure_ascii=False)
    result = subprocess.run(
        [node, "--experimental-vm-modules", str(ROOT / "tests/js/workbench_presentation.mjs")],
        input=json.dumps({"responses": responses}), text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.dumps(responses, ensure_ascii=False) == before
    return json.loads(result.stdout)


def test_javascript_locale_lifecycle(js_result):
    assert len(js_result["checks"]) == 6


def test_rendered_chrome_is_catalog_owned_and_canonical_records_are_verbatim(js_result):
    rendered = js_result["renders"]
    canonical = {}
    translated = {}
    for locale, sections in rendered.items():
        canonical[locale], translated[locale] = [], []
        for html in sections.values():
            markup = Markup(html)
            assert not markup.unowned_text, markup.unowned_text
            for node in markup.nodes:
                attrs = node["attrs"]
                if "data-canonical" in attrs:
                    assert attrs["lang"] == "en" and attrs["dir"] == "auto"
                    assert attrs["translate"] == "no"
                    assert not any("data-i18n" in ancestor["attrs"] for ancestor in node["parents"])
                    canonical[locale].append(node["text"])
                if "data-i18n" in attrs:
                    assert attrs["data-i18n"] in _catalog("en")
                    assert "⟦MISSING:" not in node["text"]
                    translated[locale].append(node["text"])
                if node["tag"] == "th":
                    assert attrs["scope"] == "col"
                if node["tag"] == "a":
                    assert attrs["rel"] == "noopener" and attrs["title"]
    assert canonical["en"] == canonical["en-XA"]
    assert translated["en"] != translated["en-XA"]
    text = "\n".join(canonical["en"])
    for protected in (
        "Pan troglodytes", "RQ0001", "H0001", "D0019", "RUN-PT-RQ0001-005",
        "CRG-C NOT_PASS", "NOT_COMPARISON_READY", "EMPIRICAL_EXECUTION_HELD",
        "RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION",
        "HELD_SCHEMA", "NULL_OR_CONTEXT_SUFFICIENT", "ZERO_SYNTHETIC",
        "GOAL_LABEL_ANONYMIZED", "NOT_RELEASED_IN_ANON_CSV",
        '“原文 e\u0301 العربية” <script> & DOI:10.0000/display-test',
    ):
        assert protected in text
    store = WorkbenchStore()
    for hypothesis in store.snapshot()["hypotheses"]:
        assert hypothesis["statement"] in text
        assert hypothesis["current_scope"] in text
    for claim in store.claims_list():
        for key in ("claim_short", "scope_boundary", "do_not_overclaim", "alternative_explanations"):
            assert claim[key] in text
    for record in store.media_placeholders():
        for key in ("rights_state", "scientific_consequence", "required_action", "placeholder_message"):
            assert record[key] in text
