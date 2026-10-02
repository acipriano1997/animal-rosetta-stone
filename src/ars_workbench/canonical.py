from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


CANONICAL_READ_CONTRACT = "WORKBENCH-CANONICAL-READ-v0.1"
REQUIRED_BINDING_DOMAINS = frozenset(
    {
        "species",
        "question",
        "hypotheses",
        "datasets",
        "runs",
        "software_verification",
        "provenance",
    }
)
REQUIRED_SNAPSHOT_KEYS = frozenset(
    {
        "snapshot_id",
        "scientific_boundary",
        "species",
        "question",
        "hypotheses",
        "datasets",
        "runs",
        "software_verification",
        "provenance",
    }
)


class CanonicalReadError(RuntimeError):
    """Raised when a canonical Workbench read source cannot be trusted."""


def _source_transport(source: str) -> str:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return "http"
    if source == "<memory>":
        return "memory"
    return "file"


def _read_json_source(source: str) -> dict[str, Any]:
    parsed = urlparse(source)
    try:
        if parsed.scheme in {"http", "https"}:
            request = Request(
                source,
                headers={"Accept": "application/json", "User-Agent": "animal-rosetta-stone-workbench"},
            )
            with urlopen(request, timeout=10) as response:
                payload = response.read().decode("utf-8")
        elif parsed.scheme == "file":
            payload = Path(unquote(parsed.path)).read_text(encoding="utf-8")
        elif parsed.scheme:
            raise CanonicalReadError(f"unsupported canonical read source scheme: {parsed.scheme}")
        else:
            payload = Path(source).read_text(encoding="utf-8")
    except CanonicalReadError:
        raise
    except Exception as exc:
        raise CanonicalReadError(f"unable to read canonical source {source!r}: {exc}") from exc

    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CanonicalReadError(f"canonical source {source!r} is not valid JSON") from exc
    if not isinstance(obj, dict):
        raise CanonicalReadError("canonical read bundle must be a JSON object")
    return obj


def _record_provenance_ids(snapshot: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("species", "question"):
        record = snapshot.get(key)
        if isinstance(record, dict):
            refs.extend(record.get("provenance_ids", []))
    for key in ("hypotheses", "datasets", "runs", "software_verification", "events"):
        rows = snapshot.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    refs.extend(row.get("provenance_ids", []))
    return refs


def canonical_bundle_to_snapshot(
    bundle: dict[str, Any], *, source: str = "<memory>"
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = bundle.get("adapter_contract")
    if contract != CANONICAL_READ_CONTRACT:
        raise CanonicalReadError(
            f"canonical adapter contract mismatch: expected {CANONICAL_READ_CONTRACT}, got {contract!r}"
        )

    authority_state = bundle.get("authority_state")
    if authority_state != "CURRENT":
        raise CanonicalReadError(
            f"canonical authority is not current: {authority_state!r}; fail closed"
        )

    bindings = bundle.get("bindings")
    if not isinstance(bindings, dict):
        raise CanonicalReadError("canonical bundle bindings must be an object")
    missing_bindings = sorted(REQUIRED_BINDING_DOMAINS - set(bindings))
    if missing_bindings:
        raise CanonicalReadError(
            "canonical bundle is missing authority bindings: " + ", ".join(missing_bindings)
        )
    for domain in sorted(REQUIRED_BINDING_DOMAINS):
        binding = bindings[domain]
        if not isinstance(binding, dict) or not str(binding.get("semantic_owner", "")).strip():
            raise CanonicalReadError(f"canonical binding {domain!r} lacks semantic_owner")
        if not any(
            binding.get(key)
            for key in (
                "drive_id",
                "spreadsheet_id",
                "registry",
                "github_repo",
                "source",
            )
        ):
            raise CanonicalReadError(f"canonical binding {domain!r} lacks a source locator")

    raw_snapshot = bundle.get("snapshot")
    if not isinstance(raw_snapshot, dict):
        raise CanonicalReadError("canonical bundle snapshot must be an object")
    missing_keys = sorted(REQUIRED_SNAPSHOT_KEYS - set(raw_snapshot))
    if missing_keys:
        raise CanonicalReadError(
            "canonical snapshot is missing required keys: " + ", ".join(missing_keys)
        )

    provenance = raw_snapshot.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise CanonicalReadError("canonical snapshot provenance index is empty")

    event_provenance = raw_snapshot.get("event_provenance", {})
    if event_provenance and not isinstance(event_provenance, dict):
        raise CanonicalReadError("event_provenance must be an object")

    events = raw_snapshot.get("events", [])
    if events:
        if "events" not in bindings:
            raise CanonicalReadError("event-enabled canonical bundle lacks events binding")
        event_binding = bindings["events"]
        if (
            not isinstance(event_binding, dict)
            or not str(event_binding.get("semantic_owner", "")).strip()
            or not any(event_binding.get(key) for key in ("spreadsheet_id", "source", "registry"))
        ):
            raise CanonicalReadError("canonical binding 'events' is incomplete")
        if not isinstance(raw_snapshot.get("event_inventory"), dict):
            raise CanonicalReadError("event-enabled canonical bundle lacks event_inventory")
        forbidden_event_fields = {"meaning", "translation", "semantic_gloss", "english_gloss"}
        for event in events:
            if not isinstance(event, dict) or not event.get("event_id"):
                raise CanonicalReadError("canonical event row lacks event_id")
            leaked = sorted(forbidden_event_fields & set(event))
            if leaked:
                raise CanonicalReadError(
                    f"event {event.get('event_id')} contains forbidden semantic fields: "
                    + ", ".join(leaked)
                )

    refs = _record_provenance_ids(raw_snapshot)
    known_provenance = set(provenance) | set(event_provenance)
    unresolved = sorted(set(refs) - known_provenance)
    if unresolved:
        raise CanonicalReadError(
            "canonical snapshot has unresolved provenance ids: " + ", ".join(unresolved)
        )

    for dataset in raw_snapshot.get("datasets", []):
        if dataset.get("semantic_authority") != "NONE":
            raise CanonicalReadError(
                f"dataset {dataset.get('dataset_id', '<unknown>')} attempts semantic authority"
            )

    for verification in raw_snapshot.get("software_verification", []):
        if (
            verification.get("class") == "ZERO_SYNTHETIC"
            and verification.get("biological_evidence") is not False
        ):
            raise CanonicalReadError(
                "ZERO_SYNTHETIC software verification cannot carry biological evidence"
            )

    transport = _source_transport(source)
    snapshot = deepcopy(raw_snapshot)
    snapshot["mode"] = "CANONICAL_READ_ADAPTER"
    snapshot["canonical_adapter_contract"] = CANONICAL_READ_CONTRACT
    status = {
        "source_mode": "CANONICAL_READ_ADAPTER",
        "source_transport": transport,
        "source": source,
        "adapter_contract": CANONICAL_READ_CONTRACT,
        "authority_state": "CURRENT",
        "captured_at_utc": bundle.get("captured_at_utc"),
        "bindings": deepcopy(bindings),
        "authoritative_live_read": transport == "http",
        "scientific_effect": "NONE",
    }
    return snapshot, status


def load_canonical_source(source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return canonical_bundle_to_snapshot(_read_json_source(source), source=source)
