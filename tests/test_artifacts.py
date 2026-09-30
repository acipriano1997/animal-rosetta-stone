from pathlib import Path
import numpy as np
import pandas as pd

from ars_receiver_harness.artifacts import ARTIFACT_FILES, write_synthetic_artifact_bundle
from ars_receiver_harness.pr0006 import PR0006Config, run_pr0006


def _data(n=600,seed=11):
    rng=np.random.default_rng(seed)
    s=rng.choice([f"S{i}" for i in range(10)],n)
    r=rng.choice([f"R{i}" for i in range(14)],n)
    m=rng.choice(["gesture","vocalization","bimodal"],n,p=[.6,.18,.22])
    bond=rng.normal(size=n)
    logit=.4*bond+np.where(m=="gesture",1.0,np.where(m=="bimodal",.35,-.8))
    p=1/(1+np.exp(-logit))
    y=np.where(rng.random(n)<p,"approach","avoidance")
    return pd.DataFrame({"Recipient_Response":y,"Communication_Type":m,"Dyad_ID":np.char.add(np.char.add(s,"__"),r),"Signaller_ID":s,"Social_Bond":bond})


def test_ha_001_016_structural_bundle(tmp_path: Path):
    df=_data()
    cfg=PR0006Config(baseline_numeric=("Social_Bond",),bootstrap_resamples=100,sanity_permutations=20)
    result=run_pr0006(df,cfg)
    manifest=write_synthetic_artifact_bundle(tmp_path,df,result,cfg,repository_sha="TEST_SHA")
    assert manifest["all_present"]
    assert {x["artifact_id"] for x in manifest["artifacts"]} == set(ARTIFACT_FILES)
    assert manifest["evidence_weight"] == "ZERO_SYNTHETIC"
    assert not manifest["biological_evidence"]
