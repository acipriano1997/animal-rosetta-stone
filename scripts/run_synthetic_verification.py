from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from ars_receiver_harness.artifacts import write_synthetic_artifact_bundle
from ars_receiver_harness.pr0006 import PR0006Config, run_pr0006


def make_data(n=900,seed=7,effect=1.25):
    rng=np.random.default_rng(seed)
    s=rng.choice([f"S{i:02d}" for i in range(12)],size=n)
    r=rng.choice([f"R{i:02d}" for i in range(18)],size=n)
    m=rng.choice(["gesture","vocalization","bimodal"],p=[.64,.16,.20],size=n)
    bond=rng.normal(size=n)
    rel=rng.choice(["kin","nonkin"],size=n,p=[.18,.82])
    term=np.where(m=="gesture",effect,np.where(m=="bimodal",effect*.35,-effect))
    logit=-.1+.45*bond+.25*(rel=="kin")+term
    p=1/(1+np.exp(-logit))
    y=np.where(rng.random(n)<p,"approach","avoidance")
    return pd.DataFrame({"Recipient_Response":y,"Communication_Type":m,"Dyad_ID":np.char.add(np.char.add(s,"__"),r),"Signaller_ID":s,"Social_Bond":bond,"Relatedness":rel})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",default="build/synthetic_verification")
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    cfg=PR0006Config(baseline_numeric=("Social_Bond",),baseline_categorical=("Relatedness",))
    df=make_data()
    result=run_pr0006(df,cfg)
    (out/"pr0006_result.json").write_text(json.dumps(result.to_dict(),indent=2)+"\n")
    manifest=write_synthetic_artifact_bundle(out/"ha_bundle",df,result,cfg,repository_sha=os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED")
    receipt={"repository_sha":os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED","evidence_weight":"ZERO_SYNTHETIC","biological_evidence":False,"pr0006_disposition":result.disposition,"ha_bundle_all_present":manifest["all_present"]}
    (out/"verification_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))
    if not manifest["all_present"]: raise SystemExit(1)

if __name__=="__main__":main()
