import csv
import hashlib
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from scripts.admit_d0019_rdc004 import final_admission, materialize_group2

HEADERS=[
    "Dataset","event","clip_old","time","initiator","group","sex_init","ini_approaching",
    "recipient","sex_rec","dyad","rel_dom","face","context_dyad","GEST","REACT"
]


def synthetic_workbook():
    header="".join(
        f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i,name in enumerate(HEADERS)
    )
    rows=[f'<row r="1">{header}</row>']
    eligible_idx=0
    for idx in range(252):
        n=idx+2
        group="1" if idx<103 else "2"
        cells=[f'<c r="F{n}"><v>{group}</v></c>']
        if group=="1":
            cells += [
                f'<c r="E{n}" t="inlineStr"><is><t>RAW_GROUP1_I_{idx}</t></is></c>',
                f'<c r="P{n}" t="inlineStr"><is><t>SECRET_GROUP1_OUTCOME_{idx}</t></is></c>',
            ]
        else:
            local=idx-103
            excluded=local>=104
            d=eligible_idx if not excluded and eligible_idx<69 else (
                eligible_idx-69 if not excluded else local%69
            )
            initiator=f"RAW_I_{d}"
            recipient=f"RAW_R_{d}"
            if not excluded:
                eligible_idx+=1
            face="NA" if excluded else ("bared" if local%3==0 else "neutral")
            context="pos" if local%2==0 else "neg"
            response="affil" if local%2==0 else "avoid"
            rank="NA" if local==3 else ("todom" if local%2==0 else "nottodom")
            cells += [
                f'<c r="A{n}"><v>{2015 if local%2==0 else 2016}</v></c>',
                f'<c r="B{n}"><v>{local%80+1}</v></c>',
                f'<c r="E{n}" t="inlineStr"><is><t>{initiator}</t></is></c>',
                f'<c r="G{n}" t="inlineStr"><is><t>{"female" if local%2==0 else "male"}</t></is></c>',
                f'<c r="I{n}" t="inlineStr"><is><t>{recipient}</t></is></c>',
                f'<c r="J{n}" t="inlineStr"><is><t>{"male" if local%2==0 else "female"}</t></is></c>',
                f'<c r="K{n}" t="inlineStr"><is><t>SOURCE_DYAD_{d}</t></is></c>',
                f'<c r="L{n}" t="inlineStr"><is><t>{rank}</t></is></c>',
                f'<c r="M{n}" t="inlineStr"><is><t>{face}</t></is></c>',
                f'<c r="N{n}" t="inlineStr"><is><t>{context}</t></is></c>',
                f'<c r="O{n}" t="inlineStr"><is><t>{"SG" if local%2==0 else "BG"}</t></is></c>',
                f'<c r="P{n}" t="inlineStr"><is><t>{response}</t></is></c>',
            ]
        rows.append(f'<row r="{n}">{"".join(cells)}</row>')
    xml=(
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:P253"/><sheetData>'+"".join(rows)+'</sheetData></worksheet>'
    )
    buf=BytesIO()
    with ZipFile(buf,"w") as z:
        z.writestr("xl/worksheets/sheet1.xml",xml)
    return buf.getvalue()


def objects(raw):
    sha=hashlib.sha256(raw).hexdigest()
    md5=hashlib.md5(raw).hexdigest()
    source_rows=list(range(105,209))
    eligible_digest=hashlib.sha256(
        ("D0019_ELIGIBLE_V0.1|"+sha+"|"+",".join(map(str,source_rows))).encode()
    ).hexdigest()
    pins={
        "source_item_id":9192509,"version":1,"doi":"10.6084/m9.figshare.9192509.v1",
        "license_as_reported":{"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"},
        "file":{"id":16741928,"name":"Rawdata_Compositionality.xlsx","bytes":len(raw),"md5":md5,"sha256":sha},
        "sheets":[{"source_header_candidates":HEADERS}],
    }
    crosswalk={
        "version":"source-crosswalk-v0.2","empirical_admission":False,
        "fields":[
            {"field":"Group_ID","status":"APPROVED_SOURCE_MAPPING","native_mapping":{"1":"Group 1","2":"Group 2"}},
            {"field":"Dyad_ID","status":"APPROVED_UNORDERED_DYAD_DERIVATION_PRE_OUTCOME_AMENDMENT"},
            {"field":"Gesture_Class","status":"APPROVED_SOURCE_MAPPING","native_mapping":{"SG":"stretched_arm","BG":"bent_arm"}},
            {"field":"Facial_Expression_Class","status":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
             "native_mapping":{"neutral":"neutral","bared":"bared_teeth","hoot":"funneled_lip_hoot","NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Social_Context","status":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
             "native_mapping":{"pos":"positive_affiliative_context","neg":"negative_agonistic_context","NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Recipient_Response","status":"PARTIAL_APPROVED_NA_NON_SUBSTANTIVE",
             "native_mapping":{"affil":"affiliative","avoid":"non_affiliative","NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Rank_Relationship","status":"APPROVED_FIELD_ROLE_NATIVE_TOKENS_UNGLOSSED",
             "normalization":{"NA":"SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE"}},
            {"field":"Rights_and_Reuse_State","status":"APPROVED_LOCAL_RESEARCH_REUSE_WITH_ATTRIBUTION_RAW_REDISTRIBUTION_NOT_NEEDED"},
            {"field":"Source_Record_Provenance","status":"APPROVED_PROVENANCE_SCHEMA"},
        ]
    }
    amendment1={"status":"FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT"}
    eligibility={
        "status":"FROZEN_PRE_MODEL_GROUP2_ELIGIBILITY","eligibility_version":"v0.1","source_sha256":sha,
        "rules":{
            "year":{"allowed":["2015","2016"]},
            "initiator_sex":{"allowed":["female","male"]},
            "recipient_sex":{"allowed":["female","male"]},
            "rank_relationship":{"allowed":["todom","nottodom","NA"]},
            "gesture":{"allowed":["SG","BG"]},
            "face":{"allowed":["neutral","bared","hoot","NA"]},
            "context":{"allowed":["pos","neg","NA"]},
            "response":{"allowed":["affil","avoid","NA"]},
        }
    }
    split_policy={
        "status":"FROZEN_PRE_OUTCOME_PERFORMANCE","deviation_id":"PD-PR0005-002",
        "support_gate":{"eligible_source_rows_digest":eligible_digest,
                        "expected_eligible_rows":104,"expected_unordered_dyads":69}
    }
    admission={
        "status":"FROZEN_FINAL_PRE_MODEL_ADMISSION","source_sha256":sha,
        "dependencies":{"eligible_rows":104,"eligible_source_row_set_sha256":eligible_digest,
                        "primary_unordered_dyads":69},
        "materialization":{"minimum_secret_bytes":32,
                           "normalized_group2_filename":"d0019_group2_normalized.csv",
                           "restricted_provenance_filename":"d0019_group2_restricted_provenance.jsonl",
                           "manifest_filename":"d0019_group2_materialization_manifest.json"}
    }
    group1={"status":"FROZEN_BEFORE_GROUP1_NONPARTITION_ACCESS","source_sha256":sha}
    item={
        "id":9192509,"version":1,"doi":pins["doi"],"license":dict(pins["license_as_reported"]),
        "files":[{"id":16741928,"name":pins["file"]["name"],"size":len(raw),"computed_md5":md5,
                  "download_url":"https://ndownloader.figshare.com/files/16741928"}],
    }
    return item,pins,crosswalk,amendment1,eligibility,split_policy,admission,group1


def test_final_premodel_gates_pass_without_materialization():
    raw=synthetic_workbook()
    objs=objects(raw)
    receipt,verified=final_admission(*objs,lambda url,size:raw)
    assert receipt["state"]=="RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"
    assert receipt["final_premodel_gates_passed"] is True
    assert receipt["rdc004_empirical_admission"] is False
    assert receipt["admission_checks"]["group2_eligible_rows"]==104
    assert receipt["group1_outcomes_accessed"] is False
    assert verified==raw
    assert "SECRET_GROUP1_OUTCOME" not in str(receipt)


def test_secret_backed_materialization_deidentifies_research_table(tmp_path):
    raw=synthetic_workbook()
    _,pins,crosswalk,_,eligibility,_,admission,_=objects(raw)
    manifest=materialize_group2(
        raw,pins,crosswalk,eligibility,admission,b"x"*32,tmp_path
    )
    assert manifest["normalized_rows"]==104
    assert manifest["raw_source_identities_in_normalized_csv"] is False
    assert manifest["group1_rows_materialized"] is False
    csv_text=(tmp_path/"d0019_group2_normalized.csv").read_text()
    assert "RAW_I_" not in csv_text
    assert "RAW_R_" not in csv_text
    assert "SECRET_GROUP1" not in csv_text
    rows=list(csv.DictReader(csv_text.splitlines()))
    assert len(rows)==104
    assert len({r["Event_ID"] for r in rows})==104
    assert len({r["Dyad_ID"] for r in rows})==69
    assert {r["Recipient_Response"] for r in rows}=={"affiliative","non_affiliative"}
    assert {r["Gesture_Class"] for r in rows}=={"stretched_arm","bent_arm"}
    assert all(r["Facial_Expression_Class"]!="SOURCE_UNAVAILABLE_OR_NOT_APPLICABLE_UNRESOLVED_SUBTYPE" for r in rows)


def test_materialization_requires_strong_secret(tmp_path):
    raw=synthetic_workbook()
    _,pins,crosswalk,_,eligibility,_,admission,_=objects(raw)
    try:
        materialize_group2(raw,pins,crosswalk,eligibility,admission,b"weak",tmp_path)
    except ValueError as exc:
        assert "at least 32 bytes" in str(exc)
    else:
        raise AssertionError("weak materialization key was accepted")


def test_source_drift_holds_final_admission():
    raw=synthetic_workbook()
    item,pins,crosswalk,amendment1,eligibility,split_policy,admission,group1=objects(raw)
    pins["file"]["sha256"]="0"*64
    admission["source_sha256"]=pins["file"]["sha256"]
    eligibility["source_sha256"]=pins["file"]["sha256"]
    receipt,_=final_admission(item,pins,crosswalk,amendment1,eligibility,split_policy,admission,group1,lambda url,size:raw)
    assert receipt["state"] in {"HELD_RECOMPUTED_H4_H5_MISMATCH","HELD_FINAL_ADMISSION_SOURCE"}
    assert receipt["rdc004_empirical_admission"] is False
