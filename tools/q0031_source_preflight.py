#!/usr/bin/env python3
"""ARS Q0031 read-only source-looking CSV preflight (NOT provider attestation).

Standard library only. Hashes full bytes, checks preserved source grain and
high-risk missingness/encoding assumptions. Emits aggregate JSON, never rows.
All three files are founder-uploaded candidate copies and remain HELD until
independent Dryad-v3/v12 file-specific immutable checksum matching.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

class QAError(ValueError):
    pass

def check(test, why):
    if not test:
        raise QAError(why)

def num(s, name):
    try:
        n = Decimal(s)
        check(n.is_finite(), f"nonfinite {name}")
        return n
    except (InvalidOperation, TypeError):
        raise QAError(f"invalid numeric value for {name}") from None

EXPECTED = {
    "spider": (774, "0f63efedad824c58c2e3645f09067d01dc07b3eb28be0668fdb83adfa1d702ab"),
    "spectra": (183204, "99e91dea80aa0cddcd773d570117f7b5df93333a8d69ac19bbab5f055e387b7f"),
    "playback": (17143, "de4df63f99ae29dd9821df3e7a15b7c97ab555e3b712971e29b676b9cf9a2451"),
}
SPIDER_COLS = ["trial_id", "total_time_min", "treatment"]
PLAYBACK_COLS = ["individual_id", "playback_type", "switch_off_response", "switch_off_duration (s)", "switch_off_playback_amplitude"]
PSD_COLS = ["frequency (Hz)", "manipulated_eel_power(dB)", "unmanipulated_eel_power (dB)", "super_b_brevirostris_power (dB)", "super_g_rondoni_power (dB)", "natural_b_brevirostris_power (dB)", "natural_g_rondoni_power (dB)"]
TYPES = ["unmanipulated_eel", "manipulated_eel", "b_brev_super", "b_brev_natural", "g_ron_super", "g_ron_natural", "silence"]

def read_rows(data, cols):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    check(reader.fieldnames == cols, "source header differs from frozen expected schema")
    rows = list(reader)
    check(not any(None in r or any(v is None for v in r.values()) for r in rows), "malformed CSV row")
    return rows

def spider(data):
    rows = read_rows(data, SPIDER_COLS)
    counts, pairs = Counter(), defaultdict(dict)
    for r in rows:
        trial = r["trial_id"]
        t = r["treatment"]
        check(trial.isdigit() and t in {"control", "female"}, "invalid trial/treatment code")
        check(t not in pairs[trial], "duplicated trial x treatment")
        time = num(r["total_time_min"], "total_time_min")
        check(time >= 0, "negative duration")
        pairs[trial][t] = time
        counts[t] += 1
    check(len(rows) == 36 and len(pairs) == 18, "incorrect raw records or paired grain")
    check(all(set(p) == {"control", "female"} for p in pairs.values()), "unpaired trial")
    check(counts == {"control": 18, "female": 18}, "incorrect treatment balance")
    check(set(pairs) == {str(i) for i in range(1, 21) if i not in (14, 19)}, "unexpected trial identifiers")
    diffs = [p["female"] - p["control"] for p in pairs.values()]
    return {"rows": len(rows), "paired_trial_ids": len(pairs), "treatment_rows": dict(counts),
            "unobserved_id_keys_not_exclusions": [14, 19], "female_longer_pairs": sum(d > 0 for d in diffs)}

def playback(data):
    rows = read_rows(data, PLAYBACK_COLS)
    raw_response, cells = Counter(), Counter()
    yes_by_type, yes_by_fish = Counter(), defaultdict(Counter)
    switch_duration_above_30 = 0
    for r in rows:
        fish, t, raw = r["individual_id"], r["playback_type"], r["switch_off_response"]
        check(fish.isdigit() and 1 <= int(fish) <= 13 and t in TYPES, "invalid fish or playback code")
        raw_response[raw] += 1
        val = raw.strip()
        check(val in {"yes", "no"}, "unexpected response token after declared whitespace normalization")
        cells[(fish, t)] += 1
        duration, amp = r["switch_off_duration (s)"], r["switch_off_playback_amplitude"]
        if val == "yes":
            d, a = num(duration, "conditional duration"), num(amp, "normalized amplitude")
            check(d >= 0 and Decimal(0) <= a <= Decimal(1), "invalid conditional measurement")
            yes_by_type[t] += 1
            yes_by_fish[fish][t] += 1
            switch_duration_above_30 += int(d > 30)
        else:
            check(duration == "NA" and amp == "NA", "no response may not be silently converted into numeric zero")
    check(len(rows) == 637 and len(cells) == 13 * 7 and all(n == 7 for n in cells.values()), "lost or multiplied within-fish playback trials")
    check(raw_response == {"no": 547, "yes": 89, "yes ": 1}, "raw response-code inventory differs")
    check(sum(yes_by_type.values()) == 90 and switch_duration_above_30 == 22, "unexpected response/timing aggregate")
    check(all(yes_by_fish[str(f)]["unmanipulated_eel"] > yes_by_fish[str(f)]["manipulated_eel"] for f in range(1, 14)), "within-fish descriptive direction changed")
    return {"rows": len(rows), "distinct_fish": 13, "playback_types": len(TYPES), "trials_per_fish_type": 7,
            "raw_response_count": dict(raw_response), "whitespace_normalization": "strip only on derived yes/no category; source preserved",
            "derived_yes_count": 90, "derived_no_count": 547, "yes_by_playback_type": dict(yes_by_type),
            "yes_switch_off_durations_over_30_seconds": switch_duration_above_30,
            "timing_caveat": "30 seconds describes source playback amplitude ramp, not maximum response duration"}

def spectra(data):
    rows = read_rows(data, PSD_COLS)
    freqs = [num(r[PSD_COLS[0]], "frequency") for r in rows]
    check(len(freqs) == 2041 and freqs[0] == 0, "unexpected PSD record count or frequency origin")
    steps = [b-a for a, b in zip(freqs, freqs[1:])]
    check(all(d > 0 for d in steps), "frequency not strictly increasing")
    check(len(set(steps)) > 1, "unexpected uniform frequency-grid assumption")
    max_gap = max(steps)
    check(max_gap == Decimal("111.328125"), "frequency gap no longer matches audit")
    for r in rows:
        for c in PSD_COLS[1:]:
            num(r[c], c)
    return {"frequency_rows": len(rows), "spectral_columns": 6, "min_hz": str(freqs[0]),
            "max_hz": str(freqs[-1]), "unique_freq_steps": len(set(steps)), "max_hz_gap": str(max_gap),
            "nonuniform_grid": "YES, reject uniform-bin integration",
            "script_6_PSD_R_direct_generator": "NOT_ESTABLISHED; default sample rate, FFT length and column shape differ"}

def source_bytes(path, key):
    data = Path(path).read_bytes()
    size, expected_sha = EXPECTED[key]
    sha = hashlib.sha256(data).hexdigest()
    check(len(data) == size and sha == expected_sha,
          f"{key} private archived copy no longer matches frozen founder-upload fingerprint")
    return data, {"size_bytes": len(data), "sha256": sha, "fingerprint_status": "MATCH_LOCAL_FOUNDER_UPLOAD_NOT_PROVIDER"}

def selftest():
    small = b"trial_id,total_time_min,treatment\n1,1,control\n1,2,female\n"
    check(len(read_rows(small, SPIDER_COLS)) == 2, "synthetic valid header failed")
    try:
        read_rows(b"x,y\n1,2\n", SPIDER_COLS)
    except QAError:
        pass
    else:
        raise QAError("synthetic bad header unexpectedly passed")
    try:
        spider(b"trial_id,total_time_min,treatment\n1,1,control\n1,2,control\n")
    except QAError as e:
        check("duplicated" in str(e), "synthetic repeated treatment unexpectedly admitted")
    else:
        raise QAError("synthetic duplicate unexpectedly passed")
    try:
        read_rows(b"individual_id,playback_type,switch_off_response\n1,silence,no\n", PLAYBACK_COLS)
    except QAError:
        pass
    else:
        raise QAError("synthetic stripped playback columns unexpectedly passed")
    return "PASS: bad header, duplicated paired-trial treatment, stripped playback schema rejected"

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spider", required=True)
    ap.add_argument("--spectra", required=True)
    ap.add_argument("--playback", required=True)
    ap.add_argument("--output", help="aggregate JSON manifest path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    report = {"project": "Animal Rosetta Stone",
              "scope": "frozen founder-uploaded source-looking bytes only; NOT source-authoritative Dryad verification",
              "version": "Q0031-source-preflight-v0.1",
              "provider_file_digest_status": "HELD_NOT_OBTAINED",
              "q0031_cross_modal_generalization": "NOT_MET",
              "no_scientific_or_gdm_admission": True}
    for key, path, fn in (("spider", args.spider, spider),
                          ("spectra", args.spectra, spectra),
                          ("playback", args.playback, playback)):
        data, fingerprint = source_bytes(path, key)
        report[key] = {**fingerprint, **fn(data)}
    if args.self_test:
        report["synthetic_pipeline_sanity"] = selftest()
    encoded = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        try:
            # Create reports exclusively; never overwrite any existing file,
            # including input source paths or symlink/hardlink aliases.
            with Path(args.output).open("x", encoding="utf-8") as out:
                out.write(encoded + "\n")
        except FileExistsError:
            raise QAError("report output already exists; refusing to overwrite any file") from None
    print(encoded)

if __name__ == "__main__":
    try:
        main()
    except (QAError, UnicodeError, ValueError) as e:
        raise SystemExit(f"SOURCE PREFLIGHT HELD/FAILED: {e}") from None
