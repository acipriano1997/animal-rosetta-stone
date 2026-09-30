from __future__ import annotations

import csv
import hashlib
import json
import pickle
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .d0019_ids import canonical_event_id, pseudonymize_source_id, unordered_dyad_id

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXPECTED_SOURCE_SHA256 = "26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e"
COLS = {
    "Dataset":"A","event":"B","initiator":"E","group":"F","sex_init":"G",
    "recipient":"I","sex_rec":"J","dyad":"K","rel_dom":"L","face":"M",
    "context_dyad":"N","GEST":"O","REACT":"P",
}
NORMALIZED_FIELDS = [
    "Event_ID","Source_Row_Locator","Group_ID","Initiator_ID","Recipient_ID","Dyad_ID",
    "Initiator_Sex","Recipient_Sex","Rank_Relationship","Collection_Year",
    "Gesture_Class","Facial_Expression_Class","Social_Context","Recipient_Response",
    "Signal_Configuration","Coding_Visibility_or_Quality","Rights_and_Reuse_State",
    "Source_Record_Provenance",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _namespace_fingerprint(secret: bytes) -> str:
    return hashlib.sha256(
        b"D0019_NAMESPACE_PUBLIC_FINGERPRINT|" + hashlib.sha256(secret).digest()
    ).hexdigest()


def _crosswalk_field(crosswalk: dict, name: str) -> dict:
    matches=[x for x in crosswalk.get("fields",[]) if x.get("field")==name]
    if len(matches)!=1:
        raise ValueError(f"Expected exactly one crosswalk field {name}")
    return matches[0]


def _verify_frozen_model_artifacts(
    freeze_manifest: dict[str, Any],
    freeze_dir: Path,
) -> None:
    _verify_frozen_model_artifacts(freeze_manifest,freeze_dir)


def validate_run005_freeze_before_group1(
    freeze_manifest: dict[str, Any],
    freeze_dir: Path,
    secret: bytes,
    *,
    evidence_weight: str,
) -> None:
    if not isinstance(secret,(bytes,bytearray)) or len(secret)<32:
        raise ValueError("Persistent HMAC secret must be at least 32 bytes")
    if freeze_manifest.get("protocol_id")!="PR0005" or freeze_manifest.get("run_id")!="RUN-005":
        raise ValueError("RUN-005 freeze manifest identity mismatch")
    if freeze_manifest.get("full_group2_b1_b2_fitted_and_frozen") is not True:
        raise ValueError("Full Group-2 B1/B2 artifacts are not frozen")
    if freeze_manifest.get("group1_accessed") is not False:
        raise ValueError("RUN-005 freeze manifest already reports Group-1 access")
    if freeze_manifest.get("group1_models_refit") is not False:
        raise ValueError("RUN-005 freeze manifest reports Group-1 refit")
    if freeze_manifest.get("development_rows")!=104 or freeze_manifest.get("primary_unordered_dyads")!=69:
        raise ValueError("RUN-005 freeze manifest differs from frozen development corpus")
    if freeze_manifest.get("evidence_weight")!=evidence_weight:
        raise ValueError("RUN-005 evidence weight mismatch")

    if evidence_weight=="D0019_EMPIRICAL":
        if freeze_manifest.get("dataset_id")!="D0019":
            raise ValueError("Empirical RUN-006 requires D0019 RUN-005 freeze")
        if freeze_manifest.get("source_sha256")!=EXPECTED_SOURCE_SHA256:
            raise ValueError("RUN-005 freeze source SHA differs from D0019 pin")
        fp=str(freeze_manifest.get("identity_namespace_fingerprint",""))
        if fp!=_namespace_fingerprint(bytes(secret)):
            raise ValueError("HMAC identity namespace does not match RUN-005")
        if freeze_manifest.get("scientific_claim_admissible") is not True:
            raise ValueError("Empirical RUN-005 freeze is not marked admissible")
    elif evidence_weight=="ZERO_SYNTHETIC":
        # Synthetic mode verifies mechanics only; it can use an authored namespace.
        expected=freeze_manifest.get("identity_namespace_fingerprint")
        if expected not in (None,"ZERO_SYNTHETIC",_namespace_fingerprint(bytes(secret))):
            raise ValueError("Synthetic namespace mismatch")
    else:
        raise ValueError("Unsupported RUN-006 evidence weight")

    artifact_hashes=freeze_manifest.get("artifacts_sha256")
    if not isinstance(artifact_hashes,dict):
        raise ValueError("RUN-005 artifact checksum map missing")
    for name in ("run005_full_group2_b1.pkl","run005_full_group2_b2.pkl"):
        expected=artifact_hashes.get(name)
        path=freeze_dir/name
        if not isinstance(expected,str) or not path.is_file() or _sha256_file(path)!=expected:
            raise ValueError(f"Frozen RUN-005 model artifact mismatch: {name}")


def _decoder(book: ZipFile):
    strings=[]
    if "xl/sharedStrings.xml" in book.namelist():
        root=ET.fromstring(book.read("xl/sharedStrings.xml"))
        strings=["".join(t.text or "" for t in si.iter(S+"t")) for si in root.findall(S+"si")]
    def decode(cell):
        if cell is None:
            return ""
        if cell.find(S+"f") is not None:
            raise ValueError("Formula present in audited source field")
        value=cell.find(S+"v")
        kind=cell.get("t")
        if kind=="s":
            if value is None or value.text is None:
                return ""
            idx=int(value.text)
            if idx<0 or idx>=len(strings):
                raise ValueError("Invalid shared-string reference")
            return strings[idx]
        if kind=="inlineStr":
            inline=cell.find(S+"is")
            return "".join(t.text or "" for t in inline.iter(S+"t")) if inline is not None else ""
        return value.text if value is not None and value.text is not None else ""
    return decode


def eligible_group1_source_rows(raw: bytes, headers: list[str], rules: dict) -> list[dict]:
    """Apply the already-frozen Group-2 eligibility rules to source group=1 unchanged."""
    with ZipFile(BytesIO(raw)) as book:
        if sum(x.file_size for x in book.infolist())>8_000_000:
            raise ValueError("Source decompression bound exceeded")
        decode=_decoder(book)
        root=ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        dim=root.find(S+"dimension")
        if dim is None or dim.get("ref")!="A1:P253":
            raise ValueError("Rawdata dimension drift")
        data=root.find(S+"sheetData")
        if data is None:
            raise ValueError("Missing Rawdata sheetData")
        rows=data.findall(S+"row")
        header=next((r for r in rows if r.get("r")=="1"),None)
        if header is None or [decode(c) for c in header.findall(S+"c")]!=headers:
            raise ValueError("Source headers differ from H1 pin")

        allowed={
            "Dataset":set(rules["rules"]["year"]["allowed"]),
            "GEST":set(rules["rules"]["gesture"]["allowed"]),
            "face":set(rules["rules"]["face"]["allowed"]),
            "context_dyad":set(rules["rules"]["context"]["allowed"]),
            "REACT":set(rules["rules"]["response"]["allowed"]),
        }
        source_rows=0
        eligible=[]
        for row in rows:
            n=int(row.get("r","0"))
            if n<=1:
                continue
            cells={c.get("r"):c for c in row.findall(S+"c")}
            group=decode(cells.get(f"F{n}")).strip()
            if group!="1":
                continue
            source_rows+=1
            values={name:decode(cells.get(f"{col}{n}")).strip() for name,col in COLS.items()}
            initiator,recipient=values["initiator"],values["recipient"]
            valid=(
                bool(initiator) and bool(recipient) and initiator!=recipient
                and values["Dataset"] in allowed["Dataset"]
                and values["GEST"] in allowed["GEST"]
                and values["face"] in allowed["face"] and values["face"]!="NA"
                and values["context_dyad"] in allowed["context_dyad"] and values["context_dyad"]!="NA"
                and values["REACT"] in allowed["REACT"] and values["REACT"]!="NA"
            )
            if valid:
                values["source_row"]=n
                eligible.append(values)
        if source_rows!=103:
            raise ValueError("Group-1 source row count differs from frozen published 103")
        return eligible


def normalize_group1(
    rows: list[dict],
    pins: dict,
    crosswalk: dict,
    secret: bytes,
) -> tuple[pd.DataFrame, bytes]:
    gesture_map=_crosswalk_field(crosswalk,"Gesture_Class")["native_mapping"]
    face_map=_crosswalk_field(crosswalk,"Facial_Expression_Class")["native_mapping"]
    context_map=_crosswalk_field(crosswalk,"Social_Context")["native_mapping"]
    response_map=_crosswalk_field(crosswalk,"Recipient_Response")["native_mapping"]
    group_map=_crosswalk_field(crosswalk,"Group_ID")["native_mapping"]
    rank_unknown=_crosswalk_field(crosswalk,"Rank_Relationship")["normalization"]["NA"]

    normalized=[]
    restricted=[]
    for src in rows:
        n=int(src["source_row"])
        initiator=pseudonymize_source_id(src["initiator"],secret)
        recipient=pseudonymize_source_id(src["recipient"],secret)
        dyad=unordered_dyad_id(initiator,recipient)
        event_id=canonical_event_id(
            source_sha256=pins["file"]["sha256"],sheet="Rawdata",original_row=n
        )
        locator=f"figshare:9192509.v1/file:16741928/sheet:Rawdata/row:{n}"
        gesture=gesture_map[src["GEST"]]
        face=face_map[src["face"]]
        context=context_map[src["context_dyad"]]
        response=response_map[src["REACT"]]
        rank=rank_unknown if src["rel_dom"]=="NA" else src["rel_dom"]
        normalized.append({
            "Event_ID":event_id,
            "Source_Row_Locator":locator,
            "Group_ID":group_map["1"],
            "Initiator_ID":initiator,
            "Recipient_ID":recipient,
            "Dyad_ID":dyad,
            "Initiator_Sex":src["sex_init"] or "UNKNOWN",
            "Recipient_Sex":src["sex_rec"] or "UNKNOWN",
            "Rank_Relationship":rank,
            "Collection_Year":src["Dataset"],
            "Gesture_Class":gesture,
            "Facial_Expression_Class":face,
            "Social_Context":context,
            "Recipient_Response":response,
            "Signal_Configuration":gesture+"|"+face,
            "Coding_Visibility_or_Quality":"PRIMARY_REQUIRED_FIELDS_OBSERVED_OR_MAPPABLE",
            "Rights_and_Reuse_State":"FIGSHARE_ITEM_CC_BY_4_OBSERVED_LOCAL_RESEARCH_REUSE",
            "Source_Record_Provenance":locator+";sha256:"+pins["file"]["sha256"],
        })
        restricted.append({
            "Event_ID":event_id,"source_row":n,"source_event_secondary":src["event"],
            "source_initiator":src["initiator"],"source_recipient":src["recipient"],
            "source_dyad":src["dyad"],"Initiator_ID":initiator,
            "Recipient_ID":recipient,"Dyad_ID":dyad,
        })
    frame=pd.DataFrame(normalized,columns=NORMALIZED_FIELDS)
    if frame.empty:
        raise ValueError("No eligible locked Group-1 rows")
    if frame["Event_ID"].duplicated().any():
        raise ValueError("Group-1 Event_ID collision")
    restricted_bytes=("".join(json.dumps(r,sort_keys=True)+"\n" for r in restricted)).encode()
    return frame,restricted_bytes


def _add_interactions(frame: pd.DataFrame) -> pd.DataFrame:
    work=frame.copy().reset_index(drop=True)
    work["__Gesture_x_Context"]=work["Gesture_Class"].astype(str)+"||"+work["Social_Context"].astype(str)
    work["__Face_x_Context"]=work["Facial_Expression_Class"].astype(str)+"||"+work["Social_Context"].astype(str)
    work["__Gesture_x_Face"]=work["Gesture_Class"].astype(str)+"||"+work["Facial_Expression_Class"].astype(str)
    work["__Gesture_x_Face_x_Context"]=(
        work["Gesture_Class"].astype(str)+"||"+
        work["Facial_Expression_Class"].astype(str)+"||"+
        work["Social_Context"].astype(str)
    )
    return work


def evaluate_locked_group1(
    group1: pd.DataFrame,
    freeze_manifest: dict[str,Any],
    freeze_dir: Path,
) -> tuple[dict[str,Any],pd.DataFrame]:
    _verify_frozen_model_artifacts(freeze_manifest,freeze_dir)
    if set(group1["Group_ID"].astype(str).unique())!={"Group 1"}:
        raise ValueError("RUN-006 accepts Group 1 rows only")
    if group1["Event_ID"].isna().any() or group1["Event_ID"].duplicated().any():
        raise ValueError("Group-1 Event_ID must be nonmissing and unique")
    for col in NORMALIZED_FIELDS:
        if col not in group1.columns:
            raise ValueError(f"Missing Group-1 normalized field {col}")
    if group1["Recipient_Response"].isna().any():
        raise ValueError("Group-1 response cannot be missing after frozen eligibility")

    with (freeze_dir/"run005_full_group2_b1.pkl").open("rb") as f:
        b1=pickle.load(f)
    with (freeze_dir/"run005_full_group2_b2.pkl").open("rb") as f:
        b2=pickle.load(f)

    work=_add_interactions(group1)
    y=work["Recipient_Response"].map({"affiliative":1,"non_affiliative":0})
    if y.isna().any() or not set(y.unique()).issubset({0,1}) or len(y)==0:
        raise ValueError("RUN-006 contains an invalid registered response code")
    yv=y.to_numpy(dtype=int)
    p1=b1.predict_proba(work)[:,1]
    p2=b2.predict_proba(work)[:,1]
    if not np.isfinite(p1).all() or not np.isfinite(p2).all():
        raise RuntimeError("Non-finite locked Group-1 predictions")

    def metrics(p):
        auc=float(roc_auc_score(yv,p)) if len(np.unique(yv))==2 else None
        return {
            "log_loss":float(log_loss(yv,p,labels=[0,1])),
            "brier":float(brier_score_loss(yv,p)),
            "roc_auc":auc,
        }
    m1,m2=metrics(p1),metrics(p2)
    transfer_delta=m2["log_loss"]-m1["log_loss"]
    development_delta=float(freeze_manifest["primary_delta_log_loss_b2_minus_b1"])
    dev_improves=development_delta<0
    transfer_improves=transfer_delta<0
    if dev_improves and transfer_improves:
        disposition="BOUNDED_H0001_SUPPORT"
    elif dev_improves != transfer_improves:
        disposition="MIXED"
    else:
        disposition="NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"

    predictions=pd.DataFrame({
        "Event_ID":work["Event_ID"].astype(str),
        "Observed_Response":work["Recipient_Response"].astype(str),
        "B1_P_affiliative":p1,
        "B2_P_affiliative":p2,
    })
    result={
        "protocol_id":"PR0005","run_id":"RUN-006",
        "group1_rows":int(len(work)),
        "B1":m1,"B2":m2,
        "locked_group1_delta_log_loss_b2_minus_b1":float(transfer_delta),
        "run005_primary_delta_log_loss_b2_minus_b1":development_delta,
        "final_pr0005_disposition":disposition,
        "models_refit_on_group1":False,
        "preprocessing_refit_on_group1":False,
        "group1_accessed":True,
        "claim_scope":"D0019_SOURCE_CODED_ENDPOINT_ONLY",
        "crg_c_credit":"REQUIRES_SEPARATE_ADJUDICATION",
    }
    return result,predictions


def run_d0019_group1_transfer(
    *,
    item: dict,
    pins: dict,
    crosswalk: dict,
    eligibility: dict,
    group1_procedure: dict,
    run005_freeze_manifest: dict,
    run005_freeze_dir: Path,
    secret: bytes,
    fetch: Callable[[str,int],bytes],
    output_dir: Path,
    evidence_weight: str,
) -> dict[str,Any]:
    """One-time locked transfer. Group-1 source fetch happens only after RUN-005 freeze validation."""
    validate_run005_freeze_before_group1(
        run005_freeze_manifest,run005_freeze_dir,secret,evidence_weight=evidence_weight
    )
    if group1_procedure.get("status")!="FROZEN_BEFORE_GROUP1_NONPARTITION_ACCESS":
        raise ValueError("Group-1 transfer procedure is not frozen")
    if group1_procedure.get("source_sha256")!=pins["file"]["sha256"]:
        raise ValueError("Group-1 procedure source SHA differs from pinned source")
    if crosswalk.get("version")!="source-crosswalk-v0.2":
        raise ValueError("RDC-004 crosswalk v0.2 required")
    if item.get("id")!=pins["source_item_id"] or item.get("version")!=1 or item.get("doi")!=pins["doi"]:
        raise ValueError("D0019 source identity mismatch")
    lic=item.get("license") or {}
    if not isinstance(lic,dict) or {k:lic.get(k) for k in ("name","url")}!=pins["license_as_reported"]:
        raise ValueError("D0019 item license metadata mismatch")
    files=item.get("files")
    if not isinstance(files,list) or len(files)!=1:
        raise ValueError("D0019 source file inventory mismatch")
    f=files[0]; expected=pins["file"]
    if (
        f.get("id")!=expected["id"] or f.get("name")!=expected["name"]
        or f.get("size")!=expected["bytes"]
        or (f.get("computed_md5") or f.get("supplied_md5"))!=expected["md5"]
    ):
        raise ValueError("D0019 source file metadata drift")
    parsed=urlparse(str(f.get("download_url")))
    if parsed.scheme!="https" or parsed.hostname!="ndownloader.figshare.com" or parsed.path!=f"/files/{expected['id']}":
        raise ValueError("Unexpected D0019 source URL")

    raw=fetch(f.get("download_url"),expected["bytes"])
    if len(raw)!=expected["bytes"] or _sha256_bytes(raw)!=expected["sha256"]:
        raise ValueError("D0019 source bytes differ from H1 pin")

    rows=eligible_group1_source_rows(raw,pins["sheets"][0]["source_header_candidates"],eligibility)
    group1,restricted_bytes=normalize_group1(rows,pins,crosswalk,secret)
    result,predictions=evaluate_locked_group1(group1,run005_freeze_manifest,run005_freeze_dir)

    output_dir.mkdir(parents=True,exist_ok=True)
    normalized_path=output_dir/"run006_group1_normalized.csv"
    restricted_path=output_dir/"run006_group1_restricted_provenance.jsonl"
    predictions_path=output_dir/"run006_group1_predictions.csv"
    result_path=output_dir/"run006_result.json"

    group1.to_csv(normalized_path,index=False)
    restricted_path.write_bytes(restricted_bytes)
    predictions.to_csv(predictions_path,index=False)
    result.update({
        "evidence_weight":evidence_weight,
        "source_sha256":pins["file"]["sha256"],
        "identity_namespace_fingerprint":_namespace_fingerprint(bytes(secret)),
        "run005_freeze_manifest_sha256":_sha256_file(run005_freeze_dir/"run005_freeze_manifest.json"),
        "group1_eligible_source_row_set_sha256":hashlib.sha256(
            ("D0019_GROUP1_ELIGIBLE_V0.1|"+pins["file"]["sha256"]+"|"+
             ",".join(str(r["source_row"]) for r in rows)).encode()
        ).hexdigest(),
        "scientific_claim_admissible":evidence_weight=="D0019_EMPIRICAL",
    })
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")

    artifacts={
        p.name:_sha256_file(p)
        for p in (normalized_path,restricted_path,predictions_path,result_path)
    }
    manifest={
        "dataset_id":"D0019" if evidence_weight=="D0019_EMPIRICAL" else "ZERO_SYNTHETIC",
        "protocol_id":"PR0005","run_id":"RUN-006","transfer_version":"v0.1",
        "evidence_weight":evidence_weight,
        "source_sha256":pins["file"]["sha256"],
        "identity_namespace_fingerprint":_namespace_fingerprint(bytes(secret)),
        "run005_freeze_manifest_sha256":_sha256_file(run005_freeze_dir/"run005_freeze_manifest.json"),
        "group1_source_rows_before_exclusions":103,
        "group1_eligible_rows":len(group1),
        "models_refit_on_group1":False,
        "preprocessing_refit_on_group1":False,
        "final_pr0005_disposition":result["final_pr0005_disposition"],
        "artifacts_sha256":artifacts,
        "crg_c_credit":"REQUIRES_SEPARATE_ADJUDICATION",
        "boundary":"One-time locked D0019 transfer; Group-1 result cannot alter RUN-005.",
    }
    manifest_path=output_dir/"run006_transfer_manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest
