import hashlib

from scripts.probe_d0019_source import check_frozen_snapshot, probe


def item_fixture():
    raw = b"authored synthetic workbook fixture"
    digest = hashlib.md5(raw).hexdigest()
    item = {
        "id": 9192509, "version": 1,
        "doi": "10.6084/m9.figshare.9192509.v1",
        "license": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
        "authors": [{"full_name": "Synthetic Author"}],
        "files": [{"id": 9192509, "name": "synthetic_test.xlsx",
                   "size": len(raw), "computed_md5": digest,
                   "download_url": "https://ndownloader.figshare.com/files/9192509"}],
    }
    return item, raw


def test_bounded_h1_h2_admission_without_opening_source_rows():
    item, raw = item_fixture()
    result = probe(item, lambda u, s: raw, lambda b: [{
        "sheet_name": "Sheet1", "header_candidate_row": 1,
        "header_candidate_cells": [{"cell_ref": "A1", "header_candidate": "Group_ID"}],
        "header_row_authoritative": False,
    }])
    assert result["state"] == "H1_FILES_VERIFIED_H2_HEADER_CANDIDATES_CODEBOOK_HELD"
    assert result["files"][0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["event_rows_inspected"] is False
    assert result["outcome_distribution_inspected"] is False
    assert result["pr0005_executed"] is False
    assert result["group1_holdout_opened"] is False
    assert result["rdc004_mapping_approved"] is False
    assert result["crg_c_credit"] == "UNMET"
    assert result["source_material_persisted"] is False


def test_unverified_item_license_never_downloads():
    item, raw = item_fixture()
    item["license"] = {"name": "Unknown"}
    result = probe(item, lambda u, s: (_ for _ in ()).throw(AssertionError("unsafe download")))
    assert result["state"] == "HELD_ITEM_LICENSE_REVIEW"


def test_wrong_file_checksum_quarantines():
    item, raw = item_fixture()
    result = probe(item, lambda u, s: b"x" * s, lambda b: [])
    assert result["state"] == "HELD_PARTIAL_SOURCE_INTEGRITY_OR_SCHEMA"
    assert "sha256" not in result["files"][0]


def test_wrong_item_version_never_downloads():
    item, raw = item_fixture()
    item["version"] = 2
    result = probe(item, lambda u, s: (_ for _ in ()).throw(AssertionError("unsafe download")))
    assert result["state"] == "HELD_SOURCE_IDENTITY"


def test_frozen_pin_accepts_only_identical_source_and_headers():
    item, raw = item_fixture()
    reader = lambda b: [{
        "sheet_name": "Rawdata", "dimension_as_declared": "A1:A2",
        "header_candidate_row": 1, "header_candidate_cells": [{
            "cell_ref": "A1", "header_candidate": "event"
        }]
    }]
    verified = probe(item, lambda u, s: raw, reader)
    pins = {
        "source_item_id": 9192509, "version": 1,
        "doi": item["doi"], "license_as_reported": item["license"],
        "file": {
            "id": item["files"][0]["id"], "name": item["files"][0]["name"],
            "bytes": len(raw), "md5": hashlib.md5(raw).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest()
        },
        "sheets": [{
            "name": "Rawdata", "declared_dimension": "A1:A2",
            "candidate_header_row": 1, "source_header_candidates": ["event"]
        }]
    }
    assert check_frozen_snapshot(verified, pins)["source_pin_verified"] is True
    pins["file"]["sha256"] = "0" * 64
    changed = probe(item, lambda u, s: raw, reader)
    assert check_frozen_snapshot(changed, pins)["state"] == "QUARANTINED_SOURCE_DRIFT"
