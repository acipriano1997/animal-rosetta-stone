from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from ars_receiver_harness.admission import AdmissionError, validate_admission
from ars_receiver_harness.cli import main
from ars_receiver_harness.pr0006 import PR0006Config


def _admission_case(tmp_path: Path):
    df = pd.DataFrame([
        {
            "Event_ID": f"event-{i}",
            "Source_Record_Locator": f"source-row-{i}",
            "Recipient_Response": "approach" if i % 2 else "avoidance",
            "Communication_Type": ("gesture", "vocalization", "bimodal")[i % 3],
            "Signaller_ID": f"S{i % 6}",
            "Dyad_ID": f"D{i % 6}",
            "Social_Bond": float(i % 4),
        } for i in range(36)
    ])
    raw = tmp_path / "pinned_raw_source.dat"
    raw.write_bytes(b"authored synthetic fixture bytes only")
    csv = tmp_path / "normalized.csv"
    df.to_csv(csv, index=False)
    checksum = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {
        "protocol_id": "PR0006", "receiver_contract": "RDC-005",
        "evidence_weight": "ZERO_SYNTHETIC",
        "rights": {"research_use_storage": True, "evidence_ref": "synthetic-fixture", "attribution_ref": "fixture-author"},
        "source": {"provider": "fixture", "dataset_id": "SYNTHETIC", "version": "1",
                   "filename": raw.name, "sha256": checksum(raw)},
        "schema": {"inventory_complete": True, "codebook_ref": "fixture-codebook"},
        "mapping": {"required_primary_unmappable": False, "review_ref": "fixture-reviewed",
                    "pre_outcome_checked": True, "approved_baseline_numeric": ["Social_Bond"],
                    "approved_baseline_categorical": []},
        "event_identity": {"source_locator_present": True, "deterministic": True,
                           "collision_check_passed": True, "derivation_rule_ref": "fixture-id-v1"},
        "missingness": {"primary_outcome_imputed": False, "states_preserved": True},
        "split": {"sealed": True},
        "grouping": {"rowwise_fallback": False, "valid_registered_key": True,
                     "outcome_or_locked_leakage": False, "fallback_activated": False},
        "nuisance": {"inventory_recorded": True, "material_shortcut_risk": False,
                    "metadata_incomplete": False, "review_ref": "fixture-nuisance"},
        "normalization": {"row_preserving": True, "semantic_escalation": False,
                          "eligible_only": True, "eligibility_ledger_ref": "fixture-ledger",
                          "normalized_sha256": checksum(csv)},
        "run_package": {"complete": True},
        "sanity": {"registered": True, "protocol_id": "PD-PR0006-003"},
    }
    cfg = PR0006Config(baseline_numeric=("Social_Bond",))
    return df, csv, raw, manifest, cfg


def test_valid_synthetic_admission_is_not_biological_claim(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    run_cfg, receipt = validate_admission(df, csv, raw, manifest, cfg)
    assert run_cfg.primary_group_col == "Dyad_ID"
    assert receipt["state"] == "ADMITTED_FOR_REGISTERED_ANALYSIS_ONLY"
    assert receipt["evidence_weight"] == "ZERO_SYNTHETIC"
    assert receipt["claim_admissible"] is False


def test_source_byte_mismatch_is_quarantined(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    raw.write_bytes(b"modified source bytes")
    with pytest.raises(AdmissionError, match="QUARANTINED_PROVENANCE"):
        validate_admission(df, csv, raw, manifest, cfg)


def test_normalized_csv_mismatch_is_quarantined(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    csv.write_text(csv.read_text() + "\n")
    with pytest.raises(AdmissionError, match="QUARANTINED_PROVENANCE"):
        validate_admission(df, csv, raw, manifest, cfg)


def test_rights_evidence_is_required(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    manifest["rights"].pop("evidence_ref")
    with pytest.raises(AdmissionError, match="HELD_RIGHTS"):
        validate_admission(df, csv, raw, manifest, cfg)


def test_frozen_permutation_count_cannot_be_changed(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    cfg = PR0006Config(baseline_numeric=("Social_Bond",), sanity_permutations=20)
    with pytest.raises(AdmissionError, match="HELD_SCHEMA"):
        validate_admission(df, csv, raw, manifest, cfg)


def test_undeclared_intercept_only_baseline_is_blocked(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    cfg = PR0006Config()
    manifest["mapping"]["approved_baseline_numeric"] = []
    with pytest.raises(AdmissionError, match="HELD_SCHEMA"):
        validate_admission(df, csv, raw, manifest, cfg)


def test_signaller_only_fallback_requires_recorded_approval(tmp_path):
    df, csv, raw, manifest, cfg = _admission_case(tmp_path)
    df = df.drop(columns=["Dyad_ID"])
    with pytest.raises(AdmissionError, match="HELD_GROUPING"):
        validate_admission(df, csv, raw, manifest, cfg)
    manifest["grouping"]["fallback_activated"] = True
    manifest["grouping"]["fallback_approval_ref"] = "fixture-fallback"
    run_cfg, receipt = validate_admission(df, csv, raw, manifest, cfg)
    assert run_cfg.primary_group_col == "Signaller_ID"
    assert receipt["fallback_activated"] is True


def test_direct_cli_requires_source_manifest_and_config():
    with pytest.raises(SystemExit) as exc:
        main(["normalized.csv"])
    assert exc.value.code == 2
