import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from ars_receiver_harness.pr0005_artifacts import freeze_run005_package
from scripts.run_pr0005_synthetic_verification import synthetic_group2


def _synthetic_input(tmp_path: Path):
    frame=synthetic_group2()
    csv_path=tmp_path/"normalized.csv"
    frame.to_csv(csv_path,index=False)
    csv_sha=hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest={
        "dataset_id":"ZERO_SYNTHETIC",
        "evidence_weight":"ZERO_SYNTHETIC",
        "normalized_rows":104,
        "normalized_csv_sha256":csv_sha,
        "raw_source_identities_in_normalized_csv":False,
        "group1_rows_materialized":False,
        "pr0005_executed":False,
        "source_sha256":"ZERO_SYNTHETIC",
        "eligible_source_row_set_sha256":"ZERO_SYNTHETIC",
        "identity_namespace_fingerprint":"ZERO_SYNTHETIC",
    }
    manifest_path=tmp_path/"materialization.json"
    manifest_path.write_text(json.dumps(manifest))
    return frame,csv_path,manifest_path,manifest


def test_freeze_package_preserves_registered_artifacts_without_identity_features(tmp_path):
    frame,csv_path,manifest_path,_=_synthetic_input(tmp_path)
    out=tmp_path/"freeze"
    result=freeze_run005_package(
        csv_path,manifest_path,out,evidence_weight="ZERO_SYNTHETIC"
    )
    assert result["development_rows"]==104
    assert result["primary_unordered_dyads"]==69
    assert result["group1_accessed"] is False
    assert result["full_group2_b1_b2_fitted_and_frozen"] is True
    assert result["scientific_claim_admissible"] is False

    features=json.loads((out/"run005_feature_map.json").read_text())
    assert features["identity_or_provenance_features_present"] is False
    joined=" ".join(features["B2_encoded_features"])
    for forbidden in ("Initiator_ID","Recipient_ID","Dyad_ID","Event_ID","Source_Row_Locator"):
        assert forbidden not in joined

    primary=pd.read_csv(out/"run005_primary_oof.csv")
    robustness=pd.read_csv(out/"run005_robustness_oof.csv")
    assert list(primary.columns)==[
        "Event_ID","Observed_Response","Fold",
        "B0_P_affiliative","B1_P_affiliative","B2_P_affiliative"
    ]
    assert list(robustness.columns)==[
        "Event_ID","Observed_Response","Fold",
        "B1_P_affiliative","B2_P_affiliative"
    ]
    assert primary["Event_ID"].nunique()==104
    assert "Initiator_ID" not in primary.columns
    assert "Recipient_ID" not in primary.columns
    assert set(result["artifacts_sha256"])=={
        "run005_development_result.json","run005_primary_oof.csv",
        "run005_robustness_oof.csv","run005_feature_map.json",
        "run005_environment.json","run005_input_manifest_snapshot.json",
        "run005_full_group2_b1.pkl","run005_full_group2_b2.pkl",
    }


def test_freeze_rejects_tampered_normalized_csv(tmp_path):
    frame,csv_path,manifest_path,_=_synthetic_input(tmp_path)
    csv_path.write_text(csv_path.read_text()+"\n")
    with pytest.raises(ValueError,match="Normalized CSV differs"):
        freeze_run005_package(
            csv_path,manifest_path,tmp_path/"freeze",evidence_weight="ZERO_SYNTHETIC"
        )


def test_empirical_mode_requires_exact_d0019_manifest_and_namespace(tmp_path):
    frame,csv_path,manifest_path,manifest=_synthetic_input(tmp_path)
    manifest.update({
        "dataset_id":"D0019",
        "source_sha256":"26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e",
        "eligible_source_row_set_sha256":"d6d004eb5a685eed1875e5a430cfb7bb0b6638bb315cf5bf2e2b998588c2be63",
        "identity_namespace_fingerprint":"",
    })
    manifest.pop("evidence_weight",None)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match="identity namespace"):
        freeze_run005_package(
            csv_path,manifest_path,tmp_path/"freeze",evidence_weight="D0019_EMPIRICAL"
        )


def test_freeze_rejects_group1_materialization_flag(tmp_path):
    frame,csv_path,manifest_path,manifest=_synthetic_input(tmp_path)
    manifest["group1_rows_materialized"]=True
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match="Group 1"):
        freeze_run005_package(
            csv_path,manifest_path,tmp_path/"freeze",evidence_weight="ZERO_SYNTHETIC"
        )


def test_synthetic_freeze_verifier_can_execute_directly():
    completed=subprocess.run(
        [sys.executable,"scripts/run_pr0005_freeze_synthetic_verification.py","--help"],
        check=False,capture_output=True,text=True,
    )
    assert completed.returncode==0, completed.stderr
