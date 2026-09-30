"""Outcome-blind D0019 Group-2 identity/dyad audit for RDC-004."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLS = {"Dataset":"A","event":"B","initiator":"E","group":"F","recipient":"I","dyad":"K"}


def group2_identity_audit(raw: bytes, expected_headers: list[str]) -> dict:
    with ZipFile(BytesIO(raw)) as book:
        if sum(x.file_size for x in book.infolist()) > 8_000_000:
            raise ValueError("Source decompression bound exceeded")
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.iter(S+"t")) for si in root.findall(S+"si")]
        root = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        dim = root.find(S+"dimension")
        if dim is None or dim.get("ref") != "A1:P253":
            raise ValueError("Rawdata dimension drift")
        data = root.find(S+"sheetData")
        if data is None:
            raise ValueError("Missing Rawdata sheetData")
        rows = data.findall(S+"row")

        def decode(cell):
            if cell is None:
                return ""
            if cell.find(S+"f") is not None:
                raise ValueError("Formula present in identity field")
            v = cell.find(S+"v")
            t = cell.get("t")
            if t == "s":
                if v is None or v.text is None:
                    return ""
                idx = int(v.text)
                if idx < 0 or idx >= len(strings):
                    raise ValueError("Invalid shared-string reference")
                return strings[idx]
            if t == "inlineStr":
                inline = cell.find(S+"is")
                return "".join(x.text or "" for x in inline.iter(S+"t")) if inline is not None else ""
            return v.text if v is not None and v.text is not None else ""

        header = next((r for r in rows if r.get("r") == "1"), None)
        if header is None:
            raise ValueError("Missing source header")
        if [decode(c) for c in header.findall(S+"c")] != expected_headers:
            raise ValueError("Source header differs from H1 pin")

        group2 = []
        for row in rows:
            n = int(row.get("r", "0"))
            if n <= 1:
                continue
            cells = {c.get("r"): c for c in row.findall(S+"c")}
            group = decode(cells.get(f"F{n}")).strip()
            if group == "2":
                values = {name: decode(cells.get(f"{col}{n}")).strip() for name,col in COLS.items()}
                values["source_row"] = n
                group2.append(values)

        if len(group2) != 149:
            raise ValueError("Group 2 row count differs from frozen 149")

        missing = {
            field: sum(1 for r in group2 if not r[field])
            for field in ("Dataset","event","initiator","recipient","dyad")
        }
        if missing["initiator"] or missing["recipient"]:
            identity_ready = False
        else:
            identity_ready = True

        events = [r["event"] for r in group2 if r["event"]]
        event_unique = len(events) == len(set(events)) and len(events) == 149
        event_year = [(r["Dataset"], r["event"]) for r in group2 if r["Dataset"] and r["event"]]
        event_group_year = [(r["Dataset"], "2", r["event"]) for r in group2 if r["Dataset"] and r["event"]]
        event_unique_with_year = len(event_year) == len(set(event_year)) and len(event_year) == 149
        event_unique_with_group_year = (
            len(event_group_year) == len(set(event_group_year)) and len(event_group_year) == 149
        )

        same_individual = sum(
            1 for r in group2
            if r["initiator"] and r["recipient"] and r["initiator"] == r["recipient"]
        )

        source_dyad_to_ordered: dict[str,set[tuple[str,str]]] = {}
        source_dyad_to_unordered: dict[str,set[tuple[str,str]]] = {}
        unordered_to_source: dict[tuple[str,str],set[str]] = {}
        ordered_to_source: dict[tuple[str,str],set[str]] = {}
        for r in group2:
            if not r["initiator"] or not r["recipient"] or not r["dyad"]:
                continue
            ordered=(r["initiator"],r["recipient"])
            unordered=tuple(sorted(ordered))
            source_dyad_to_ordered.setdefault(r["dyad"],set()).add(ordered)
            source_dyad_to_unordered.setdefault(r["dyad"],set()).add(unordered)
            unordered_to_source.setdefault(unordered,set()).add(r["dyad"])
            ordered_to_source.setdefault(ordered,set()).add(r["dyad"])

        dyad_maps_one_unordered_pair = all(len(v)==1 for v in source_dyad_to_unordered.values())
        unordered_pair_maps_one_source_dyad = all(len(v)==1 for v in unordered_to_source.values())
        ordered_pair_maps_one_source_dyad = all(len(v)==1 for v in ordered_to_source.values())
        reverse_orientation_present = any(len(v)>1 for v in source_dyad_to_ordered.values())

        pair_year_to_source: dict[tuple[str,str,str],set[str]] = {}
        source_to_years: dict[str,set[str]] = {}
        for r in group2:
            if not r["Dataset"] or not r["initiator"] or not r["recipient"] or not r["dyad"]:
                continue
            unordered=tuple(sorted((r["initiator"],r["recipient"])))
            pair_year_to_source.setdefault((r["Dataset"],)+unordered,set()).add(r["dyad"])
            source_to_years.setdefault(r["dyad"],set()).add(r["Dataset"])
        unordered_pair_year_maps_one_source_dyad = all(len(v)==1 for v in pair_year_to_source.values())
        source_dyad_is_single_year = all(len(v)==1 for v in source_to_years.values())

        years=sorted({r["Dataset"] for r in group2 if r["Dataset"]})
        return {
            "group2_rows":149,
            "source_row_locator_unique_by_construction":len({r["source_row"] for r in group2})==149,
            "missing_identifier_counts":missing,
            "event_field_unique_within_group2":event_unique,
            "event_plus_year_unique_within_group2":event_unique_with_year,
            "event_plus_group_plus_year_unique_within_group2":event_unique_with_group_year,
            "same_initiator_recipient_rows":same_individual,
            "collection_year_tokens":years,
            "source_dyad_unique_tokens":len(source_dyad_to_ordered),
            "ordered_initiator_recipient_pairs":len(ordered_to_source),
            "unordered_initiator_recipient_pairs":len(unordered_to_source),
            "source_dyad_maps_to_one_unordered_pair":dyad_maps_one_unordered_pair,
            "unordered_pair_maps_to_one_source_dyad":unordered_pair_maps_one_source_dyad,
            "ordered_pair_maps_to_one_source_dyad":ordered_pair_maps_one_source_dyad,
            "source_dyad_contains_both_directions_for_at_least_one_pair":reverse_orientation_present,
            "unordered_pair_plus_year_maps_to_one_source_dyad":unordered_pair_year_maps_one_source_dyad,
            "source_dyad_token_is_confined_to_one_year":source_dyad_is_single_year,
            "identity_fields_ready_for_deterministic_pseudonymization":identity_ready,
            "identity_values_or_row_level_pairs_emitted":False,
            "group1_identity_signal_or_outcome_cells_decoded":False,
            "group1_holdout_opened":False,
        }


def audit(item: dict, pins: dict, crosswalk: dict, fetch) -> dict:
    receipt={
        "dataset_id":"D0019","phase":"H3_GROUP2_IDENTITY_DYAD_AUDIT",
        "state":"HELD_SOURCE_OR_MAPPING","source_bytes_stored":False,
        "group1_holdout_opened":False,"group1_outcomes_accessed":False,
        "rdc004_empirical_admission":False,"pr0005_executed":False,
        "scientific_effect":"NONE","crg_c_credit":"UNMET",
    }
    if (
        crosswalk.get("version")!="source-crosswalk-v0.2"
        or crosswalk.get("empirical_admission") is not False
        or crosswalk.get("group1_outcomes_accessed") is not False
        or crosswalk.get("source_sha256")!=pins["file"]["sha256"]
    ):
        return receipt
    if item.get("id")!=pins.get("source_item_id") or item.get("version")!=1 or item.get("doi")!=pins.get("doi"):
        receipt["state"]="HELD_SOURCE_IDENTITY"; return receipt
    lic=item.get("license") or {}
    if not isinstance(lic,dict) or {k:lic.get(k) for k in ("name","url")}!=pins.get("license_as_reported"):
        receipt["state"]="HELD_LICENSE"; return receipt
    files=item.get("files")
    if not isinstance(files,list) or len(files)!=1:
        receipt["state"]="HELD_FILE_INVENTORY"; return receipt
    f=files[0]; expected=pins["file"]
    if (
        f.get("id")!=expected["id"] or f.get("name")!=expected["name"]
        or f.get("size")!=expected["bytes"]
        or (f.get("computed_md5") or f.get("supplied_md5"))!=expected["md5"]
    ):
        receipt["state"]="QUARANTINED_SOURCE_DRIFT"; return receipt
    parsed=urlparse(str(f.get("download_url")))
    if parsed.scheme!="https" or parsed.hostname!="ndownloader.figshare.com" or parsed.path!=f"/files/{expected['id']}":
        receipt["state"]="QUARANTINED_SOURCE_LOCATION"; return receipt
    try:
        raw=fetch(f.get("download_url"),expected["bytes"])
        if len(raw)!=expected["bytes"] or hashlib.sha256(raw).hexdigest()!=expected["sha256"]:
            raise ValueError("Source bytes differ from H1 SHA-256")
        structural=group2_identity_audit(raw,pins["sheets"][0]["source_header_candidates"])
        receipt["identity_audit"]=structural
        if (
            structural["identity_fields_ready_for_deterministic_pseudonymization"]
            and structural["same_initiator_recipient_rows"]==0
            and structural["source_dyad_maps_to_one_unordered_pair"]
            and structural["unordered_pair_maps_to_one_source_dyad"]
        ):
            receipt["state"]="H3_IDENTITY_DYAD_STRUCTURE_VERIFIED_GROUPING_RULE_REVIEW_REQUIRED"
        else:
            receipt["state"]="HELD_IDENTITY_OR_DYAD_STRUCTURE"
    except (OSError,ValueError,TypeError,IndexError,KeyError,BadZipFile,ET.ParseError) as exc:
        receipt["state"]="HELD_IDENTITY_AUDIT_SOURCE"
        receipt["error_type"]=type(exc).__name__
        receipt["error_summary"]=str(exc)[:180]
    return receipt


def main():
    ap=argparse.ArgumentParser(description="Audit Group-2 event IDs and dyad structure without outcomes")
    ap.add_argument("--pins",default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk",default="contracts/d0019_rdc004_source_crosswalk_v0_2.json")
    ap.add_argument("--out",default="build/d0019_group2_identity_dyad_audit.json")
    args=ap.parse_args()
    try:
        from scripts.probe_d0019_source import public_item,fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item,fetch_source
    pins=json.loads(Path(args.pins).read_text()); crosswalk=json.loads(Path(args.crosswalk).read_text())
    try:
        receipt=audit(public_item(),pins,crosswalk,fetch_source)
    except (OSError,ValueError,TypeError) as exc:
        receipt={"dataset_id":"D0019","phase":"H3_GROUP2_IDENTITY_DYAD_AUDIT",
                 "state":"HELD_SOURCE_METADATA","error_type":type(exc).__name__,
                 "error_summary":str(exc)[:180],"group1_holdout_opened":False,
                 "group1_outcomes_accessed":False,"rdc004_empirical_admission":False,
                 "pr0005_executed":False}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"state":receipt["state"],"group1_outcomes_accessed":False,
                      "pr0005_executed":False,"output":str(out)}))


if __name__=="__main__":
    main()
