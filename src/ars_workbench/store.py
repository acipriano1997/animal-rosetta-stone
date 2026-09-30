from __future__ import annotations

import json
from copy import deepcopy
from importlib.resources import files
from typing import Any


class WorkbenchStore:
    """Read-only view-model adapter over a frozen canonical fixture snapshot.

    Slice 1 intentionally does not fetch live Drive data and does not compute
    evidence grades, semantics, scientific status, or schedule estimates.
    """

    def __init__(self) -> None:
        path = files("ars_workbench").joinpath("data/chimp_rq0001_snapshot.json")
        self._snapshot: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

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
