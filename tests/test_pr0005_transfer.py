import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pytest

from ars_receiver_harness.pr0005_transfer import (
    evaluate_locked_group1,
    run_d0019_group1_transfer,
)
from scripts.run_pr0005_transfer_synthetic_verification import build_synthetic_case


@pytest.fixture(scope="module")
def synthetic_case(tmp_path_factory):
    return build_synthetic_case(tmp_path_factory.mktemp("run006_case"))


def test_end_to_end_locked_transfer_uses_frozen_models_without_refit(synthetic_case):
    case=synthetic_case
    manifest=case["transfer_manifest"]
    assert manifest["group1_source_rows_before_exclusions"]==103
    assert manifest["group1_eligible_rows"]==103
    assert manifest["models_refit_on_group1"] is False
    assert manifest["preprocessing_refit_on_group1"] is False
    assert manifest["crg_c_credit"]=="REQUIRES_SEPARATE_ADJUDICATION"
    assert manifest["final_pr0005_disposition"] in {
        "BOUNDED_H0001_SUPPORT","MIXED","NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
    }
    predictions=pd.read_csv(case["output_dir"]/"run006_group1_predictions.csv")
    assert list(predictions.columns)==[
        "Event_ID","Observed_Response","B1_P_affiliative","B2_P_affiliative"
    ]
    assert len(predictions)==103
    assert predictions["Event_ID"].nunique()==103
    assert "Initiator_ID" not in predictions.columns
    assert "Recipient_ID" not in predictions.columns


def test_invalid_run005_freeze_blocks_before_group1_fetch(tmp_path,synthetic_case):
    case=synthetic_case
    bad=copy.deepcopy(case["freeze_manifest"])
    bad["group1_accessed"]=True
    called=False
    def forbidden(url,size):
        nonlocal called
        called=True
        raise AssertionError("Group-1 source must not be fetched")
    with pytest.raises(ValueError,match="Group-1 access"):
        run_d0019_group1_transfer(
            item=case["item"],pins=case["pins"],crosswalk=case["crosswalk"],
            eligibility=case["eligibility"],group1_procedure=case["group1_procedure"],
            run005_freeze_manifest=bad,run005_freeze_dir=case["freeze_dir"],
            secret=case["secret"],fetch=forbidden,output_dir=tmp_path/"blocked",
            evidence_weight="ZERO_SYNTHETIC",
        )
    assert called is False


def test_tampered_frozen_model_blocks_before_group1_fetch(tmp_path,synthetic_case):
    case=synthetic_case
    copied=tmp_path/"freeze_copy"
    shutil.copytree(case["freeze_dir"],copied)
    model=copied/"run005_full_group2_b1.pkl"
    model.write_bytes(model.read_bytes()+b"tamper")
    called=False
    def forbidden(url,size):
        nonlocal called
        called=True
        raise AssertionError("Group-1 source must not be fetched")
    with pytest.raises(ValueError,match="model artifact mismatch"):
        run_d0019_group1_transfer(
            item=case["item"],pins=case["pins"],crosswalk=case["crosswalk"],
            eligibility=case["eligibility"],group1_procedure=case["group1_procedure"],
            run005_freeze_manifest=case["freeze_manifest"],
            run005_freeze_dir=copied,secret=case["secret"],
            fetch=forbidden,output_dir=tmp_path/"blocked",
            evidence_weight="ZERO_SYNTHETIC",
        )
    assert called is False


def test_namespace_mismatch_blocks_before_group1_fetch(tmp_path,synthetic_case):
    case=synthetic_case
    bad=copy.deepcopy(case["freeze_manifest"])
    bad["identity_namespace_fingerprint"]="0"*64
    called=False
    def forbidden(url,size):
        nonlocal called
        called=True
        raise AssertionError("Group-1 source must not be fetched")
    with pytest.raises(ValueError,match="namespace"):
        run_d0019_group1_transfer(
            item=case["item"],pins=case["pins"],crosswalk=case["crosswalk"],
            eligibility=case["eligibility"],group1_procedure=case["group1_procedure"],
            run005_freeze_manifest=bad,run005_freeze_dir=case["freeze_dir"],
            secret=case["secret"],fetch=forbidden,output_dir=tmp_path/"blocked",
            evidence_weight="ZERO_SYNTHETIC",
        )
    assert called is False


def test_one_class_locked_transfer_keeps_log_loss_and_sets_auc_none(synthetic_case):
    case=synthetic_case
    group1=pd.read_csv(case["output_dir"]/"run006_group1_normalized.csv")
    group1["Recipient_Response"]="affiliative"
    result,predictions=evaluate_locked_group1(
        group1,case["freeze_manifest"],case["freeze_dir"]
    )
    assert result["B1"]["roc_auc"] is None
    assert result["B2"]["roc_auc"] is None
    assert result["models_refit_on_group1"] is False
    assert len(predictions)==103


def test_empirical_cli_imports_directly_without_secret_on_help():
    completed=subprocess.run(
        [sys.executable,"scripts/run_pr0005_group1_transfer.py","--help"],
        check=False,capture_output=True,text=True,
    )
    assert completed.returncode==0,completed.stderr
