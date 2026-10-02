from __future__ import annotations

import json
import os
from copy import deepcopy
from importlib.resources import files
from typing import Any

from .canonical import load_canonical_source


class WorkbenchStore:
    """Read-only Workbench service boundary.

    With ARS_WORKBENCH_CANONICAL_SOURCE (or an explicit canonical_source), the
    store consumes a fail-closed canonical read bundle. Without one it preserves
    the Phase I Slice 1 frozen fixture as an explicitly non-live fallback.

    The store never computes evidence grades, semantics, scientific status, or
    schedule estimates.
    """

    def __init__(self, canonical_source: str | None = None) -> None:
        source = canonical_source or os.getenv("ARS_WORKBENCH_CANONICAL_SOURCE")
        if source:
            self._snapshot, self._authority_status = load_canonical_source(source)
        else:
            path = files("ars_workbench").joinpath("data/chimp_rq0001_snapshot.json")
            self._snapshot = json.loads(path.read_text(encoding="utf-8"))
            self._authority_status = {
                "source_mode": "STATIC_FIXTURE",
                "source": "package:ars_workbench/data/chimp_rq0001_snapshot.json",
                "adapter_contract": None,
                "authority_state": "STATIC_FIXTURE",
                "captured_at_utc": None,
                "bindings": {},
                "authoritative_live_read": False,
                "scientific_effect": "NONE",
            }

    def authority_status(self) -> dict[str, Any]:
        return deepcopy(self._authority_status)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._snapshot)

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
            return None
        return {"provenance_id": provenance_id, **deepcopy(item)}
