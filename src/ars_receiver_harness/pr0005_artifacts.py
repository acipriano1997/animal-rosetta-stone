from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import pickle
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import log_loss

from .pr0005 import (
    PR0005Config,
    _columns,
    _logo_splits,
    _pipeline,
    _prepare,
    run_pr0005_development,
)

EXPECTED_SOURCE_SHA256 = "26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e"
EXPECTED_ELIGIBLE_ROW_DIGEST = "d6d004eb5a685eed1875e5a430cfb7bb0b6638bb315cf5bf2e2b998588c2be63"
ALLOWED_EVIDENCE_WEIGHTS = {"ZERO_SYNTHETIC", "D0019_EMPIRICAL"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _validate_materialization_manifest(
    manifest: dict[str, Any],
    csv_sha256: str,
    evidence_weight: str,
) -> None:
    if evidence_weight not in ALLOWED_EVIDENCE_WEIGHTS:
        raise ValueError("Unsupported evidence weight")
    if manifest.get("normalized_csv_sha256") != csv_sha256:
        raise ValueError("Normalized CSV differs from materialization manifest")
    if manifest.get("normalized_rows") != 104:
        raise ValueError("RUN-005 requires exactly 104 materialized Group-2 rows")
    if manifest.get("group1_rows_materialized") is not False:
        raise ValueError("Group 1 must remain unmaterialized before RUN-005")
    if manifest.get("pr0005_executed") is not False:
        raise ValueError("Input manifest already marks PR0005 as executed")
    if manifest.get("raw_source_identities_in_normalized_csv") is not False:
        raise ValueError("Normalized RUN-005 input must not contain raw source identities")

    if evidence_weight == "D0019_EMPIRICAL":
        if manifest.get("dataset_id") != "D0019":
            raise ValueError("Empirical package must be D0019")
        if manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256:
            raise ValueError("D0019 source SHA-256 differs from frozen source")
        if manifest.get("eligible_source_row_set_sha256") != EXPECTED_ELIGIBLE_ROW_DIGEST:
            raise ValueError("D0019 eligible row set differs from frozen H4 corpus")
        fingerprint = str(manifest.get("identity_namespace_fingerprint", ""))
        if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint.lower()):
            raise ValueError("Persistent D0019 identity namespace fingerprint is missing/invalid")
    else:
        if manifest.get("evidence_weight") != "ZERO_SYNTHETIC":
            raise ValueError("Synthetic freeze requires ZERO_SYNTHETIC manifest")


def _oof_table(
    work: pd.DataFrame,
    y: np.ndarray,
    cfg: PR0005Config,
    group_col: str,
    model_names: tuple[str, ...],
) -> pd.DataFrame:
    splits = _logo_splits(work, y, group_col)
    result = pd.DataFrame({
        "Event_ID": work["Event_ID"].astype(str),
        "Observed_Response": work[cfg.outcome_col].astype(str),
        "Fold": np.full(len(work), -1, dtype=int),
    })
    for name in model_names:
        result[f"{name}_P_affiliative"] = np.nan

    for fold, (train, test) in enumerate(splits, start=1):
        result.loc[test, "Fold"] = fold
        for name in model_names:
            pipe = _pipeline(_columns(name), cfg)
            pipe.fit(work.iloc[train], y[train])
            result.loc[test, f"{name}_P_affiliative"] = pipe.predict_proba(work.iloc[test])[:, 1]

    if (result["Fold"] < 1).any():
        raise RuntimeError("Incomplete fold assignment")
    probability_cols = [f"{name}_P_affiliative" for name in model_names]
    if not np.isfinite(result[probability_cols].to_numpy(dtype=float)).all():
        raise RuntimeError("Incomplete/non-finite OOF prediction artifact")
    return result


def _verify_oof_matches_result(
    table: pd.DataFrame,
    metrics: dict[str, dict],
    model_names: tuple[str, ...],
) -> None:
    y = table["Observed_Response"].map({"affiliative": 1, "non_affiliative": 0}).to_numpy(dtype=int)
    for name in model_names:
        observed = float(log_loss(y, table[f"{name}_P_affiliative"], labels=[0, 1]))
        expected = float(metrics[name]["log_loss"])
        if not np.isclose(observed, expected, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"{name} OOF artifact does not reproduce registered pooled log loss")


def _fit_full_pipeline(
    work: pd.DataFrame,
    y: np.ndarray,
    cfg: PR0005Config,
    model_name: str,
) -> tuple[bytes, list[str]]:
    pipe = _pipeline(_columns(model_name), cfg)
    pipe.fit(work, y)
    feature_names = list(pipe.named_steps["pre"].get_feature_names_out())
    return pickle.dumps(pipe, protocol=pickle.HIGHEST_PROTOCOL), feature_names


def freeze_run005_package(
    normalized_csv: Path,
    materialization_manifest: Path,
    output_dir: Path,
    *,
    evidence_weight: str,
    cfg: PR0005Config = PR0005Config(),
) -> dict[str, Any]:
    csv_bytes = normalized_csv.read_bytes()
    csv_sha = _sha256_bytes(csv_bytes)
    input_manifest = json.loads(materialization_manifest.read_text())
    _validate_materialization_manifest(input_manifest, csv_sha, evidence_weight)

    frame = pd.read_csv(normalized_csv)
    result = run_pr0005_development(frame, cfg)
    work, y = _prepare(frame, cfg)

    primary = _oof_table(work, y, cfg, cfg.primary_group_col, ("B0", "B1", "B2"))
    robustness = _oof_table(work, y, cfg, cfg.robustness_group_col, ("B1", "B2"))
    _verify_oof_matches_result(primary, result.primary, ("B0", "B1", "B2"))
    _verify_oof_matches_result(robustness, result.robustness, ("B1", "B2"))

    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "run005_development_result.json"
    primary_path = output_dir / "run005_primary_oof.csv"
    robustness_path = output_dir / "run005_robustness_oof.csv"
    feature_path = output_dir / "run005_feature_map.json"
    environment_path = output_dir / "run005_environment.json"
    input_snapshot_path = output_dir / "run005_input_manifest_snapshot.json"
    b1_path = output_dir / "run005_full_group2_b1.pkl"
    b2_path = output_dir / "run005_full_group2_b2.pkl"

    result_payload = result.to_dict()
    result_payload.update({
        "protocol_id": "PR0005",
        "run_id": "RUN-005",
        "evidence_weight": evidence_weight,
        "scientific_claim_admissible": evidence_weight == "D0019_EMPIRICAL",
        "group1_accessed": False,
    })
    result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n")
    primary.to_csv(primary_path, index=False)
    robustness.to_csv(robustness_path, index=False)

    b1_bytes, b1_features = _fit_full_pipeline(work, y, cfg, "B1")
    b2_bytes, b2_features = _fit_full_pipeline(work, y, cfg, "B2")
    b1_path.write_bytes(b1_bytes)
    b2_path.write_bytes(b2_bytes)

    feature_payload = {
        "B0_columns": list(_columns("B0")),
        "B1_columns": list(_columns("B1")),
        "B2_columns": list(_columns("B2")),
        "B1_encoded_features": b1_features,
        "B2_encoded_features": b2_features,
        "identity_or_provenance_features_present": False,
    }
    if any(
        token in name
        for name in b2_features
        for token in ("Initiator_ID", "Recipient_ID", "Dyad_ID", "Event_ID", "Source_Row_Locator")
    ):
        raise RuntimeError("Identity/provenance leaked into fitted feature map")
    feature_path.write_text(json.dumps(feature_payload, indent=2, sort_keys=True) + "\n")

    environment_payload = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "config": asdict(cfg),
        "serialization": "python_pickle_HIGHEST_PROTOCOL",
    }
    environment_path.write_text(json.dumps(environment_payload, indent=2, sort_keys=True) + "\n")
    input_snapshot_path.write_text(json.dumps(input_manifest, indent=2, sort_keys=True) + "\n")

    artifacts = {
        path.name: _sha256_file(path)
        for path in (
            result_path, primary_path, robustness_path, feature_path,
            environment_path, input_snapshot_path, b1_path, b2_path
        )
    }
    freeze_manifest = {
        "dataset_id": "D0019" if evidence_weight == "D0019_EMPIRICAL" else "ZERO_SYNTHETIC",
        "protocol_id": "PR0005",
        "run_id": "RUN-005",
        "freeze_version": "v0.1",
        "evidence_weight": evidence_weight,
        "normalized_csv_sha256": csv_sha,
        "materialization_manifest_sha256": _sha256_file(materialization_manifest),
        "source_sha256": input_manifest.get("source_sha256"),
        "eligible_source_row_set_sha256": input_manifest.get("eligible_source_row_set_sha256"),
        "identity_namespace_fingerprint": input_manifest.get("identity_namespace_fingerprint"),
        "development_rows": result.n_rows,
        "primary_unordered_dyads": result.n_primary_groups,
        "robustness_initiators": result.n_robustness_groups,
        "development_disposition": result.disposition,
        "primary_delta_log_loss_b2_minus_b1": result.primary_delta_log_loss_b2_minus_b1,
        "group1_accessed": False,
        "group1_models_refit": False,
        "full_group2_b1_b2_fitted_and_frozen": True,
        "artifacts_sha256": artifacts,
        "scientific_claim_admissible": evidence_weight == "D0019_EMPIRICAL",
        "crg_c_credit": "UNMET",
        "boundary": (
            "RUN-005 development and artifact freeze only. "
            "No Group-1 data are read; RUN-006 remains locked."
        ),
    }
    manifest_path = output_dir / "run005_freeze_manifest.json"
    manifest_path.write_text(json.dumps(freeze_manifest, indent=2, sort_keys=True) + "\n")
    return freeze_manifest
