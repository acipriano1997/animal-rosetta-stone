"""D0025 H2 candidate: inspect Excel sheet names/dimensions/row-1 headers only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import posixpath
from typing import Any, Callable
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import ZipFile

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
P = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def inspect_xlsx_headers(raw: bytes) -> list[dict[str, Any]]:
    """Decode only sheet-level structure and first-row candidates, never analyze outcome rows."""
    with ZipFile(io.BytesIO(raw)) as xlsx:
        if sum(info.file_size for info in xlsx.infolist()) > 25_000_000:
            raise ValueError("Uncompressed XML exceeds the header-inspection limit")
        wb = ET.fromstring(xlsx.read("xl/workbook.xml"))
        rels = ET.fromstring(xlsx.read("xl/_rels/workbook.xml.rels"))
        targets = {x.get("Id"): x.get("Target") for x in rels.findall(P + "Relationship")}
        shared = []
        if "xl/sharedStrings.xml" in xlsx.namelist():
            strings = ET.fromstring(xlsx.read("xl/sharedStrings.xml"))
            for si in strings.findall(S + "si"):
                shared.append("".join(t.text or "" for t in si.iter(S + "t")))
        result = []
        for sheet in wb.findall("./" + S + "sheets/" + S + "sheet"):
            rel_id = sheet.get(R + "id")
            target = targets.get(rel_id)
            if not target:
                raise ValueError("Missing worksheet relationship")
            if target.startswith("/"):
                member = target.lstrip("/")
            else:
                member = posixpath.normpath(posixpath.join("xl", target))
            if not member.startswith("xl/worksheets/"):
                raise ValueError("Unrecognized worksheet relationship path")
            root = ET.fromstring(xlsx.read(member))
            dim = root.find(S + "dimension")
            data = root.find(S + "sheetData")
            header_row = None
            if data is not None:
                for row in data.findall(S + "row"):
                    if row.get("r") == "1":
                        header_row = row
                        break
            headers = []
            if header_row is not None:
                for cell in header_row.findall(S + "c"):
                    kind = cell.get("t")
                    v = cell.find(S + "v")
                    if kind == "s" and v is not None:
                        index = int(v.text)
                        if index < 0 or index >= len(shared):
                            raise ValueError("Header references a missing shared string")
                        value = shared[index]
                    elif kind == "inlineStr":
                        instr = cell.find(S + "is")
                        value = "".join(t.text or "" for t in instr.iter(S + "t")) if instr is not None else ""
                    else:
                        value = v.text if v is not None else None
                    headers.append({"cell_ref": cell.get("r"), "header_candidate": value})
            result.append({
                "sheet_name": sheet.get("name"),
                "dimension_as_declared": dim.get("ref") if dim is not None else None,
                "header_candidate_row": 1,
                "header_candidate_cells": headers,
            })
        if not result:
            raise ValueError("No worksheets listed in XLSX")
        return result


def inspect_item_headers(
    item: dict[str, Any], pins: dict[str, Any],
    fetch_bytes: Callable[[str, int], bytes],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset_id": "D0025",
        "phase": "H2_PRE_OUTCOME_HEADER_INVENTORY_ONLY",
        "state": "HELD_SCHEMA_SOURCE",
        "source_files_stored": False,
        "data_rows_or_outcome_distributions_examined": False,
        "codebook_documents_reviewed": False,
        "timing_mapping_adjudicated": False,
        "pr0006_executed": False,
        "crg_c_credit": "UNMET",
        "workbooks": [],
    }
    if item.get("id") != pins.get("item_id") or item.get("version") != pins.get("version") or item.get("doi") != pins.get("doi"):
        return result
    if item.get("license", {}).get("name") != pins.get("license_as_reported", {}).get("name"):
        return result
    source = {f.get("id"): f for f in item.get("files", []) if isinstance(f, dict)}
    success = True
    for pinned in pins.get("files", []):
        if not pinned["name"].lower().endswith(".xlsx"):
            continue
        fid = pinned["id"]
        f = source.get(fid, {})
        info = {"file_id": fid, "filename": pinned["name"], "pinned_sha256": pinned["sha256"]}
        result["workbooks"].append(info)
        try:
            if f.get("name") != pinned["name"] or f.get("size") != pinned["size"] or f.get("computed_md5") != pinned["md5"]:
                raise ValueError("Source metadata changed from H1 pins")
            url = f.get("download_url")
            parsed = urlparse(str(url))
            if parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com" or parsed.path != f"/files/{fid}":
                raise ValueError("Unexpected source URL")
            raw = fetch_bytes(url, pinned["size"])
            if len(raw) != pinned["size"] or hashlib.sha256(raw).hexdigest() != pinned["sha256"]:
                raise ValueError("Workbook differs from H1-verified bytes")
            info["sheets"] = inspect_xlsx_headers(raw)
            info["state"] = "ROW1_HEADER_CANDIDATES_RECORDED"
        except (OSError, ValueError, TypeError, KeyError) as exc:
            success = False
            info["state"] = "HELD_SCHEMA_SOURCE"
            info["error_type"] = type(exc).__name__
            info["error_summary"] = str(exc)[:180]
    result["state"] = "H2_PARTIAL_HEADERS_ONLY_CODEBOOK_HELD" if success and len(result["workbooks"]) == 2 else "HELD_SCHEMA_SOURCE"
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Record only D0025 v1 XLSX header candidates")
    ap.add_argument("--pins", default="contracts/d0025_v1_verified_source_snapshot.json")
    ap.add_argument("--out", default="build/d0025_header_inventory.json")
    args = ap.parse_args()
    from probe_d0025_metadata import public_json
    from freeze_d0025_source_integrity import download_bounded
    pins = json.loads(Path(args.pins).read_text())
    try:
        result = inspect_item_headers(public_json("/articles/19683768"), pins, download_bounded)
    except (OSError, ValueError, TypeError) as exc:
        result = {"dataset_id": "D0025", "phase": "H2_PRE_OUTCOME_HEADER_INVENTORY_ONLY",
                  "state": "HELD_SCHEMA_SOURCE", "error_type": type(exc).__name__,
                  "error_summary": str(exc)[:180], "source_files_stored": False,
                  "data_rows_or_outcome_distributions_examined": False,
                  "pr0006_executed": False, "crg_c_credit": "UNMET"}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"state": result["state"], "workbooks": len(result.get("workbooks", [])),
                      "source_rows_examined": False, "output": str(out)}))


if __name__ == "__main__":
    main()
