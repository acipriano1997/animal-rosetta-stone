"""Bounded D0029 provenance inspection. Never execute deposited code or models.

Default: replay the ignored local API/byte cache. --refresh explicitly retrieves
public metadata and small non-media files. Output contains schemas/hashes only;
production research bytes stay in the ignored cache and must not be uploaded.
"""
from __future__ import annotations

try:
    from scripts.research_integrity import write_private
except ModuleNotFoundError:
    from research_integrity import write_private

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

try:
    from scripts.inspect_d0025_headers import inspect_xlsx_headers, S, R, P
except ModuleNotFoundError:
    from inspect_d0025_headers import inspect_xlsx_headers, S, R, P

BASE = "https://api.figshare.com/v2"
ITEM = 16910173
MEDIA = {".wav", ".mp4", ".mov", ".mp3", ".avi"}
MAX_BYTES = 3_000_000
MAX_UNPACKED = 25_000_000
MISSING = {"", "NA", "N/A", "NaN"}
HELD = "HELD_RDC006_SCHEMA_TIMING_DEPENDENCE_REVIEW"


def digests(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "md5": hashlib.md5(raw).hexdigest()}


def verify_bytes(file, raw):
    parsed = urlparse(str(file.get("download_url")))
    if (parsed.scheme != "https" or parsed.hostname != "ndownloader.figshare.com"
            or parsed.path != f"/files/{file['id']}" or parsed.query or parsed.fragment
            or file.get("is_link_only") is not False):
        raise ValueError("Unexpected file route or link-only source")
    if not isinstance(file.get("size"), int) or not 0 < file["size"] <= MAX_BYTES:
        raise ValueError("Non-media file exceeds acquisition bound")
    if len(raw) != file["size"]:
        raise ValueError("Byte size differs from manifest")
    hashes = digests(raw)
    computed = file.get("computed_md5")
    if not isinstance(computed, str) or not re.fullmatch(r"[0-9a-f]{32}", computed):
        raise ValueError("Authoritative computed MD5 unavailable")
    if hashes["md5"] != computed:
        raise ValueError("Local MD5 differs from authoritative computed MD5")
    if file.get("supplied_md5") and hashes["md5"] != file["supplied_md5"]:
        raise ValueError("Local MD5 differs from authoritative supplied MD5")
    return hashes


def validate_history(api):
    history = api["version_history"]["record"]
    if not isinstance(history, list) or not history:
        raise ValueError("Authoritative version listing missing")
    versions = sorted(x["version"] for x in history)
    if versions != list(range(1, max(versions) + 1)):
        raise ValueError("Version listing is duplicated or has gaps")
    for x in history:
        if x["url"] != f"{BASE}/articles/{ITEM}/versions/{x['version']}":
            raise ValueError("Unexpected version route")
    envelopes = sorted(api["versions"], key=lambda x: x["record"]["version"])
    if [x["record"]["version"] for x in envelopes] != versions:
        raise ValueError(f"Version retrieval incomplete: listed={versions}, retrieved="
                         f"{[x['record']['version'] for x in envelopes]}")
    for env in envelopes:
        d = env["record"]
        if (d["id"] != ITEM or d["doi"] != f"10.6084/m9.figshare.{ITEM}.v{d['version']}"
                or env["endpoint"] != f"{BASE}/articles/{ITEM}/versions/{d['version']}"):
            raise ValueError(f"Version identity mismatch at {env['endpoint']}")
        files = d.get("files")
        if not isinstance(files, list) or len({f["id"] for f in files}) != len(files):
            raise ValueError("File manifest missing or duplicate IDs")
        for f in files:
            if not all(k in f for k in ("id", "name", "size", "supplied_md5", "computed_md5", "download_url")):
                raise ValueError("Required manifest field unavailable")
    return envelopes


def manifest_diff(before, after):
    """Use IDs for continuity; same-name replacement is a distinct file, not identity."""
    old = {f["id"]: f for f in before}
    new = {f["id"]: f for f in after}
    removed = sorted(old.keys() - new.keys())
    added = sorted(new.keys() - old.keys())
    changes = []
    for fid in sorted(old.keys() & new.keys()):
        fields = {k: {"before": old[fid].get(k), "after": new[fid].get(k)}
                  for k in ("name", "size", "computed_md5", "supplied_md5", "download_url")
                  if old[fid].get(k) != new[fid].get(k)}
        if fields:
            changes.append({"file_id": fid, "changed_fields": fields})
    replacements = [{"removed_file_id": a, "added_file_id": b, "name": old[a]["name"],
                     "same_bytes_established": False}
                    for a in removed for b in added if old[a]["name"] == new[b]["name"]]
    return {"added_file_ids": added, "removed_file_ids": removed,
            "same_id_changes": changes, "same_name_replacements": replacements,
            "rename_rule": "Only same-ID name changes are called renames; different names remain distinct."}


def member_diff(before, after):
    old = {m["path"]: m for m in before if m["role"] == "SOURCE_MEMBER"}
    new = {m["path"]: m for m in after if m["role"] == "SOURCE_MEMBER"}
    return {"added_paths": sorted(new.keys() - old.keys()),
            "removed_paths": sorted(old.keys() - new.keys()),
            "changed_paths": [p for p in sorted(old.keys() & new.keys())
                              if (old[p]["sha256"], old[p]["size"]) != (new[p]["sha256"], new[p]["size"])],
            "different_paths_not_collapsed": True}


def table_summary(headers, rows, source_row_numbers, unnamed_row_labels=False):
    if len(headers) != len(set(headers)) or any(len(r) != len(headers) for r in rows):
        raise ValueError("Ambiguous/ragged table schema")
    data = [dict(zip(headers, row)) for row in rows]
    result = {
        "row_count": len(rows), "column_count": len(headers), "exact_headers": headers,
        "unnamed_leading_row_label": unnamed_row_labels,
        "source_rows": {"first": min(source_row_numbers, default=None),
                        "last": max(source_row_numbers, default=None)},
        "missing_tokens_counted": sorted(MISSING), "missingness_is_not_zero_imputation": True,
        "missing_count_by_column": {h: sum(r[h] in MISSING for r in data) for h in headers},
        "identifier_candidates": [h for h in headers if h in
                                  {"PC_ID", "Study_group", "Study_year", "Victim", "Aggressor",
                                   "FileSource", "File", "Bout_number", "Individual", "Consoler_ID"}],
        "timing_or_order_candidates": [h for h in headers if re.search(
            r"(begin time|end time|duration|dur$|bout_number|bout_n|post_bout_event|pc_event)", h, re.I)],
        "receiver_fields": [h for h in headers if re.search(
            r"(consolation|reconciliation|renewed|post_bout_event|pc_event|consoler)", h, re.I)],
        "signal_audience_arousal_fields": [h for h in headers if re.search(
            r"(signal|bout|gesture|vocal|facial|body|audience|friend|dominant|kin_|piloerect)", h, re.I)],
    }
    if "Analysis_level" in headers:
        result["analysis_level_counts"] = dict(sorted(Counter(r["Analysis_level"] for r in data).items()))
        display = [r for r in data if r["Analysis_level"] == "Display"]
        result["display_identifier_counts"] = {h: len({r[h] for r in display if r[h] not in MISSING})
                                               for h in ("PC_ID", "Study_group", "Victim", "Aggressor") if h in headers}
        result["display_missing_count_by_column"] = {h: sum(r[h] in MISSING for r in display) for h in headers}
    if {"PC_ID", "Study_group", "Study_year", "Bout_number"} <= set(headers):
        bouts = [r for r in data if r.get("Analysis_level") == "Bout"]
        keys = [(r["Study_group"], r["Study_year"], r["PC_ID"], r["Bout_number"]) for r in bouts]
        result["bout_composite_key"] = ["Study_group", "Study_year", "PC_ID", "Bout_number"]
        result["bout_key_missing_rows"] = sum(any(x in MISSING for x in k) for k in keys)
        result["duplicate_bout_key_excess"] = len(keys) - len(set(keys))
    return result, data


def inspect_tsv(raw):
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t"))
    if not rows:
        raise ValueError("Empty tabular file")
    headers, body = rows[0], rows[1:]
    widths = {len(r) for r in body}
    implicit = bool(body) and widths == {len(headers) + 1}
    labels = [r[0] for r in body] if implicit else []
    values = [r[1:] for r in body] if implicit else body
    result, data = table_summary(headers, values, list(range(2, len(rows) + 1)), implicit)
    if implicit:
        result["leading_row_label_unique_count"] = len(set(labels))
        result["leading_row_label_role"] = "R write.table row-name convention; not a conflict identifier"
    return result, data


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for c in letters:
        n = n * 26 + ord(c) - 64
    return n - 1


def inspect_xlsx(raw):
    """Reuse established header probing, then count stored nonempty rows/missing cells."""
    headers = inspect_xlsx_headers(raw)
    with ZipFile(io.BytesIO(raw)) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        targets = {x.get("Id"): x.get("Target") for x in ET.fromstring(
            z.read("xl/_rels/workbook.xml.rels")).findall(P + "Relationship")}
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in si.iter(S + "t"))
                      for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(S + "si")]
        for sheet, summary in zip(wb.findall(f"./{S}sheets/{S}sheet"), headers, strict=True):
            target = targets[sheet.get(R + "id")]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            if not member.startswith("xl/worksheets/"):
                raise ValueError("Unexpected worksheet route")
            root = ET.fromstring(z.read(member))
            stored = []
            for row in root.findall(f"./{S}sheetData/{S}row"):
                cells = {}
                for c in row.findall(S + "c"):
                    v = c.find(S + "v")
                    value = v.text if v is not None and v.text is not None else ""
                    if c.get("t") == "s" and value:
                        value = shared[int(value)]
                    elif c.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in c.iter(S + "t"))
                    if value or c.find(S + "f") is not None:
                        cells[_col_index(c.get("r"))] = value
                if cells:
                    stored.append((int(row.get("r")), cells))
            summary["nonempty_stored_row_count_including_headers"] = len(stored)
            summary["column_extent_with_values"] = max((max(c) + 1 for _, c in stored), default=0)
            hrow = summary["header_candidate_row"]
            if hrow is None:
                summary["table_admission"] = "HELD_MULTILEVEL_HEADER_REQUIRES_SOURCE_MAPPING"
                summary["opening_header_cells_as_reported"] = [
                    {"row": n, "cells_by_zero_based_column": cells} for n, cells in stored if n <= 4]
                continue
            candidate = next(c for n, c in stored if n == hrow)
            exact = [candidate.get(i, "") for i in range(max(candidate) + 1)]
            selected = [(n, c) for n, c in stored if n > hrow]
            rows = [[cells.get(i, "") for i in range(len(exact))] for _, cells in selected]
            summary["unheaded_nonempty_cell_count"] = sum(
                sum(i >= len(exact) for i in cells) for _, cells in selected)
            tab, _ = table_summary(exact, rows, [n for n, _ in selected])
            summary["table_structure"] = tab
            summary["observation_unit"] = "Stored worksheet row; not certified as independent event"
    return headers


def inspect_code(raw):
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    patterns = {
        "read_commands": r"read\.(table|csv|delim)|readRDS|load\(",
        "seed_commands": r"set\.seed\(",
        "model_declarations": r"brm\(.*formula|family\s*=|warmup\s*=|iter\s*=|chains\s*=",
        "filter_aggregation_timing": r"merge\(|aggregate\(|replace\(is.na|rowSums|Analysis_level ==|as.numeric.*duration|excluded|less data points|two conflicts|write.table|transposed",
        "runtime_clues": r"R version|sessionInfo|packageVersion|RStudio|Version:",
    }
    reads = sorted(set(re.findall(r'read\.(?:table|csv|delim)\(\s*["\']([^"\']+)', text)))
    return {
        "inspection": "STATIC_TEXT_ONLY_NOT_EXECUTED", "line_count": len(lines),
        "dependencies_as_coded": sorted(set(re.findall(r'(?:library|require)\(\s*([A-Za-z0-9_.]+)', text))),
        "expected_read_filenames": reads,
        "cues": {name: [{"line": i, "text": line.strip()} for i, line in enumerate(lines, 1)
                         if re.search(pattern, line, re.I)] for name, pattern in patterns.items()},
        "runtime_and_package_versions": "Not pinned unless explicit runtime clues say otherwise",
        "seed_scope": "Only where explicitly coded; do not treat a plotting seed as a model seed",
    }


def inspect_document(raw):
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    matches, routes = [], set()
    with ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED:
            raise ValueError("Document uncompressed limit exceeded")
        root = ET.fromstring(z.read("word/document.xml"))
        for i, para in enumerate(root.iter(w + "p"), 1):
            text = "".join(t.text or "" for t in para.iter(w + "t"))
            if re.search(r"figshare|\.(zip|csv|tsv|xlsx|r)\b|repository|accession", text, re.I):
                matches.append({"paragraph": i, "location_cue": text})
        for n in z.namelist():
            if n.endswith(".rels"):
                for rel in ET.fromstring(z.read(n)):
                    target = rel.get("Target", "")
                    if rel.get("TargetMode") == "External" and re.search(r"figshare|repository", target, re.I):
                        routes.add(target)
    return {"location_cues": matches, "authoritative_routes": sorted(routes),
            "generic_availability_prose_is_not_location_proof": True}


def link_inspection(main, aso):
    fields = ["Study_group", "Study_year", "PC_ID"]
    def key(r): return tuple(r[x] for x in fields)
    displays = {key(r): (i + 2, r) for i, r in enumerate(main) if r["Analysis_level"] == "Display"}
    if len(displays) != sum(r["Analysis_level"] == "Display" for r in main):
        raise ValueError("Display conflict key is not unique")
    main_bout_keys = {key(r) + (r["Bout_number"],) for r in main if r["Analysis_level"] == "Bout"}
    results = {}
    for label, data in (("main", main), ("persistence", aso)):
        missing, mismatches, extra = [], [], []
        for i, row in enumerate(data, 2):
            if row["Analysis_level"] != "Bout":
                continue
            if key(row) not in displays:
                missing.append(i)
                continue
            drow, display = displays[key(row)]
            changed = [h for h in ("Victim", "Aggressor", "FileSource") if row[h] != display[h]]
            if changed:
                mismatches.append({"bout_source_row": i, "display_source_row": drow, "columns": changed})
            if label == "persistence" and key(row) + (row["Bout_number"],) not in main_bout_keys:
                extra.append(i)
        results[label] = {"unmatched_conflict_source_rows": missing,
                          "conflict_metadata_mismatches": mismatches,
                          "rows_without_main_bout_key": extra}
    return {"candidate_conflict_key": fields, "candidate_bout_key": fields + ["Bout_number"],
            "key_match_is_not_semantic_or_timing_admission": True, "tables": results}


def build_receipt(api, read_bytes):
    envelopes = validate_history(api)  # fail before acquiring bytes if any version is unverified
    receipt = {
        "dataset_id": "D0029", "scope": "SOURCE_ADMISSION_ONLY", "outcome": "A",
        "state": HELD, "canonical_final_publication_doi": "10.6084/m9.figshare.16910173.v4",
        "version_history": api["version_history"], "versions": [], "adjacent_manifest_diffs": [],
        "scientific_files": [], "member_content_inspections": {}, "archive_members": {},
        "rdc006_empirical_admission": False, "confirmatory_rq0005_run": "NOT_STARTED",
        "deposited_code_executed": False, "media_downloaded": False,
        "production_bytes_in_git": False, "semantic_effect": "NONE",
    }
    prior = None
    associations, metadata = {}, {}
    for env in envelopes + [api["supplement"]]:
        d = env["record"]
        if d["id"] == ITEM:
            rec = {"endpoint": env["endpoint"], "retrieved_utc": env["retrieved_utc"],
                   "response_sha256": env["response_sha256"],
                   **{k: d.get(k) for k in ("id", "version", "doi", "title", "published_date", "created_date", "modified_date", "license", "files")}}
            receipt["versions"].append(rec)
            if prior:
                receipt["adjacent_manifest_diffs"].append({"from_version": prior["version"], "to_version": d["version"],
                                                          **manifest_diff(prior["files"], d["files"])})
            prior = d
        else:
            if d["id"] != 20131650 or d["version"] != 2 or d["doi"] != "10.6084/m9.figshare.20131650.v2":
                raise ValueError("Supplement item identity mismatch")
            receipt["supplement"] = {"endpoint": env["endpoint"], "retrieved_utc": env["retrieved_utc"],
                                     "response_sha256": env["response_sha256"],
                                     **{k: d.get(k) for k in ("id", "version", "doi", "title", "license", "files")}}
        for f in d["files"]:
            if PurePosixPath(f["name"]).suffix.lower() in MEDIA:
                continue
            fid = f["id"]
            if fid in metadata and metadata[fid] != f:
                raise ValueError("Same file ID has inconsistent source metadata")
            metadata[fid] = f
            associations.setdefault(fid, []).append({"item_id": d["id"], "version": d["version"], "doi": d["doi"],
                                                      "item_license_as_reported": d.get("license")})
    for fid, f in sorted(metadata.items()):
        try:
            raw = read_bytes(f)
            hashes = verify_bytes(f, raw)
        except (OSError, ValueError) as error:
            raise ValueError(f"File {fid} ({f['download_url']}): {error}") from error
        file = {"metadata_as_reported": f, "associations": associations[fid], **hashes,
                "file_license_as_reported": f.get("license"), "md5_match": True}
        receipt["scientific_files"].append(file)
        if f["name"].lower().endswith(".docx"):
            file["document_inspection"] = inspect_document(raw)
            continue
        if not f["name"].lower().endswith(".zip"):
            raise ValueError("Unexpected non-media type requires separate source inspection")
        members, tables, code = [], {}, []
        with ZipFile(io.BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED:
                raise ValueError("Archive uncompressed limit exceeded")
            if len(z.namelist()) != len(set(z.namelist())):
                raise ValueError("Duplicate archive member path")
            for info in z.infolist():
                if info.is_dir():
                    continue
                payload = z.read(info)
                digest = digests(payload)
                member = {"path": info.filename, "size": len(payload), **digest,
                          "file_license_as_reported": None}
                members.append(member)
                path = PurePosixPath(info.filename)
                if "__MACOSX" in path.parts or ".Rproj.user" in path.parts:
                    member["role"] = "ARCHIVE_METADATA_NOT_ANALYSIS_INPUT"
                    continue
                member["role"] = "SOURCE_MEMBER"
                sha = digest["sha256"]
                if path.suffix.lower() == ".txt":
                    summary, data = inspect_tsv(payload)
                    receipt["member_content_inspections"].setdefault(sha, {"type": "TSV", **summary})
                    tables[path.name] = data
                elif path.suffix.lower() == ".xlsx":
                    if sha not in receipt["member_content_inspections"]:
                        receipt["member_content_inspections"][sha] = {"type": "XLSX", "sheets": inspect_xlsx(payload)}
                elif path.suffix.lower() in {".r", ".rproj"}:
                    inspection = inspect_code(payload)
                    receipt["member_content_inspections"].setdefault(sha, {"type": "R_STATIC", **inspection})
                    code.append(inspection)
            receipt["archive_members"][str(fid)] = sorted(members, key=lambda x: x["path"])
        available = {PurePosixPath(m["path"]).name for m in members if m["role"] == "SOURCE_MEMBER"}
        file["expected_read_files_absent_from_archive"] = sorted({n for c in code for n in c["expected_read_filenames"]} - available)
        if "processed_dataset.txt" in tables and "data_victimsignalling_BoutAso.txt" in tables:
            file["link_inspection"] = link_inspection(tables["processed_dataset.txt"], tables["data_victimsignalling_BoutAso.txt"])
    receipt["adjacent_analysis_archive_member_diffs"] = []
    for diff in receipt["adjacent_manifest_diffs"]:
        for replacement in diff["same_name_replacements"]:
            a, b = replacement["removed_file_id"], replacement["added_file_id"]
            if str(a) in receipt["archive_members"] and str(b) in receipt["archive_members"]:
                receipt["adjacent_analysis_archive_member_diffs"].append({
                    "from_version": diff["from_version"], "to_version": diff["to_version"],
                    "from_file_id": a, "to_file_id": b,
                    **member_diff(receipt["archive_members"][str(a)], receipt["archive_members"][str(b)])})
    if not receipt["archive_members"]:
        receipt.update(outcome="B", state="HELD_R0011_DATA_CODE_UNLOCATED_AFTER_ROUTE_ENUMERATION")
    return receipt


def refresh(cache):
    def fetch(path):
        url = BASE + path
        with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "AnimalRosettaStone-source-admission/0.1"}), timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Metadata response limit exceeded")
        return {"endpoint": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "response_sha256": hashlib.sha256(raw).hexdigest(), "record": json.loads(raw)}
    history = fetch(f"/articles/{ITEM}/versions")
    api = {"version_history": history,
           "versions": [fetch(f"/articles/{ITEM}/versions/{v['version']}") for v in history["record"]],
           "supplement": fetch("/articles/20131650/versions/2")}
    validate_history(api)
    (cache / "api.json").write_text(json.dumps(api, indent=2) + "\n")
    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="build/d0029_source_history")
    parser.add_argument("--refresh", action="store_true", help="Explicitly use the public API and acquire small non-media files")
    parser.add_argument("--out", default="build/d0029_version_history_receipt.json")
    args = parser.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    def read(f):
        name = PurePosixPath(f["name"])
        if name.name != f["name"] or name.name in {".", ".."}:
            raise ValueError("Unsafe source filename")
        path = cache / str(f["id"]) / f["name"]
        if path.exists():
            raw = path.read_bytes()
        elif args.refresh:
            if not isinstance(f["size"], int) or not 0 < f["size"] <= MAX_BYTES:
                raise ValueError("File exceeds bounded download limit")
            # Validate the route before any network call using the same verifier.
            parsed = urlparse(f["download_url"])
            if parsed.scheme != "https" or parsed.netloc != "ndownloader.figshare.com" or parsed.path != f"/files/{f['id']}":
                raise ValueError("Unexpected download route")
            with urlopen(Request(f["download_url"], headers={"User-Agent": "AnimalRosettaStone-source-admission/0.1"}), timeout=20) as response:
                raw = response.read(f["size"] + 1)
            verify_bytes(f, raw)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        else:
            raise ValueError(f"Verified local source bytes missing for file {f['id']}")
        return raw
    try:
        api = refresh(cache) if args.refresh else json.loads((cache / "api.json").read_text())
        receipt = build_receipt(api, read)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, RuntimeError, ET.ParseError) as error:
        receipt = {"dataset_id": "D0029", "outcome": "C", "state": "HELD_INCOMPLETE_SOURCE_ACCESS",
                   "error_type": type(error).__name__, "error": str(error),
                   "rdc006_empirical_admission": False, "confirmatory_rq0005_run": "NOT_STARTED"}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_private(out, receipt)
    print(json.dumps({"outcome": receipt["outcome"], "state": receipt["state"], "output": str(out)}))
    if receipt["outcome"] == "C":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
