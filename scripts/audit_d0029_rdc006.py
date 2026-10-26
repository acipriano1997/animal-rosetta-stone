"""Offline v4 RDC-006 structure/eligibility audit. No R or inferential execution.

Read only the pinned 36230763 archive. Freeze schema, descriptive joins and
within-file annotation chronology, never a normalized empirical analysis corpus.
"""
from __future__ import annotations

try:
    from scripts.research_integrity import write_private
except ModuleNotFoundError:
    from research_integrity import write_private

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

try:
    from scripts.probe_d0029_source_history import (
        HELD, MAX_UNPACKED, MISSING, S, R, P, _col_index,
        digests, inspect_tsv, verify_bytes,
    )
except ModuleNotFoundError:
    from probe_d0029_source_history import (
        HELD, MAX_UNPACKED, MISSING, S, R, P, _col_index,
        digests, inspect_tsv, verify_bytes,
    )

SNAPSHOT_SHA256 = "696dbd94d2b8511c545e961b428be7a159286253ca48e7ae19e2e02af719dc7a"
ARCHIVE_ID = 36230763
CONFLICT = ["Study_group", "Study_year", "PC_ID"]
BOUT = CONFLICT + ["Bout_number"]
RAW_BOUT = "Bout_N¬∞"
TIME = ["Begin Time - msec", "End Time - msec", "Duration - msec"]
IDENTITIES = {"PC_ID", "Study_group", "Study_year", "Victim", "Aggressor", "Individual",
              "Consoler_ID", "File", "FileSource", "Bout_number", RAW_BOUT}
DOWNSTREAM = {"Bout_persistence", "Bout_persistence.01", "PersistenceCount", "Proppersistence"}
OUTCOMES = {"Consolation", "Reconciliation", "Renewed_ag", "PC_event", "PC_event_type",
            "PC_event_type_other", "Post_bout_event", "Consolation_afterbout", "Reconciliation_afterbout"}
OUTCOME_DERIVED = {"Consolation.01", "Reconciliation.01", "Renewed_ag.01", "Consolation_received",
                   "Reconciliation_received", "Consolationcount", "Reconciliationcount", "RenewedAGcount",
                   "PropConsolation", "PropReconciliation", "PropRenAG", "PC_beh_01"}
CLASSES = {"BASELINE_STATIC", "BASELINE_PRE_SIGNAL", "SIGNAL_TIME_ELIGIBLE",
           "TIMING_DEPENDENT_REQUIRES_EVENT_ORDER", "POST_RECEIVER_DOWNSTREAM", "OUTCOME",
           "DERIVED_FROM_OUTCOME", "IDENTITY_OR_CLUSTERING_ONLY", "UNKNOWN_TIMING_HELD"}


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def key(row, fields):
    return tuple(row.get(f, "") for f in fields)


def key_record(value, fields):
    return dict(zip(fields, value))


def locator(row):
    return row["_source_row"]


def profile(rows, fields):
    index = defaultdict(list)
    missing = []
    for row in rows:
        k = key(row, fields)
        if any(x in MISSING for x in k):
            missing.append(locator(row))
        else:
            index[k].append(row)
    return {"fields": fields, "row_count": len(rows), "distinct_complete_keys": len(index),
            "missing_key_source_rows": missing,
            "duplicate_keys": [{"key": key_record(k, fields), "source_rows": [locator(r) for r in rs],
                                "source_values_identical_excluding_locator": len({stable_hash({f: v for f, v in r.items() if not f.startswith('_')}) for r in rs}) == 1}
                               for k, rs in sorted(index.items()) if len(rs) > 1],
            "unique_complete": len(index) == len(rows)}, index


def join_diagnostics(left, right, fields, compare=()):
    lp, li = profile(left, fields)
    rp, ri = profile(right, fields)
    mismatches = []
    for k in sorted(li.keys() & ri.keys()):
        for a in li[k]:
            for b in ri[k]:
                changes = {f: {"left": a.get(f), "right": b.get(f)} for f in compare
                           if a.get(f) != b.get(f)}
                if changes:
                    mismatches.append({"key": key_record(k, fields), "left_source_row": locator(a),
                                       "right_source_row": locator(b), "fields": changes})
    return {
        "key_fields": fields, "left_profile": lp, "right_profile": rp,
        "intersection_unique_keys": len(li.keys() & ri.keys()),
        "left_unmatched": [{"key": key_record(k, fields), "source_rows": [locator(r) for r in li[k]]} for k in sorted(li.keys() - ri.keys())],
        "right_unmatched": [{"key": key_record(k, fields), "source_rows": [locator(r) for r in ri[k]]} for k in sorted(ri.keys() - li.keys())],
        "multiplicity_pairs": dict(sorted(Counter(f"{len(li[k])}:{len(ri[k])}" for k in li.keys() & ri.keys()).items())),
        "metadata_mismatches": mismatches, "keys_repaired": False,
    }


def read_sheets(raw):
    """Preserve worksheet cells/row locators; do not run formulas or fill sparse tiers."""
    with ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED:
            raise ValueError("Workbook exceeds established uncompressed bound")
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        targets = {x.get("Id"): x.get("Target") for x in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall(P + "Relationship")}
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in si.iter(S + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(S + "si")]
        result = {}
        for sheet in wb.findall(f"./{S}sheets/{S}sheet"):
            target = targets[sheet.get(R + "id")]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            if not member.startswith("xl/worksheets/"):
                raise ValueError("Unexpected worksheet relationship")
            cells_by_row, formulas = {}, []
            for row in ET.fromstring(z.read(member)).findall(f"./{S}sheetData/{S}row"):
                cells = {}
                for c in row.findall(S + "c"):
                    v = c.find(S + "v")
                    value = v.text if v is not None and v.text is not None else ""
                    if c.get("t") == "s" and value:
                        value = shared[int(value)]
                    elif c.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in c.iter(S + "t"))
                    if c.find(S + "f") is not None:
                        formulas.append(c.get("r"))
                    if value:
                        cells[_col_index(c.get("r"))] = value
                if cells:
                    cells_by_row[int(row.get("r"))] = cells
            result[sheet.get("name")] = {"cells": cells_by_row, "formula_cells_not_executed": formulas}
        return result


def rows_from_sheet(sheet, header_row=1):
    header = sheet["cells"].get(header_row)
    if not header:
        raise ValueError("No explicit nominated header row")
    if len(set(header.values())) != len(header):
        raise ValueError("Duplicate nominated worksheet headers")
    rows = []
    for n, cells in sheet["cells"].items():
        if n <= header_row:
            continue
        row = {header.get(i, f"_unheaded_column_{i + 1}"): v for i, v in cells.items()}
        row["_source_row"] = n
        rows.append(row)
    return rows


def load_v4(snapshot, raw):
    files = [f for f in snapshot["scientific_files"] if f["metadata_as_reported"]["id"] == ARCHIVE_ID]
    if len(files) != 1 or files[0]["associations"] != [{
            "doi": "10.6084/m9.figshare.16910173.v4", "item_id": 16910173,
            "item_license_as_reported": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "value": 1}, "version": 4}]:
        raise ValueError("Active package is not exclusively item 16910173 v4/file 36230763")
    f = files[0]
    if verify_bytes(f["metadata_as_reported"], raw) != {"md5": f["md5"], "sha256": f["sha256"]}:
        raise ValueError("Archive differs from frozen v4 pin")
    pins = {m["path"]: m for m in snapshot["archive_members"][str(ARCHIVE_ID)]}
    payloads = {}
    with ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_UNPACKED:
            raise ValueError("Archive exceeds established uncompressed bound")
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        if len(names) != len(set(names)) or set(names) != set(pins):
            raise ValueError("Archive member manifest drift")
        for name in names:
            data = z.read(name)
            pin = pins[name]
            if len(data) != pin["size"] or digests(data) != {"md5": pin["md5"], "sha256": pin["sha256"]}:
                raise ValueError(f"Member hash/size drift: {name}")
            if pin["role"] == "SOURCE_MEMBER":
                payloads[name] = data
    return f, payloads


def interval(row):
    try:
        values = [Decimal(row.get(k, "")) for k in TIME]
        if any(not v.is_finite() or v != v.to_integral_value() for v in values):
            return None
        return tuple(int(v) for v in values)
    except (InvalidOperation, ValueError):
        return None


def time_quality(rows):
    out = Counter(total_rows=len(rows))
    anomalies = []
    for row in rows:
        t = interval(row)
        if t is None:
            out["missing_or_invalid_ms_rows"] += 1
            anomalies.append({"source_row": locator(row), "issue": "MISSING_INVALID_OR_NONINTEGER_MS"})
            continue
        b, e, d = t
        out["valid_numeric_ms_rows"] += 1
        issues = []
        if b < 0 or e < 0 or d < 0 or e < b:
            out["negative_or_reversed_interval_rows"] += 1
            issues.append("NEGATIVE_OR_REVERSED")
        if e - b != d:
            out["duration_identity_mismatch_rows"] += 1
            issues.append("DURATION_NOT_END_MINUS_BEGIN")
        if b == e:
            out["zero_length_interval_rows"] += 1
        for i, prefix in enumerate(("Begin Time", "End Time", "Duration")):
            try:
                s = Decimal(row.get(prefix + " - ss.msec", ""))
                hms = re.fullmatch(r"(\d+):(\d{2}):(\d{2})\.(\d{3})", row.get(prefix + " - hh:mm:ss.ms", ""))
                hms_ms = ((int(hms[1]) * 3600 + int(hms[2]) * 60 + int(hms[3])) * 1000 + int(hms[4])) if hms else None
                if not s.is_finite() or abs(s * 1000 - t[i]) > Decimal("0.001") or hms_ms != t[i]:
                    issues.append(prefix + "_REDUNDANT_UNIT_MISMATCH")
            except (InvalidOperation, ValueError):
                issues.append(prefix + "_REDUNDANT_UNIT_UNAVAILABLE")
        if issues:
            anomalies.append({"source_row": locator(row), "issues": issues})
        else:
            out["all_redundant_units_and_interval_identity_valid_rows"] += 1
    for k in ("missing_or_invalid_ms_rows", "negative_or_reversed_interval_rows", "duration_identity_mismatch_rows", "zero_length_interval_rows"):
        out.setdefault(k, 0)
    return {"counts": dict(out), "anomalies": anomalies,
            "units": "Milliseconds as explicitly headed; seconds and hh:mm:ss.ms checked redundantly",
            "origin": "FILE_LOCAL_ORIGIN; CONFLICT_END_ORIGIN_NOT_ESTABLISHED"}


def receiver_display_relation(event, display):
    e, d = interval(event), interval(display)
    if e is None or d is None or any(v < 0 for v in (*e, *d)) or e[1] - e[0] != e[2] or d[1] - d[0] != d[2]:
        return "INVALID_INTERVAL_HELD"
    t, start, end = e[0], d[0], d[1]
    if t < start:
        return "BEFORE_DISPLAY_START"
    if t == start:
        return "TIED_DISPLAY_START"
    if t < end:
        return "DURING_ONGOING_DISPLAY"
    if t == end:
        return "TIED_DISPLAY_END"
    return "AFTER_DISPLAY_COMPLETION"


def filename_anchor(filename):
    """ARS candidate only. Never replace native keys or certify a join this way."""
    pc = re.match(r"PC([^_]+)_", filename)
    dates = re.findall(r"\d{2}\.\d{2}\.\d{2}", filename)
    if not dates:
        dates = re.findall(r"_(\d{2}\.\d{2})(?=[._ )])", filename)
    return (pc[1], dates[-1]) if pc and dates else None


def raw_structure(rows, displays):
    grouped = defaultdict(list)
    orphan = []
    for r in rows:
        if r.get("File"):
            grouped[r["File"]].append(r)
        else:
            orphan.append({"source_row": locator(r), "unheaded_cells": {k: v for k, v in r.items() if k.startswith("_unheaded")}})
    metadata, native_rows = {}, []
    for file, rs in sorted(grouped.items()):
        candidates = {f: sorted({r[f] for r in rs if r.get(f)}) for f in CONFLICT + ["Victim", "Aggressor"]}
        metadata[file] = candidates
        if all(len(candidates[f]) == 1 for f in CONFLICT):
            native_rows.append({f: candidates[f][0] for f in CONFLICT} | {"FileSource": file, "_source_row": min(locator(r) for r in rs),
                              **{f: candidates[f][0] for f in ("Victim", "Aggressor") if len(candidates[f]) == 1}})
    native = join_diagnostics(displays, native_rows, CONFLICT, ["Victim", "Aggressor"])
    ri, mi = defaultdict(list), defaultdict(list)
    for file in grouped:
        ri[filename_anchor(file)].append(file)
    for d in displays:
        mi[filename_anchor(d["FileSource"])].append(d)
    candidates, unmapped = [], []
    for anchor, ds in sorted(mi.items(), key=lambda x: str(x[0])):
        fs = ri.get(anchor, [])
        if anchor is None or len(ds) != 1 or len(fs) != 1:
            unmapped.extend(locator(d) for d in ds)
            continue
        d, file = ds[0], fs[0]
        raw_meta = metadata[file]
        discrepancies = {f: {"raw_values": raw_meta[f], "processed_value": d[f]} for f in CONFLICT + ["Victim", "Aggressor"]
                         if raw_meta[f] != [d[f]]}
        candidates.append({"processed_conflict_key": key_record(key(d, CONFLICT), CONFLICT), "processed_display_source_row": locator(d),
                           "raw_file": file, "raw_metadata_as_reported": raw_meta, "metadata_differences": discrepancies,
                           "status": "ARS_FILENAME_ANCHOR_CANDIDATE_NOT_SOURCE_AUTHORED_OR_ADMITTED"})
    raw_unmatched = sorted(file for a, fs in ri.items() if a not in mi for file in fs)
    tiers = {}
    for f in [RAW_BOUT, "Bout_modalities", "Signal_complexity_bout", "Bout_direction", "Post_bout_event", "Bout_persistence.01",
              "Victim_signalled.01", "Signal_display_dur", "PC_event", "PC_event_type", "Victim_piloerect.01", "Video_dur"]:
        rs = [r for r in rows if r.get(f)]
        tier_profile, _ = profile(rs, ["File", "Begin Time - msec", "End Time - msec"])
        tiers[f] = {"row_count": len(rs), "file_count": len({r.get('File') for r in rs if r.get('File')}), "interval_key_profile": tier_profile}
    bouts = [{**r, "Bout_number": r[RAW_BOUT]} for r in rows if r.get(RAW_BOUT)]
    bout_profile, _ = profile(bouts, ["File", "Bout_number"])
    interval_links = {}
    for f in ["Bout_modalities", "Post_bout_event", "Bout_persistence.01", "Signal_complexity_bout", "Bout_direction"]:
        interval_links[f] = join_diagnostics([r for r in rows if r.get(RAW_BOUT)], [r for r in rows if r.get(f)],
                                             ["File", "Begin Time - msec", "End Time - msec"])
    # A sparse annotation row is not a row of simultaneous conflict metadata.
    # Inspect file/tier/interval keys instead of repeatedly reporting thousands
    # of missing composite keys on unrelated single-tier annotations.
    annotations, row_shapes = [], Counter()
    for r in rows:
        tier_count = 0
        for field, value in r.items():
            if value and not field.startswith('_') and field != 'File' and not re.match(r'^(Begin Time|End Time|Duration) - ', field):
                tier_count += 1
                annotations.append({'File': r.get('File', ''), 'Tier': field,
                                    'Annotation_value': value,
                                    'Begin Time - msec': r['Begin Time - msec'],
                                    'End Time - msec': r['End Time - msec'], '_source_row': locator(r)})
        row_shapes[str(tier_count)] += 1
    annotation_profile = profile(annotations, ['File', 'Tier', 'Begin Time - msec', 'End Time - msec'])[0]
    return {"file_count": len(grouped), "orphan_file_annotations": orphan,
            "ambiguous_file_metadata": [{"file": f, "values": m} for f, m in metadata.items() if any(len(v) != 1 for v in m.values())],
            "native_metadata_join": native, "raw_tiers": tiers, "raw_bout_profile": bout_profile,
            "exact_interval_bout_tier_joins": interval_links,
            'annotation_file_tier_interval_profile': annotation_profile,
            'raw_row_named_tier_value_counts': dict(sorted(row_shapes.items())),
            "filename_candidate_crosswalk": {"rule": "Filename PC token + final full dd.mm.yy date, or dd.mm fallback; require unique anchors on both sides",
                                             "join_admissible": False, "candidate_matches": candidates, "processed_unmapped_rows": unmapped,
                                             "raw_files_without_processed_candidate": raw_unmatched}}, grouped


def temporal_coverage(rows, grouped):
    relation_counts, event_details = Counter(), []
    bout_relations = Counter()
    missing_display = 0
    video_lengths = []
    receiver_ties = []
    occlusion = Counter()
    for file, rs in sorted(grouped.items()):
        display = [r for r in rs if r.get("Signal_display_dur")]
        events = [r for r in rs if r.get("PC_event")]
        bouts = [r for r in rs if r.get(RAW_BOUT)]
        video = [r for r in rs if r.get("Video_dur")]
        if len(video) == 1 and interval(video[0]) is not None:
            video_lengths.append(interval(video[0])[2])
        starts = defaultdict(list)
        for e in events:
            t = interval(e)
            if t:
                starts[t[0]].append(e)
            if len(display) != 1:
                missing_display += 1
                continue
            relation = receiver_display_relation(e, display[0])
            relation_counts[relation] += 1
            event_details.append({"file": file, "receiver_source_row": locator(e), "source_outcome_label": e["PC_event"],
                                  "display_source_row": locator(display[0]), "relation": relation,
                                  'receiver_interval_ms_as_reported': list(t) if t is not None else None,
                                  'display_interval_ms_as_reported': list(interval(display[0])) if interval(display[0]) is not None else None,
                                  "window_eligibility": "HELD_CONFLICT_END_ORIGIN_AND_ACTIVE_RECEIVER_DEFINITION"})
            if t:
                bt = [interval(b) for b in bouts]
                bt = [b for b in bt if b is not None]
                overlaps = sum(b[0] < t[0] < b[1] for b in bt)
                ties = sum(t[0] in (b[0], b[1]) for b in bt)
                bout_relations["event_starts_inside_at_least_one_bout" if overlaps else "event_starts_outside_bout_interiors"] += 1
                if ties:
                    bout_relations["event_starts_tied_with_bout_boundary"] += 1
        for t, es in starts.items():
            if len(es) > 1:
                receiver_ties.append({"file": file, "start_ms": t, "source_rows": [locator(e) for e in es]})
        for r in rs:
            for f in ("Gesture", "Vocalization", "Body_signals", "Facial_expression"):
                if re.search(r"out.?of.?sight|not.?visible", r.get(f, ""), re.I):
                    occlusion[f + ":" + r[f]] += 1
    return {
        "all_annotation_time_quality": time_quality(rows),
        "receiver_annotation_time_quality": time_quality([r for r in rows if r.get("PC_event")]),
        'receiver_annotation_counts_by_source_label': dict(sorted(Counter(r['PC_event'] for r in rows if r.get('PC_event')).items())),
        "receiver_display_start_relations": dict(sorted(relation_counts.items())),
        "receiver_events_without_unique_display_interval": missing_display,
        "receiver_start_vs_bout_interiors": dict(bout_relations), "simultaneous_receiver_start_groups": receiver_ties,
        "event_order_diagnostics": event_details,
        "coverage": {"file_count": len(grouped), "valid_video_duration_intervals": len(video_lengths),
                     "video_intervals_shorter_than_300000_ms": sum(d < 300000 for d in video_lengths),
                     "files_without_receiver_annotation": sum(not any(r.get('PC_event') for r in rs) for rs in grouped.values()),
                     "conflicts_with_verified_conflict_end_timestamp": 0,
                     "conflicts_with_certified_five_minute_observable_followup": 0,
                     "five_minute_eligibility_status": "UNKNOWN_ORIGIN_AND_OBSERVABILITY; DO_NOT_USE_FILE_ZERO_AS_CONFLICT_END",
                     "explicit_component_occlusion_labels": dict(occlusion), "missing_receiver_tier_is_not_negative_outcome": True},
        "comparison_scope": "Annotation intervals on the same deposited File only; no prediction or hypothesis test",
        'receiver_definition_status': 'PC_event tier interval start; active receiver endpoint and conflict-relative window not certified',
        'post_bout_event_definition_status': 'Bout-related label interval; do not substitute its start for actual receiver-event onset',
    }


def classification(field):
    if field in IDENTITIES or field in {"Analysis_level", "Signaltype", "Signaltype_kind"}:
        return "IDENTITY_OR_CLUSTERING_ONLY", "Identity, source locator, observation level or category; no causal/semantic interpretation"
    if field in DOWNSTREAM:
        return "POST_RECEIVER_DOWNSTREAM", "Receiver-dependent continuation/persistence; prohibited as baseline"
    if field in OUTCOME_DERIVED:
        return "DERIVED_FROM_OUTCOME", "Binary/count/proportion or interaction state depends on receiver outcomes"
    if field in OUTCOMES or field == "Bout_ASO_other":
        return "OUTCOME", "Source-coded event/outcome; active receiver/window qualification is held"
    if field in {"Age", "Binary_ageclass", "Sex", "Rearing", "Age_victim", "Age_aggressor", "Binary_ageclass_victim", "Binary_ageclass_aggressor", "Sex_victim", "Sex_aggressor", "Rearing_victim", "Rearing_aggressor", "Ageclass", "Binary_AgeClass_Victim"}:
        return "BASELINE_STATIC", "Deposited demographic/static covariate; coding/reference-date linkage still requires review"
    if re.search(r"piloerect|audience|bystander|friend|dominant|kin_|aggression_severity|rankclass|aggression_cause|Video_dur", field, re.I):
        return "UNKNOWN_TIMING_HELD", "Measurement interval/origin or baseline ascertainment not source-certified"
    if re.search(r"signal|bout|gesture|vocal|facial|body|duration|time|Number\.|Binary\.[PAG]|Proportion\.|Prop[GPAVFB]|sum|paedomorphic|affiliative|aggressive|percentage", field, re.I):
        return "TIMING_DEPENDENT_REQUIRES_EVENT_ORDER", "Whole display/aggregate or signal interval must be ordered against an endpoint before eligibility"
    return "UNKNOWN_TIMING_HELD", "No source-supported baseline timing classification"


def validate_eligibility(entry):
    field, cls = entry["source_field"], entry["classification"]
    if cls not in CLASSES:
        raise ValueError("Unknown temporal classification")
    if field in DOWNSTREAM and cls != "POST_RECEIVER_DOWNSTREAM":
        raise ValueError("Persistence cannot be promoted out of the downstream class")
    if field in OUTCOME_DERIVED and cls != "DERIVED_FROM_OUTCOME":
        raise ValueError("Outcome-derived fields cannot become baseline")
    if field in OUTCOMES and cls != "OUTCOME":
        raise ValueError("Receiver fields must remain outcomes")
    if entry.get("baseline_eligible"):
        if cls not in {"BASELINE_STATIC", "BASELINE_PRE_SIGNAL", "SIGNAL_TIME_ELIGIBLE"}:
            raise ValueError("Forbidden class promoted to baseline")
        if entry.get("status") != "SOURCE_TIMING_ADMITTED" or not entry.get("endpoint_specific_timing_proof"):
            raise ValueError("Baseline eligibility requires explicit source/endpoint timing proof")


def code_crosswalk(raw):
    lines = raw.decode("utf-8-sig").splitlines()
    patterns = {
        "loading": r"read\.(table|csv|delim)", "joins": r"merge\(",
        "outcomes": r"Consolation\.01 <-|Reconciliation\.01 <-|Renewed_ag\.01 <-",
        "signal_counts": r"Number\.[PAG]|rowSums|aggregate\(Data.Display\$Number|Binary\.[PAG].*ifelse",
        "filters_and_exclusions": r"Analysis_level ==|excluded|two conflicts|less data points|na.omit|complete.cases|subset\(|filter\(|na.action",
        "persistence": r"DataASO|Bout_persistence|Consolation_afterbout|Reconciliation_afterbout",
        "duration_and_time": r"duration|Duration|timebase|timestamp",
        "audience_subset": r"Data_AudComp|two conflicts|model1\.5.*formula|model1\.6.*formula|less data points",
        "missingness_and_factor_coding": r"is.na|as.factor|factor\(.*levels|as.numeric|relevel|droplevel",
    }

    # These are source lines, including model declarations, never instructions
    # submitted to an R runtime. Unmatched constructs remain inspectable in
    # the pinned member rather than being interpreted as absent dependencies.
    patterns['dependencies_and_runtime_clues'] = r'library\(|require\(|R version|sessionInfo|R\.version'
    patterns['seeds_and_model_declarations'] = r'set.seed|family\s*=|chains\s*=|iter\s*=|warmup\s*='
    return {"member": "VictimSignalling_Publication.R", "sha256": digests(raw)["sha256"],
            "executed": False, "sections": {name: [{"line_start": i, "line_end": i, "source_text": line.strip()}
                                                    for i, line in enumerate(lines, 1) if re.search(pat, line)] for name, pat in patterns.items()},
            "absence_findings": {"six_exclusion_record_filter": "NOT_FOUND_IN_DEPOSITED_SCRIPT",
                                 "persistence_construction": "READS_PRECONSTRUCTED_TABLE; RAW_TO_PERSISTENCE_GENERATION_NOT_CODED",
                                 "raw_to_processed_generation": "NOT_CODED; INITIAL_INPUT_IS_ALREADY_PROCESSED",
                                 "explicit_audience_row_filter": "NOT_CODED; FORMULA_COMPLETENESS_IS_ARS_DESCRIPTIVE_RECONSTRUCTION",
                                 "factor_reference_levels": "as.factor lacks explicit reference levels in model paths; plot levels are explicitly coded"}}


def observational_level(name, sheet=None):
    if name == 'Signaltypes_classifier.xlsx' and sheet == 'Sheet1':
        return 'UNKNOWN_MULTILEVEL_WORKSHEET; NO_FLAT_OBSERVATION_SCHEMA_ADMITTED'
    if name in {"processed_dataset.txt", "data_victimsignalling.txt", "processed_dataset.xlsx"}:
        return "MIXED_CONFLICT_DISPLAY_AND_SIGNAL_BOUT"
    if name == "data_victimsignalling_BoutAso.txt":
        return "SIGNAL_BOUT_RECEIVER_DEPENDENT_PERSISTENCE"
    if name == "raw_data_signaltypes_below5min.xlsx":
        return "SPARSE_FILE_LOCAL_ANNOTATION_TIERS; COMPONENT_BOUT_DISPLAY_RECEIVER_AND_METADATA"
    if name == "demographic_info.txt":
        return "DEMOGRAPHIC_STATIC"
    if name.endswith((".R", ".Rproj")):
        return "STATIC_CODE_OR_PROJECT_CONFIGURATION"
    return "DERIVED_ANALYSIS_SUMMARY; NOT_INDEPENDENT_CONFLICT_ROWS"


def candidate_profiles(rows, headers):
    profiles = []
    for fields in (CONFLICT, BOUT, ['Individual'], ['Victim'], ['Victim', 'Binary.P'],
                   ['Victim', 'Signaltype'], ['Victim', 'Signaltype_kind'],
                   ['Victim', 'Consolation_received'], ['Victim', 'Reconciliation_received']):
        if set(fields) <= set(headers):
            selected = [r for r in rows if r.get('Analysis_level') == 'Bout'] if fields == BOUT else rows
            profiles.append(profile(selected, fields)[0])
    return profiles


def contract_crosswalk(snapshot):
    """Extend the already-pinned twenty fields; do not create a replacement contract."""
    evidence = {
        1: 'source_inventory', 2: 'display_conflict_profile; raw_relational_crosswalk',
        3: 'relational_crosswalk.display_to_main_bout', 4: 'demographic_links.Victim',
        5: 'demographic_links.Aggressor', 6: 'demographic_links; variable_eligibility',
        7: 'variable_eligibility', 8: 'cardinality_reconciliation.audience_missing_records; variable_eligibility',
        9: 'raw_relational_crosswalk.exact_interval_bout_tier_joins; variable_eligibility',
        10: 'temporal_coverage; raw_relational_crosswalk.exact_interval_bout_tier_joins',
        11: 'static_source_code.sections.signal_counts; variable_eligibility',
        12: 'cardinality_reconciliation; static_source_code.sections.persistence; variable_eligibility',
        13: 'variable_eligibility; raw_relational_crosswalk.raw_tiers',
        14: 'temporal_coverage; relational_crosswalk.main_bout_to_persistence',
        15: 'temporal_coverage; relational_crosswalk.main_bout_to_persistence',
        16: 'temporal_coverage; variable_eligibility',
        17: 'temporal_coverage; raw_relational_crosswalk',
        18: 'temporal_coverage.coverage; six_exclusions',
        19: 'active_source.item_licence_as_reported; active_source.file_licence_as_reported',
        20: 'active_source; source_inventory; provenance_corrections',
    }
    fields = snapshot['rdc006_field_assessment']
    if [x['field_id'] for x in fields] != [f'RDC-006-F{i:02}' for i in range(1, 21)]:
        raise ValueError('Existing RDC-006 field inventory drift')
    return [{**f, 'prior_source_history_disposition': f['bounded_disposition'],
             'review_status': 'V4_DESCRIPTIVE_REVIEW_COMPLETE_EMPIRICAL_ELIGIBILITY_HELD',
             'audit_evidence': evidence[i], 'empirical_admission_granted': False}
            for i, f in enumerate(fields, 1)]


def audit(snapshot, raw):
    archive, payloads = load_v4(snapshot, raw)
    tables, inventory, sheets_by_file = {}, [], {}
    for name, payload in sorted(payloads.items()):
        sha = digests(payload)["sha256"]
        pin = snapshot["member_content_inspections"].get(sha)
        member_pin = next(x for x in snapshot["archive_members"][str(ARCHIVE_ID)] if x["path"] == name)
        item = {"member": name, "sha256": sha, "md5": member_pin["md5"], "size": len(payload),
                "apparent_observational_level": observational_level(name), "tables": []}
        if name.endswith(".txt"):
            summary, rows = inspect_tsv(payload)
            if any(summary[k] != pin[k] for k in ("row_count", "column_count", "exact_headers")):
                raise ValueError(f"Frozen table schema drift: {name}")
            rows = [r | {"_source_row": i} for i, r in enumerate(rows, 2)]
            tables[name] = rows
            candidates = candidate_profiles(rows, summary['exact_headers'])
            item["tables"].append({"table": name, **summary, "candidate_key_profiles": candidates})
        elif name.endswith(".xlsx"):
            sheets = read_sheets(payload)
            sheets_by_file[name] = sheets
            for frozen in pin["sheets"]:
                sheet_name = frozen["sheet_name"]
                cells = sheets[sheet_name]["cells"]
                counted = len(cells)
                if counted != frozen["nonempty_stored_row_count_including_headers"]:
                    raise ValueError(f"Frozen worksheet row count drift: {name}/{sheet_name}")
                structure = frozen.get('table_structure')
                nominated = rows_from_sheet(sheets[sheet_name], frozen['header_candidate_row']) if structure else []
                item["tables"].append({"table": sheet_name, "apparent_observational_level": observational_level(name, sheet_name),
                                       "frozen_schema": frozen,
                                       'candidate_key_profiles': candidate_profiles(nominated, structure['exact_headers']) if structure and name != 'raw_data_signaltypes_below5min.xlsx' else [],
                                       'key_review_location': 'raw_relational_crosswalk' if name == 'raw_data_signaltypes_below5min.xlsx' else None,
                                       "formula_cells_not_executed": sheets[sheet_name]["formula_cells_not_executed"]})
        inventory.append(item)
    main, exported, persistence = (tables[n] for n in ("processed_dataset.txt", "data_victimsignalling.txt", "data_victimsignalling_BoutAso.txt"))
    displays = [r for r in main if r["Analysis_level"] == "Display"]
    bouts = [r for r in main if r["Analysis_level"] == "Bout"]
    display_profile, di = profile(displays, CONFLICT)
    if not display_profile["unique_complete"]:
        raise ValueError("Display conflict key ambiguous; no downstream joins permitted")
    main_persistence = join_diagnostics(bouts, persistence, BOUT,
                                        ["Victim", "Aggressor", "FileSource", "Bout_complexity", "Post_bout_event", "Bout_persistence", "Bout_modality", "Bout_direction", "Piloerection_bout"])
    conflict_joins = {
        "display_to_main_bout": join_diagnostics(displays, bouts, CONFLICT, ["Victim", "Aggressor", "FileSource"]),
        "display_to_persistence": join_diagnostics(displays, persistence, CONFLICT, ["Victim", "Aggressor", "FileSource"]),
        "main_bout_to_persistence": main_persistence,
        "processed_to_export_display": join_diagnostics(displays, [r for r in exported if r['Analysis_level'] == 'Display'], CONFLICT,
                                                       sorted(set(displays[0]) & set(exported[0]) - {'_source_row'})),
        "processed_to_export_bout": join_diagnostics(bouts, [r for r in exported if r['Analysis_level'] == 'Bout'], BOUT,
                                                    sorted(set(bouts[0]) & set(exported[0]) - {'_source_row'})),
    }
    workbook = rows_from_sheet(sheets_by_file['processed_dataset.xlsx']['processed_dataset'])
    conflict_joins['processed_txt_to_xlsx_display'] = join_diagnostics(displays, [r for r in workbook if r.get('Analysis_level') == 'Display'], CONFLICT,
                                                                     sorted(set(displays[0]) - {'_source_row'}))
    conflict_joins['processed_txt_to_xlsx_bout'] = join_diagnostics(bouts, [r for r in workbook if r.get('Analysis_level') == 'Bout'], BOUT,
                                                                  sorted(set(bouts[0]) - {'_source_row'}))
    raw_rows = rows_from_sheet(sheets_by_file['raw_data_signaltypes_below5min.xlsx']['raw_data_signaltypes'])
    raw_diagnostics, grouped = raw_structure(raw_rows, displays)
    candidates = raw_diagnostics['filename_candidate_crosswalk']['candidate_matches']
    candidate_by_conflict = {key(x['processed_conflict_key'], CONFLICT): x for x in candidates}
    unmatched = []
    for entry in main_persistence['right_unmatched']:
        for source_row in entry['source_rows']:
            p = next(r for r in persistence if locator(r) == source_row)
            candidate = candidate_by_conflict.get(key(p, CONFLICT))
            rb = [r for r in grouped.get(candidate['raw_file'], []) if r.get(RAW_BOUT)] if candidate else []
            index_matches = [r for r in rb if r[RAW_BOUT] == p['Bout_number']]
            unmatched.append({'source_row': source_row, 'source_key': {f: p[f] for f in BOUT + ['Victim', 'Aggressor', 'FileSource']},
                              'raw_candidate_file': candidate['raw_file'] if candidate else None,
                              'same_number_raw_candidates': [{'source_row': locator(r), 'begin_ms': interval(r)[0], 'end_ms': interval(r)[1]} for r in index_matches if interval(r)],
                              'classification': 'UNRESOLVED_SOURCE_DISCREPANCY; INDEX_CANDIDATE_IS_NOT_PROOF_OF_SAME_BOUT',
                              'source_exclusion_or_addition_logic': 'NOT_CODED'})
    duplicate_details = []
    _, pi = profile(persistence, BOUT)
    for k, rs in pi.items():
        if len(rs) <= 1:
            continue
        changed = [f for f in rs[0] if not f.startswith('_') and len({r[f] for r in rs}) > 1]
        candidate = candidate_by_conflict.get(k[:3])
        raw_bouts = [r for r in grouped.get(candidate['raw_file'], []) if r.get(RAW_BOUT)] if candidate else []
        duplicate_details.append({'source_key': key_record(k, BOUT), 'source_rows': [locator(r) for r in rs],
                                  'identical_on_named_fields': not changed, 'differing_fields': {f: [r[f] for r in rs] for f in changed},
                                  'timestamps_in_persistence_table': False,
                                  'raw_candidate_order': [{'index': r[RAW_BOUT], 'source_row': locator(r), 'begin_ms': interval(r)[0], 'end_ms': interval(r)[1]} for r in raw_bouts if interval(r)],
                                  'disposition': 'RETAIN_BOTH; CANDIDATE_KEY_INCOMPLETE_OR_SOURCE_CODING_DISCREPANCY_UNRESOLVED'})
    audience_fields = ['N_friends_within10m', 'N_dominants_within10m', 'Kin_within10m.01', 'Audience_0.10m',
                       'Binary_ageclass_victim', 'Aggression_severity', 'Piloerection_display', 'Victim', 'Aggressor']
    edisplay = [r for r in exported if r['Analysis_level'] == 'Display']
    audience_missing = [{'key': {f: r[f] for f in CONFLICT + ['Victim', 'Aggressor', 'FileSource']},
                         'export_source_row': locator(r), 'missing_fields': [f for f in audience_fields if r.get(f, '') in MISSING]}
                        for r in edisplay if any(r.get(f, '') in MISSING for f in audience_fields)]
    audience_predictors = [f for f in audience_fields if f != 'N_dominants_within10m']
    audience_models = {}
    for model, outcome, lines in [('model1.5', 'Total_signals', [625, 629]),
                                   ('model1.6', 'Display_duration.s.', [743, 747])]:
        fields = [outcome] + audience_predictors
        incomplete = [r for r in edisplay if any(r.get(f, '') in MISSING for f in fields)]
        audience_models[model] = {'source_formula_line_range': lines, 'required_formula_fields': fields,
                                 'descriptive_complete_row_count': len(edisplay) - len(incomplete),
                                 'incomplete_source_rows': [locator(r) for r in incomplete], 'model_executed': False}
    count_disagreements = []
    main_counts = Counter(key(r, CONFLICT) for r in bouts)
    persistence_counts = Counter(key(r, CONFLICT) for r in persistence)
    for d in displays:
        k = key(d, CONFLICT)
        candidate = candidate_by_conflict.get(k)
        rb_count = sum(bool(r.get(RAW_BOUT)) for r in grouped.get(candidate['raw_file'], [])) if candidate else None
        if len({int(d['Total_bouts']), main_counts[k], persistence_counts[k], rb_count}) > 1:
            count_disagreements.append({'key': key_record(k, CONFLICT), 'display_source_row': locator(d), 'display_Total_bouts': int(d['Total_bouts']),
                                       'main_bout_rows': main_counts[k], 'persistence_rows': persistence_counts[k], 'raw_candidate_bout_rows': rb_count,
                                       'candidate_raw_link_admissible': False})
    demography = tables['demographic_info.txt']
    demographic_profile, demo_index = profile(demography, ['Individual'])
    demographic_links = {f: {'source_identifier_count': len({r[f] for r in displays}),
                            'identifiers_missing_demographic_record': sorted({r[f] for r in displays} - {k[0] for k in demo_index})}
                         for f in ('Victim', 'Aggressor')}
    variables = []
    source_lines = payloads['VictimSignalling_Publication.R'].decode('utf-8-sig').splitlines()
    for file in inventory:
        for table in file['tables']:
            schema = table.get('frozen_schema', table)
            struct = schema.get('table_structure', schema)
            headers = struct.get('exact_headers', [])
            for field in headers:
                cls, rationale = classification(field)
                entry = {'source_table': file['member'] + (('/' + table['table']) if file['member'].endswith('.xlsx') else ''),
                         'source_field': field, 'observational_level': table.get('apparent_observational_level', file['apparent_observational_level']), 'classification': cls,
                         'timestamp_fields': TIME if file['member'] == 'raw_data_signaltypes_below5min.xlsx' else [],
                         'source_evidence': {'member_sha256': file['sha256'], 'exact_header': field,
                                             'code_crosswalk': 'static_source_code.sections; no raw-to-processed timing construction deposited',
                                             'field_reference_lines': [i for i, line in enumerate(source_lines, 1)
                                                                       if re.search(r'(?<![\w.])' + re.escape(field) + r'(?![\w.])', line)],
                                             'definition_status': 'EXACT_HEADER_AND_STATIC_REFERENCES; NO_INFERRED_EVENT_DEFINITION'},
                         'eligibility_rationale': rationale, 'status': 'SOURCE_SCHEMA_VERIFIED_ELIGIBILITY_HELD',
                         'baseline_eligible': False, 'endpoint_specific_timing_proof': None}
                validate_eligibility(entry)
                variables.append(entry)
    human_exclusions = []
    for file in raw_diagnostics['filename_candidate_crosswalk']['raw_files_without_processed_candidate']:
        rs = grouped[file]
        explicit = 'excluded as conflict was human related' in file
        human_exclusions.append({'raw_file': file, 'raw_source_key_as_reported': {f: sorted({r[f] for r in rs if r.get(f)}) for f in CONFLICT + ['Victim', 'Aggressor']},
                                 'source_rows': [locator(r) for r in rs if r.get('PC_ID') or r.get('Video_dur')],
                                 'source_authored_reason': 'HUMAN_RELATED_CONFLICT' if explicit else None,
                                 'reason_evidence': 'Exact deposited filename' if explicit else None,
                                 'affected_analysis': 'Absent from processed tables; exact exclusion procedure not deposited',
                                 'exclusion_decision_time_relative_to_receiver': 'UNKNOWN',
                                 'record_identification_method': 'ARS_FILENAME_CANDIDATE_ANTI_JOIN; DOES_NOT_REPLACE_NATIVE_KEYS'})
    blockers = [
        'PERSISTENCE_BOUT_KEYS_UNRECONCILED: 4 extra rows, one duplicate nonidentical key, one main key absent in persistence',
        f"MAIN_PERSISTENCE_FIELD_DISAGREEMENTS: {len(main_persistence['metadata_mismatches'])} matched row-pair discrepancies retained",
        'RAW_TO_PROCESSED_LINK_NOT_SOURCE_AUTHORED: renamed IDs, inconsistent individual codes and ambiguous metadata; filename anchors are ARS candidates',
        'RAW_BOUT_TIER_INTERVALS_NOT_IDENTICAL_ACROSS_TIERS; corrected source alignment not deposited',
        'CONFLICT_END_TIME_ORIGIN_AND_FULL_FIVE_MINUTE_OBSERVABILITY_NOT_VERIFIED',
        'SIX_EXCLUSIONS_NOT_RECONSTRUCTIBLE_FROM_DEPOSIT: one explicit filename reason; five record identities/reasons not exposed',
        'SIGNAL_COUNT_DURATION_PILOERECTION_AUDIENCE_BASELINE_ELIGIBILITY_REMAINS_TIMING_GATED',
    ]
    return {
        'dataset_id': 'D0029', 'contract_id': 'RDC-006', 'state': HELD, 'scope': 'V4_SOURCE_STRUCTURE_AND_ELIGIBILITY_ONLY',
        'source_audit_complete': True,
        'rdc006_field_crosswalk': contract_crosswalk(snapshot),
        'active_source': {'item_id': 16910173, 'version': 4, 'doi': '10.6084/m9.figshare.16910173.v4', 'file_id': ARCHIVE_ID,
                          'sha256': archive['sha256'], 'md5': archive['md5'], 'item_licence_as_reported': archive['associations'][0]['item_license_as_reported'],
                          'file_licence_as_reported': archive['file_license_as_reported'], 'source_snapshot_sha256': SNAPSHOT_SHA256},
        'source_inventory': inventory, 'relational_crosswalk': conflict_joins,
        'display_conflict_profile': display_profile, 'raw_relational_crosswalk': raw_diagnostics,
        'cardinality_reconciliation': {'display_rows': len(displays), 'unique_display_conflicts': len(di), 'main_bout_rows': len(bouts),
                                      'persistence_rows': len(persistence), 'unique_persistence_bout_keys': len(pi),
                                      'display_Total_bouts_sum': sum(int(r['Total_bouts']) for r in displays),
                                      'bout_count_disagreements': count_disagreements, 'unmatched_persistence_rows': unmatched,
                                      'duplicate_persistence_keys': duplicate_details,
                                      'audience_model_candidate_complete_rows': audience_models['model1.5']['descriptive_complete_row_count'],
                                      'audience_model_completeness': audience_models,
                                      'audience_missing_records': audience_missing, 'audience_subset_status': '142_FROM_DESCRIPTIVE_FORMULA_COMPLETENESS; TWO_MISSING_CONFLICTS_SOURCE_COMMENTED; NO_MODEL_EXECUTION'},
        'demographic_links': {'primary_key_profile': demographic_profile, **demographic_links},
        'six_exclusions': {'reported_coded_conflicts': 150, 'processed_analyzed_conflicts': 144,
                           'raw_named_files': len(grouped), 'source_keyed_candidates': human_exclusions,
                           'unlocated_excluded_record_count': 5, 'unlocated_record_keys': None,
                           'all_six_source_reproducible': False, 'invented_keys_or_reasons': False,
                           'source_vs_ARS_boundary': 'Filename reason is source-authored; candidate anti-join is ARS-derived; absent five identities cannot be inferred'},
        'temporal_coverage': temporal_coverage(raw_rows, grouped), 'variable_eligibility': variables,
        'static_source_code': code_crosswalk(payloads['VictimSignalling_Publication.R']),
        'provenance_corrections': {'R0011': {'role': 'HISTORICAL_INCOMPLETE_MANIFEST_OBSERVATION', 'history_mutated': False},
                                  'R0012': {'role': 'ACTIVE_SOURCE_LOCATION_CORRECTION', 'authority': 'USER_CANONICAL_HANDOFF; NO_REGISTRY_ROW_INVENTED'},
                                  'cause_of_prior_observation': 'OUT_OF_SCOPE_UNVERIFIED'},
        'admission': {'granted': False, 'blockers': blockers, 'machine_enforcement': 'No variable has baseline_eligible=true; validators reject downstream/outcome promotion'},
        'firewall': {'SEMANTIC_COMPOSITIONALITY': 'CONTESTED_UNRESOLVED', 'EMPIRICAL_CONFIRMATORY_RUN': 'NOT_STARTED',
                     'deposited_statistical_code_executed': False, 'inferential_models_executed': False, 'historical_analysis_bytes_used': False,
                     'chimpanzee_meaning_inheritance': False, 'unrelated_gates_changed': False, 'source_rows_exported_as_analysis_corpus': False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', default='contracts/d0029_version_history_source_snapshot.json')
    parser.add_argument('--archive', default='build/d0029_source_history/36230763/Data and R code.zip')
    parser.add_argument('--out', default='build/d0029_rdc006_crosswalk.json')
    args = parser.parse_args()
    try:
        snapshot_bytes = Path(args.snapshot).read_bytes()
        if hashlib.sha256(snapshot_bytes).hexdigest() != SNAPSHOT_SHA256:
            raise ValueError('Frozen e8d6fb8 source snapshot integrity mismatch')
        result = audit(json.loads(snapshot_bytes), Path(args.archive).read_bytes())
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, ET.ParseError) as error:
        result = {'dataset_id': 'D0029', 'state': HELD, 'source_audit_complete': False,
                  'error': str(error), 'admission': {'granted': False},
                  'firewall': {'EMPIRICAL_CONFIRMATORY_RUN': 'NOT_STARTED', 'deposited_statistical_code_executed': False}}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_private(out, result)
    print(json.dumps({'state': result['state'], 'admission': result['admission']['granted'], 'output': str(out)}))
    if result.get('source_audit_complete') is False:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
