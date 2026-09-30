"""D0025 v1 byte-integrity check. Preserve hashes only; no rows or source files exported."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ITEM_ID = 19683768
EXPECTED_DOI = "10.6084/m9.figshare.19683768.v1"
EXPECTED_FILE_IDS = {35234047, 35234059, 35888735, 35888738}
MAX_SIZE = 1_000_000


def download_bounded(url: str, declared_size: int) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com":
        raise ValueError("Unexpected download host")
    request = Request(url, headers={"User-Agent": "AnimalRosettaStone-integrity-only/0.1"})
    with urlopen(request, timeout=18) as response:
        content = response.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE or len(content) != declared_size:
        raise ValueError("Downloaded byte count differs from the source manifest")
    return content


def freeze_manifest(
    item: dict[str, Any],
    fetch_bytes: Callable[[str, int], bytes] = download_bounded,
) -> dict[str, Any]:
    """Verify byte hashes in memory; do not preserve or inspect underlying research records."""
    receipt: dict[str, Any] = {
        "source": "D0025",
        "source_identity": EXPECTED_DOI,
        "protocol": "H1_BYTE_INTEGRITY_ONLY",
        "source_bytes_sha256_verified": False,
        "raw_files_persisted": False,
        "source_rows_inspected": False,
        "rdc005_mapping": "NOT_ATTEMPTED",
        "pr0006_execution": "NOT_ATTEMPTED",
        "scientific_effect": "NONE",
        "crg_c_credit": "UNMET",
        "research_rights_state": "HELD_PENDING_SOURCE_SPECIFIC_REVIEW",
        "files": [],
    }
    doi = str(item.get("doi", "")).removeprefix("https://doi.org/")
    if item.get("id") != ITEM_ID or item.get("version") != 1 or doi != EXPECTED_DOI:
        receipt["state"] = "HELD_SOURCE_IDENTITY"
        return receipt
    license_record = item.get("license") or {}
    if not isinstance(license_record, dict) or license_record.get("name") != "CC BY 4.0" or license_record.get("url") != "https://creativecommons.org/licenses/by/4.0/":
        receipt["state"] = "HELD_RIGHTS"
        return receipt
    receipt["item_license_as_reported"] = {
        "name": license_record["name"], "url": license_record["url"]
    }
    receipt["authors_as_reported"] = [
        a.get("full_name") for a in item.get("authors", []) if isinstance(a, dict) and a.get("full_name")
    ]
    candidates = item.get("files", [])
    if not isinstance(candidates, list) or {x.get("id") for x in candidates if isinstance(x, dict)} != EXPECTED_FILE_IDS:
        receipt["state"] = "HELD_FILE_INVENTORY"
        return receipt
    valid = True
    for file in candidates:
        fid, name, size, url = (file.get(k) for k in ("id", "name", "size", "download_url"))
        record = {"id": fid, "name": name, "source_url": url, "declared_size": size}
        receipt["files"].append(record)
        try:
            if not isinstance(size, int) or not (0 < size <= MAX_SIZE):
                raise ValueError("File size outside pinned bounded range")
            parsed = urlparse(str(url))
            if parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com" or parsed.path != f"/files/{fid}":
                raise ValueError("Unexpected source download location")
            expected_md5 = file.get("computed_md5")
            if not isinstance(expected_md5, str) or len(expected_md5) != 32 or expected_md5 != file.get("supplied_md5"):
                raise ValueError("Figshare MD5 fields absent/inconsistent")
            raw = fetch_bytes(url, size)
            if len(raw) != size:
                raise ValueError("Byte count does not match the published file size")
            actual_md5 = hashlib.md5(raw).hexdigest()
            if actual_md5 != expected_md5:
                raise ValueError("Downloaded MD5 differs from Figshare metadata")
            record["md5_verified"] = actual_md5
            record["sha256"] = hashlib.sha256(raw).hexdigest()
            record["state"] = "BYTE_INTEGRITY_VERIFIED"
        except (OSError, ValueError, TypeError) as error:
            valid = False
            record["state"] = "HELD_SOURCE_DOWNLOAD_OR_CHECKSUM"
            record["error_type"] = type(error).__name__
            record["error_summary"] = str(error)[:180]
    receipt["source_bytes_sha256_verified"] = valid
    receipt["state"] = "H1_TRANSIENT_BYTES_VERIFIED" if valid else "HELD_PARTIAL_SOURCE_INTEGRITY"
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Check public D0025 file hashes; do not store source bytes")
    parser.add_argument("--out", default="build/d0025_source_integrity.json")
    args = parser.parse_args()
    from probe_d0025_metadata import public_json
    try:
        item = public_json(f"/articles/{ITEM_ID}")
        receipt = freeze_manifest(item)
    except (OSError, ValueError, TypeError) as error:
        receipt = {
            "source": "D0025", "protocol": "H1_BYTE_INTEGRITY_ONLY",
            "state": "HELD_SOURCE_METADATA",
            "error_type": type(error).__name__, "error_summary": str(error)[:180],
            "source_bytes_sha256_verified": False, "raw_files_persisted": False,
            "source_rows_inspected": False, "pr0006_execution": "NOT_ATTEMPTED",
            "crg_c_credit": "UNMET",
        }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "source": receipt["source"], "state": receipt["state"],
        "byte_integrity_verified": receipt["source_bytes_sha256_verified"],
        "file_count": len(receipt.get("files", [])),
        "source_rows_inspected": receipt["source_rows_inspected"],
        "output": str(path),
    }))


if __name__ == "__main__":
    main()
