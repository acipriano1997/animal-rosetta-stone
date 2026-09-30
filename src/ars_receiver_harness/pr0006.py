from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import platform
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class PR0006Config:
    outcome_col: str = "Recipient_Response"
    modality_col: str = "Communication_Type"
    primary_group_col: str = "Dyad_ID"
    signaller_col: str = "Signaller_ID"
    baseline_numeric: tuple[str, ...] = ()
    baseline_categorical: tuple[str, ...] = ()
    n_splits: int = 5
    c: float = 1.0
    bootstrap_resamples: int = 2000
    sanity_permutations: int = 200
    seed: int = 20260929


@dataclass(frozen=True)
class PR0006Result:
    disposition: str
    mean_delta_log_loss: float
    bootstrap_ci_low: float
    bootstrap_ci_high: float
    b0_log_loss: float
    b1_log_loss: float
    leave_signaller_out_delta: float | None
    leave_signaller_out_available: bool
    primary_fold_support_passed: bool
    sanity_passed: bool
    sanity_mean_permuted_delta: float
    sanity_ci_low: float
    sanity_ci_high: float
    n_rows: int
    n_primary_groups: int
    n_signallers: int
    modality_counts: dict[str, int]
    fold_support: tuple[dict, ...]
    config_snapshot: dict
    runtime_versions: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


def _binary_outcome(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int).to_numpy()
    vals = list(pd.unique(series.dropna()))
    if len(vals) != 2:
        raise ValueError(f"Primary outcome must have exactly two observed classes; found {vals!r}")
    ordered = sorted(vals, key=lambda x: str(x))
    mapping = {ordered[0]: 0, ordered[1]: 1}
    return series.map(mapping).to_numpy(dtype=int)


def _pipeline(numeric: Sequence[str], categorical: Sequence[str], c: float) -> Pipeline:
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), list(numeric)))
    if categorical:
        transformers.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), list(categorical)))
    if not transformers:
        raise ValueError("At least one predictor column is required")
    pre = ColumnTransformer(transformers, remainder="drop")
    model = LogisticRegression(C=c, solver="liblinear", max_iter=2000)
    return Pipeline([("pre", pre), ("model", model)])


def _prepare_frame(df: pd.DataFrame, cfg: PR0006Config) -> tuple[pd.DataFrame, np.ndarray, list[str], list[str]]:
    required = {cfg.outcome_col, cfg.modality_col, cfg.primary_group_col, cfg.signaller_col}
    required |= set(cfg.baseline_numeric) | set(cfg.baseline_categorical)
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df[cfg.outcome_col].isna().any():
        raise ValueError("Primary outcome contains missing values; PR0006 forbids outcome imputation")
    if df[cfg.primary_group_col].isna().any() or df[cfg.signaller_col].isna().any():
        raise ValueError("Primary grouping/signaller identifiers contain missing values")
    if df[cfg.modality_col].isna().any():
        raise ValueError("Communication_Type contains missing values")

    work = df.copy().reset_index(drop=True)
    work["__ARS_INTERCEPT__"] = 1.0
    y = _binary_outcome(work[cfg.outcome_col])
    num = list(cfg.baseline_numeric)
    cat = list(cfg.baseline_categorical)
    if not num and not cat:
        num = ["__ARS_INTERCEPT__"]
    return work, y, num, cat


def _check_training_fold_support(work: pd.DataFrame, y: np.ndarray, splits: Iterable[tuple[np.ndarray, np.ndarray]], cfg: PR0006Config) -> tuple[dict, ...]:
    all_modalities = set(work[cfg.modality_col].astype(str).unique())
    report = []
    for fold, (train, test) in enumerate(splits, start=1):
        train_classes = set(np.unique(y[train]).tolist())
        train_mods = set(work.iloc[train][cfg.modality_col].astype(str).unique())
        test_classes = set(np.unique(y[test]).tolist())
        test_mods = set(work.iloc[test][cfg.modality_col].astype(str).unique())
        ok = train_classes == {0, 1} and train_mods == all_modalities
        report.append({
            "fold": fold,
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_outcome_classes": sorted(train_classes),
            "test_outcome_classes": sorted(test_classes),
            "train_modalities": sorted(train_mods),
            "test_modalities": sorted(test_mods),
            "passed": bool(ok),
        })
    return tuple(report)


def _oof_predictions(work: pd.DataFrame, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]], numeric: list[str], categorical: list[str], cfg: PR0006Config, modality_values: pd.Series | None = None) -> tuple[np.ndarray, np.ndarray]:
    p0 = np.full(len(work), np.nan, dtype=float)
    p1 = np.full(len(work), np.nan, dtype=float)
    frame = work.copy()
    if modality_values is not None:
        frame[cfg.modality_col] = modality_values.to_numpy()

    b0_num = numeric
    b0_cat = categorical
    b1_num = numeric
    b1_cat = categorical + [cfg.modality_col]

    for train, test in splits:
        pipe0 = _pipeline(b0_num, b0_cat, cfg.c)
        pipe1 = _pipeline(b1_num, b1_cat, cfg.c)
        pipe0.fit(frame.iloc[train], y[train])
        pipe1.fit(frame.iloc[train], y[train])
        p0[test] = pipe0.predict_proba(frame.iloc[test])[:, 1]
        p1[test] = pipe1.predict_proba(frame.iloc[test])[:, 1]
    if not np.isfinite(p0).all() or not np.isfinite(p1).all():
        raise RuntimeError("OOF prediction coverage is incomplete/non-finite")
    return p0, p1


def _cluster_bootstrap_delta(y: np.ndarray, p0: np.ndarray, p1: np.ndarray, groups: pd.Series, n: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    unique = pd.unique(groups)
    indices = {g: np.flatnonzero(groups.to_numpy() == g) for g in unique}
    deltas = np.empty(n, dtype=float)
    for i in range(n):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([indices[g] for g in sampled])
        deltas[i] = log_loss(y[idx], p1[idx], labels=[0, 1]) - log_loss(y[idx], p0[idx], labels=[0, 1])
    low, high = np.quantile(deltas, [0.025, 0.975])
    return float(low), float(high)


def _leave_signaller_out(work: pd.DataFrame, y: np.ndarray, numeric: list[str], categorical: list[str], cfg: PR0006Config) -> tuple[bool, float | None]:
    groups = work[cfg.signaller_col]
    if groups.nunique() < 2:
        return False, None
    logo = LeaveOneGroupOut()
    splits = list(logo.split(work, y, groups=groups))
    all_modalities = set(work[cfg.modality_col].astype(str).unique())
    for train, _ in splits:
        if set(np.unique(y[train]).tolist()) != {0, 1}:
            return False, None
        if set(work.iloc[train][cfg.modality_col].astype(str).unique()) != all_modalities:
            return False, None
    p0, p1 = _oof_predictions(work, y, splits, numeric, categorical, cfg)
    delta = log_loss(y, p1, labels=[0, 1]) - log_loss(y, p0, labels=[0, 1])
    return True, float(delta)


def _modality_permutation_sanity(work: pd.DataFrame, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]], numeric: list[str], categorical: list[str], cfg: PR0006Config) -> tuple[bool, float, float, float]:
    """Equivalent negative control preserving rows/groups/splits/outcomes."""
    rng = np.random.default_rng(cfg.seed + 17)
    original = work[cfg.modality_col].reset_index(drop=True)

    p0, _ = _oof_predictions(work, y, splits, numeric, categorical, cfg)
    b0_loss = log_loss(y, p0, labels=[0, 1])
    deltas = np.empty(cfg.sanity_permutations, dtype=float)
    for i in range(cfg.sanity_permutations):
        perm = original.iloc[rng.permutation(len(original))].reset_index(drop=True)
        frame = work.copy()
        frame[cfg.modality_col] = perm.to_numpy()
        p1 = np.full(len(work), np.nan, dtype=float)
        b1_cat = categorical + [cfg.modality_col]
        for train, test in splits:
            pipe1 = _pipeline(numeric, b1_cat, cfg.c)
            pipe1.fit(frame.iloc[train], y[train])
            p1[test] = pipe1.predict_proba(frame.iloc[test])[:, 1]
        if not np.isfinite(p1).all():
            raise RuntimeError("Sanity OOF prediction coverage is incomplete/non-finite")
        deltas[i] = log_loss(y, p1, labels=[0, 1]) - b0_loss
    low, high = np.quantile(deltas, [0.025, 0.975])
    passed = not (high < 0.0)
    return bool(passed), float(deltas.mean()), float(low), float(high)


def run_pr0006(df: pd.DataFrame, cfg: PR0006Config = PR0006Config()) -> PR0006Result:
    work, y, numeric, categorical = _prepare_frame(df, cfg)
    if work[cfg.primary_group_col].nunique() < cfg.n_splits:
        raise ValueError("HELD_SPLIT: fewer primary groups than frozen GroupKFold splits")

    gkf = GroupKFold(n_splits=cfg.n_splits)
    splits = list(gkf.split(work, y, groups=work[cfg.primary_group_col]))
    fold_support = _check_training_fold_support(work, y, splits, cfg)
    if not all(x["passed"] for x in fold_support):
        raise ValueError("HELD_SPLIT: a training fold lacks both outcome classes or a required Communication_Type level")

    p0, p1 = _oof_predictions(work, y, splits, numeric, categorical, cfg)
    b0_loss = float(log_loss(y, p0, labels=[0, 1]))
    b1_loss = float(log_loss(y, p1, labels=[0, 1]))
    mean_delta = b1_loss - b0_loss
    ci_low, ci_high = _cluster_bootstrap_delta(
        y, p0, p1, work[cfg.primary_group_col], cfg.bootstrap_resamples, cfg.seed
    )

    loo_available, loo_delta = _leave_signaller_out(work, y, numeric, categorical, cfg)
    sanity_passed, sanity_mean, sanity_low, sanity_high = _modality_permutation_sanity(
        work, y, splits, numeric, categorical, cfg
    )

    if not sanity_passed:
        disposition = "HELD_SANITY"
    elif mean_delta >= 0:
        disposition = "NULL_OR_CONTEXT_SUFFICIENT"
    elif ci_high < 0 and loo_available and loo_delta is not None and loo_delta < 0:
        disposition = "BOUNDED_MODALITY_RECEIVER_INCREMENT"
    else:
        disposition = "MIXED"

    return PR0006Result(
        disposition=disposition,
        mean_delta_log_loss=float(mean_delta),
        bootstrap_ci_low=ci_low,
        bootstrap_ci_high=ci_high,
        b0_log_loss=b0_loss,
        b1_log_loss=b1_loss,
        leave_signaller_out_delta=loo_delta,
        leave_signaller_out_available=loo_available,
        primary_fold_support_passed=True,
        sanity_passed=sanity_passed,
        sanity_mean_permuted_delta=sanity_mean,
        sanity_ci_low=sanity_low,
        sanity_ci_high=sanity_high,
        n_rows=int(len(work)),
        n_primary_groups=int(work[cfg.primary_group_col].nunique()),
        n_signallers=int(work[cfg.signaller_col].nunique()),
        modality_counts={str(k): int(v) for k, v in work[cfg.modality_col].value_counts().to_dict().items()},
        fold_support=fold_support,
        config_snapshot=asdict(cfg),
        runtime_versions={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    )
