"""ZERO_SYNTHETIC executable verification for frozen PR0005 RUN-005."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ars_receiver_harness.pr0005 import run_pr0005_development


def synthetic_group2() -> pd.DataFrame:
    rows=[]
    dyads=[f"D{i:02d}" for i in range(69)]
    dyad_seq=dyads+dyads[:35]
    for i,dyad in enumerate(dyad_seq):
        gesture="stretched_arm" if i%2==0 else "bent_arm"
        face=("neutral","bared_teeth","funneled_lip_hoot")[i%3]
        context="positive_affiliative_context" if (i//2)%2==0 else "negative_agonistic_context"
        # Authored fixture outcome: both classes distributed across groups.
        response="affiliative" if (i%4 in (0,1)) else "non_affiliative"
        rows.append({
            "Event_ID":f"SYN-E{i:03d}",
            "Source_Row_Locator":f"synthetic:row:{i+2}",
            "Group_ID":"Group 2",
            "Initiator_ID":f"SYN-I{i%28:02d}",
            "Recipient_ID":f"SYN-R{(i*3+5)%31:02d}",
            "Dyad_ID":dyad,
            "Initiator_Sex":"female" if i%2==0 else "male",
            "Recipient_Sex":"male" if i%3==0 else "female",
            "Rank_Relationship":("todom","nottodom","SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE")[i%3],
            "Collection_Year":"2015" if i%2==0 else "2016",
            "Gesture_Class":gesture,
            "Facial_Expression_Class":face,
            "Social_Context":context,
            "Recipient_Response":response,
            "Signal_Configuration":gesture+"|"+face,
            "Coding_Visibility_or_Quality":"ZERO_SYNTHETIC_VISIBLE",
            "Rights_and_Reuse_State":"ZERO_SYNTHETIC",
            "Source_Record_Provenance":f"synthetic:fixture:{i}",
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap=argparse.ArgumentParser(description="Verify PR0005 RUN-005 on authored synthetic data only")
    ap.add_argument("--out",default="build/pr0005_synthetic_verification.json")
    args=ap.parse_args()
    frame=synthetic_group2()
    result=run_pr0005_development(frame)
    payload={
        "protocol_id":"PR0005",
        "run_id":"RUN-005",
        "evidence_weight":"ZERO_SYNTHETIC",
        "biological_evidence":False,
        "scientific_claim_admissible":False,
        "crg_c_credit":"UNMET",
        "group1_accessed":False,
        "fixture_rows":len(frame),
        "fixture_primary_dyads":frame["Dyad_ID"].nunique(),
        "fixture_initiators":frame["Initiator_ID"].nunique(),
        "result":result.to_dict(),
        "allowed_inference":"Executable verification of frozen RUN-005 mechanics only.",
        "forbidden_inferences":[
            "chimpanzee signal meaning",
            "gesture or face semantic content",
            "biological compositionality",
            "D0019 empirical support",
            "CRG-C credit",
        ],
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":"PASS_ZERO_SYNTHETIC",
        "rows":len(frame),
        "primary_folds":result.primary_fold_count,
        "robustness_folds":result.robustness_fold_count,
        "biological_evidence":False,
        "output":str(out),
    }))


if __name__=="__main__":
    main()
