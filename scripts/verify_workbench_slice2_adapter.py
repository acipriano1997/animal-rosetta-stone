from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ars_workbench.canonical import CANONICAL_READ_CONTRACT
from ars_workbench.store import WorkbenchStore


def _bundle(snapshot):
    return {
        "adapter_contract": CANONICAL_READ_CONTRACT,
        "authority_state": "CURRENT",
        "captured_at_utc": "2026-10-02T18:00:00Z",
        "bindings": {
            "species": {
                "semantic_owner": "Chimpanzee — Species Activation Record v0.1",
                "drive_id": "1KYlWfx-aD39DledKlF8xZdHOEKBdrMyXcQJwhHqAbic",
            },
            "question": {
                "semantic_owner": "ACEB Research Questions",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Research Questions:RQ0001",
            },
            "hypotheses": {
                "semantic_owner": "ACEB Hypotheses",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Hypotheses:H0001..H0003",
            },
            "datasets": {
                "semantic_owner": "ACEB Datasets",
                "spreadsheet_id": "1OXXnv9Q5Gse3D-r9EZNSR9H8FXugiHyRqndF3pv9czQ",
                "registry": "Datasets:D0018,D0019,D0020,D0025",
            },
            "runs": {
                "semantic_owner": "RQ0001 frozen run authorities",
                "source": "per-record provenance pointers",
            },
            "software_verification": {
                "semantic_owner": "ARS executable verification records",
                "github_repo": "acipriano1997/animal-rosetta-stone",
            },
            "provenance": {
                "semantic_owner": "record-specific canonical provenance authorities",
                "source": "snapshot provenance index",
            },
        },
        "snapshot": snapshot,
    }


def main() -> None:
    fixture_store = WorkbenchStore()
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "canonical.json"
        source.write_text(json.dumps(_bundle(fixture_store.overview())), encoding="utf-8")
        store = WorkbenchStore(canonical_source=str(source))

        status = store.authority_status()
        checks = {
            "canonical_mode_active": status["source_mode"] == "CANONICAL_READ_ADAPTER",
            "file_transport_not_mislabeled_live": (
                status["source_transport"] == "file"
                and status["authoritative_live_read"] is False
            ),
            "authority_current": status["authority_state"] == "CURRENT",
            "all_required_domains_bound": len(status["bindings"]) == 7,
            "species_adapter_operational": store.species_get("SP001")["taxon"] == "Pan troglodytes",
            "question_adapter_operational": store.question_get("RQ0001") is not None,
            "dataset_adapter_operational": store.dataset_get("D0019") is not None,
            "run_adapter_operational": store.run_get("RUN-PT-RQ0001-004") is not None,
            "provenance_adapter_operational": store.provenance_get("PROV-RUN004") is not None,
            "synthetic_stays_nonevidentiary": all(
                not x["biological_evidence"] for x in store.software_verification_list()
            ),
        }

    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 2A adapter boundary",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "adapter_contract": CANONICAL_READ_CONTRACT,
        "checks": checks,
        "all_passed": all(checks.values()),
        "scientific_effect": "NONE",
        "biological_evidence": False,
        "completion_scope": "transport-and-validation adapter only; direct Drive/ACEB synchronization remains open",
    }
    out = Path("build/workbench_slice2_adapter_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
