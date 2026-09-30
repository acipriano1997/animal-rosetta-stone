import numpy as np
import pandas as pd
import pytest

from ars_receiver_harness.pr0005 import (
    B0_COLUMNS,
    B1_ADDITIONS,
    B2_ADDITIONS,
    PR0005Config,
    _columns,
    _pipeline,
    run_pr0005_development,
)


def synthetic_group2(n=104):
    rows=[]
    # 69 unordered dyads, 28 initiators. First 35 dyads appear twice, the rest once.
    dyads=[f"D{i:02d}" for i in range(69)]
    dyad_seq=dyads + dyads[:35]
    assert len(dyad_seq)==n
    for i,dyad in enumerate(dyad_seq):
        initiator=f"I{i % 28:02d}"
        recipient=f"R{(i * 3 + 5) % 31:02d}"
        gesture="stretched_arm" if i % 2 == 0 else "bent_arm"
        face=("neutral","bared_teeth","funneled_lip_hoot")[i % 3]
        context="positive_affiliative_context" if (i // 2) % 2 == 0 else "negative_agonistic_context"
        # Ensure both outcome classes are broadly distributed over dyads/initiators.
        outcome="affiliative" if ((i % 4) in (0,1)) else "non_affiliative"
        rows.append({
            "Event_ID":f"E{i:03d}",
            "Source_Row_Locator":f"synthetic:{i+2}",
            "Group_ID":"Group 2",
            "Initiator_ID":initiator,
            "Recipient_ID":recipient,
            "Dyad_ID":dyad,
            "Initiator_Sex":"female" if i % 2 == 0 else "male",
            "Recipient_Sex":"male" if i % 3 == 0 else "female",
            "Rank_Relationship":("todom","nottodom","SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE")[i % 3],
            "Collection_Year":"2015" if i % 2 == 0 else "2016",
            "Gesture_Class":gesture,
            "Facial_Expression_Class":face,
            "Social_Context":context,
            "Recipient_Response":outcome,
            "Signal_Configuration":gesture+"|"+face,
            "Coding_Visibility_or_Quality":"PRIMARY_REQUIRED_FIELDS_OBSERVED_OR_MAPPABLE",
            "Rights_and_Reuse_State":"ZERO_SYNTHETIC",
            "Source_Record_Provenance":f"synthetic:{i}",
        })
    return pd.DataFrame(rows)


def test_frozen_feature_sets_are_nested_and_exclude_identity_fields():
    assert _columns("B0") == B0_COLUMNS
    assert _columns("B1") == B0_COLUMNS + B1_ADDITIONS
    assert _columns("B2") == B0_COLUMNS + B1_ADDITIONS + B2_ADDITIONS
    for name in ("B0","B1","B2"):
        cols=set(_columns(name))
        assert not cols & {
            "Event_ID","Source_Row_Locator","Group_ID","Initiator_ID",
            "Recipient_ID","Dyad_ID","Source_Record_Provenance",
        }


def test_run005_uses_frozen_logo_schemes_and_complete_group2_only_input():
    result=run_pr0005_development(synthetic_group2())
    assert result.n_rows==104
    assert result.n_primary_groups==69
    assert result.n_robustness_groups==28
    assert result.primary_fold_count==69
    assert result.robustness_fold_count==28
    assert result.primary_test_size_min==1
    assert result.primary_test_size_max==2
    assert result.all_primary_training_folds_supported is True
    assert result.all_robustness_training_folds_supported is True
    assert np.isfinite(result.primary_delta_log_loss_b2_minus_b1)
    assert np.isfinite(result.robustness_delta_log_loss_b2_minus_b1)
    assert set(result.primary)=={"B0","B1","B2"}
    assert result.group1_accessed is False
    assert result.evidence_scope=="DEVELOPMENT_ONLY"


def test_group1_rows_are_rejected_by_run005():
    frame=synthetic_group2()
    frame.loc[0,"Group_ID"]="Group 1"
    with pytest.raises(ValueError,match="Group 2"):
        run_pr0005_development(frame)


def test_outcome_convention_is_strict_and_missing_is_not_negative():
    frame=synthetic_group2()
    frame.loc[0,"Recipient_Response"]="NA"
    with pytest.raises(ValueError,match="affiliative/non_affiliative"):
        run_pr0005_development(frame)
    frame=synthetic_group2()
    frame.loc[0,"Recipient_Response"]=None
    with pytest.raises(ValueError,match="missing"):
        run_pr0005_development(frame)


def test_event_identity_must_be_unique():
    frame=synthetic_group2()
    frame.loc[1,"Event_ID"]=frame.loc[0,"Event_ID"]
    with pytest.raises(ValueError,match="Event_ID"):
        run_pr0005_development(frame)


def test_frozen_model_settings_cannot_be_changed():
    frame=synthetic_group2()
    with pytest.raises(ValueError,match="frozen model settings"):
        run_pr0005_development(frame,PR0005Config(c=0.5))
    with pytest.raises(ValueError,match="frozen grouping"):
        run_pr0005_development(frame,PR0005Config(primary_group_col="Initiator_ID"))


def test_identity_column_cannot_be_injected_into_pipeline():
    with pytest.raises(ValueError,match="forbidden predictors"):
        _pipeline(("Social_Context","Initiator_ID"),PR0005Config())


def test_unsupported_leave_dyad_out_training_fold_fails_closed():
    frame=synthetic_group2()
    # Make the only non-affiliative observations belong to one dyad. Leaving it
    # out creates an all-affiliative training set and must HOLD rather than
    # merge/rebalance folds.
    frame["Recipient_Response"]="affiliative"
    target=frame["Dyad_ID"]=="D00"
    frame.loc[target,"Recipient_Response"]="non_affiliative"
    with pytest.raises(ValueError,match="HELD_SPLIT"):
        run_pr0005_development(frame)
