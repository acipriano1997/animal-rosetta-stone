"""Outcome-blind D0019 split-key audit; never read REACT or model on Group 1."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TARGETS = ("Dataset", "group")
PUBLISHED_SIZES = (103, 149)


def partition_counts_only(raw: bytes, expected_headers: list[str]) -> dict:
    """Access only A/F partition cells after checking the exact workbook header."""
    with ZipFile(BytesIO(raw)) as workbook:
        if sum(z.file_size for z in workbook.infolist()) > 8_000_000:
            raise ValueError("Source workbook exceeds declared decompression bound")
        strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for entry in root.findall(S + "si"):
                strings.append("".join(t.text or "" for t in entry.iter(S + "t")))
        worksheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        dim = worksheet.find(S + "dimension")
        if dim is None or dim.get("ref") != "A1:P253":
            raise ValueError("Rawdata sheet dimension differs from H1 pins")
        data = worksheet.find(S + "sheetData")
        if data is None:
            raise ValueError("No Rawdata sheetData in pinned workbook")

        def decode(cell):
            if cell.find(S + "f") is not None:
                raise ValueError("Partition field contains a formula")
            v = cell.find(S + "v")
            kind = cell.get("t")
            if kind == "s":
                if v is None or v.text is None:
                    return None
                return strings[int(v.text)]
            if kind == "inlineStr":
                elem = cell.find(S + "is")
                return "".join(x.text or "" for x in elem.iter(S + "t")) if elem is not None else None
            return v.text if v is not None else None

        rows = data.findall(S + "row")
        header = next((r for r in rows if r.get("r") == "1"), None)
        if header is None:
            raise ValueError("Source header missing")
        observed = [decode(c) for c in header.findall(S + "c")]
        if observed != expected_headers:
            raise ValueError("Source headers differ from H1 pinned order")

        # Source-header order is pinned; no other data cells are accessed.
        target_ref = {"Dataset": "A", "group": "F"}
        values = {col: [] for col in TARGETS}
        for row in rows:
            number = int(row.get("r", "0"))
            if number <= 1:
                continue
            lookup = {}
            for cell in row.findall(S + "c"):
                ref = cell.get("r", "")
                col = re.match(r"^[A-Z]+", ref)
                if col and col.group(0) in {"A", "F"}:
                    lookup[col.group(0)] = decode(cell)
            for col in TARGETS:
                value = lookup.get(target_ref[col])
                values[col].append(
                    value.strip() if isinstance(value, str) else
                    str(value) if value is not None else ""
                )

        if len(values["Dataset"]) != 252:
            raise ValueError("Partition row count differs from published source size")
        summaries = {}
        compatible = []
        for key in TARGETS:
            counts = Counter(v for v in values[key] if v)
            missing = sum(1 for v in values[key] if not v)
            match = missing == 0 and len(counts) == 2 and sorted(counts.values()) == list(PUBLISHED_SIZES)
            summaries[key] = {
                "observed_levels": len(counts),
                "missing_partition_labels": missing,
                "aggregate_counts": dict(sorted(counts.items())),
                "matches_published_103_149_partition_sizes": match,
                "partition_interpretation_approved": False,
            }
            if match:
                compatible.append(key)
        return {
            "source_data_rows_checked_for_partition_columns_only": 252,
            "partition_candidates_by_published_sizes": compatible,
            "source_partition_columns": summaries,
            "outcome_or_signal_values_decoded": False,
            "group1_outcomes_exposed": False,
        }


def audit(item: dict, pins: dict, fetch) -> dict:
    result = {
        "dataset": "D0019", "protocol": "H3_OUTCOME_BLIND_PARTITION_KEY_CHECK",
        "state": "HELD_SOURCE_IDENTITY", "source_bytes_persisted": False,
        "source_event_or_recipient_outcomes_inspected": False,
        "group1_outcomes_exposed": False, "group1_holdout_opened": False,
        "source_mapping_approved": False, "pr0005_executed": False,
        "crg_c_credit": "UNMET",
    }
    if item.get("id") != pins.get("source_item_id") or item.get("version") != pins.get("version") or item.get("doi") != pins.get("doi"):
        return result
    license_info = item.get("license") or {}
    if not isinstance(license_info, dict) or {
        k: license_info.get(k) for k in ("name", "url")
    } != pins.get("license_as_reported"):
        result["state"] = "HELD_ITEM_LICENSE_DRIFT"
        return result
    source_files = item.get("files")
    reference = pins["file"]
    if not isinstance(source_files, list) or len(source_files) != 1:
        result["state"] = "HELD_FILE_INVENTORY"
        return result
    file = source_files[0]
    if (file.get("id") != reference["id"] or file.get("name") != reference["name"]
            or file.get("size") != reference["bytes"]
            or (file.get("computed_md5") or file.get("supplied_md5")) != reference["md5"]):
        result["state"] = "QUARANTINED_SOURCE_DRIFT"
        return result
    url = file.get("download_url")
    parsed = urlparse(str(url))
    if (parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com"
            or parsed.path != f"/files/{reference['id']}"):
        result["state"] = "QUARANTINED_SOURCE_LOCATION"
        return result
    try:
        raw = fetch(url, reference["bytes"])
        if len(raw) != reference["bytes"] or hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            raise ValueError("Raw workbook fails exact H1 SHA-256 pin")
        summary = partition_counts_only(raw, pins["sheets"][0]["source_header_candidates"])
        result["partition_audit"] = summary
        candidates = summary["partition_candidates_by_published_sizes"]
        if len(candidates) == 1:
            result["state"] = "H3_ONE_PARTITION_CANDIDATE_UNAPPROVED"
        elif len(candidates) > 1:
            result["state"] = "HELD_AMBIGUOUS_PARTITION_KEYS"
        else:
            result["state"] = "HELD_PARTITION_KEY_NO_PUBLISHED_COUNT_MATCH"
    except (OSError, ValueError, TypeError, IndexError, KeyError, BadZipFile, ET.ParseError) as error:
        result["state"] = "HELD_PARTITION_SOURCE_OR_STRUCTURE"
        result["error_type"] = type(error).__name__
        result["error_summary"] = str(error)[:150]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit only D0019 split-column counts; no outcomes")
    parser.add_argument("--pins", default="contracts/d0019_v1_verified_source_snapshot.json")
    parser.add_argument("--out", default="build/d0019_partition_key_audit.json")
    args = parser.parse_args()
    try:
        from scripts.probe_d0019_source import public_item, fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item, fetch_source
    pins = json.loads(Path(args.pins).read_text())
    try:
        receipt = audit(public_item(), pins, fetch_source)
    except (OSError, ValueError, TypeError) as error:
        receipt = {
            "dataset": "D0019", "protocol": "H3_OUTCOME_BLIND_PARTITION_KEY_CHECK",
            "state": "HELD_SOURCE_METADATA", "error_type": type(error).__name__,
            "error_summary": str(error)[:150], "source_bytes_persisted": False,
            "source_event_or_recipient_outcomes_inspected": False,
            "group1_outcomes_exposed": False, "group1_holdout_opened": False,
            "source_mapping_approved": False, "pr0005_executed": False
        }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "state": receipt["state"],
        "candidates": receipt.get("partition_audit", {}).get("partition_candidates_by_published_sizes", []),
        "group1_outcomes_exposed": False, "pr0005_executed": False,
        "output": str(output)
    }))


if __name__ == "__main__":
    main()
