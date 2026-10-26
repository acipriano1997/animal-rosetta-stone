"""Source-free leakage, biological-unit and exact-tail regression checks."""
from fractions import Fraction
import itertools
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replay_receiver_robustness as replay


def test_held_subject_outcomes_and_trial_repetition_cannot_affect_training():
    training = [("train-a", "silence", 0), ("train-b", "silence", 1),
                ("train-a", "unmanipulated_eel", 1)]
    p = replay.fit_held_out(training + [("held", "silence", 0)], "held", "M3", 0.5)
    changed = replay.fit_held_out(training + [("held", "silence", 1)] * 20, "held", "M3", 0.5)
    assert p == changed
    assert p["silence"] == 0.5
    assert p["unmanipulated_eel"] == 0.75
    with pytest.raises(ValueError, match="NO_TRAINING"):
        replay.fit_held_out([("held", "silence", 1)], "held", "M3", 0.5)


def test_model_groupings_and_training_smoothing_are_explicit():
    rows = [("a", "unmanipulated_eel", 1), ("b", "manipulated_eel", 0),
            ("held", "silence", 0)]
    m0 = replay.fit_held_out(rows, "held", "M0", 0.5)
    assert len(set(m0.values())) == 1
    assert replay.cell("unmanipulated_eel", "M1") == replay.cell("manipulated_eel", "M1")
    assert replay.cell("unmanipulated_eel", "M2") != replay.cell("manipulated_eel", "M2")
    for alpha in (0, -1, float("nan")):
        with pytest.raises(ValueError, match="SMOOTHING"):
            replay.fit_held_out(rows, "held", "M0", alpha)


def test_loss_mean_weights_fish_equally_despite_unequal_trial_counts():
    rows = [("a", "silence", 0)] * 8 + [("b", "silence", 1)] * 2
    result = replay.held_out_scores(rows, 0.5)
    # A is predicted from two successes; B from eight failures. Hand calculation
    # averages the two fish losses rather than ten correlated trial losses.
    expected = (-math.log(1 - 2.5 / 3) - math.log(0.5 / 9)) / 2
    assert result["models"]["M0"]["log_loss"] == pytest.approx(expected)
    assert result["loss_aggregation"] == "EQUAL_MEAN_OVER_BIOLOGICAL_FISH"


def test_rational_sign_flip_tail_matches_exhaustive_independent_enumeration():
    differences = [Fraction("0.1"), Fraction("0.2"), Fraction("-0.3")]
    observed = abs(sum(differences))
    sums = [sum(s * d for s, d in zip(signs, differences))
            for signs in itertools.product((-1, 1), repeat=3)]
    result = replay.paired_statistics(differences)
    assert result["exact_sign_flip_exceedances"] == sum(abs(s) >= observed for s in sums) == 8
    assert replay.sign_test([Fraction(0), Fraction(1), Fraction(-1)])["ties"] == 1
    assert replay.sign_test([Fraction(0)])["two_sided_sign_p"] == 1
    with pytest.raises(ValueError, match="BOUNDED"):
        replay.paired_statistics([Fraction(1)] * 21)


def test_missing_response_is_never_recoded_as_zero_and_pairs_never_multiplied():
    missing = b"individual_id,playback_type,switch_off_response,switch_off_duration (s),switch_off_playback_amplitude\n1,silence,unknown,NA,NA\n"
    with pytest.raises(ValueError, match="CATEGORY"):
        replay.playback_analysis(missing)
    duplicate = b"trial_id,total_time_min,treatment\n1,2,control\n1,3,control\n"
    with pytest.raises(ValueError, match="DUPLICATE"):
        replay.spider_analysis(duplicate)
    with pytest.raises(ValueError, match="HEADER"):
        replay.playback_analysis(b"subject,response\n1,yes\n")
