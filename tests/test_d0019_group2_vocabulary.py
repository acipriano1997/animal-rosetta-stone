import hashlib
from io import BytesIO
from zipfile import ZipFile

from scripts.audit_d0019_group2_vocabulary import audit, group2_vocabulary

HEADERS = [
    "Dataset", "event", "clip_old", "time", "initiator", "group",
    "sex_init", "ini_approaching", "recipient", "sex_rec", "dyad",
    "rel_dom", "face", "context_dyad", "GEST", "REACT"
]


def synthetic_source():
    cols = {6: ("G", "M"), 9: ("J", "F"), 11: ("L", "lower"),
            12: ("M", "neutral"), 13: ("N", "positive"),
            14: ("O", "SG"), 15: ("P", "AFF")}
    titles = "".join(
        f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i, name in enumerate(HEADERS)
    )
    rows = ['<row r="1">' + titles + '</row>']
    for idx in range(252):
        n = idx + 2
        group = "1" if idx < 103 else "2"
        cells = [f'<c r="F{n}"><v>{group}</v></c>']
        if group == "1":
            # Deliberate forbidden holdout values must never appear in output.
            cells.append(
                f'<c r="P{n}" t="inlineStr"><is><t>SECRET_HOLDOUT_RESPONSE_{idx}</t></is></c>'
            )
        else:
            for i, (col, sample) in cols.items():
                value = sample
                if col == "M" and idx % 2:
                    value = "bared"
                if col == "O" and idx % 2:
                    value = "BG"
                if col == "P" and idx == 104:
                    continue
                cells.append(
                    f'<c r="{col}{n}" t="inlineStr"><is><t>{value}</t></is></c>'
                )
        rows.append(f'<row r="{n}">{"".join(cells)}</row>')
    xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:P253"/><sheetData>' + "".join(rows)
        + '</sheetData></worksheet>'
    )
    buf = BytesIO()
    with ZipFile(buf, "w") as zipfile:
        zipfile.writestr("xl/worksheets/sheet1.xml", xml)
    raw = buf.getvalue()
    source_file = {
        "id": 16741928, "name": "Rawdata_Compositionality.xlsx",
        "bytes": len(raw), "md5": hashlib.md5(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest()
    }
    pins = {
        "source_item_id": 9192509, "version": 1,
        "doi": "10.6084/m9.figshare.9192509.v1",
        "license_as_reported": {
            "name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"
        },
        "file": source_file,
        "sheets": [{"source_header_candidates": HEADERS}],
    }
    item = {
        "id": pins["source_item_id"], "version": 1, "doi": pins["doi"],
        "license": dict(pins["license_as_reported"]),
        "files": [{
            "id": source_file["id"], "name": source_file["name"],
            "size": source_file["bytes"], "computed_md5": source_file["md5"],
            "download_url": f"https://ndownloader.figshare.com/files/{source_file['id']}"
        }]
    }
    crosswalk = {
        "contract_id": "RDC-004",
        "source_sha256": source_file["sha256"],
        "empirical_admission": False,
        "group1_outcomes_accessed": False,
        "mapping_state": "SOURCE_BACKED_CANDIDATES_NOT_APPROVED",
        "fields": [{"field": "Recipient_Response",
                    "status": "PAPER_AND_HEADER_CORROBORATED_CANDIDATE"}],
    }
    return raw, item, pins, crosswalk


def test_group2_only_tokens_no_holdout_or_outcome_counts():
    raw, item, pins, crosswalk = synthetic_source()
    output = audit(item, pins, crosswalk, lambda url, size: raw)
    assert output["state"] == "H3_GROUP2_VOCABULARY_RECORDED_MAPPING_UNAPPROVED"
    assert output["vocabulary"]["groups_structural_counts_only"] == {"1": 103, "2": 149}
    vocab = output["vocabulary"]["group2_category_vocabulary"]
    assert vocab["GEST"]["source_tokens_no_frequencies"] == ["BG", "SG"]
    assert vocab["REACT"]["source_tokens_no_frequencies"] == ["AFF"]
    assert vocab["REACT"]["missing_blank_group2"] == 1
    assert vocab["REACT"]["source_code_mapping_approved"] is False
    assert output["vocabulary"]["group1_categorical_and_outcome_cells_decoded"] is False
    assert output["vocabulary"]["group2_outcome_frequency_computed"] is False
    assert output["group1_outcomes_accessed"] is False
    assert output["pr0005_executed"] is False
    assert "SECRET_HOLDOUT_RESPONSE" not in str(output)


def test_source_drift_quarantines_before_read():
    raw, item, pins, crosswalk = synthetic_source()
    pins["file"]["sha256"] = "0" * 64
    crosswalk["source_sha256"] = pins["file"]["sha256"]
    output = audit(item, pins, crosswalk, lambda url, size: raw)
    assert output["state"] == "HELD_GROUP2_VOCABULARY_OR_SOURCE"
    assert output["group1_holdout_opened"] is False


def test_crosswalk_cannot_preapprove_mapping():
    raw, item, pins, crosswalk = synthetic_source()
    crosswalk["fields"][0]["status"] = "APPROVED"
    output = audit(item, pins, crosswalk,
                   lambda url, size: (_ for _ in ()).throw(AssertionError("No fetch")))
    assert output["state"] == "HELD_SOURCE_OR_CROSSWALK"


def test_unverified_license_blocks_download():
    raw, item, pins, crosswalk = synthetic_source()
    item["license"]["name"] = "Not reviewed"
    output = audit(item, pins, crosswalk,
                   lambda url, size: (_ for _ in ()).throw(AssertionError("No fetch")))
    assert output["state"] == "HELD_LICENSE"


def test_no_group1_value_revealed_on_raw_helper():
    raw, _, pins, _ = synthetic_source()
    summary = group2_vocabulary(raw, pins["sheets"][0]["source_header_candidates"])
    assert summary["group1_categorical_and_outcome_cells_decoded"] is False
    assert "SECRET_HOLDOUT_RESPONSE" not in str(summary)
