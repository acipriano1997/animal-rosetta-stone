"""Read-only public metadata probe for D0025. Never download data or assign rights."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

BASE = "https://api.figshare.com/v2"
ARTICLE_ID = 19683768
COLLECTION_ID = 6060702
EXPECTED_DOI = "10.6084/m9.figshare.19683768"


def public_json(endpoint: str) -> dict[str, Any]:
    request = Request(BASE + endpoint, headers={
        "Accept": "application/json",
        "User-Agent": "AnimalRosettaStone-metadata-only-research/0.1",
    })
    with urlopen(request, timeout=12) as response:
        data = response.read(2_000_000)
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("Figshare public API returned a non-object record")
    return payload


def _license_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("value", "name", "url") if value.get(key) is not None}


def _article_summary(record: dict[str, Any]) -> dict[str, Any]:
    identifier = record.get("id")
    doi = str(record.get("doi") or "")
    canonical = doi.lower().rstrip("/").removeprefix("https://doi.org/")
    version = record.get("version")
    allowed = {EXPECTED_DOI}
    if isinstance(version, int) and version >= 1:
        allowed.add(f"{EXPECTED_DOI}.v{version}")
    match = identifier == ARTICLE_ID and canonical in allowed
    raw_files = record.get("files")
    files = []
    if isinstance(raw_files, list):
        for file in raw_files:
            if isinstance(file, dict):
                files.append({
                    "id": file.get("id"), "name": file.get("name"),
                    "size": file.get("size"), "is_link_only": file.get("is_link_only"),
                    "supplied_md5": file.get("supplied_md5"),
                    "computed_md5": file.get("computed_md5"),
                    "download_url": file.get("download_url"),
                })
    return {
        "state": "IDENTITY_MATCH_METADATA_ONLY" if match else "IDENTITY_MISMATCH_HELD",
        "id": identifier, "title": record.get("title"), "doi": doi,
        "version": record.get("version"),
        "published_date": record.get("published_date"),
        "modified_date": record.get("modified_date"),
        "license_as_reported": _license_summary(record.get("license")),
        "files_as_reported": files,
        "file_count": len(files),
    }


def _collection_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": "IDENTITY_MATCH_METADATA_ONLY" if record.get("id") == COLLECTION_ID else "IDENTITY_MISMATCH_HELD",
        "id": record.get("id"),
        "title": record.get("title"),
        "doi": record.get("doi"),
        "published_date": record.get("published_date"),
    }


def probe(fetcher: Callable[[str], dict[str, Any]] = public_json) -> dict[str, Any]:
    """Keep the main dataset and paper's supplement collection separate."""
    receipt: dict[str, Any] = {
        "dataset_id": "D0025",
        "probe_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "METADATA_DISCOVERY_ONLY",
        "figshare_dataset_article_id": ARTICLE_ID,
        "figshare_paper_supplement_collection_id": COLLECTION_ID,
        "source_materialized": False,
        "source_bytes_sha256_verified": False,
        "row_level_data_inspected": False,
        "research_rights_state": "HELD_RIGHTS_PENDING_HUMAN_REVIEW",
        "rdc005_admission": "NOT_ATTEMPTED",
        "pr0006_execution": "NOT_ATTEMPTED",
        "crg_c_credit": "UNMET",
    }
    for label, endpoint, transform in (
        ("article", f"/articles/{ARTICLE_ID}", _article_summary),
        ("supplement_collection", f"/collections/{COLLECTION_ID}", _collection_summary),
    ):
        try:
            data = fetcher(endpoint)
            receipt[label] = transform(data)
        except (OSError, ValueError, TypeError, KeyError) as error:
            receipt[label] = {
                "state": "METADATA_UNAVAILABLE_HELD",
                "error_type": type(error).__name__,
                "error_summary": str(error)[:240],
            }
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe only public Figshare metadata for D0025")
    parser.add_argument("--out", default="build/d0025_metadata_probe.json")
    args = parser.parse_args()
    receipt = probe()
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "article": receipt["article"]["state"],
        "supplement_collection": receipt["supplement_collection"]["state"],
        "rights": receipt["research_rights_state"],
        "source_materialized": receipt["source_materialized"],
        "output": str(dest),
    }))


if __name__ == "__main__":
    main()
