from __future__ import annotations

import json
import os
from copy import deepcopy
from importlib.resources import files
from typing import Any

from .canonical import load_canonical_source


class WorkbenchStore:
    """Read-only Workbench service boundary.

    Canonical bundles may carry the full event/provenance corpus. The packaged
    fallback carries only a tiny, explicitly sample-only event fixture so the UI
    remains executable without becoming a second scientific database.

    The store never computes evidence grades, semantics, scientific status, or
    schedule estimates.
    """

    def __init__(self, canonical_source: str | None = None) -> None:
        source = canonical_source or os.getenv("ARS_WORKBENCH_CANONICAL_SOURCE")
        if source:
            self._snapshot, self._authority_status = load_canonical_source(source)
            self._events = deepcopy(self._snapshot.get("events", []))
            self._event_inventory = deepcopy(self._snapshot.get("event_inventory", {}))
            self._event_provenance = deepcopy(self._snapshot.get("event_provenance", {}))
        else:
            path = files("ars_workbench").joinpath("data/chimp_rq0001_snapshot.json")
            self._snapshot = json.loads(path.read_text(encoding="utf-8"))
            event_path = files("ars_workbench").joinpath("data/chimp_rq0001_events_sample.json")
            event_fixture = json.loads(event_path.read_text(encoding="utf-8"))
            self._events = event_fixture["events"]
            self._event_inventory = event_fixture["event_inventory"]
            self._event_provenance = event_fixture["event_provenance"]
            self._authority_status = {
                "source_mode": "STATIC_FIXTURE",
                "source": "package:ars_workbench/data/chimp_rq0001_snapshot.json",
                "adapter_contract": None,
                "authority_state": "STATIC_FIXTURE",
                "captured_at_utc": None,
                "bindings": {},
                "authoritative_live_read": False,
                "event_coverage": "STATIC_SAMPLE_ONLY",
                "scientific_effect": "NONE",
            }

    def authority_status(self) -> dict[str, Any]:
        return deepcopy(self._authority_status)

    def snapshot(self) -> dict[str, Any]:
        out = deepcopy(self._snapshot)
        if self._events:
            out["events"] = deepcopy(self._events)
            out["event_inventory"] = deepcopy(self._event_inventory)
            out["event_provenance"] = deepcopy(self._event_provenance)
        return out

    def overview(self) -> dict[str, Any]:
        """Return the browser landing payload without thousands of event rows."""
        out = deepcopy(self._snapshot)
        out.pop("events", None)
        out.pop("event_provenance", None)
        out["event_inventory"] = deepcopy(self._event_inventory)
        return out

    def species_list(self) -> list[dict[str, Any]]:
        s = self._snapshot["species"]
        return [deepcopy({k: s[k] for k in ("species_id", "taxon", "common_name", "activation_state")})]

    def species_get(self, species_id: str) -> dict[str, Any] | None:
        s = self._snapshot["species"]
        return deepcopy(s) if species_id == s["species_id"] else None

    def question_get(self, question_id: str) -> dict[str, Any] | None:
        q = self._snapshot["question"]
        if question_id != q["question_id"]:
            return None
        out = deepcopy(q)
        out["hypotheses"] = deepcopy(self._snapshot["hypotheses"])
        return out

    def dataset_get(self, dataset_id: str) -> dict[str, Any] | None:
        for row in self._snapshot["datasets"]:
            if row["dataset_id"] == dataset_id:
                return deepcopy(row)
        return None

    def dataset_list(self) -> list[dict[str, Any]]:
        return deepcopy(self._snapshot["datasets"])

    def event_inventory(self) -> dict[str, Any]:
        return deepcopy(self._event_inventory)

    def events_list(
        self,
        *,
        dataset_id: str | None = None,
        population: str | None = None,
        split: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 250:
            raise ValueError("event limit must be between 1 and 250")
        if offset < 0:
            raise ValueError("event offset must be non-negative")

        rows = self._events
        if dataset_id:
            rows = [row for row in rows if row.get("dataset_id") == dataset_id]
        if population:
            rows = [
                row for row in rows
                if row.get("population_or_group_id") == population
            ]
        if split:
            rows = [row for row in rows if row.get("split") == split]

        total = len(rows)
        return {
            "items": deepcopy(rows[offset: offset + limit]),
            "total": total,
            "offset": offset,
            "limit": limit,
            "filters": {
                "dataset_id": dataset_id,
                "population": population,
                "split": split,
            },
            "inventory": deepcopy(self._event_inventory),
        }

    def event_get(self, event_id: str) -> dict[str, Any] | None:
        for row in self._events:
            if row.get("event_id") == event_id:
                return deepcopy(row)
        return None

    def run_list(self) -> list[dict[str, Any]]:
        return deepcopy(self._snapshot["runs"])

    def run_get(self, run_id: str) -> dict[str, Any] | None:
        for row in self._snapshot["runs"]:
            if row["run_id"] == run_id:
                return deepcopy(row)
        return None

    def software_verification_list(self) -> list[dict[str, Any]]:
        return deepcopy(self._snapshot["software_verification"])

    def evidence_get(self, question_id: str) -> dict[str, Any] | None:
        if question_id != self._snapshot["question"]["question_id"]:
            return None
        return {
            "question_id": question_id,
            "hypotheses": deepcopy(self._snapshot["hypotheses"]),
            "empirical_runs": deepcopy(self._snapshot["runs"]),
            "software_verification": deepcopy(self._snapshot["software_verification"]),
            "rule": "ZERO_SYNTHETIC software verification is segregated from empirical evidence.",
        }

    def provenance_get(self, provenance_id: str) -> dict[str, Any] | None:
        item = self._snapshot["provenance"].get(provenance_id)
        if item is None:
            item = self._event_provenance.get(provenance_id)
        if item is None:
            return None
        return {"provenance_id": provenance_id, **deepcopy(item)}
