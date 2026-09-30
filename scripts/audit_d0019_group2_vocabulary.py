"""RDC-004 H3: inventory only candidate Group-2 raw labels, never Group-1 outcomes."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
VOCAB_COLUMNS = {
    "sex_init": "G", "sex_rec": "J", "rel_dom": "L",
    "face": "M", "context_dyad": "N", "GEST": "O", "REACT": "P",
}
MAX_CATEGORY_LEVELS = 32


def group2_vocabulary(raw: bytes, expected_headers: list[str]) -> dict:
    """Decode only source-group labels and Group-2 selected categorical cells.

    Group 1 is never used for field-value inspection, model fitting,
    eligibility selection or source-label interpretation.
    """
    with ZipFile(BytesIO(raw)) as book:
        if sum(z.file_size for z in book.infolist()) > 8_000_000:
            raise ValueError("Source XLSX exceeds its decompression bound")
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            shared = ET.fromstring(book.read("xl/sharedStrings.xml"))
            strings = [
                "".join(t.text or "" for t in si.iter(S + "t"))
                for si in shared.findall(S + "si")
            ]
        tree = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        dimension = tree.find(S + "dimension")
        if dimension is None or dimension.get("ref") != "A1:P253":
            raise ValueError("Rawdata source dimension drift")
        data = tree.find(S + "sheetData")
        if data is None:
            raise ValueError("Source has no sheet data")
        rows = data.findall(S + "row")

        def decode(cell):
            if cell.find(S + "f") is not None:
                raise ValueError("Formula in pinned categorical source field")
            value = cell.find(S + "v")
            kind = cell.get("t")
            if kind == "s":
                if value is None or value.text is None:
                    return ""
                idx = int(value.text)
                if idx < 0 or idx >= len(strings):
                    raise ValueError("Missing source shared-string index")
                return strings[idx]
            if kind == "inlineStr":
                inline = cell.find(S + "is")
                return "".join(t.text or "" for t in inline.iter(S + "t")) if inline is not None else ""
            return value.text if value is not None and value.text is not None else ""

        header = next((row for row in rows if row.get("r") == "1"), None)
        if header is None:
            raise ValueError("Source header absent")
        observed_headers = [decode(cell) for cell in header.findall(S + "c")]
        if observed_headers != expected_headers:
            raise ValueError("Source column order differs from frozen H1 pins")

        sets = {field: set() for field in VOCAB_COLUMNS}
        empty = {field: 0 for field in VOCAB_COLUMNS}
        group_counts = {"1": 0, "2": 0}
        row_numbers = []
        for row in rows:
            number = int(row.get("r", "0"))
            if number == 1:
                continue
            row_numbers.append(number)
            group_cell = next(
                (c for c in row.findall(S + "c") if c.get("r") == f"F{number}"),
                None,
            )
            group = decode(group_cell).strip() if group_cell is not None else ""
            if group not in group_counts:
                raise ValueError("Unknown/missing source-group code")
            group_counts[group] += 1
            if group != "2":
                continue
            # For Group 2 only: decode named categorical variables and retain
            # native labels without reinterpreting either endpoint or predictors.
            selected = {
                c.get("r"): c for c in row.findall(S + "c")
                if c.get("r") in {f"{col}{number}" for col in VOCAB_COLUMNS.values()}
            }
            for name, col in VOCAB_COLUMNS.items():
                cell = selected.get(f"{col}{number}")
                raw_value = decode(cell).strip() if cell is not None else ""
                if not raw_value:
                    empty[name] += 1
                    continue
                sets[name].add(raw_value)
                if len(sets[name]) > MAX_CATEGORY_LEVELS:
                    raise ValueError(f"{name} exceeds prespecified category cap")

        if row_numbers != list(range(2, 254)) or group_counts != {"1": 103, "2": 149}:
            raise ValueError("Row locators or registered group partition changed")
        return {
            "groups_structural_counts_only": group_counts,
            "group2_category_vocabulary": {
                name: {
                    "source_tokens_no_frequencies": sorted(sets[name]),
                    "missing_blank_group2": empty[name],
                    "source_code_mapping_approved": False,
                }
                for name in VOCAB_COLUMNS
            },
            "group1_categorical_and_outcome_cells_decoded": False,
            "group2_outcome_frequency_computed": False,
            "row_level_records_exported": False,
        }


def audit(item: dict, pins: dict, crosswalk: dict, fetch) -> dict:
    receipt = {
        "dataset_id": "D0019", "phase": "H3_GROUP2_RAW_VOCABULARY_ONLY",
        "state": "HELD_SOURCE_OR_CROSSWALK", "source_bytes_stored": False,
        "group1_holdout_opened": False, "group1_outcomes_accessed": False,
        "rdc004_mapping_approved": False, "pr0005_executed": False,
        "scientific_effect": "NONE", "crg_c_credit": "UNMET",
    }
    if (
        crosswalk.get("contract_id") != "RDC-004"
        or crosswalk.get("source_sha256") != pins["file"]["sha256"]
        or crosswalk.get("empirical_admission") is not False
        or crosswalk.get("group1_outcomes_accessed") is not False
        or crosswalk.get("mapping_state") != "SOURCE_BACKED_CANDIDATES_NOT_APPROVED"
    ):
        return receipt
    if any(field.get("status") == "APPROVED" for field in crosswalk.get("fields", [])):
        return receipt
    if item.get("id") != pins.get("source_item_id") or item.get("version") != 1 or item.get("doi") != pins.get("doi"):
        receipt["state"] = "HELD_SOURCE_IDENTITY"
        return receipt
    lic = item.get("license") or {}
    if not isinstance(lic, dict) or {key: lic.get(key) for key in ("name", "url")} != pins.get("license_as_reported"):
        receipt["state"] = "HELD_LICENSE"
        return receipt
    files = item.get("files")
    if not isinstance(files, list) or len(files) != 1:
        receipt["state"] = "HELD_FILE_INVENTORY"
        return receipt
    f = files[0]
    expected = pins["file"]
    if (f.get("id") != expected["id"] or f.get("name") != expected["name"]
            or f.get("size") != expected["bytes"]
            or (f.get("computed_md5") or f.get("supplied_md5")) != expected["md5"]):
        receipt["state"] = "QUARANTINED_SOURCE_DRIFT"
        return receipt
    url = f.get("download_url")
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com" or parsed.path != f"/files/{expected['id']}":
        receipt["state"] = "QUARANTINED_SOURCE_LOCATION"
        return receipt
    try:
        raw = fetch(url, expected["bytes"])
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError("Original source bytes differ from H1 SHA-256")
        receipt["vocabulary"] = group2_vocabulary(raw, pins["sheets"][0]["source_header_candidates"])
        receipt["state"] = "H3_GROUP2_VOCABULARY_RECORDED_MAPPING_UNAPPROVED"
    except (OSError, ValueError, TypeError, IndexError, KeyError, BadZipFile, ET.ParseError) as exc:
        receipt["state"] = "HELD_GROUP2_VOCABULARY_OR_SOURCE"
        receipt["error_type"] = type(exc).__name__
        receipt["error_summary"] = str(exc)[:180]
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser(description="Group-2-only source-label vocabulary, no model or holdout outcomes")
    ap.add_argument("--pins", default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk", default="contracts/d0019_rdc004_source_crosswalk_v0_1.json")
    ap.add_argument("--out", default="build/d0019_group2_label_vocabulary.json")
    args = ap.parse_args()
    try:
        from scripts.probe_d0019_source import public_item, fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item, fetch_source
    pins = json.loads(Path(args.pins).read_text())
    crosswalk = json.loads(Path(args.crosswalk).read_text())
    try:
        receipt = audit(public_item(), pins, crosswalk, fetch_source)
    except (OSError, ValueError, TypeError) as exc:
        receipt = {
            "dataset_id": "D0019", "phase": "H3_GROUP2_RAW_VOCABULARY_ONLY",
            "state": "HELD_SOURCE_METADATA", "error_type": type(exc).__name__,
            "error_summary": str(exc)[:180], "source_bytes_stored": False,
            "group1_holdout_opened": False, "group1_outcomes_accessed": False,
            "rdc004_mapping_approved": False, "pr0005_executed": False,
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "state": receipt["state"], "group1_outcomes_accessed": False,
        "rdc004_mapping_approved": False, "pr0005_executed": False, "output": str(out)
    }))


if __name__ == "__main__":
    main()
