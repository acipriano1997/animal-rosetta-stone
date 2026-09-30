from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .preflight import postflight, preflight
from .pr0006 import PR0006Config, run_pr0006


@dataclass(frozen=True)
class FixtureResult:
    fixture_id: str
    contract_id: str
    expected_state: str
    observed_state: str
    passed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _common_state(payload: dict[str, Any]) -> str | None:
    if payload.get("rights") is False:
        return "HELD_RIGHTS"
    if payload.get("provenance") is False:
        return "QUARANTINED_PROVENANCE"
    return None


def _rdc001(payload: dict[str, Any]) -> str:
    common = _common_state(payload)
    if common:
        return common
    if not payload.get("caller", True) or not payload.get("recipient", True):
        return "INELIGIBLE_PRIMARY"
    if not payload.get("outcome", True):
        return "OUTCOME_UNAVAILABLE"
    if payload.get("negative_inference") and not payload.get("coverage", True):
        return "REJECT_NEGATIVE_INFERENCE"
    return "PASS_INGESTION_PREFLIGHT"


def _rdc002(payload: dict[str, Any]) -> str:
    if payload.get("combined_rights_provenance_test"):
        a = _rdc002({**payload, "rights": False, "provenance": True, "combined_rights_provenance_test": False})
        b = _rdc002({**payload, "rights": True, "provenance": False, "combined_rights_provenance_test": False})
        return "HELD_OR_QUARANTINED" if {a, b} == {"HELD_RIGHTS", "QUARANTINED_PROVENANCE"} else "INVALID_COMBINED_GATE"
    common = _common_state(payload)
    if common:
        return common
    if payload.get("post_response_leakage"):
        return "QUARANTINED_OUTCOME_LEAKAGE"
    if not payload.get("caller", True) or not payload.get("responder", True):
        return "INELIGIBLE_PRIMARY"
    if not payload.get("timing", True):
        return "PRIMARY_ENDPOINT_UNAVAILABLE"
    if payload.get("negative_inference") and not payload.get("coverage", True):
        return "REJECT_NEGATIVE_INFERENCE"
    return "PASS_INGESTION_PREFLIGHT"


def _rdc003(payload: dict[str, Any]) -> str:
    if payload.get("combined_rights_provenance_test"):
        a = _rdc003({**payload, "rights": False, "provenance": True, "combined_rights_provenance_test": False})
        b = _rdc003({**payload, "rights": True, "provenance": False, "combined_rights_provenance_test": False})
        return "HELD_OR_QUARANTINED" if {a, b} == {"HELD_RIGHTS", "QUARANTINED_PROVENANCE"} else "INVALID_COMBINED_GATE"
    common = _common_state(payload)
    if common:
        return common
    if not payload.get("mother", True):
        return "INELIGIBLE_PRIMARY"
    if payload.get("visibility_inferred"):
        return "QUARANTINED_SEMANTIC_ESCALATION"
    if not payload.get("acoustic_link", True):
        return "ACOUSTIC_INCREMENT_UNAVAILABLE"
    if payload.get("heldout_outcome_leakage"):
        return "QUARANTINED_OUTCOME_LEAKAGE"
    if payload.get("negative_inference") and not payload.get("coverage", True):
        return "OUTCOME_UNAVAILABLE"
    return "PASS_INGESTION_PREFLIGHT"


def _rdc004(payload: dict[str, Any]) -> str:
    common = _common_state(payload)
    if common:
        return common
    if payload.get("locked_group_leakage"):
        return "QUARANTINED_OUTCOME_LEAKAGE"
    if not payload.get("group", True):
        return "HELD_SPLIT"
    if not payload.get("dyad", True):
        return "PASS_WITH_REGISTERED_FALLBACK" if payload.get("initiator_fallback", False) else "HELD_GROUPING"
    if payload.get("face_missing_to_neutral") or payload.get("semantic_gloss"):
        return "QUARANTINED_SEMANTIC_ESCALATION"
    if payload.get("response_missing_to_negative"):
        return "QUARANTINED_OUTCOME_LEAKAGE"
    return "PASS_INGESTION_PREFLIGHT"


def _good_manifest() -> dict[str, Any]:
    return {
        "rights": {"research_use_storage": True},
        "source": {"provider": "synthetic", "dataset_id": "D0025", "version": "fixture", "filename": "fixture.csv", "sha256": "a" * 64},
        "schema": {"inventory_complete": True},
        "mapping": {"required_primary_unmappable": False},
        "event_identity": {"source_locator_present": True, "deterministic": True},
        "missingness": {"primary_outcome_imputed": False, "states_preserved": True},
        "split": {"sealed": True},
        "grouping": {"rowwise_fallback": False, "valid_registered_key": True, "outcome_or_locked_leakage": False},
        "nuisance": {"inventory_recorded": True, "material_shortcut_risk": False, "metadata_incomplete": False},
        "normalization": {"row_preserving": True, "semantic_escalation": False},
        "run_package": {"complete": True},
        "sanity": {"registered": True},
    }


def _fold_failure_df() -> pd.DataFrame:
    rows = []
    for g in range(5):
        for i in range(24):
            rows.append({
                "Recipient_Response": "approach" if i % 2 else "avoidance",
                "Communication_Type": "vocalization" if g == 0 else "gesture",
                "Dyad_ID": f"D{g}",
                "Signaller_ID": f"S{g % 3}",
            })
    return pd.DataFrame(rows)


def _rdc005(payload: dict[str, Any]) -> str:
    mode = payload.get("mode")
    if mode == "fold_support_failure":
        try:
            run_pr0006(_fold_failure_df(), PR0006Config(bootstrap_resamples=20, sanity_permutations=5))
        except ValueError as exc:
            return "HELD_SPLIT" if "HELD_SPLIT" in str(exc) else f"UNEXPECTED_ERROR:{exc}"
        return "UNEXPECTED_PASS"
    if mode == "nuisance_limit":
        m = _good_manifest()
        m["nuisance"]["material_shortcut_risk"] = True
        m["nuisance"]["mitigation_or_claim_limit_recorded"] = True
        return preflight(m).state
    if mode == "sanity_failure":
        return postflight({"sanity": {"passed": False}, "result": {"preserved": True}}).state
    if mode == "valid":
        return preflight(_good_manifest()).state
    raise ValueError(f"Unknown RDC-005 fixture mode {mode!r}")


FIXTURE_PAYLOADS: dict[str, dict[str, Any]] = {
    "RHF-001":{"rights":True,"provenance":True},
    "RHF-002":{"rights":True,"provenance":True,"caller":False},
    "RHF-003":{"rights":True,"provenance":True,"recipient":False},
    "RHF-004":{"rights":True,"provenance":True,"outcome":False},
    "RHF-005":{"rights":True,"provenance":True,"negative_inference":True,"coverage":False},
    "RHF-006":{"rights":False,"provenance":True},
    "RHF-007":{"rights":True,"provenance":False},
    "RHF-008":{"rights":True,"provenance":True},
    "RHF-009":{"rights":True,"provenance":True,"post_response_leakage":True},
    "RHF-010":{"rights":True,"provenance":True,"caller":False},
    "RHF-011":{"rights":True,"provenance":True,"responder":False},
    "RHF-012":{"rights":True,"provenance":True,"timing":False},
    "RHF-013":{"rights":True,"provenance":True,"negative_inference":True,"coverage":False},
    "RHF-014":{"combined_rights_provenance_test":True},
    "RHF-015":{"rights":True,"provenance":True},
    "RHF-016":{"rights":True,"provenance":True,"mother":False},
    "RHF-017":{"rights":True,"provenance":True,"visibility_inferred":True},
    "RHF-018":{"rights":True,"provenance":True,"acoustic_link":False},
    "RHF-019":{"rights":True,"provenance":True,"heldout_outcome_leakage":True},
    "RHF-020":{"rights":True,"provenance":True,"negative_inference":True,"coverage":False},
    "RHF-021":{"combined_rights_provenance_test":True},
    "RHF-022":{"rights":True,"provenance":True},
    "RHF-023":{"rights":True,"provenance":True,"locked_group_leakage":True},
    "RHF-024":{"rights":True,"provenance":True,"group":False},
    "RHF-025":{"rights":True,"provenance":True,"dyad":False,"initiator_fallback":True},
    "RHF-026":{"rights":True,"provenance":True,"dyad":False,"initiator_fallback":False},
    "RHF-027":{"rights":True,"provenance":True,"face_missing_to_neutral":True},
    "RHF-028":{"rights":True,"provenance":True,"response_missing_to_negative":True},
    "RHF-029":{"rights":False,"provenance":True},
    "RHF-030":{"rights":True,"provenance":False},
    "RHF-031":{"rights":True,"provenance":True,"semantic_gloss":True},
    "RHF-032":{"mode":"fold_support_failure"},
    "RHF-033":{"mode":"nuisance_limit"},
    "RHF-034":{"mode":"sanity_failure"},
    "RHF-035":{"mode":"valid"},
}


def load_snapshot(path: Path | None = None) -> list[dict[str, str]]:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "contracts" / "rhf_fixture_snapshot.json"
    return json.loads(path.read_text())


def run_fixture(row: dict[str, str]) -> FixtureResult:
    fid, contract, expected = row["id"], row["contract"], row["expected"]
    payload = FIXTURE_PAYLOADS[fid]
    if contract == "RDC-001":
        observed = _rdc001(payload)
    elif contract == "RDC-002":
        observed = _rdc002(payload)
    elif contract == "RDC-003":
        observed = _rdc003(payload)
    elif contract == "RDC-004":
        observed = _rdc004(payload)
    elif contract == "RDC-005":
        observed = _rdc005(payload)
    else:
        observed = "UNSUPPORTED_CONTRACT"
    return FixtureResult(fid, contract, expected, observed, observed == expected, {"scenario": row["scenario"]})


def run_suite(snapshot_path: Path | None = None) -> dict[str, Any]:
    rows = load_snapshot(snapshot_path)
    results = [run_fixture(row) for row in rows]
    expected_ids = [f"RHF-{i:03d}" for i in range(1, 36)]
    observed_ids = [r.fixture_id for r in results]
    all_passed = all(r.passed for r in results) and observed_ids == expected_ids
    return {
        "suite": "RHF-001..035",
        "evidence_weight": "ZERO_SYNTHETIC",
        "biological_evidence": False,
        "repository_sha": os.getenv("GITHUB_SHA") or os.getenv("ARS_REPOSITORY_SHA") or "LOCAL_UNCOMMITTED",
        "all_passed": all_passed,
        "passed": sum(r.passed for r in results),
        "total": len(results),
        "results": [r.to_dict() for r in results],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run ARS receiver-harness fixtures RHF-001..035")
    ap.add_argument("--out", default="rhf_suite_receipt.json")
    args = ap.parse_args()
    receipt = run_suite()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{receipt['passed']}/{receipt['total']} fixtures pass")
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
