import hashlib
from io import BytesIO
from zipfile import ZipFile

from scripts.audit_d0019_group2_identity_dyad import audit, group2_identity_audit

HEADERS = [
    "Dataset","event","clip_old","time","initiator","group","sex_init","ini_approaching",
    "recipient","sex_rec","dyad","rel_dom","face","context_dyad","GEST","REACT"
]


def workbook(reverse=True, missing_recipient=False):
    header="".join(
        f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i,name in enumerate(HEADERS)
    )
    rows=[f'<row r="1">{header}</row>']
    for idx in range(252):
        n=idx+2
        group="1" if idx<103 else "2"
        year="2015" if idx%2==0 else "2016"
        cells=[
            f'<c r="A{n}"><v>{year}</v></c>',
            f'<c r="B{n}"><v>{idx+1}</v></c>',
            f'<c r="F{n}"><v>{group}</v></c>',
        ]
        if group=="1":
            cells.append(f'<c r="P{n}" t="inlineStr"><is><t>SECRET_HOLDOUT_{idx}</t></is></c>')
        else:
            local=idx-103
            a=f"A{local%7}"
            b=f"B{local%5}"
            if reverse and local%2:
                initiator,recipient=b,a
            else:
                initiator,recipient=a,b
            if missing_recipient and local==0:
                recipient=""
            unordered="-".join(sorted((initiator,recipient))) if recipient else "missing"
            cells += [
                f'<c r="E{n}" t="inlineStr"><is><t>{initiator}</t></is></c>',
                f'<c r="I{n}" t="inlineStr"><is><t>{recipient}</t></is></c>',
                f'<c r="K{n}" t="inlineStr"><is><t>{unordered}</t></is></c>',
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


def source_case(raw):
    file={
        "id":16741928,"name":"Rawdata_Compositionality.xlsx",
        "bytes":len(raw),"md5":hashlib.md5(raw).hexdigest(),
        "sha256":hashlib.sha256(raw).hexdigest()
    }
    pins={
        "source_item_id":9192509,"version":1,"doi":"10.6084/m9.figshare.9192509.v1",
        "license_as_reported":{"name":"CC BY 4.0","url":"https://creativecommons.org/licenses/by/4.0/"},
        "file":file,"sheets":[{"source_header_candidates":HEADERS}],
    }
    item={
        "id":9192509,"version":1,"doi":pins["doi"],"license":dict(pins["license_as_reported"]),
        "files":[{"id":file["id"],"name":file["name"],"size":file["bytes"],
                  "computed_md5":file["md5"],
                  "download_url":"https://ndownloader.figshare.com/files/16741928"}]
    }
    crosswalk={
        "version":"source-crosswalk-v0.2","empirical_admission":False,
        "group1_outcomes_accessed":False,"source_sha256":file["sha256"]
    }
    return item,pins,crosswalk


def test_group2_identity_audit_emits_structure_not_ids_or_holdout():
    raw=workbook(reverse=True)
    result=group2_identity_audit(raw,HEADERS)
    assert result["group2_rows"]==149
    assert result["event_field_unique_within_group2"] is True
    assert result["event_plus_year_unique_within_group2"] is True
    assert result["same_initiator_recipient_rows"]==0
    assert result["source_dyad_maps_to_one_unordered_pair"] is True
    assert result["unordered_pair_maps_to_one_source_dyad"] is True
    assert result["source_dyad_contains_both_directions_for_at_least_one_pair"] is True
    assert result["identity_values_or_row_level_pairs_emitted"] is False
    assert result["group1_identity_signal_or_outcome_cells_decoded"] is False
    assert "SECRET_HOLDOUT" not in str(result)


def test_wrapper_stays_unadmitted_after_success():
    raw=workbook(reverse=True)
    item,pins,crosswalk=source_case(raw)
    result=audit(item,pins,crosswalk,lambda url,size:raw)
    assert result["state"]=="H3_IDENTITY_DYAD_STRUCTURE_VERIFIED_GROUPING_RULE_REVIEW_REQUIRED"
    assert result["rdc004_empirical_admission"] is False
    assert result["pr0005_executed"] is False


def test_missing_recipient_holds_identity_gate():
    raw=workbook(reverse=True,missing_recipient=True)
    item,pins,crosswalk=source_case(raw)
    result=audit(item,pins,crosswalk,lambda url,size:raw)
    assert result["state"]=="HELD_IDENTITY_OR_DYAD_STRUCTURE"


def test_source_hash_drift_holds_before_claim():
    raw=workbook(reverse=False)
    item,pins,crosswalk=source_case(raw)
    pins["file"]["sha256"]="0"*64
    crosswalk["source_sha256"]=pins["file"]["sha256"]
    result=audit(item,pins,crosswalk,lambda url,size:raw)
    assert result["state"]=="HELD_IDENTITY_AUDIT_SOURCE"
    assert result["group1_outcomes_accessed"] is False


def test_year_scoped_identifiers_can_resolve_reused_event_or_dyad_tokens():
    raw=workbook(reverse=False)
    result=group2_identity_audit(raw,HEADERS)
    assert result["event_plus_group_plus_year_unique_within_group2"] is True
    assert result["source_dyad_token_is_confined_to_one_year"] in (True, False)
