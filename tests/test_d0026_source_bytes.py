from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_d0026_source_bytes import audit_source_bytes  # noqa: E402


FROZEN_SNAPSHOT = ROOT / "contracts" / "d0026_osf_metadata_snapshot.json"


def _hashes(path: Path) -> dict[str, str]:
    payload = path.read_bytes()
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
    }


def _synthetic_snapshot(root: Path) -> dict:
    analysis = root / "analysis" / "a.R"
    data = root / "data" / "b.xlsx"
    analysis.parent.mkdir(parents=True)
    data.parent.mkdir(parents=True)
    analysis.write_text("x <- 1\n")
    data.write_bytes(b"synthetic-xlsx-placeholder")
    files = [
        {
            "file_id": "file-a",
            "path": "/analysis/a.R",
            "size_bytes": analysis.stat().st_size,
            "current_version": 1,
            "provider_reported_hashes": _hashes(analysis),
        },
        {
            "file_id": "file-b",
            "path": "/data/b.xlsx",
            "size_bytes": data.stat().st_size,
            "current_version": 1,
            "provider_reported_hashes": _hashes(data),
        },
    ]
    return {
        "dataset_id": "D0026",
        "study_id": "S0091",
        "license_name": "No license",
        "license_is_reuse_permission": False,
        "file_count": len(files),
        "files": files,
        "publication_version_equivalence": "UNCONFIRMED",
        "schema_and_runtime_audit": "HELD_UNTIL_RIGHTS_AND_PUBLICATION_VERSION_RESOLUTION",
        "scientific_role": "ACOUSTIC_PRODUCTION_TAXONOMY_ONLY",
        "biological_evidence": False,
        "scientific_effect": "NONE",
    }


def test_complete_byte_verification_preserves_all_admission_holds(tmp_path: Path) -> None:
    snapshot = _synthetic_snapshot(tmp_path)

    receipt = audit_source_bytes(tmp_path, snapshot)

    assert receipt["byte_integrity_verified"] is True
    assert receipt["state"] == "SOURCE_BYTES_HASH_VERIFIED"
    assert receipt["admission_ready"] is False
    assert receipt["rights_ready"] is False
    assert receipt["rights_state"]["license_name"] == "No license"
    assert receipt["rights_state"]["license_is_reuse_permission"] is False
    assert receipt["publication_version_equivalence"] == "UNCONFIRMED"
    assert receipt["schema_runtime_audit_performed"] is False
    assert receipt["source_rows_inspected"] is False
    assert receipt["scientific_role"] == "ACOUSTIC_PRODUCTION_TAXONOMY_ONLY"
    assert receipt["biological_evidence"] is False
    assert receipt["scientific_effect"] == "NONE"


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    snapshot = _synthetic_snapshot(tmp_path)
    (tmp_path / "analysis" / "a.R").unlink()

    receipt = audit_source_bytes(tmp_path, snapshot)

    assert receipt["byte_integrity_verified"] is False
    assert receipt["state"] == "HELD_SOURCE_BYTE_INTEGRITY"
    assert receipt["admission_ready"] is False
    assert any("failed byte-integrity audit" in failure for failure in receipt["failures"])


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    snapshot = _synthetic_snapshot(tmp_path)
    target = tmp_path / "data" / "b.xlsx"
    target.write_bytes(b"tampered-but-different")
    snapshot["files"][1]["size_bytes"] = target.stat().st_size

    receipt = audit_source_bytes(tmp_path, snapshot)

    assert receipt["byte_integrity_verified"] is False
    file_receipt = receipt["files"][1]
    assert any("differs from frozen provider metadata" in failure for failure in file_receipt["failures"])
    assert receipt["scientific_effect"] == "NONE"


def test_unsafe_provider_path_is_held(tmp_path: Path) -> None:
    snapshot = _synthetic_snapshot(tmp_path)
    snapshot["files"][0]["path"] = "/analysis/../escape.R"

    receipt = audit_source_bytes(tmp_path, snapshot)

    assert receipt["byte_integrity_verified"] is False
    assert "unsafe or missing provider path" in receipt["files"][0]["failures"]
    assert receipt["admission_ready"] is False


def test_frozen_d0026_snapshot_has_required_integrity_and_rights_fields() -> None:
    snapshot = json.loads(FROZEN_SNAPSHOT.read_text())

    assert snapshot["dataset_id"] == "D0026"
    assert snapshot["file_count"] == 5
    assert len(snapshot["files"]) == 5
    assert snapshot["license_name"] == "No license"
    assert snapshot["license_is_reuse_permission"] is False
    assert snapshot["publication_version_equivalence"] == "UNCONFIRMED"
    assert snapshot["scientific_role"] == "ACOUSTIC_PRODUCTION_TAXONOMY_ONLY"
    assert snapshot["biological_evidence"] is False
    for item in snapshot["files"]:
        assert item["current_version"] == 1
        assert item["size_bytes"] > 0
        assert len(item["provider_reported_hashes"]["sha256"]) == 64
        assert len(item["provider_reported_hashes"]["md5"]) == 32
