"""Only synthetic test inputs; no source data or trial outcome imported."""
from __future__ import annotations
import csv
import hashlib
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_d0037_playback_csv import audit_playback_csv, REQUIRED  # noqa: E402


def write_csv(path, records, *, headers=REQUIRED):
    with path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(headers)
        writer.writerows(records)


def healthy_rows():
    return [
        ("1", "unmanipulated_eel", "yes", "12.5", "0.5"),
        ("1", "silence", "no", "NA", "NA"),
        ("2", "manipulated_eel", "yes", "2.75", "1"),
    ]


def test_missing_bytes_fail_closed(tmp_path):
    r = audit_playback_csv(tmp_path / "not_found.csv")
    assert r["state"] == "HELD_NO_SOURCE_BYTES"
    assert r["source_rows_inspected"] is False
    assert r["admission_ready"] is False


def test_valid_synthetic_rows_preserve_provider_hold(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, healthy_rows())
    r = audit_playback_csv(p)
    assert r["state"] == "USER_SOURCE_ROWS_PARSED_PROVIDER_IDENTITY_HELD"
    assert r["observed_trial_rows"] == 3
    assert r["observed_individual_count"] == 2
    assert r["conditional_measure_status_counts"]["no_response_duration_not_applicable"] == 1
    assert r["observed_response_counts"] == {"no": 1, "yes": 2}
    assert r["provider_byte_identity_verified"] is False
    assert r["admission_ready"] is False
    assert r["scientific_effect"] == "NONE"


def test_proven_provider_hash_only_passes_identity_not_admission(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, healthy_rows())
    r = audit_playback_csv(p, provider_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    assert r["state"] == "PROVIDER_HASH_MATCH_AND_ROW_SCHEMA_PASS_ADMISSION_NOT_AUTOMATIC"
    assert r["provider_byte_identity_verified"] is True
    assert r["admission_ready"] is False


def test_hash_mismatch_fails_closed(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, healthy_rows())
    r = audit_playback_csv(p, provider_sha256="0" * 64)
    assert any("mismatch" in x for x in r["failures"])
    assert r["admission_ready"] is False


def test_response_conditional_measure_is_not_zero(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, [("1", "silence", "no", "0", "0")])
    r = audit_playback_csv(p)
    assert any("conditional measure" in x for x in r["failures"])


def test_out_of_range_amplitude_fails(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, [("1", "silence", "yes", "1", "1.1")])
    r = audit_playback_csv(p)
    assert any("amplitude > 1" in x for x in r["failures"])


def test_missing_positive_conditional_value_requires_review(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, [("1", "silence", "yes", "", "NA")])
    r = audit_playback_csv(p)
    assert r["conditional_measure_status_counts"]["yes_response_duration_absent_review"] == 1
    assert r["conditional_measure_status_counts"]["yes_response_amplitude_absent_review"] == 1
    assert any("missing" in x for x in r["warnings"])
    assert r["admission_ready"] is False


def test_unrecognized_category_and_subject_fail(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, [("14", "eel_magic", "yes", "2", "0.7")])
    r = audit_playback_csv(p)
    assert any("playback type" in x for x in r["failures"])
    assert any("individual_id" in x for x in r["failures"])


def test_unknown_extra_fields_not_silently_truncated(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    write_csv(p, [(*healthy_rows()[0], "extra")], headers=(*REQUIRED, "unused"))
    r = audit_playback_csv(p)
    assert r["observed_trial_rows"] == 1
    assert any("additional columns" in x for x in r["warnings"])


def test_duplicate_rows_warn_not_auto_dedup(tmp_path):
    p = tmp_path / "dataset_8_lab_g_rondoni_playback_experiment.csv"
    row = healthy_rows()[0]
    write_csv(p, [row, row])
    r = audit_playback_csv(p)
    assert r["observed_trial_rows"] == 2
    assert r["identical_source_row_count"] == 1
    assert any("no automatic deduplication" in x for x in r["warnings"])
