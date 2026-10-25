#!/usr/bin/env python3
"""Read-only S0002 supplement audit; aggregate output, no author-code execution.

Pins the publisher bytes observed on 2026-10-25, not a publisher-supplied
checksum. R0014 and all scientific/rights decisions remain under ACEB authority.
Original OOXML files are parsed in memory, never extracted, edited or executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
import zipfile

from research_integrity import fingerprint, write_private

SOURCES = {
    "workbook": (79710, "cf2c80aa4a8c9e461b70f3cf305af35cf73f0887c11f3d0de21ccaee56518103", "s002"),
    "code": (16385, "9298e872b72ebb17426ded1b0c798623f485622ae0da585c162f72e99cec4111", "s001"),
    "table": (18591, "caa482168262d81cc8f2f3e8333f1f20712397ef12931f94929f91852a78450f", "s003"),
}
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
P = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def pinned_bytes(path: Path, role: str) -> bytes:
    size, digest, _ = SOURCES[role]
    if fingerprint(path) != {"size_bytes": size, "sha256": digest}:
        raise ValueError(f"SOURCE_FINGERPRINT_MISMATCH:{role}")
    # Parse exactly the attested bytes even if the path changes after hashing.
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"SOURCE_CHANGED_BEFORE_PARSE:{role}")
    return data


def ooxml(data: bytes) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(BytesIO(data))
    members = archive.infolist()
    if len({m.filename for m in members}) != len(members) or sum(m.file_size for m in members) > 10_000_000:
        archive.close()
        raise ValueError("INVALID_OR_OVERSIZED_OOXML")
    return archive


def read_workbook(data: bytes) -> dict[str, list[list[str]]]:
    with ooxml(data) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(t.text or "" for t in si.iter(S + "t"))
                       for si in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        relationships = {}
        for rel in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels")).findall(P + "Relationship"):
            if rel.get("TargetMode") == "External":
                raise ValueError("EXTERNAL_WORKBOOK_RELATIONSHIP")
            target = PurePosixPath(rel.attrib["Target"])
            if target.is_absolute() or ".." in target.parts:
                raise ValueError("UNSAFE_WORKBOOK_RELATIONSHIP")
            relationships[rel.attrib["Id"]] = "xl/" + target.as_posix()
        result = {}
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in book.find(S + "sheets"):
            name = sheet.attrib["name"]
            if name in result:
                raise ValueError("DUPLICATE_SHEET")
            rows = []
            source = ET.fromstring(archive.read(relationships[sheet.attrib[R + "id"]]))
            for row in source.findall(S + "sheetData/" + S + "row"):
                values = {}
                for cell in row.findall(S + "c"):
                    if cell.find(S + "f") is not None:
                        raise ValueError("FORMULA_NOT_SOURCE_OBSERVATION")
                    match = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", cell.attrib["r"])
                    if not match:
                        raise ValueError("INVALID_CELL_REFERENCE")
                    col = 0
                    for char in match[1]:
                        col = 26 * col + ord(char) - ord("A") + 1
                    if col > 100 or col in values:
                        raise ValueError("INVALID_OR_DUPLICATE_COLUMN")
                    value = cell.findtext(S + "v", default="")
                    if cell.get("t") == "s":
                        index = int(value)
                        if not 0 <= index < len(strings):
                            raise ValueError("INVALID_SHARED_STRING")
                        value = strings[index]
                    elif cell.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in cell.iter(S + "t"))
                    elif cell.get("t") not in (None, "n"):
                        raise ValueError("UNSUPPORTED_CELL_TYPE")
                    values[col] = value
                if any(values.values()):
                    rows.append([values.get(i, "") for i in range(1, max(values) + 1)])
            result[name] = rows
        return result


def raw_summary(rows: list[list[str]], headers: list[str]) -> dict:
    if not rows or rows[0] != headers or any(len(r) != 3 or any(not v for v in r) for r in rows[1:]):
        raise ValueError("RAW_SCHEMA_OR_MISSING_CELL")
    data = rows[1:]
    # Identical reduced triples lack event IDs: never deduplicate observations.
    return {"columns": headers, "rows": len(data),
            "distinct_gesture_labels": len({r[1] for r in data}),
            "distinct_outcome_labels": len({r[0] for r in data}),
            "distinct_values_in_identity_column": len({r[2] for r in data}),
            "identity_column_role": headers[2],
            "unknown_outcome_rows": sum(r[0] == "Unknown" for r in data),
            "gesture_labels_with_edge_whitespace": len({r[1] for r in data if r[1] != r[1].strip()}),
            "repeated_reduced_triples_beyond_first": len(data) - len({tuple(r) for r in data}),
            "deduplication_performed": False}


def matrix(rows: list[list[str]]) -> tuple[list[str], dict[str, list[int]]]:
    if not rows or len(rows[0]) != 12 or rows[0][0] != "":
        raise ValueError("MATRIX_HEADER_SCHEMA")
    headers = rows[0][1:]
    if len(set(headers)) != 11 or any(not h for h in headers):
        raise ValueError("MATRIX_OUTCOME_LABELS")
    values = {}
    for row in rows[1:]:
        if not row or len(row) > 12 or not row[0] or row[0] in values:
            raise ValueError("MATRIX_GESTURE_LABELS")
        cells = row[1:] + [""] * (12 - len(row))
        if any(v not in ("", "0", "1") for v in cells):
            raise ValueError("NON_BINARY_MATRIX_CELL")
        # Released S1 R explicitly replaces matrix NA with zero. This treatment
        # belongs only to the binary matrices, never to missing raw observations.
        values[row[0]] = [int(v or "0") for v in cells]
    return headers, values


def overlap(a: dict[str, list[int]], b: dict[str, list[int]]) -> dict:
    if not a or a.keys() != b.keys() or any(len(a[g]) != len(b[g]) for g in a):
        raise ValueError("UNALIGNED_MATRICES")
    pairs = [(x, y) for g in sorted(a) for x, y in zip(a[g], b[g], strict=True)]
    cells = len(pairs)
    ones_a, ones_b = sum(x for x, _ in pairs), sum(y for _, y in pairs)
    shared = sum(x == y == 1 for x, y in pairs)
    matches = sum(x == y for x, y in pairs)
    if matches != cells - ones_a - ones_b + 2 * shared:
        raise ValueError("OVERLAP_IDENTITY_FAILED")
    return {"gesture_rows": len(a), "cells": cells, "bonobo_ones": ones_a,
            "chimp_ones": ones_b, "shared_ones": shared,
            "shared_zeros": matches - shared, "total_matches": matches,
            "fixed_ones_affine_identity_verified": True,
            "permutation_test_executed": False}


def table_summary(data: bytes) -> dict:
    with ooxml(data) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = root.findall(".//" + W + "tbl")
    if len(tables) != 1:
        raise ValueError("TABLE_COUNT")
    rows = [["".join(t.text or "" for t in c.iter(W + "t")) for c in r.findall(W + "tc")]
            for r in tables[0].findall(W + "tr")]
    if not rows or rows[0] != ["Gesture type", "Goal (ASO)", "# Instances", "Proportion"]:
        raise ValueError("TABLE_SCHEMA")
    gesture, gestures, outcomes, counts = None, set(), set(), []
    for row in rows[1:]:
        if len(row) != 4 or not row[1] or not re.fullmatch(r"[1-9][0-9]*", row[2]):
            raise ValueError("INVALID_TABLE_ROW")
        gesture = row[0] or gesture
        if not gesture:
            raise ValueError("MISSING_TABLE_GESTURE")
        gestures.add(gesture)
        outcomes.add(row[1])
        counts.append(int(row[2]))
    return {"gesture_outcome_entries": len(counts), "gesture_types": len(gestures),
            "outcome_types": len(outcomes), "sum_instances": sum(counts),
            "row_level_exclusion_ledger_present": False}


def audit(workbook: bytes, code: bytes, table: bytes) -> dict:
    sheets = read_workbook(workbook)
    if set(sheets) != {"Bonobo Raw", "Chimp Raw", "Bonobo matrix", "Chimp matrix"}:
        raise ValueError("UNEXPECTED_SHEETS")
    hb, b = matrix(sheets["Bonobo matrix"])
    hc, c = matrix(sheets["Chimp matrix"])
    if [h.casefold() for h in hb] != [h.casefold() for h in hc]:
        raise ValueError("MATRIX_COLUMN_ALIGNMENT")
    text = code.decode("utf-8")
    for literal in ['N_REPEATS = 10000', 'rownames(chimp_mat_orig)!="Foot present"',
                    'rownames(bonobo_mat_orig)!="Foot present"']:
        if literal not in text:
            raise ValueError("SOURCE_CODE_BOUNDARY_CHANGED")
    deposited = overlap(b, c)
    if "Foot present" not in b or any(b["Foot present"]) or sum(c["Foot present"]) != 1:
        raise ValueError("FOOT_PRESENT_BOUNDARY_CHANGED")
    executed = overlap({k: v for k, v in b.items() if k != "Foot present"},
                       {k: v for k, v in c.items() if k != "Foot present"})
    summary = table_summary(table)
    raw = raw_summary(sheets["Bonobo Raw"], ["Goal", "Gesture", "Recipient"])
    return {"contract": "ARS-S0002-DEPOSIT-AUDIT-v1", "status": "EXECUTED_BOUNDED_SOURCE_AUDIT",
            "scientific_effect": "NONE_NO_CLAIM_PROMOTION", "canonical_owner": "ACEB_R0014",
            "fingerprints": {role: {"size_bytes": v[0], "sha256": v[1],
                "doi": "10.1371/journal.pbio.2004825." + v[2]} for role, v in SOURCES.items()},
            "fingerprint_scope": "LOCALLY_OBSERVED_PUBLISHER_BYTES_NOT_PROVIDER_SUPPLIED_CHECKSUMS",
            "bonobo_raw": raw,
            "chimp_raw": raw_summary(sheets["Chimp Raw"], ["function", "gesture 66", "signaller"]),
            "published_s1_table": summary,
            "raw_minus_published_table_instances": raw["rows"] - summary["sum_instances"],
            "difference_is_not_an_observed_play_exclusion_count": True,
            "deposited_matrices": deposited, "source_code_after_foot_present_removal": executed,
            "matrix_column_alignment": "SAME_ORDER_CASE_ONLY_DIFFERENCE_STOP_BEHAVIOUR",
            "matrix_blank_policy": "ZERO_AS_IN_RELEASED_R_NOT_BIOLOGICAL_ABSENCE",
            "source_code_executed": False, "author_csv_inputs_packaged_in_xlsx": False,
            "receiver_attempt_success_estimand": "NOT_IDENTIFIABLE_FROM_DEPOSIT",
            "missing_fields": ["full_attempt_denominator", "play_flag", "recipient_response_status",
                "sequence_or_bout_id", "timestamps", "bonobo_signaller_id", "exclusion_ledger"],
            "r0014_disposition": "OPEN_SOURCE_SAMPLE_FLOW_NOT_RECONCILED_NO_CLAIM_PROMOTION",
            "limits": "Reduced ASO tables cannot identify unconditional response rates, independent sequences, "
                      "causal effects or receptive transfer. The 142-row difference has no source exclusion mapping. "
                      "No source rows, individual names or animal-language translations are emitted."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workbook", "code", "table", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(*(pinned_bytes(getattr(args, role), role) for role in ("workbook", "code", "table")))
        write_private(args.out, report)
        print(json.dumps({"status": report["status"], "report": str(args.out)}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, ET.ParseError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "HELD", "error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
