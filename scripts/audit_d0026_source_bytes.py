"""Offline byte-integrity audit for the frozen D0026 OSF snapshot.

This script never downloads provider data and never interprets source rows. It verifies only
already-materialized local files against the source-authoritative identities, sizes and hashes
frozen in contracts/d0026_osf_metadata_snapshot.json. Successful byte verification does not
resolve rights, publication-version equivalence, schema/runtime audit, or scientific admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_SNAPSHOT = Path("contracts/d0026_osf_metadata_snapshot.json")


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(provider_path: str) -> Path | None:
    if not provider_path or "\\" in provider_path or "\x00" in provider_path:
        return None
    candidate = PurePosixPath(provider_path)
    parts = candidate.parts[1:] if candidate.is_absolute() else candidate.parts
    if not parts or ".." in parts:
        return None
    return Path(*parts)


def _audit_file(root: Path, declared: dict[str, Any]) -> dict[str, Any]:
    provider_path = declared.get("path")
    relative = _safe_relative_path(provider_path) if isinstance(provider_path, str) else None
    record: dict[str, Any] = {
        "file_id": declared.get("file_id"),
        "provider_path": provider_path,
        "current_version": declared.get("current_version"),
        "exists": False,
        "hashes_verified": False,
        "failures": [],
    }
    failures: list[str] = record["failures"]
    if relative is None:
        failures.append("unsafe or missing provider path")
        return record

    local_path = root / relative
    record["relative_path"] = relative.as_posix()
    record["local_path"] = str(local_path)
    if not local_path.is_file():
        failures.append("materialized file is missing")
        return record

    record["exists"] = True
    actual_size = local_path.stat().st_size
    record["size_bytes"] = actual_size
    expected_size = declared.get("size_bytes")
    record["expected_size_bytes"] = expected_size
    if not isinstance(expected_size, int) or actual_size != expected_size:
        failures.append("local size differs from frozen provider metadata")

    provider_hashes = declared.get("provider_reported_hashes")
    if not isinstance(provider_hashes, dict) or not provider_hashes:
        failures.append("frozen provider hashes are missing")
        return record

    local_hashes: dict[str, str] = {}
    for algorithm in ("sha256", "md5"):
        expected = provider_hashes.get(algorithm)
        if not expected:
            failures.append(f"frozen provider {algorithm} is missing")
            continue
        actual = _hash_file(local_path, algorithm)
        local_hashes[algorithm] = actual
        if actual.lower() != str(expected).lower():
            failures.append(f"local {algorithm} differs from frozen provider metadata")

    record["local_hashes"] = local_hashes
    record["provider_reported_hashes"] = provider_hashes
    record["hashes_verified"] = not failures
    return record


def audit_source_bytes(root: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if snapshot.get("dataset_id") != "D0026":
        failures.append("snapshot dataset_id is not D0026")

    declared_files = snapshot.get("files")
    if not isinstance(declared_files, list):
        declared_files = []
        failures.append("snapshot files must be a list")

    declared_count = snapshot.get("file_count")
    if declared_count != len(declared_files):
        failures.append("snapshot file_count does not match file inventory")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    file_receipts: list[dict[str, Any]] = []
    expected_relative_paths: set[str] = set()

    for declared in declared_files:
        if not isinstance(declared, dict):
            failures.append("snapshot contains a non-object file entry")
            continue
        file_id = declared.get("file_id")
        provider_path = declared.get("path")
        if not isinstance(file_id, str) or not file_id:
            failures.append("snapshot file entry is missing file_id")
        elif file_id in seen_ids:
            failures.append(f"duplicate frozen file_id: {file_id}")
        else:
            seen_ids.add(file_id)
        if not isinstance(provider_path, str) or not provider_path:
            failures.append("snapshot file entry is missing provider path")
        elif provider_path in seen_paths:
            failures.append(f"duplicate frozen provider path: {provider_path}")
        else:
            seen_paths.add(provider_path)

        relative = _safe_relative_path(provider_path) if isinstance(provider_path, str) else None
        if relative is not None:
            expected_relative_paths.add(relative.as_posix())

        receipt = _audit_file(root, declared)
        file_receipts.append(receipt)
        if not receipt["hashes_verified"]:
            failures.append(f"{file_id or provider_path or 'unknown file'} failed byte-integrity audit")

    local_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    } if root.is_dir() else set()

    byte_integrity_verified = bool(declared_files) and not failures
    return {
        "dataset_id": "D0026",
        "study_id": snapshot.get("study_id"),
        "phase": "SOURCE_BYTE_INTEGRITY_ONLY",
        "state": "SOURCE_BYTES_HASH_VERIFIED" if byte_integrity_verified else "HELD_SOURCE_BYTE_INTEGRITY",
        "byte_integrity_verified": byte_integrity_verified,
        "source_bytes_downloaded": byte_integrity_verified,
        "source_rows_inspected": False,
        "schema_runtime_audit_performed": False,
        "admission_ready": False,
        "rights_ready": False,
        "rights_state": {
            "license_name": snapshot.get("license_name"),
            "license_is_reuse_permission": snapshot.get("license_is_reuse_permission"),
        },
        "publication_version_equivalence": snapshot.get("publication_version_equivalence"),
        "schema_and_runtime_audit": snapshot.get("schema_and_runtime_audit"),
        "scientific_role": snapshot.get("scientific_role"),
        "biological_evidence": snapshot.get("biological_evidence"),
        "scientific_effect": "NONE",
        "files": file_receipts,
        "unregistered_local_files": sorted(local_files - expected_relative_paths),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit already-materialized D0026 OSF source bytes offline")
    parser.add_argument("--root", required=True, help="Local root containing the frozen /analysis and /data paths")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--out", default="build/d0026_source_byte_receipt.json")
    args = parser.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text())
    receipt = audit_source_bytes(Path(args.root), snapshot)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "dataset_id": receipt["dataset_id"],
        "state": receipt["state"],
        "byte_integrity_verified": receipt["byte_integrity_verified"],
        "admission_ready": receipt["admission_ready"],
        "rights_ready": receipt["rights_ready"],
        "scientific_effect": receipt["scientific_effect"],
        "output": str(out),
    }))
    raise SystemExit(0 if receipt["byte_integrity_verified"] else 2)


if __name__ == "__main__":
    main()
