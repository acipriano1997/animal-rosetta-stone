"""Fail-closed D0037 Dryad playback trial intake, without raw-row publication.

Publication schema only. Never asserts that a user-supplied file is Dryad's
original unless an *independently sourced* provider SHA-256 is supplied and
matches. No GDM/ACEB writes or biological claim promotion.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path

DOI = "10.5061/dryad.1ns1rn95w"
VERSION_ID = 429568
FILE_ID = 4640875
FILENAME = "dataset_8_lab_g_rondoni_playback_experiment.csv"
PLAYBACKS = frozenset({"unmanipulated_eel", "manipulated_eel", "b_brev_super", "b_brev_natural", "g_ron_super", "g_ron_natural", "silence"})
REQUIRED = ("individual_id", "playback_type", "switch_off_response", "switch_off_duration (s)", "switch_off_playback_amplitude")
BLANKS = {"", "NA", "N/A", "NULL"}


def _optional_number(value: str, row_index: int, name: str, failures: list[str]) -> float | None:
    if value.strip().upper() in BLANKS:
        return None
    try:
        number = float(value.strip())
    except ValueError:
        failures.append(f"source line {row_index}: nonnumeric {name}")
        return None
    if not (number >= 0 and number < float("inf")):
        failures.append(f"source line {row_index}: negative or nonfinite {name}")
        return None
    return number


def audit_playback_csv(path: Path, *, provider_sha256: str | None = None) -> dict:
    receipt: dict = {
        "dataset_id": "D0037", "source_doi": DOI, "dryad_version_id": VERSION_ID,
        "provider_file_id": FILE_ID, "target_filename": FILENAME,
        "source_channel": "EXTERNAL_FILE_INPUT_NOT_PROVIDER_ATTESTED",
        "source_rows_inspected": False, "provider_byte_identity_verified": False,
        "admission_ready": False, "generalization_gate": "NOT_MET",
        "scientific_effect": "NONE", "failures": [], "warnings": [],
    }
    failures: list[str] = receipt["failures"]
    warnings: list[str] = receipt["warnings"]
    if not path.is_file():
        failures.append("file not found; no source bytes available")
        receipt["state"] = "HELD_NO_SOURCE_BYTES"
        return receipt
    data = path.read_bytes()
    receipt["local_filename"] = path.name
    receipt["size_bytes"] = len(data)
    receipt["local_sha256"] = hashlib.sha256(data).hexdigest()
    if len(data) == 0 or len(data) > 1024 * 1024:
        failures.append("empty or unexpectedly large candidate for the ~17 KB published target")
    if path.name != FILENAME:
        warnings.append("local name differs from provider filename; do not infer identity")
    if provider_sha256 is None:
        warnings.append("provider SHA-256 not independently supplied; file identity held")
    elif (len(provider_sha256) != 64 or any(x not in "0123456789abcdefABCDEF" for x in provider_sha256)):
        failures.append("invalid provider SHA-256 input")
    elif receipt["local_sha256"] != provider_sha256.lower():
        failures.append("provider SHA-256 mismatch")
    else:
        receipt["provider_byte_identity_verified"] = True
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        failures.append("file is not UTF-8")
        receipt["state"] = "HELD_FORMAT_OR_SCHEMA"
        return receipt
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error):
        failures.append("CSV has no readable header")
        receipt["state"] = "HELD_FORMAT_OR_SCHEMA"
        return receipt
    if len(header) != len(set(header)):
        failures.append("duplicate CSV header names")
    missing = [name for name in REQUIRED if name not in header]
    if missing:
        failures.append("missing published schema fields: " + ", ".join(missing))
        receipt["state"] = "HELD_FORMAT_OR_SCHEMA"
        return receipt
    extra = [name for name in header if name not in REQUIRED]
    receipt["header"] = header
    if extra:
        warnings.append("unexpected additional columns: " + ", ".join(extra))
    treatment_count = collections.Counter()
    subject_count = collections.Counter()
    outcome_count = collections.Counter()
    conditional_missing = collections.Counter()
    exact_rows = set()
    duplicate_count = 0
    n = 0
    try:
        for source_line, values in enumerate(reader, start=2):
            if not values or all(not v.strip() for v in values):
                failures.append(f"source line {source_line}: empty data record")
                continue
            if len(values) != len(header):
                failures.append(f"source line {source_line}: {len(values)} cells, expected {len(header)}")
                continue
            n += 1
            row = dict(zip(header, values))
            key = tuple(values)
            if key in exact_rows:
                duplicate_count += 1
            exact_rows.add(key)
            who = row["individual_id"].strip()
            try:
                subject = int(who)
                if str(subject) != who or not 1 <= subject <= 13:
                    raise ValueError()
                subject_count[who] += 1
            except ValueError:
                failures.append(f"source line {source_line}: individual_id outside published 1-13 codebook")
            playback = row["playback_type"].strip()
            if playback not in PLAYBACKS:
                failures.append(f"source line {source_line}: unrecognized playback type")
            treatment_count[playback] += 1
            outcome = row["switch_off_response"].strip().lower()
            if outcome not in {"yes", "no"}:
                failures.append(f"source line {source_line}: response not yes/no")
            outcome_count[outcome] += 1
            duration = _optional_number(row["switch_off_duration (s)"], source_line, "duration", failures)
            amplitude = _optional_number(row["switch_off_playback_amplitude"], source_line, "amplitude", failures)
            if amplitude is not None and amplitude > 1:
                failures.append(f"source line {source_line}: normalized amplitude > 1")
            if outcome == "no":
                if duration is not None or amplitude is not None:
                    failures.append(f"source line {source_line}: switch-off conditional measure present for no response")
                conditional_missing["no_response_duration_not_applicable"] += 1
                conditional_missing["no_response_amplitude_not_applicable"] += 1
            elif outcome == "yes":
                if duration is None:
                    conditional_missing["yes_response_duration_absent_review"] += 1
                if amplitude is None:
                    conditional_missing["yes_response_amplitude_absent_review"] += 1
    except csv.Error:
        failures.append("malformed CSV quoting/row structure")
    receipt.update({
        "source_rows_inspected": n > 0,
        "observed_trial_rows": n,
        "observed_individual_count": len(subject_count),
        "observed_individual_trial_counts": dict(sorted(subject_count.items(), key=lambda p:int(p[0]))),
        "observed_playback_counts": dict(sorted(treatment_count.items())),
        "observed_response_counts": dict(sorted(outcome_count.items())),
        "conditional_measure_status_counts": dict(sorted(conditional_missing.items())),
        "identical_source_row_count": duplicate_count,
    })
    if duplicate_count:
        warnings.append("identical data rows detected; trial lacks a unique provided trial ID; no automatic deduplication")
    if conditional_missing.get("yes_response_duration_absent_review") or conditional_missing.get("yes_response_amplitude_absent_review"):
        warnings.append("positive-response conditional measure(s) missing; distinguish missing from zero")
    if n == 0:
        failures.append("no data records")
    if failures:
        receipt["state"] = "HELD_ROW_SCHEMA_OR_INTEGRITY"
    elif not receipt["provider_byte_identity_verified"]:
        receipt["state"] = "USER_SOURCE_ROWS_PARSED_PROVIDER_IDENTITY_HELD"
    else:
        receipt["state"] = "PROVIDER_HASH_MATCH_AND_ROW_SCHEMA_PASS_ADMISSION_NOT_AUTOMATIC"
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser(description="Source-private, fail-closed D0037 Dryad playback CSV audit")
    ap.add_argument("csv", type=Path, help="Original unmodified Dryad dataset 8 CSV")
    ap.add_argument("--provider-sha256", help="Independent authoritative file checksum; never synthesize")
    ap.add_argument("--out", type=Path, default=Path("build/d0037_playback_receipt.json"))
    args = ap.parse_args()
    receipt = audit_playback_csv(args.csv, provider_sha256=args.provider_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("dataset_id", "state", "source_rows_inspected", "provider_byte_identity_verified", "admission_ready", "scientific_effect")}, sort_keys=True))
    raise SystemExit(0 if not receipt["failures"] else 2)


if __name__ == "__main__":
    main()
