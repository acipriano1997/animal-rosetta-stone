#!/usr/bin/env python3
"""Reproduce the October 23/25 retrospective D0037/D0043 diagnostics.

Exact archived bytes only. Source-native fish and paired trials stay separate;
no pooled cross-taxon estimand, population CI, semantic claim or authority edit.
No dependencies beyond Python's standard library. No source rows are emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
from fractions import Fraction
import hashlib
from io import StringIO
import json
import math
from pathlib import Path
import statistics

from audit_d0037_playback_csv import PLAYBACKS, REQUIRED
from research_integrity import fingerprint, write_private

EXPECTED = {
    "playback": (17143, "de4df63f99ae29dd9821df3e7a15b7c97ab555e3b712971e29b676b9cf9a2451"),
    "spider": (774, "0f63efedad824c58c2e3645f09067d01dc07b3eb28be0668fdb83adfa1d702ab"),
}
LAYOUT = ["silence", "unmanipulated_eel", "manipulated_eel", "b_brev_super",
          "b_brev_natural", "g_ron_super", "g_ron_natural"]


def source(path: Path, role: str) -> bytes:
    size, sha = EXPECTED[role]
    if fingerprint(path) != {"size_bytes": size, "sha256": sha}:
        raise ValueError("ARCHIVED_SOURCE_FINGERPRINT_MISMATCH:" + role)
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise ValueError("SOURCE_CHANGED_BEFORE_PARSE")
    return data


def read_csv(data: bytes, columns: tuple[str, ...]) -> list[dict]:
    reader = csv.DictReader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    if reader.fieldnames != list(columns):
        raise ValueError("SOURCE_HEADER_CHANGED")
    rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("MALFORMED_ROW")
    return rows


def cell(playback: str, model: str) -> str:
    if playback not in PLAYBACKS:
        raise ValueError("UNKNOWN_PLAYBACK")
    if model == "M0":
        return "all"
    if model == "M1":
        return "eel" if playback in {"unmanipulated_eel", "manipulated_eel"} else "other"
    if model == "M2":
        return playback if playback in {"unmanipulated_eel", "manipulated_eel"} else "other"
    if model == "M3":
        return playback
    raise ValueError("UNKNOWN_MODEL")


def fit_held_out(rows: list[tuple[str, str, int]], held: str, model: str, alpha: float) -> dict[str, float]:
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("POSITIVE_SMOOTHING_REQUIRED")
    counts, successes = Counter(), Counter()
    for who, playback, y in rows:
        if who == held:
            continue
        if y not in (0, 1):
            raise ValueError("NON_BINARY_RESPONSE")
        group = cell(playback, model)
        counts[group] += 1
        successes[group] += y
    if not counts:
        raise ValueError("NO_TRAINING_SUBJECT")
    return {t: (successes[cell(t, model)] + alpha) / (counts[cell(t, model)] + 2 * alpha)
            for t in PLAYBACKS}


def held_out_scores(rows: list[tuple[str, str, int]], alpha: float) -> dict:
    subjects = sorted({r[0] for r in rows})
    if len(subjects) < 2:
        raise ValueError("INSUFFICIENT_SUBJECTS")
    losses = defaultdict(list)
    for who in subjects:
        test = [(t, y) for subject, t, y in rows if subject == who]
        for model in ("M0", "M1", "M2", "M3"):
            probabilities = fit_held_out(rows, who, model, alpha)
            ll = statistics.mean(-math.log(probabilities[t]) if y else -math.log1p(-probabilities[t]) for t, y in test)
            brier = statistics.mean((probabilities[t] - y) ** 2 for t, y in test)
            losses[model].append((ll, brier))
    differences = [b[0] - m[0] for b, m in zip(losses["M0"], losses["M2"], strict=True)]
    leave_one_evaluation_out = [statistics.mean(d for j, d in enumerate(differences) if j != i)
                                for i in range(len(subjects))]
    return {"alpha_per_binary_outcome": alpha, "held_out_subjects": len(subjects),
            "loss_aggregation": "EQUAL_MEAN_OVER_BIOLOGICAL_FISH",
            "models": {m: {"log_loss": statistics.mean(x[0] for x in values),
                            "brier_loss": statistics.mean(x[1] for x in values)} for m, values in losses.items()},
            "M2_vs_M0_fish_improved_log_loss": sum(d > 0 for d in differences),
            "M2_vs_M0_fish_worse_log_loss": sum(d < 0 for d in differences),
            "M2_vs_M0_mean_log_loss_improvement": statistics.mean(differences),
            "leave_one_evaluation_fish_out_improvement_range": [min(leave_one_evaluation_out), max(leave_one_evaluation_out)],
            "interval_or_confirmatory_pvalue": "NOT_ASSERTED_FOLD_OVERLAP_POSTHOC_SELECTION_AND_SITE_DEPENDENCE"}


def sign_test(differences: list[Fraction]) -> dict:
    positive = sum(d > 0 for d in differences)
    negative = sum(d < 0 for d in differences)
    n = positive + negative  # Ties excluded explicitly, never counted negative.
    numerator = min(2 ** n, 2 * sum(math.comb(n, k) for k in range(min(positive, negative) + 1)))
    return {"positive": positive, "negative": negative, "ties": len(differences) - n,
            "two_sided_sign_p": numerator / 2 ** n,
            "assumptions": "INDEPENDENT_UNITS_EQUIPROBABLE_NONZERO_SIGNS_NOT_VALIDATED_HERE"}


def paired_statistics(differences: list[Fraction]) -> dict:
    if not 2 <= len(differences) <= 20:
        raise ValueError("PAIR_COUNT_OUTSIDE_BOUNDED_ENUMERATION")
    scale = math.lcm(*(d.denominator for d in differences))
    integer_diffs = [int(d * scale) for d in differences]
    null_sums = [0]
    for d in integer_diffs:
        null_sums = [s + d for s in null_sums] + [s - d for s in null_sums]
    observed = abs(sum(integer_diffs))
    exceedances = sum(abs(s) >= observed for s in null_sums)
    values = [float(d) for d in differences]
    sd = statistics.stdev(values)
    return {"pairs": len(values), "mean_female_minus_control_minutes": statistics.mean(values),
            "paired_t": statistics.mean(values) / (sd / math.sqrt(len(values))) if sd else None,
            "exact_sign_flip_exceedances": exceedances, "exact_sign_flip_assignments": len(null_sums),
            "exact_two_sided_sign_flip_p": exceedances / len(null_sums),
            "sign_flip_comparison": "EXACT_RATIONAL_SOURCE_DECIMALS_NO_FLOAT_TIE_TOLERANCE",
            "sign_flip_assumptions": "SIGN_EXCHANGEABILITY_AND_APPROPRIATE_UNIT_INDEPENDENCE_NOT_VALIDATED_HERE",
            **sign_test(differences)}


def playback_analysis(data: bytes) -> dict:
    raw = read_csv(data, REQUIRED)
    triples, ordered, successes, cells = [], defaultdict(list), defaultdict(Counter), Counter()
    for r in raw:
        who, t, token = r["individual_id"], r["playback_type"], r["switch_off_response"]
        if who not in {str(i) for i in range(1, 14)} or t not in PLAYBACKS or token.strip() not in {"yes", "no"}:
            raise ValueError("UNEXPECTED_PLAYBACK_CATEGORY")
        y = int(token.strip() == "yes")
        if not y and (r[REQUIRED[3]] != "NA" or r[REQUIRED[4]] != "NA"):
            raise ValueError("NO_RESPONSE_MISSINGNESS_CHANGED")
        triples.append((who, t, y))
        ordered[who].append(t)
        successes[who][t] += y
        cells[(who, t)] += 1
    if len(raw) != 637 or len(cells) != 91 or set(cells.values()) != {7}:
        raise ValueError("REPEATED_MEASURES_GRAIN_CHANGED")
    differences = [Fraction(s["unmanipulated_eel"] - s["manipulated_eel"], 7) for s in successes.values()]
    return {"rows": len(raw), "biological_fish": len(ordered),
            "yes_by_condition": {t: sum(v[t] for v in successes.values()) for t in sorted(PLAYBACKS)},
            "raw_response_tokens": dict(Counter(r["switch_off_response"] for r in raw)),
            "paired_condition_contrast": {"mean_unmanipulated_minus_manipulated_probability": float(statistics.mean(differences)), **sign_test(differences)},
            "jeffreys": held_out_scores(triples, 0.5), "laplace": held_out_scores(triples, 1.0),
            "fish_with_seven_repeated_layout_blocks": sum(order == LAYOUT * 7 for order in ordered.values()),
            "layout_is_actual_presentation_order": "UNKNOWN_NOT_A_PREDICTOR",
            "absent_nuisance_fields": ["actual_trial_order", "session_id", "timestamps", "pre_stimulus_state", "delivered_waveform_calibration"],
            "limits": "Retrospective post-data model comparison; overlapping training folds, common site and physical/order confounds remain. No population transfer or semantic decoding."}


def spider_analysis(data: bytes) -> dict:
    rows = read_csv(data, ("trial_id", "total_time_min", "treatment"))
    pairs = defaultdict(dict)
    for row in rows:
        key, condition = row["trial_id"], row["treatment"]
        if not key.isdigit() or condition not in {"female", "control"} or condition in pairs[key]:
            raise ValueError("DUPLICATE_OR_INVALID_PAIR")
        value = Decimal(row["total_time_min"])
        if not value.is_finite() or value < 0:
            raise ValueError("INVALID_CONTACT_TIME")
        pairs[key][condition] = Fraction(value)
    if len(rows) != 36 or len(pairs) != 18 or any(set(p) != {"female", "control"} for p in pairs.values()):
        raise ValueError("PAIRED_TRIAL_GRAIN_CHANGED")
    differences = {key: p["female"] - p["control"] for key, p in pairs.items()}
    exceptions = {key for key, p in pairs.items() if sum(p.values()) > 30}
    return {"rows": len(rows), "complete": paired_statistics(list(differences.values())),
            "nominal_30_minute_budget_exception_count": len(exceptions),
            "exception_total_minutes": sorted(float(sum(pairs[k].values())) for k in exceptions),
            "excluding_time_budget_exceptions_posthoc": paired_statistics([d for k, d in differences.items() if k not in exceptions]),
            "measurement_status": "R0015_OPEN_TIME_BUDGET_SEMANTICS",
            "limits": "Source pair IDs preserved; repeated female donor identities absent. Sign-flip/sign tests are exploratory conditional diagnostics, not independent donor replication, mechanism isolation or semantic evidence."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("playback", "spider", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = {"method": "ARS-RETROSPECTIVE-RECEIVER-REPLAY-v1", "status": "EXECUTED_EXPLORATORY_REPLAY",
                  "source_identity": "MATCH_FROZEN_ARCHIVE_PROVIDER_VERIFICATION_REMAINS_CANONICAL_ACEB",
                  "fingerprints": {role: {"size_bytes": v[0], "sha256": v[1]} for role, v in EXPECTED.items()},
                  "q0031": "NOT_MET", "scientific_promotion": "NONE", "confirmatory": False,
                  "D0037": playback_analysis(source(args.playback, "playback")),
                  "D0043": spider_analysis(source(args.spider, "spider"))}
        write_private(args.out, report)
        print(json.dumps({"status": report["status"], "report": str(args.out)}))
        return 0
    except (OSError, ValueError, csv.Error, ArithmeticError) as error:
        print(json.dumps({"status": "HELD", "error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
