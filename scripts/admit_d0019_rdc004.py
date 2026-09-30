"""Final pre-model RDC-004 admission and secret-backed D0019 Group-2 materializer."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from ars_receiver_harness.d0019_ids import (
    canonical_event_id,
    pseudonymize_source_id,
    unordered_dyad_id,
)
try:
    from scripts.audit_d0019_group2_eligibility import group2_eligibility
    from scripts.audit_d0019_split_support import split_support
except ModuleNotFoundError:
    from audit_d0019_group2_eligibility import group2_eligibility
    from audit_d0019_split_support import split_support

S="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLS={
    "Dataset":"A","event":"B","initiator":"E","group":"F","sex_init":"G",
    "recipient":"I","sex_rec":"J","dyad":"K","rel_dom":"L","face":"M",
    "context_dyad":"N","GEST":"O","REACT":"P",
}
NORMALIZED_FIELDS=[
    "Event_ID","Source_Row_Locator","Group_ID","Initiator_ID","Recipient_ID","Dyad_ID",
    "Initiator_Sex","Recipient_Sex","Rank_Relationship","Collection_Year",
    "Gesture_Class","Facial_Expression_Class","Social_Context","Recipient_Response",
    "Signal_Configuration","Coding_Visibility_or_Quality","Rights_and_Reuse_State",
    "Source_Record_Provenance",
]


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
        v=cell.find(S+"v")
        kind=cell.get("t")
        if kind=="s":
            if v is None or v.text is None:
                return ""
            idx=int(v.text)
            if idx<0 or idx>=len(strings):
                raise ValueError("Invalid shared-string index")
            return strings[idx]
        if kind=="inlineStr":
            inline=cell.find(S+"is")
            return "".join(x.text or "" for x in inline.iter(S+"t")) if inline is not None else ""
        return v.text if v is not None and v.text is not None else ""
    return decode


def _crosswalk_field(crosswalk: dict, name: str) -> dict:
    match=[x for x in crosswalk.get("fields",[]) if x.get("field")==name]
    if len(match)!=1:
        raise ValueError(f"Expected exactly one crosswalk field {name}")
    return match[0]


def _eligible_rows_for_materialization(raw: bytes, headers: list[str], rules: dict) -> list[dict]:
    """Decode Group 2 only and return eligible source rows in original order."""
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
            raise ValueError("Source header differs from H1 pin")

        allowed={
            "Dataset":set(rules["rules"]["year"]["allowed"]),
            "GEST":set(rules["rules"]["gesture"]["allowed"]),
            "face":set(rules["rules"]["face"]["allowed"]),
            "context_dyad":set(rules["rules"]["context"]["allowed"]),
            "REACT":set(rules["rules"]["response"]["allowed"]),
        }
        eligible=[]
        for row in rows:
            n=int(row.get("r","0"))
            if n<=1:
                continue
            cells={c.get("r"):c for c in row.findall(S+"c")}
            group=decode(cells.get(f"F{n}")).strip()
            if group!="2":
                continue
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
        return eligible


def _validate_contracts(pins: dict,crosswalk: dict,amendment1: dict,eligibility: dict,split_policy: dict,admission: dict,group1: dict) -> None:
    if pins.get("file",{}).get("sha256")!=admission.get("source_sha256"):
        raise ValueError("Final admission source SHA differs from H1 pin")
    if crosswalk.get("version")!="source-crosswalk-v0.2":
        raise ValueError("RDC-004 crosswalk v0.2 required")
    if crosswalk.get("source_sha256")!=pins["file"]["sha256"]:
        raise ValueError("Crosswalk source SHA differs from H1 pin")
    if crosswalk.get("empirical_admission") is not False:
        raise ValueError("Crosswalk must remain pre-model until this gate completes")
    if amendment1.get("status")!="FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT":
        raise ValueError("PD-PR0005-001 is not frozen")
    if amendment1.get("evidence",{}).get("source_sha256")!=pins["file"]["sha256"]:
        raise ValueError("PD-PR0005-001 source SHA differs from H1 pin")
    if eligibility.get("status")!="FROZEN_PRE_MODEL_GROUP2_ELIGIBILITY":
        raise ValueError("H4 eligibility rules are not frozen")
    if split_policy.get("status")!="FROZEN_PRE_OUTCOME_PERFORMANCE":
        raise ValueError("PD-PR0005-002 is not frozen")
    if admission.get("status")!="FROZEN_FINAL_PRE_MODEL_ADMISSION":
        raise ValueError("Final admission contract is not frozen")
    if group1.get("status")!="FROZEN_BEFORE_GROUP1_NONPARTITION_ACCESS":
        raise ValueError("Group-1 transfer procedure is not frozen")
    if group1.get("source_sha256")!=pins["file"]["sha256"]:
        raise ValueError("Group-1 transfer procedure source pin differs")
    required={
        "Gesture_Class":"APPROVED_SOURCE_MAPPING",
        "Facial_Expression_Class":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
        "Social_Context":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
        "Recipient_Response":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
        "Dyad_ID":"APPROVED_UNORDERED_DYAD_DERIVATION_PRE_OUTCOME_AMENDMENT",
        "Rights_and_Reuse_State":"APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED",
        "Source_Record_Provenance":"APPROVED_PROVENANCE_SCHEMA",
    }
    for field,status in required.items():
        if _crosswalk_field(crosswalk,field).get("status")!=status:
            raise ValueError(f"Crosswalk field {field} is not at the required frozen state")


def final_admission(item: dict,pins: dict,crosswalk: dict,amendment1: dict,eligibility: dict,split_policy: dict,admission: dict,group1: dict,fetch) -> tuple[dict,bytes]:
    """Return aggregate admission receipt plus verified raw bytes kept in memory only."""
    receipt={
        "dataset_id":"D0019","phase":"H6_FINAL_RDC004_ADMISSION",
        "state":"HELD_FINAL_ADMISSION","source_bytes_stored":False,
        "group1_holdout_opened":False,"group1_outcomes_accessed":False,
        "rdc004_empirical_admission":False,"pr0005_executed":False,
        "scientific_effect":"NONE","crg_c_credit":"UNMET",
    }
    try:
        _validate_contracts(pins,crosswalk,amendment1,eligibility,split_policy,admission,group1)
    except (ValueError,TypeError,KeyError) as exc:
        receipt["state"]="HELD_CONTRACT_MISMATCH"
        receipt["error_type"]=type(exc).__name__
        receipt["error_summary"]=str(exc)[:180]
        return receipt,b""
    if item.get("id")!=pins["source_item_id"] or item.get("version")!=1 or item.get("doi")!=pins["doi"]:
        receipt["state"]="HELD_SOURCE_IDENTITY"; return receipt,b""
    lic=item.get("license") or {}
    if not isinstance(lic,dict) or {k:lic.get(k) for k in ("name","url")}!=pins["license_as_reported"]:
        receipt["state"]="HELD_LICENSE"; return receipt,b""
    files=item.get("files")
    if not isinstance(files,list) or len(files)!=1:
        receipt["state"]="HELD_FILE_INVENTORY"; return receipt,b""
    f=files[0]; expected=pins["file"]
    if (
        f.get("id")!=expected["id"] or f.get("name")!=expected["name"]
        or f.get("size")!=expected["bytes"]
        or (f.get("computed_md5") or f.get("supplied_md5"))!=expected["md5"]
    ):
        receipt["state"]="QUARANTINED_SOURCE_DRIFT"; return receipt,b""
    parsed=urlparse(str(f.get("download_url")))
    if parsed.scheme!="https" or parsed.hostname!="ndownloader.figshare.com" or parsed.path!=f"/files/{expected['id']}":
        receipt["state"]="QUARANTINED_SOURCE_LOCATION"; return receipt,b""
    try:
        raw=fetch(f.get("download_url"),expected["bytes"])
        if len(raw)!=expected["bytes"] or hashlib.sha256(raw).hexdigest()!=expected["sha256"]:
            raise ValueError("Source bytes differ from H1 SHA-256")
        h4=group2_eligibility(raw,pins["sheets"][0]["source_header_candidates"],eligibility)
        h5=split_support(raw,pins["sheets"][0]["source_header_candidates"],eligibility,split_policy)
        if (
            h4["eligible_primary_rows"]!=admission["dependencies"]["eligible_rows"]
            or h4["eligible_source_row_set_sha256"]!=admission["dependencies"]["eligible_source_row_set_sha256"]
            or h4["eligible_unordered_dyad_count"]!=admission["dependencies"]["primary_unordered_dyads"]
            or not h4["all_tokens_within_frozen_domains"]
            or not h5["support_gate_passed"]
            or h5["eligible_source_row_set_sha256"]!=h4["eligible_source_row_set_sha256"]
        ):
            receipt["state"]="HELD_RECOMPUTED_H4_H5_MISMATCH"; return receipt,b""
        receipt["admission_checks"]={
            "source_sha256_verified":True,
            "item_license_metadata_verified":True,
            "crosswalk_and_amendments_frozen":True,
            "group2_eligible_rows":h4["eligible_primary_rows"],
            "eligible_source_row_set_sha256":h4["eligible_source_row_set_sha256"],
            "eligible_unordered_dyads":h4["eligible_unordered_dyad_count"],
            "primary_split_support_passed":h5["primary_leave_unordered_dyad_out"]["all_training_folds_have_both_registered_response_classes"],
            "robustness_split_support_passed":h5["robustness_leave_initiator_out"]["all_training_folds_have_both_registered_response_classes"],
            "group1_transfer_procedure_frozen":True,
            "outcome_frequencies_emitted":False,
            "group1_nonpartition_cells_decoded":False,
        }
        receipt["final_premodel_gates_passed"]=True
        receipt["rdc004_empirical_admission"]=False
        receipt["state"]="RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"
        return receipt,raw
    except (OSError,ValueError,TypeError,KeyError,IndexError,BadZipFile,ET.ParseError) as exc:
        receipt["state"]="HELD_FINAL_ADMISSION_SOURCE"
        receipt["error_type"]=type(exc).__name__
        receipt["error_summary"]=str(exc)[:180]
        return receipt,b""


def materialize_group2(raw: bytes,pins: dict,crosswalk: dict,eligibility: dict,admission: dict,secret: bytes,output_dir: Path) -> dict:
    min_bytes=int(admission["materialization"]["minimum_secret_bytes"])
    if not isinstance(secret,(bytes,bytearray)) or len(secret)<min_bytes:
        raise ValueError(f"ARS_D0019_HMAC_KEY must be at least {min_bytes} bytes")
    rows=_eligible_rows_for_materialization(raw,pins["sheets"][0]["source_header_candidates"],eligibility)
    if len(rows)!=admission["dependencies"]["eligible_rows"]:
        raise ValueError("Eligible row count changed before materialization")

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
        record={
            "Event_ID":event_id,
            "Source_Row_Locator":locator,
            "Group_ID":group_map["2"],
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
        }
        normalized.append(record)
        restricted.append({
            "Event_ID":event_id,"source_row":n,"source_event_secondary":src["event"],
            "source_initiator":src["initiator"],"source_recipient":src["recipient"],
            "source_dyad":src["dyad"],"Initiator_ID":initiator,
            "Recipient_ID":recipient,"Dyad_ID":dyad,
        })

    if len({r["Event_ID"] for r in normalized})!=len(normalized):
        raise ValueError("Canonical Event_ID collision")
    row_digest=hashlib.sha256(
        ("D0019_ELIGIBLE_V0.1|"+pins["file"]["sha256"]+"|"+
         ",".join(str(r["source_row"]) for r in restricted)).encode()
    ).hexdigest()
    if row_digest!=admission["dependencies"]["eligible_source_row_set_sha256"]:
        raise ValueError("Materialized row set differs from H4 freeze")

    output_dir.mkdir(parents=True,exist_ok=True)
    csv_path=output_dir/admission["materialization"]["normalized_group2_filename"]
    restricted_path=output_dir/admission["materialization"]["restricted_provenance_filename"]
    manifest_path=output_dir/admission["materialization"]["manifest_filename"]

    buffer=StringIO()
    writer=csv.DictWriter(buffer,fieldnames=NORMALIZED_FIELDS,lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized)
    csv_bytes=buffer.getvalue().encode()
    csv_path.write_bytes(csv_bytes)

    restricted_bytes=("".join(json.dumps(r,sort_keys=True)+"\n" for r in restricted)).encode()
    restricted_path.write_bytes(restricted_bytes)

    namespace_id=hashlib.sha256(
        b"D0019_NAMESPACE_PUBLIC_FINGERPRINT|"+
        hashlib.sha256(bytes(secret)).digest()
    ).hexdigest()
    manifest={
        "dataset_id":"D0019","materialization_version":"v0.1",
        "source_sha256":pins["file"]["sha256"],
        "eligible_source_row_set_sha256":row_digest,
        "normalized_rows":len(normalized),
        "normalized_fields":NORMALIZED_FIELDS,
        "normalized_csv_sha256":hashlib.sha256(csv_bytes).hexdigest(),
        "restricted_provenance_sha256":hashlib.sha256(restricted_bytes).hexdigest(),
        "identity_namespace_fingerprint":namespace_id,
        "raw_source_identities_in_normalized_csv":False,
        "group1_rows_materialized":False,
        "pr0005_executed":False,
        "scientific_effect":"NONE",
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest


def main():
    ap=argparse.ArgumentParser(description="Final D0019 RDC-004 admission; optional secret-backed Group-2 materialization")
    ap.add_argument("--pins",default="contracts/d0019_v1_verified_source_snapshot.json")
    ap.add_argument("--crosswalk",default="contracts/d0019_rdc004_source_crosswalk_v0_2.json")
    ap.add_argument("--amendment1",default="contracts/pr0005_pd_001_grouping_amendment.json")
    ap.add_argument("--eligibility",default="contracts/d0019_group2_eligibility_rules_v0_1.json")
    ap.add_argument("--split-policy",default="contracts/pr0005_pd_002_split_policy.json")
    ap.add_argument("--admission",default="contracts/d0019_rdc004_final_admission_v0_1.json")
    ap.add_argument("--group1-procedure",default="contracts/d0019_group1_transfer_procedure_v0_1.json")
    ap.add_argument("--out",default="build/d0019_final_admission.json")
    ap.add_argument("--materialize-dir",default=None)
    args=ap.parse_args()
    try:
        from scripts.probe_d0019_source import public_item,fetch_source
    except ModuleNotFoundError:
        from probe_d0019_source import public_item,fetch_source

    paths=(args.pins,args.crosswalk,args.amendment1,args.eligibility,args.split_policy,args.admission,args.group1_procedure)
    objs=[json.loads(Path(p).read_text()) for p in paths]
    try:
        receipt,raw=final_admission(public_item(),*objs,fetch_source)
        if receipt.get("final_premodel_gates_passed") and args.materialize_dir:
            secret=os.environ.get("ARS_D0019_HMAC_KEY","").encode()
            if not secret:
                receipt["state"]="HELD_MATERIALIZATION_KEY"
                receipt["materialization_error"]="ARS_D0019_HMAC_KEY is not configured"
            else:
                manifest=materialize_group2(
                    raw,objs[0],objs[1],objs[3],objs[5],secret,Path(args.materialize_dir)
                )
                receipt["materialization"]=manifest
                receipt["rdc004_empirical_admission"]=True
                receipt["state"]="RDC004_GROUP2_MATERIALIZED_PR0005_READY"
    except (OSError,ValueError,TypeError,KeyError) as exc:
        receipt={"dataset_id":"D0019","phase":"H6_FINAL_RDC004_ADMISSION",
                 "state":"HELD_FINAL_ADMISSION","error_type":type(exc).__name__,
                 "error_summary":str(exc)[:180],"source_bytes_stored":False,
                 "group1_holdout_opened":False,"group1_outcomes_accessed":False,
                 "rdc004_empirical_admission":False,"pr0005_executed":False}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({
        "state":receipt["state"],
        "rdc004_empirical_admission":receipt.get("rdc004_empirical_admission",False),
        "group2_materialized":"materialization" in receipt,
        "group1_outcomes_accessed":False,"pr0005_executed":False,"output":str(out)
    }))


if __name__=="__main__":
    main()
