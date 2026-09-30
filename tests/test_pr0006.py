import numpy as np
import pandas as pd
import pytest

from ars_receiver_harness.pr0006 import PR0006Config, run_pr0006


def make_data(n=900, seed=7, effect=1.25):
    rng = np.random.default_rng(seed)
    signallers = np.array([f"S{i:02d}" for i in range(12)])
    recipients = np.array([f"R{i:02d}" for i in range(18)])
    s = rng.choice(signallers, size=n)
    r = rng.choice(recipients, size=n)
    dyad = np.char.add(np.char.add(s, "__"), r)
    modality = rng.choice(["gesture", "vocalization", "bimodal"], p=[0.64, 0.16, 0.20], size=n)
    bond = rng.normal(size=n)
    related = rng.choice(["kin", "nonkin"], size=n, p=[0.18, 0.82])
    mod_term = np.where(modality == "gesture", effect, np.where(modality == "bimodal", effect * 0.35, -effect))
    logit = -0.1 + 0.45 * bond + 0.25 * (related == "kin") + mod_term
    p = 1 / (1 + np.exp(-logit))
    y = np.where(rng.random(n) < p, "approach", "avoidance")
    return pd.DataFrame({
        "Recipient_Response": y,
        "Communication_Type": modality,
        "Dyad_ID": dyad,
        "Signaller_ID": s,
        "Social_Bond": bond,
        "Relatedness": related,
    })


def cfg():
    return PR0006Config(
        baseline_numeric=("Social_Bond",),
        baseline_categorical=("Relatedness",),
        bootstrap_resamples=300,
        sanity_permutations=30,
        seed=20260929,
    )


def test_strong_modality_signal_is_bounded_or_mixed_but_not_null():
    result = run_pr0006(make_data(effect=1.5), cfg())
    assert result.primary_fold_support_passed
    assert result.sanity_passed
    assert result.mean_delta_log_loss < 0
    assert result.disposition in {"BOUNDED_MODALITY_RECEIVER_INCREMENT", "MIXED"}


def test_no_modality_signal_not_forced_positive():
    result = run_pr0006(make_data(effect=0.0, seed=12), cfg())
    assert result.disposition in {"NULL_OR_CONTEXT_SUFFICIENT", "MIXED"}


def test_missing_outcome_rejected():
    df = make_data(300)
    df.loc[0, "Recipient_Response"] = None
    with pytest.raises(ValueError, match="forbids outcome imputation"):
        run_pr0006(df, cfg())


def test_frozen_fold_support_failure_is_held():
    df = make_data(500)
    df["Communication_Type"] = "gesture"
    first_group = df["Dyad_ID"].iloc[0]
    df.loc[df["Dyad_ID"] == first_group, "Communication_Type"] = "vocalization"
    with pytest.raises(ValueError, match="HELD_SPLIT"):
        run_pr0006(df, cfg())
