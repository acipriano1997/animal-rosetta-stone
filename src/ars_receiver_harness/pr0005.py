from __future__ import annotations

from dataclasses import asdict, dataclass
import platform
from typing import Iterable

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

OUTCOME_MAP = {"affiliative": 1, "non_affiliative": 0}

B0_COLUMNS = (
    "Social_Context",
    "Initiator_Sex",
    "Recipient_Sex",
    "Rank_Relationship",
    "Collection_Year",
)
B1_ADDITIONS = (
    "Gesture_Class",
    "Facial_Expression_Class",
    "__Gesture_x_Context",
    "__Face_x_Context",
)
B2_ADDITIONS = (
    "__Gesture_x_Face",
    "__Gesture_x_Face_x_Context",
)
IDENTITY_PROVENANCE_COLUMNS = {
    "Event_ID",
    "Source_Row_Locator",
    "Group_ID",
    "Initiator_ID",
    "Recipient_ID",
    "Dyad_ID",
    "Source_Record_Provenance",
    "Rights_and_Reuse_State",
}
REQUIRED_NORMALIZED_COLUMNS = set(B0_COLUMNS) | {
    "Event_ID",
    "Group_ID",
    "Initiator_ID",
    "Recipient_ID",
    "Dyad_ID",
    "Gesture_Class",
    "Facial_Expression_Class",
    "Recipient_Response",
}


@dataclass(frozen=True)
class PR0005Config:
    c: float = 1.0
    solver: str = "lbfgs"
    max_iter: int = 5000
    primary_group_col: str = "Dyad_ID"
    robustness_group_col: str = "Initiator_ID"
    outcome_col: str = "Recipient_Response"
    positive_class: str = "affiliative"


@dataclass(frozen=True)
class ModelOOFMetrics:
    log_loss: float
    brier: float
    roc_auc: float | None


@dataclass(frozen=True)
class PR0005DevelopmentResult:
    disposition: str
    primary_delta_log_loss_b2_minus_b1: float
    primary: dict[str, dict]
    robustness_delta_log_loss_b2_minus_b1: float
    robustness: dict[str, dict]
    n_rows: int
    n_primary_groups: int
    n_robustness_groups: int
    primary_fold_count: int
    robustness_fold_count: int
    primary_test_size_min: int
    primary_test_size_max: int
    robustness_test_size_min: int
    robustness_test_size_max: int
    all_primary_training_folds_supported: bool
    all_robustness_training_folds_supported: bool
    config_snapshot: dict
    runtime_versions: dict[str, str]
    group1_accessed: bool = False
    evidence_scope: str = "DEVELOPMENT_ONLY"

    def to_dict(self) -> dict:
        return asdict(self)


def _strict_outcome(series: pd.Series) -> np.ndarray:
    if series.isna().any():
        raise ValueError("Recipient_Response contains missing values")
    observed = set(series.astype(str).unique())
    if observed != set(OUTCOME_MAP):
        raise ValueError(
            "PR0005 requires exactly affiliative/non_affiliative; "
            f"observed {sorted(observed)!r}"
        )
    return series.map(OUTCOME_MAP).to_numpy(dtype=int)


def _prepare(df: pd.DataFrame, cfg: PR0005Config) -> tuple[pd.DataFrame, np.ndarray]:
    missing = sorted(REQUIRED_NORMALIZED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Missing RDC-004 normalized columns: {missing}")
    if len(df) == 0:
        raise ValueError("Normalized Group-2 corpus is empty")
    if df["Event_ID"].isna().any() or df["Event_ID"].duplicated().any():
        raise ValueError("Event_ID must be nonmissing and unique")
    for col in ("Initiator_ID", "Recipient_ID", cfg.primary_group_col, cfg.robustness_group_col):
        if df[col].isna().any() or (df[col].astype(str).str.len() == 0).any():
            raise ValueError(f"{col} contains missing/empty identities")
    if set(df["Group_ID"].astype(str).unique()) != {"Group 2"}:
        raise ValueError("RUN-005 accepts Group 2 development rows only")
    for col in (
        "Gesture_Class",
        "Facial_Expression_Class",
        "Social_Context",
        "Initiator_Sex",
        "Recipient_Sex",
        "Rank_Relationship",
        "Collection_Year",
    ):
        if df[col].isna().any():
            raise ValueError(f"{col} contains missing values after frozen normalization")
    if (df["Initiator_ID"].astype(str) == df["Recipient_ID"].astype(str)).any():
        raise ValueError("Self-directed identity conflict in normalized development corpus")

    work = df.copy().reset_index(drop=True)
    work["__Gesture_x_Context"] = (
        work["Gesture_Class"].astype(str) + "||" + work["Social_Context"].astype(str)
    )
    work["__Face_x_Context"] = (
        work["Facial_Expression_Class"].astype(str) + "||" + work["Social_Context"].astype(str)
    )
    work["__Gesture_x_Face"] = (
        work["Gesture_Class"].astype(str) + "||" + work["Facial_Expression_Class"].astype(str)
    )
    work["__Gesture_x_Face_x_Context"] = (
        work["Gesture_Class"].astype(str)
        + "||"
        + work["Facial_Expression_Class"].astype(str)
        + "||"
        + work["Social_Context"].astype(str)
    )
    y = _strict_outcome(work[cfg.outcome_col])
    return work, y


def _columns(model_name: str) -> tuple[str, ...]:
    if model_name == "B0":
        return B0_COLUMNS
    if model_name == "B1":
        return B0_COLUMNS + B1_ADDITIONS
    if model_name == "B2":
        return B0_COLUMNS + B1_ADDITIONS + B2_ADDITIONS
    raise ValueError(f"Unknown PR0005 model {model_name!r}")


def _pipeline(columns: tuple[str, ...], cfg: PR0005Config) -> Pipeline:
    if set(columns) & IDENTITY_PROVENANCE_COLUMNS:
        raise ValueError("Identity/provenance fields are forbidden predictors")
    pre = ColumnTransformer(
        [(
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            list(columns),
        )],
        remainder="drop",
    )
    # scikit-learn 1.8 defaults to L2; omitting deprecated explicit penalty='l2'
    # preserves the frozen L2 semantics.
    model = LogisticRegression(
        C=cfg.c,
        solver=cfg.solver,
        max_iter=cfg.max_iter,
    )
    return Pipeline([("pre", pre), ("model", model)])


def _logo_splits(
    work: pd.DataFrame,
    y: np.ndarray,
    group_col: str,
) -> list[tuple[np.ndarray, np.ndarray]]:
    groups = work[group_col]
    if groups.nunique() < 2:
        raise ValueError(f"HELD_SPLIT: {group_col} has fewer than two groups")
    splits = list(LeaveOneGroupOut().split(work, y, groups=groups))
    if not splits:
        raise ValueError("HELD_SPLIT: no leave-one-group-out folds")
    return splits


def _support(
    work: pd.DataFrame,
    y: np.ndarray,
    splits: Iterable[tuple[np.ndarray, np.ndarray]],
    group_col: str,
) -> tuple[bool, tuple[dict, ...]]:
    rows = []
    ok = True
    for fold, (train, test) in enumerate(splits, start=1):
        train_classes = set(np.unique(y[train]).tolist())
        train_groups = set(work.iloc[train][group_col].astype(str))
        test_groups = set(work.iloc[test][group_col].astype(str))
        passed = train_classes == {0, 1} and not (train_groups & test_groups)
        ok = ok and passed
        rows.append(
            {
                "fold": fold,
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "training_has_both_registered_classes": train_classes == {0, 1},
                "zero_group_overlap": not bool(train_groups & test_groups),
                "passed": bool(passed),
            }
        )
    return bool(ok), tuple(rows)


def _oof_predictions(
    work: pd.DataFrame,
    y: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
    model_name: str,
    cfg: PR0005Config,
) -> np.ndarray:
    pred = np.full(len(work), np.nan, dtype=float)
    columns = _columns(model_name)
    for train, test in splits:
        pipe = _pipeline(columns, cfg)
        pipe.fit(work.iloc[train], y[train])
        pred[test] = pipe.predict_proba(work.iloc[test])[:, 1]
    if not np.isfinite(pred).all():
        raise RuntimeError(f"Incomplete/non-finite OOF predictions for {model_name}")
    return pred


def _metrics(y: np.ndarray, p: np.ndarray) -> ModelOOFMetrics:
    auc = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None
    return ModelOOFMetrics(
        log_loss=float(log_loss(y, p, labels=[0, 1])),
        brier=float(brier_score_loss(y, p)),
        roc_auc=auc,
    )


def _run_scheme(
    work: pd.DataFrame,
    y: np.ndarray,
    group_col: str,
    cfg: PR0005Config,
) -> tuple[dict[str, ModelOOFMetrics], float, tuple[dict, ...]]:
    splits = _logo_splits(work, y, group_col)
    supported, support = _support(work, y, splits, group_col)
    if not supported:
        raise ValueError(
            f"HELD_SPLIT: {group_col} leave-one-group-out has unsupported training fold"
        )
    preds = {
        name: _oof_predictions(work, y, splits, name, cfg)
        for name in ("B0", "B1", "B2")
    }
    metrics = {name: _metrics(y, pred) for name, pred in preds.items()}
    delta = metrics["B2"].log_loss - metrics["B1"].log_loss
    return metrics, float(delta), support


def run_pr0005_development(
    group2_normalized: pd.DataFrame,
    cfg: PR0005Config = PR0005Config(),
) -> PR0005DevelopmentResult:
    """Run frozen RUN-005 only. This function has no Group-1 input by design."""
    if cfg.c != 1.0 or cfg.solver != "lbfgs" or cfg.max_iter != 5000:
        raise ValueError("PR0005 frozen model settings changed")
    if cfg.primary_group_col != "Dyad_ID" or cfg.robustness_group_col != "Initiator_ID":
        raise ValueError("PR0005 frozen grouping fields changed")
    if cfg.outcome_col != "Recipient_Response" or cfg.positive_class != "affiliative":
        raise ValueError("PR0005 frozen outcome convention changed")

    work, y = _prepare(group2_normalized, cfg)
    primary_metrics, primary_delta, primary_support = _run_scheme(
        work, y, cfg.primary_group_col, cfg
    )
    robustness_metrics, robustness_delta, robustness_support = _run_scheme(
        work, y, cfg.robustness_group_col, cfg
    )

    if primary_delta < 0:
        disposition = "DEVELOPMENT_B2_IMPROVES_PENDING_LOCKED_GROUP1"
    elif primary_delta > 0:
        disposition = "DEVELOPMENT_B2_DOES_NOT_IMPROVE_PENDING_LOCKED_GROUP1"
    else:
        disposition = "DEVELOPMENT_TIE_PENDING_LOCKED_GROUP1"

    def asdict_metrics(values: dict[str, ModelOOFMetrics]) -> dict[str, dict]:
        return {name: asdict(metric) for name, metric in values.items()}

    return PR0005DevelopmentResult(
        disposition=disposition,
        primary_delta_log_loss_b2_minus_b1=primary_delta,
        primary=asdict_metrics(primary_metrics),
        robustness_delta_log_loss_b2_minus_b1=robustness_delta,
        robustness=asdict_metrics(robustness_metrics),
        n_rows=int(len(work)),
        n_primary_groups=int(work[cfg.primary_group_col].nunique()),
        n_robustness_groups=int(work[cfg.robustness_group_col].nunique()),
        primary_fold_count=len(primary_support),
        robustness_fold_count=len(robustness_support),
        primary_test_size_min=min(x["test_rows"] for x in primary_support),
        primary_test_size_max=max(x["test_rows"] for x in primary_support),
        robustness_test_size_min=min(x["test_rows"] for x in robustness_support),
        robustness_test_size_max=max(x["test_rows"] for x in robustness_support),
        all_primary_training_folds_supported=all(x["passed"] for x in primary_support),
        all_robustness_training_folds_supported=all(x["passed"] for x in robustness_support),
        config_snapshot=asdict(cfg),
        runtime_versions={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    )
