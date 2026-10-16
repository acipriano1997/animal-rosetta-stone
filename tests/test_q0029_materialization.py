from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_q0029_materialization import audit_materialization  # noqa: E402


CONTRACT_PATH = ROOT / "contracts" / "q0029_provider_materialization_v0_1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest_dataset(root: Path, dataset_id: str, spec: dict, filename: str) -> None:
    files = root / dataset_id / "files"
    files.mkdir(parents=True)
    source = files / filename
    source.write_text("interaction_id,dyad\nI1,A-B\n")
    manifest = {
        "source_identity": spec["source_identity"],
        "version": spec["version"],
        "files": [
            {
                "name": filename,
                "size_bytes": source.stat().st_size,
                "source_url": f"https://example.invalid/{dataset_id}/{filename}",
                "provider_hashes": {"sha256": _sha256(source)},
                "role": "data",
            }
        ],
    }
    (root / dataset_id / spec["provider_manifest_filename"]).write_text(json.dumps(manifest))


def _write_zip(path: Path, member: str = "table.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr(member, "id,value\n1,2\n")


def _complete_tree(tmp_path: Path, contract: dict) -> None:
    _write_manifest_dataset(tmp_path, "D0031", contract["datasets"]["D0031"], "analysis.csv")
    _write_manifest_dataset(tmp_path, "D0033", contract["datasets"]["D0033"], "turns.csv")
    for item in contract["datasets"]["D0032"]["provider_objects"]:
        _write_zip(tmp_path / "D0032" / "files" / item["filename"])


def test_complete_materialization_never_promotes_scientific_admission(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT_PATH.read_text())
    _complete_tree(tmp_path, contract)

    receipt = audit_materialization(tmp_path, contract)

    assert receipt["materialization_complete"] is True
    assert receipt["state"] == "LOCAL_PROVIDER_BYTES_HASHED"
    assert receipt["admission_ready"] is False
    assert receipt["scientific_effect"] == "NONE"
    assert receipt["replication_credit_change"] == "NONE"
    assert receipt["source_rows_inspected"] is False
    assert receipt["archive_members_extracted"] is False
    assert receipt["d0031_d0033_dependence_gate"]["current_evidence_weighting_state"] == "NON_INDEPENDENT"
    assert len(receipt["datasets"]["D0032"]["files"]) == 12


def test_missing_fixed_provider_object_fails_closed(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT_PATH.read_text())
    _complete_tree(tmp_path, contract)
    missing = contract["datasets"]["D0032"]["provider_objects"][0]["filename"]
    (tmp_path / "D0032" / "files" / missing).unlink()

    receipt = audit_materialization(tmp_path, contract)

    assert receipt["materialization_complete"] is False
    assert receipt["state"] == "HELD_PROVIDER_MATERIALIZATION"
    assert receipt["datasets"]["D0032"]["bytes_materialized"] is False
    assert receipt["admission_ready"] is False


def test_unsafe_zip_member_is_held_without_extraction(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT_PATH.read_text())
    _complete_tree(tmp_path, contract)
    target = contract["datasets"]["D0032"]["provider_objects"][0]["filename"]
    _write_zip(tmp_path / "D0032" / "files" / target, "../escape.csv")

    receipt = audit_materialization(tmp_path, contract)

    assert receipt["materialization_complete"] is False
    first = receipt["datasets"]["D0032"]["files"][0]
    assert any("unsafe ZIP member path" in failure for failure in first["failures"])
    assert first["archive_extracted"] is False
    assert receipt["admission_ready"] is False


def test_provider_manifest_identity_mismatch_is_held(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT_PATH.read_text())
    _complete_tree(tmp_path, contract)
    manifest_path = tmp_path / "D0031" / contract["datasets"]["D0031"]["provider_manifest_filename"]
    manifest = json.loads(manifest_path.read_text())
    manifest["source_identity"] = "wrong-doi"
    manifest_path.write_text(json.dumps(manifest))

    receipt = audit_materialization(tmp_path, contract)

    assert receipt["materialization_complete"] is False
    assert receipt["datasets"]["D0031"]["state"] == "HELD_PROVIDER_MATERIALIZATION"
    assert any("source_identity" in failure for failure in receipt["datasets"]["D0031"]["failures"])
