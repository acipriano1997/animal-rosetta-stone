import hashlib
from io import BytesIO
from zipfile import ZipFile

from scripts.audit_d0019_group2_eligibility import audit, group2_eligibility

HEADERS=[
    "Dataset","event","clip_old","time","initiator","group","sex_init","ini_approaching",
    "recipient","sex_rec","dyad","rel_dom","face","context_dyad","GEST","REACT"
]


def synthetic_workbook(invalid_gesture=False, missing_recipient=False):
    header="".join(
        f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i,name in enumerate(HEADERS)
    )
    rows=[f'<row r="1">{header}</row>']
    for idx in range(252):
        n=idx+2
        group="1" if idx<103 else "2"
        cells=[f'<c r="F{n}"><v>{group}</v></c>']
        if group=="1":
            cells.append(f'<c r="P{n}" t="inlineStr"><is><t>SECRET_HOLDOUT_{idx}</t></is></c>')
        else:
            local=idx-103
            face="NA" if local==0 else ("bared" if local%3==0 else "neutral")
            context="NA" if local==1 else ("pos" if local%2==0 else "neg")
            response="NA" if local==2 else ("affil" if local%2==0 else "avoid")
            rank="NA" if local==3 else ("todom" if local%2==0 else "nottodom")
            gesture="XX" if invalid_gesture and local==4 else ("SG" if local%2==0 else "BG")
            cells += [
                f'<c r="A{n}"><v>{2015 if local%2==0 else 2016}</v></c>',
                f'<c r="E{n}" t="inlineStr"><is><t>I{local%13}</t></is></c>',
                f'<c r="G{n}" t="inlineStr"><is><t>{"female" if local%2==0 else "male"}</t></is></c>',
                ('' if (missing_recipient and local==0) else f'<c r="I{n}" t="inlineStr"><is><t>R{local%17}</t></is></c>'),
                f'<c r="J{n}" t="inlineStr"><is><t>{"male" if local%2==0 else "female"}</t></is></c>',
                f'<c r="K{n}" t="inlineStr"><is><t>D{local%23}</t></is></c>',
                f'<c r="L{n}" t="inlineStr"><is><t>{rank}</t></is></c>',
                f'<c r="M{n}" t="inlineStr"><is><t>{face}</t></is></c>',
                f'<c r="N{n}" t="inlineStr"><is><t>{context}</t></is></c>',
                f'<c r="O{n}" t="inlineStr"><is><t>{gesture}</t></is></c>',
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
        "eligibility_version":"v0.1","source_sha256":sha,
        "crosswalk_ref":"contracts/d0019_rdc004_source_crosswalk_v0_2.json",
        "grouping_amendment_ref":"contracts/pr0005_pd_001_grouping_amendment.json",
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


def wrapper_case(raw):
    r=rules(raw)
    md5=hashlib.md5(raw).hexdigest()
    pins={
        "source_item_id":9192509,"version":1,"doi":"10.6084/m9.figshare.9192509.v1",
        "license_as_reported":{"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"},
        "file":{"id":16741928,"name":"Rawdata_Compositionality.xlsx","bytes":len(raw),"md5":md5,"sha256":r["source_sha256"]},
        "sheets":[{"source_header_candidates":HEADERS}],
    }
    item={
        "id":9192509,"version":1,"doi":pins["doi"],"license":dict(pins["license_as_reported"]),
        "files":[{"id":16741928,"name":pins["file"]["name"],"size":len(raw),"computed_md5":md5,
                  "download_url":"https://ndownloader.figshare.com/files/16741928"}],
    }
    crosswalk={"version":"source-crosswalk-v0.2","empirical_admission":False}
    amendment={"status":"FROZEN_PRE_OUTCOME_SOURCE_SCHEMA_AMENDMENT",
               "evidence":{"group1_outcomes_accessed":False}}
    return item,pins,crosswalk,amendment,r


def test_frozen_na_rules_create_aggregate_only_eligibility():
    raw=synthetic_workbook()
    summary=group2_eligibility(raw,HEADERS,rules(raw))
    assert summary["source_group2_rows"]==149
    assert summary["eligible_primary_rows"]==146
    assert summary["exclusion_reason_counts"]=={
        "CONTEXT_UNAVAILABLE_OR_INVALID":1,
        "FACE_UNAVAILABLE_OR_INVALID":1,
        "OUTCOME_UNAVAILABLE_OR_INVALID":1,
    }
    assert summary["retained_explicit_unknown_counts"]["rel_dom"]==1
    assert summary["all_tokens_within_frozen_domains"] is True
    assert summary["outcome_class_frequencies_computed"] is False
    assert summary["row_level_records_emitted"] is False
    assert summary["canonical_group2_source_rows_unique"] is True
    assert summary["group1_holdout_opened"] is False
    assert "SECRET_HOLDOUT" not in str(summary)


def test_invalid_substantive_token_fails_admission():
    raw=synthetic_workbook(invalid_gesture=True)
    item,pins,crosswalk,amendment,r=wrapper_case(raw)
    result=audit(item,pins,crosswalk,amendment,r,lambda url,size:raw)
    assert result["state"]=="HELD_ELIGIBILITY_OR_DOMAIN"
    assert result["eligibility"]["invalid_token_counts"]["GEST"]==1


def test_clean_structure_passes_but_does_not_authorize_model():
    raw=synthetic_workbook()
    item,pins,crosswalk,amendment,r=wrapper_case(raw)
    result=audit(item,pins,crosswalk,amendment,r,lambda url,size:raw)
    assert result["state"]=="H4_ELIGIBILITY_STRUCTURE_PASS_SPLIT_SUPPORT_PENDING"
    assert result["rdc004_empirical_admission"] is False
    assert result["pr0005_executed"] is False


def test_rule_or_source_drift_holds_closed():
    raw=synthetic_workbook()
    item,pins,crosswalk,amendment,r=wrapper_case(raw)
    r["source_sha256"]="0"*64
    result=audit(item,pins,crosswalk,amendment,r,lambda url,size:raw)
    assert result["state"]=="HELD_SOURCE_OR_RULE_MISMATCH"


def test_missing_required_recipient_holds_structural_admission():
    raw=synthetic_workbook(missing_recipient=True)
    item,pins,crosswalk,amendment,r=wrapper_case(raw)
    result=audit(item,pins,crosswalk,amendment,r,lambda url,size:raw)
    assert result["state"]=="HELD_ELIGIBILITY_OR_DOMAIN"
    assert result["eligibility"]["exclusion_reason_counts"]["MISSING_RECIPIENT"]==1
    assert result["rdc004_empirical_admission"] is False
    assert result["pr0005_executed"] is False
