"""D0019 Figshare v1 source provenance and header-only inspection; never fit models."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ITEM_ID = 9192509
DOI = "10.6084/m9.figshare.9192509"
MAX_FILE_BYTES = 2_000_000


def public_item() -> dict[str, Any]:
    req = Request(f"https://api.figshare.com/v2/articles/{ITEM_ID}",
                  headers={"Accept": "application/json", "User-Agent": "ARS-provenance-only/0.1"})
    with urlopen(req, timeout=15) as response:
        return json.loads(response.read(1_000_000))


def fetch_source(url: str, expected_size: int) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com":
        raise ValueError("Unexpected Figshare source host.")
    with urlopen(Request(url, headers={"User-Agent": "ARS-provenance-only/0.1"}), timeout=20) as response:
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) != expected_size:
        raise ValueError("Downloaded size differs from the source manifest.")
    return data


def probe(item: dict[str, Any],
          fetch: Callable[[str, int], bytes] = fetch_source,
          header_reader: Callable[[bytes], list[dict]] | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "dataset": "D0019", "protocol": "SOURCE_H0_H1_H2_HEADER_ONLY",
        "source_item_id": ITEM_ID, "source_version": 1,
        "source_material_persisted": False, "event_rows_inspected": False,
        "outcome_distribution_inspected": False,
        "pr0005_executed": False, "group1_holdout_opened": False,
        "rdc004_mapping_approved": False,
        "scientific_effect": "NONE", "crg_c_credit": "UNMET",
        "rights": "HELD_UNTIL_SOURCE_SPECIFIC_REVIEW",
        "files": [], "state": "HELD_SOURCE_IDENTITY",
    }
    raw_doi = str(item.get("doi") or "").lower().removeprefix("https://doi.org/").rstrip("/")
    if (item.get("id") != ITEM_ID or item.get("version") != 1
            or raw_doi not in {DOI, DOI + ".v1"}):
        return receipt
    license_data = item.get("license") or {}
    receipt["doi_as_reported"] = item.get("doi")
    receipt["license_as_reported"] = (
        {k: license_data.get(k) for k in ("name", "url") if license_data.get(k)}
        if isinstance(license_data, dict) else {}
    )
    receipt["authors_as_reported"] = [
        a.get("full_name") for a in item.get("authors", [])
        if isinstance(a, dict) and a.get("full_name")
    ]
    candidates = item.get("files")
    if not isinstance(candidates, list) or not candidates:
        receipt["state"] = "HELD_FILE_INVENTORY"
        return receipt
    if not (isinstance(license_data, dict) and license_data.get("name") == "CC BY 4.0"
            and str(license_data.get("url", "")).rstrip("/") == "https://creativecommons.org/licenses/by/4.0"):
        receipt["state"] = "HELD_ITEM_LICENSE_REVIEW"
        return receipt
    receipt["rights"] = "ITEM_CC_BY_4_OBSERVED_ADDITIONAL_SOURCE_REVIEW_PENDING"
    if header_reader is None:
        try:
            from scripts.inspect_d0025_headers import inspect_xlsx_headers
        except ModuleNotFoundError:
            from inspect_d0025_headers import inspect_xlsx_headers
        header_reader = inspect_xlsx_headers
    success = True
    inspected_excel = 0
    seen_ids: set[int] = set()
    for item_file in candidates:
        fid, name, declared_size, url = (
            item_file.get("id"), item_file.get("name"),
            item_file.get("size"), item_file.get("download_url")
        )
        summary = {"file_id": fid, "filename": name, "declared_size": declared_size}
        receipt["files"].append(summary)
        try:
            if not isinstance(fid, int) or fid in seen_ids:
                raise ValueError("Missing or duplicate Figshare file identifier.")
            seen_ids.add(fid)
            if not isinstance(declared_size, int) or not 0 < declared_size <= MAX_FILE_BYTES:
                raise ValueError("File outside the registered source-size bound.")
            parsed = urlparse(str(url))
            if (parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com"
                    or parsed.path != f"/files/{fid}"):
                raise ValueError("Unexpected source-file download URL.")
            expected_md5 = item_file.get("computed_md5") or item_file.get("supplied_md5")
            if not isinstance(expected_md5, str) or len(expected_md5) != 32:
                raise ValueError("No Figshare source MD5 to compare.")
            raw = fetch(url, declared_size)
            if len(raw) != declared_size or hashlib.md5(raw).hexdigest().lower() != expected_md5.lower():
                raise ValueError("File does not match source size/MD5.")
            summary["md5_verified"] = expected_md5
            summary["sha256"] = hashlib.sha256(raw).hexdigest()
            summary["state"] = "H1_FILE_INTEGRITY_VERIFIED"
            if isinstance(name, str) and name.lower().endswith(".xlsx"):
                summary["header_inventory"] = header_reader(raw)
                summary["header_candidates_authoritative"] = False
                inspected_excel += 1
        except (OSError, ValueError, TypeError, KeyError, IndexError, BadZipFile) as exc:
            success = False
            summary["state"] = "HELD_FILE_INTEGRITY_OR_SCHEMA"
            summary["error_type"] = type(exc).__name__
            summary["error_summary"] = str(exc)[:160]
    if not success:
        receipt["state"] = "HELD_PARTIAL_SOURCE_INTEGRITY_OR_SCHEMA"
    elif inspected_excel:
        receipt["state"] = "H1_FILES_VERIFIED_H2_HEADER_CANDIDATES_CODEBOOK_HELD"
    else:
        receipt["state"] = "H1_FILES_VERIFIED_H2_NO_XLSX_HEADER_INVENTORY"
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser(description="Discover only D0019 Figshare source identities and header candidates")
    ap.add_argument("--out", default="build/d0019_figshare_source_probe.json")
    args = ap.parse_args()
    try:
        receipt = probe(public_item())
    except (OSError, ValueError, TypeError) as exc:
        receipt = {
            "dataset": "D0019", "protocol": "SOURCE_H0_H1_H2_HEADER_ONLY",
            "state": "HELD_PUBLIC_SOURCE_UNAVAILABLE", "error_type": type(exc).__name__,
            "error_summary": str(exc)[:160], "source_material_persisted": False,
            "event_rows_inspected": False, "outcome_distribution_inspected": False,
            "pr0005_executed": False, "group1_holdout_opened": False
        }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "state": receipt["state"], "file_count": len(receipt.get("files", [])),
        "event_rows_inspected": False, "pr0005_executed": False
    }))


if __name__ == "__main__":
    main()
