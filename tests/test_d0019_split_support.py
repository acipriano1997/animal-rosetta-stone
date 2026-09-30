import hashlib
from io import BytesIO
from zipfile import ZipFile

from scripts.audit_d0019_split_support import split_support, audit

HEADERS=[
    "Dataset","event","clip_old","time","initiator","group","sex_init","ini_approaching",
    "recipient","sex_rec","dyad","rel_dom","face","context_dyad","GEST","REACT"
]


def synthetic_workbook(single_rare_class=False):
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
            cells.append(f'<c r="P{n}" t="inlineStr"><is><t>SECRET_GROUP1_{idx}</t></is></c>')
        else:
            local=idx-103
            excluded=local>=104
            if not excluded:
                d=eligible_idx if eligible_idx<69 else eligible_idx-69
                initiator=f"I{d}"
                recipient=f"R{d}"
                if single_rare_class:
                    response="avoid" if eligible_idx==0 else "affil"
                else:
                    response="affil" if eligible_idx%2==0 else "avoid"
                eligible_idx+=1
                face="neutral"
            else:
                d=local%69
                initiator=f"I{d}"
                recipient=f"R{d}"
                response="affil" if local%2==0 else "avoid"
                face="NA"
            cells += [
                f'<c r="A{n}"><v>{2015 if local%2==0 else 2016}</v></c>',
                f'<c r="E{n}" t="inlineStr"><is><t>{initiator}</t></is></c>',
                f'<c r="G{n}" t="inlineStr"><is><t>female</t></is></c>',
                f'<c r="I{n}" t="inlineStr"><is><t>{recipient}</t></is></c>',
                f'<c r="J{n}" t="inlineStr"><is><t>male</t></is></c>',
                f'<c r="L{n}" t="inlineStr"><is><t>todom</t></is></c>',
                f'<c r="M{n}" t="inlineStr"><is><t>{face}</t></is></c>',
                f'<c r="N{n}" t="inlineStr"><is><t>pos</t></is></c>',
                f'<c r="O{n}" t="inlineStr"><is><t>SG</t></is></c>',
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


def rules(raw):
    sha=hashlib.sha256(raw).hexdigest()
    return {
        "status":"FROZEN_PRE_MODEL_GROUP2_ELIGIBILITY",
        "eligibility_version":"v0.1",
        "source_sha256":sha,
        "rules":{
            "year":{"allowed":["2015","2016"]},
            "gesture":{"allowed":["SG","BG"]},
            "face":{"allowed":["neutral","bared","hoot","NA"]},
            "context":{"allowed":["pos","neg","NA"]},
            "response":{"allowed":["affil","avoid","NA"]},
        }
    }


def policy(raw):
    return {
        "deviation_id":"PD-PR0005-002",
        "status":"FROZEN_PRE_OUTCOME_PERFORMANCE",
        "support_gate":{
            "eligible_source_rows_digest":"",
            "expected_eligible_rows":104,
            "expected_unordered_dyads":69,
        }
    }


def prepare(raw):
    r=rules(raw)
    p=policy(raw)
    rows=[]
    # Recompute the exact digest by running once with a temporary expected digest
    # derived from the known source rows 105..208 (Excel rows for the first 104 Group-2 rows).
    source_rows=list(range(105,209))
    p["support_gate"]["eligible_source_rows_digest"]=hashlib.sha256(
        ("D0019_ELIGIBLE_V0.1|"+r["source_sha256"]+"|"+",".join(map(str,source_rows))).encode()
    ).hexdigest()
    return r,p


def wrapper_case(raw):
    r,p=prepare(raw)
    md5=hashlib.md5(raw).hexdigest()
    pins={
        "source_item_id":9192509,"version":1,"doi":"10.6084/m9.figshare.9192509.v1",
        "license_as_reported":{"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"},
        "file":{"id":16741928,"name":"Rawdata_Compositionality.xlsx","bytes":len(raw),
                "md5":md5,"sha256":r["source_sha256"]},
        "sheets":[{"source_header_candidates":HEADERS}],
    }
    item={
        "id":9192509,"version":1,"doi":pins["doi"],"license":dict(pins["license_as_reported"]),
        "files":[{"id":16741928,"name":pins["file"]["name"],"size":len(raw),"computed_md5":md5,
                  "download_url":"https://ndownloader.figshare.com/files/16741928"}],
    }
    crosswalk={"version":"source-crosswalk-v0.2","empirical_admission":False}
    amendment1={"status":"FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT"}
    return item,pins,crosswalk,amendment1,r,p


def test_primary_and_robustness_logo_support_without_class_counts():
    raw=synthetic_workbook()
    r,p=prepare(raw)
    result=split_support(raw,HEADERS,r,p)
    assert result["eligible_rows"]==104
    assert result["primary_leave_unordered_dyad_out"]["fold_count"]==69
    assert result["primary_leave_unordered_dyad_out"]["all_eligible_events_tested_exactly_once"]
    assert result["primary_leave_unordered_dyad_out"]["zero_train_test_group_overlap"]
    assert result["primary_leave_unordered_dyad_out"]["all_training_folds_have_both_registered_response_classes"]
    assert result["robustness_leave_initiator_out"]["all_training_folds_have_both_registered_response_classes"]
    assert result["support_gate_passed"] is True
    assert result["outcome_class_counts_or_frequencies_emitted"] is False
    assert result["row_level_assignments_emitted"] is False
    assert "SECRET_GROUP1" not in str(result)


def test_rare_class_in_one_group_fails_support_without_reselecting_folds():
    raw=synthetic_workbook(single_rare_class=True)
    r,p=prepare(raw)
    result=split_support(raw,HEADERS,r,p)
    assert result["support_gate_passed"] is False
    assert result["primary_leave_unordered_dyad_out"]["all_training_folds_have_both_registered_response_classes"] is False


def test_wrapper_passes_structure_but_keeps_pr0005_unrun():
    raw=synthetic_workbook()
    item,pins,crosswalk,amendment1,r,p=wrapper_case(raw)
    result=audit(item,pins,crosswalk,amendment1,r,p,lambda url,size:raw)
    assert result["state"]=="H5_GROUPED_SPLIT_SUPPORT_PASS_FINAL_ADMISSION_PENDING"
    assert result["rdc004_empirical_admission"] is False
    assert result["pr0005_executed"] is False
    assert result["group1_outcomes_accessed"] is False


def test_policy_drift_holds_closed_before_source_use():
    raw=synthetic_workbook()
    item,pins,crosswalk,amendment1,r,p=wrapper_case(raw)
    p["status"]="MUTATED"
    result=audit(item,pins,crosswalk,amendment1,r,p,
                 lambda url,size:(_ for _ in ()).throw(AssertionError("No fetch")))
    assert result["state"]=="HELD_SOURCE_OR_POLICY_MISMATCH"
