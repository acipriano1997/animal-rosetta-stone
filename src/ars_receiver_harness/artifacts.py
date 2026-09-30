from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
from typing import Any

import numpy as np
import pandas as pd
import sklearn

from .pr0006 import PR0006Config, PR0006Result


ARTIFACT_FILES = {
    "HA-001":"source_manifest.json",
    "HA-002":"rights_record.json",
    "HA-003":"schema_inventory.json",
    "HA-004":"rdc_mapping.json",
    "HA-005":"event_identity_manifest.json",
    "HA-006":"missingness_visibility_audit.json",
    "HA-007":"split_manifest.json",
    "HA-008":"grouping_leakage_audit.json",
    "HA-009":"normalized_row_preserving_table.csv",
    "HA-010":"eligibility_exclusion_ledger.csv",
    "HA-011":"run_manifest.json",
    "HA-012":"protocol_deviations.json",
    "HA-013":"execution_log.json",
    "HA-014":"predictions_metrics_results.json",
    "HA-015":"model_artifact_manifest.json",
    "HA-016":"claim_propagation_record.json",
}


def _json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_synthetic_artifact_bundle(out_dir: str | Path, frame: pd.DataFrame, result: PR0006Result, cfg: PR0006Config, *, repository_sha: str | None = None) -> dict[str, Any]:
    """Write HA-001..016 structural artifacts for ZERO_SYNTHETIC verification."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    repo_sha = repository_sha or os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED"
    source_sha = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    base = {"evidence_weight":"ZERO_SYNTHETIC","biological_evidence":False,"repository_sha":repo_sha}

    _json(out/ARTIFACT_FILES["HA-001"], {**base,"provider":"synthetic","dataset_id":"SYNTHETIC_PR0006","version":"v0","filename":"in_memory.csv","sha256":source_sha})
    _json(out/ARTIFACT_FILES["HA-002"], {**base,"research_use_storage":True,"redistribution":"synthetic_only","note":"No real-data rights inference."})
    _json(out/ARTIFACT_FILES["HA-003"], {**base,"columns":[{"name":c,"dtype":str(frame[c].dtype)} for c in frame.columns],"rows":len(frame)})
    _json(out/ARTIFACT_FILES["HA-004"], {**base,"contract":"RDC-005","mapping":"synthetic canonical-column fixture","required_primary_unmappable":False})
    _json(out/ARTIFACT_FILES["HA-005"], {**base,"event_identity":"synthetic row index + source digest","deterministic":True,"outcome_in_identity":False})
    _json(out/ARTIFACT_FILES["HA-006"], {**base,"primary_outcome_missing":int(frame[cfg.outcome_col].isna().sum()),"modality_missing":int(frame[cfg.modality_col].isna().sum()),"states_preserved":True})
    _json(out/ARTIFACT_FILES["HA-007"], {**base,"rule":f"GroupKFold(n_splits={cfg.n_splits}) by {cfg.primary_group_col}","sealed":True,"fold_support":list(result.fold_support)})
    _json(out/ARTIFACT_FILES["HA-008"], {**base,"primary_group":cfg.primary_group_col,"fallback_group":cfg.signaller_col,"rowwise_fallback":False,"sanity_passed":result.sanity_passed,"nuisance_note":"synthetic fixture only"})
    frame.to_csv(out/ARTIFACT_FILES["HA-009"], index=False)
    pd.DataFrame(columns=["Event_ID","included","reason","affected_endpoint","contract_rule"]).to_csv(out/ARTIFACT_FILES["HA-010"],index=False)
    _json(out/ARTIFACT_FILES["HA-011"], {**base,"preregistration":"PR0006","contract":"RDC-005","config":asdict(cfg),"source_sha256":source_sha,"expected_outputs":list(ARTIFACT_FILES.values())})
    _json(out/ARTIFACT_FILES["HA-012"], {**base,"deviations":[]})
    _json(out/ARTIFACT_FILES["HA-013"], {**base,"runner":"ars_receiver_harness.pr0006","status":"success","runtime":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"scikit_learn":sklearn.__version__}})
    _json(out/ARTIFACT_FILES["HA-014"], {**base,"registered_disposition":result.disposition,"metrics":result.to_dict(),"per_event_predictions":"not exported by synthetic structural verifier"})
    _json(out/ARTIFACT_FILES["HA-015"], {**base,"model":"L2 logistic regression","C":cfg.c,"artifact_hash_scope":"configuration/result structural verifier","digest":hashlib.sha256(json.dumps({"cfg":asdict(cfg),"result":result.to_dict()},sort_keys=True).encode()).hexdigest()})
    _json(out/ARTIFACT_FILES["HA-016"], {**base,"allowed_wording":"Synthetic executable verification only.","forbidden_promotions":["animal signal meaning","component meaning","compositionality","cross-species claim","CRG-C biological credit"],"registered_disposition":result.disposition})

    manifest={"evidence_weight":"ZERO_SYNTHETIC","biological_evidence":False,"repository_sha":repo_sha,"artifacts":[]}
    for aid,name in ARTIFACT_FILES.items():
        p=out/name
        manifest["artifacts"].append({"artifact_id":aid,"path":name,"sha256":_sha256(p),"bytes":p.stat().st_size})
    manifest["all_present"] = len(manifest["artifacts"]) == 16 and all((out/x).exists() for x in ARTIFACT_FILES.values())
    _json(out/"artifact_bundle_manifest.json",manifest)
    return manifest
