import hashlib
from io import BytesIO
from zipfile import ZipFile

from scripts.audit_d0019_partition_keys import audit, partition_counts_only


HEADERS = [
    "Dataset", "event", "clip_old", "time", "initiator", "group",
    "sex_init", "ini_approaching", "recipient", "sex_rec", "dyad",
    "rel_dom", "face", "context_dyad", "GEST", "REACT"
]


def _fixture(group_values=None, changed_counts=False):
    if group_values is None:
        group_values = ["social"] * 252
    first = ["G1"] * (104 if changed_counts else 103)
    first += ["G2"] * (252 - len(first))
    title = "".join(
        f'<c r="{chr(65 + i)}1" t="inlineStr"><is><t>{name}</t></is></c>'
        for i, name in enumerate(HEADERS)
    )
    rows = [f'<row r="1">{title}</row>']
    for i in range(252):
        row = i + 2
        rows.append(
            f'<row r="{row}">'
            f'<c r="A{row}" t="inlineStr"><is><t>{first[i]}</t></is></c>'
            f'<c r="F{row}" t="inlineStr"><is><t>{group_values[i]}</t></is></c>'
            f'<c r="P{row}" t="inlineStr"><is><t>PRIVATE_RESPONSE_{i}</t></is></c>'
            '</row>'
        )
    xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:P253"/><sheetData>' + "".join(rows)
        + '</sheetData></worksheet>'
    )
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", xml)
    raw = buf.getvalue()
    manifest = {
        "source_item_id": 9192509, "version": 1,
        "doi": "10.6084/m9.figshare.9192509.v1",
        "license_as_reported": {
            "name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"
        },
        "file": {
            "id": 16741928, "name": "Rawdata_Compositionality.xlsx",
            "bytes": len(raw), "md5": hashlib.md5(raw).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest()
        },
        "sheets": [{"name": "Rawdata", "source_header_candidates": HEADERS}],
    }
    item = {
        "id": 9192509, "version": 1, "doi": manifest["doi"],
        "license": manifest["license_as_reported"],
        "files": [{
            "id": 16741928, "name": manifest["file"]["name"],
            "size": len(raw), "computed_md5": manifest["file"]["md5"],
            "download_url": "https://ndownloader.figshare.com/files/16741928"
        }]
    }
    return raw, item, manifest


def test_one_candidate_without_outcomes_or_group1_exposure():
    raw, item, pins = _fixture()
    result = audit(item, pins, lambda url, size: raw)
    assert result["state"] == "H3_ONE_PARTITION_CANDIDATE_UNAPPROVED"
    assert result["partition_audit"]["partition_candidates_by_published_sizes"] == ["Dataset"]
    assert result["partition_audit"]["source_partition_columns"]["Dataset"]["aggregate_counts"] == {
        "G1": 103, "G2": 149
    }
    assert result["partition_audit"]["outcome_or_signal_values_decoded"] is False
    assert result["group1_holdout_opened"] is False
    assert result["source_mapping_approved"] is False
    assert result["pr0005_executed"] is False
    assert "PRIVATE_RESPONSE" not in str(result)


def test_competing_partition_columns_are_not_resolved_by_guess():
    raw, item, pins = _fixture(group_values=["G1"] * 103 + ["G2"] * 149)
    result = audit(item, pins, lambda url, size: raw)
    assert result["state"] == "HELD_AMBIGUOUS_PARTITION_KEYS"


def test_published_count_mismatch_stays_held():
    raw, item, pins = _fixture(changed_counts=True)
    result = audit(item, pins, lambda url, size: raw)
    assert result["state"] == "HELD_PARTITION_KEY_NO_PUBLISHED_COUNT_MATCH"


def test_source_hash_drift_is_quarantined():
    raw, item, pins = _fixture()
    pins["file"]["sha256"] = "0" * 64
    result = audit(item, pins, lambda url, size: raw)
    assert result["state"] == "HELD_PARTITION_SOURCE_OR_STRUCTURE"
    assert result["group1_outcomes_exposed"] is False


def test_license_drift_never_fetches_source():
    raw, item, pins = _fixture()
    item["license"]["name"] = "Unknown"
    def forbidden(url, size):
        raise AssertionError("Never fetch unverified item")
    result = audit(item, pins, forbidden)
    assert result["state"] == "HELD_ITEM_LICENSE_DRIFT"
