"""Offline Q0029 provider-byte materialization audit.

This script never downloads provider data. It inventories bytes already materialized by an
approved binary-capable runtime, hashes them locally, inspects ZIP central directories without
extracting archive members, and preserves all scientific/rights gates as separate holds.
"""
from __future__ import annotations

try:
    from scripts.research_integrity import write_private
except ModuleNotFoundError:
    from research_integrity import write_private

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

DEFAULT_CONTRACT = Path("contracts/q0029_provider_materialization_v0_1.json")


def _hash_file(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_name(name: str) -> bool:
    if not name or "\\" in name or "\x00" in name:
        return False
    candidate = PurePosixPath(name)
    return not candidate.is_absolute() and ".." not in candidate.parts


def _zip_inventory(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    members: list[dict[str, Any]] = []
    failures: list[str] = []
    try:
        with ZipFile(path) as archive:
            for info in archive.infolist():
                if not _safe_relative_name(info.filename):
                    failures.append(f"unsafe ZIP member path: {info.filename!r}")
                if info.flag_bits & 0x1:
                    failures.append(f"encrypted ZIP member is not admissible for deterministic audit: {info.filename!r}")
                members.append(
                    {
                        "name": info.filename,
                        "compressed_size": info.compress_size,
                        "uncompressed_size": info.file_size,
                        "crc32": f"{info.CRC:08x}",
                        "is_dir": info.is_dir(),
                    }
                )
    except (OSError, BadZipFile) as exc:
        failures.append(f"ZIP central-directory read failed: {type(exc).__name__}: {exc}")
    return members, failures


def _audit_local_file(path: Path, declared: dict[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"local_path": str(path), "exists": path.is_file()}
    failures: list[str] = []
    if not path.is_file():
        record["failures"] = ["provider file is missing"]
        return record

    size = path.stat().st_size
    record["size_bytes"] = size
    record["sha256"] = _hash_file(path, "sha256")

    declared = declared or {}
    declared_size = declared.get("size_bytes")
    if isinstance(declared_size, int):
        record["declared_size_bytes"] = declared_size
        if declared_size != size:
            failures.append("local size differs from provider manifest")

    provider_hashes = declared.get("provider_hashes") or {}
    verified_hashes: dict[str, str] = {}
    if isinstance(provider_hashes, dict):
        for algorithm in ("sha256", "md5"):
            expected = provider_hashes.get(algorithm)
            if not expected:
                continue
            actual = record["sha256"] if algorithm == "sha256" else _hash_file(path, "md5")
            if str(expected).lower() != actual.lower():
                failures.append(f"local {algorithm} differs from provider manifest")
            else:
                verified_hashes[algorithm] = actual
    record["provider_hashes_verified"] = verified_hashes
    record["provider_hash_available"] = bool(provider_hashes)

    if path.suffix.lower() == ".zip":
        members, zip_failures = _zip_inventory(path)
        record["zip_member_count"] = len(members)
        record["zip_members"] = members
        record["archive_extracted"] = False
        failures.extend(zip_failures)

    record["failures"] = failures
    return record


def _load_provider_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"provider manifest unreadable: {type(exc).__name__}: {exc}"]
    if not isinstance(value, dict):
        return None, ["provider manifest root must be an object"]
    return value, []


def _audit_manifest_bound(root: Path, dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    dataset_root = root / dataset_id
    manifest_path = dataset_root / str(spec["provider_manifest_filename"])
    manifest, failures = _load_provider_manifest(manifest_path)
    receipt: dict[str, Any] = {
        "dataset_id": dataset_id,
        "mode": "PROVIDER_MANIFEST_BOUND",
        "provider_manifest_path": str(manifest_path),
        "files": [],
        "failures": failures,
    }
    if manifest is None:
        receipt["state"] = "HELD_PROVIDER_MANIFEST"
        receipt["bytes_materialized"] = False
        return receipt

    expected_identity = str(spec["source_identity"])
    if str(manifest.get("source_identity")) != expected_identity:
        failures.append("provider manifest source_identity does not match frozen contract")
    if str(manifest.get("version")) != str(spec["version"]):
        failures.append("provider manifest version does not match frozen contract")

    declared_files = manifest.get("files")
    if not isinstance(declared_files, list) or not declared_files:
        failures.append("provider manifest must declare at least one file")
        declared_files = []

    seen: set[str] = set()
    all_present = bool(declared_files)
    for declared in declared_files:
        if not isinstance(declared, dict):
            failures.append("provider manifest contains a non-object file entry")
            all_present = False
            continue
        name = declared.get("relative_path") or declared.get("name")
        if not isinstance(name, str) or not _safe_relative_name(name):
            failures.append(f"unsafe or missing provider relative path: {name!r}")
            all_present = False
            continue
        if name in seen:
            failures.append(f"duplicate provider file declaration: {name}")
            all_present = False
            continue
        seen.add(name)
        source_url = declared.get("source_url")
        if source_url:
            parsed = urlparse(str(source_url))
            if parsed.scheme != "https" or not parsed.hostname:
                failures.append(f"provider source_url must be HTTPS: {name}")
        file_receipt = _audit_local_file(dataset_root / "files" / name, declared)
        file_receipt["relative_path"] = name
        file_receipt["source_url"] = source_url
        file_receipt["role"] = declared.get("role")
        receipt["files"].append(file_receipt)
        if not file_receipt["exists"] or file_receipt["failures"]:
            all_present = False

    files_dir = dataset_root / "files"
    if files_dir.is_dir():
        local_files = {
            p.relative_to(files_dir).as_posix()
            for p in files_dir.rglob("*")
            if p.is_file()
        }
        receipt["unregistered_local_files"] = sorted(local_files - seen)
    else:
        receipt["unregistered_local_files"] = []

    receipt["bytes_materialized"] = all_present and not failures
    receipt["state"] = (
        "LOCAL_PROVIDER_BYTES_HASHED"
        if receipt["bytes_materialized"]
        else "HELD_PROVIDER_MATERIALIZATION"
    )
    receipt["failures"] = failures
    return receipt


def _audit_fixed_objects(root: Path, dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    dataset_root = root / dataset_id / "files"
    failures: list[str] = []
    receipts: list[dict[str, Any]] = []
    expected_names: set[str] = set()

    objects = spec.get("provider_objects") or []
    for provider_object in objects:
        name = str(provider_object["filename"])
        expected_names.add(name)
        local = _audit_local_file(dataset_root / name)
        local.update(
            {
                "provider_object": provider_object["provider_object"],
                "filename": name,
                "source_url": provider_object["source_url"],
                "display_label": provider_object.get("display_label"),
                "publication_role": provider_object.get("publication_role"),
            }
        )
        receipts.append(local)
        if not local["exists"] or local["failures"]:
            failures.append(f"{provider_object['provider_object']} is missing or failed local audit")

    if dataset_root.is_dir():
        local_names = {p.name for p in dataset_root.iterdir() if p.is_file()}
        extras = sorted(local_names - expected_names)
    else:
        extras = []
    complete = len(receipts) == len(objects) and not failures
    return {
        "dataset_id": dataset_id,
        "mode": "FIXED_PROVIDER_OBJECTS",
        "state": "LOCAL_PROVIDER_BYTES_HASHED" if complete else "HELD_PROVIDER_MATERIALIZATION",
        "bytes_materialized": complete,
        "files": receipts,
        "unregistered_local_files": extras,
        "failures": failures,
    }


def audit_materialization(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    dataset_receipts: dict[str, Any] = {}
    failures: list[str] = []
    for dataset_id, spec in contract["datasets"].items():
        mode = spec.get("local_mode")
        if mode == "PROVIDER_MANIFEST_BOUND":
            receipt = _audit_manifest_bound(root, dataset_id, spec)
        elif mode == "FIXED_PROVIDER_OBJECTS":
            receipt = _audit_fixed_objects(root, dataset_id, spec)
        else:
            receipt = {
                "dataset_id": dataset_id,
                "state": "HELD_UNKNOWN_MATERIALIZATION_MODE",
                "bytes_materialized": False,
                "failures": [f"unsupported local_mode: {mode!r}"],
            }
        dataset_receipts[dataset_id] = receipt
        if not receipt["bytes_materialized"]:
            failures.append(f"{dataset_id} materialization incomplete")

    materialization_complete = not failures
    return {
        "contract_id": contract["contract_id"],
        "queue_id": contract["queue_id"],
        "phase": "PROVIDER_BYTE_MATERIALIZATION_ONLY",
        "state": "LOCAL_PROVIDER_BYTES_HASHED" if materialization_complete else "HELD_PROVIDER_MATERIALIZATION",
        "materialization_complete": materialization_complete,
        "admission_ready": False,
        "scientific_effect": "NONE",
        "replication_credit_change": "NONE",
        "source_rows_inspected": False,
        "archive_members_extracted": False,
        "datasets": dataset_receipts,
        "d0031_d0033_dependence_gate": contract["d0031_d0033_dependence_gate"],
        "pending_scientific_admission_requirements": contract["completion_gate"]["scientific_admission_still_requires"],
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit already-materialized Q0029 provider bytes offline")
    parser.add_argument("--root", required=True, help="Root containing D0031/, D0032/, D0033/ materialization folders")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--out", default="build/q0029_materialization_receipt.json")
    args = parser.parse_args()

    contract = json.loads(Path(args.contract).read_text())
    receipt = audit_materialization(Path(args.root), contract)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_private(out, receipt)
    print(json.dumps({
        "contract_id": receipt["contract_id"],
        "state": receipt["state"],
        "materialization_complete": receipt["materialization_complete"],
        "admission_ready": receipt["admission_ready"],
        "scientific_effect": receipt["scientific_effect"],
        "output": str(out),
    }))
    raise SystemExit(0 if receipt["materialization_complete"] else 2)


if __name__ == "__main__":
    main()
