from scripts.probe_d0025_metadata import probe


def _fake_fetch(path):
    if path.endswith("/19683768"):
        return {
            "id": 19683768,
            "doi": "10.6084/m9.figshare.19683768",
            "title": "Synthetic test-only source metadata",
            "version": 1,
            "license": {"name": "CC BY 4.0"},
            "files": [{"id": 12345, "name": "fake_data.csv", "size": 42}],
        }
    if path.endswith("/6060702"):
        return {"id": 6060702, "title": "Synthetic supplemental metadata"}
    raise OSError("Unexpected URL")


def test_metadata_never_grants_rights_or_inspects_rows():
    result = probe(_fake_fetch)
    assert result["article"]["state"] == "IDENTITY_MATCH_METADATA_ONLY"
    assert result["article"]["file_count"] == 1
    assert result["research_rights_state"] == "HELD_RIGHTS_PENDING_HUMAN_REVIEW"
    assert result["source_materialized"] is False
    assert result["row_level_data_inspected"] is False
    assert result["source_bytes_sha256_verified"] is False
    assert result["rdc005_admission"] == "NOT_ATTEMPTED"
    assert result["crg_c_credit"] == "UNMET"


def test_network_failures_remain_held_without_substituted_facts():
    def unavailable(path):
        raise OSError("No public API connection")
    result = probe(unavailable)
    assert result["article"]["state"] == "METADATA_UNAVAILABLE_HELD"
    assert result["supplement_collection"]["state"] == "METADATA_UNAVAILABLE_HELD"
    assert result["research_rights_state"].startswith("HELD_RIGHTS")


def test_dataset_identity_mismatch_is_not_accepted():
    def wrong(path):
        value = _fake_fetch(path)
        if path.endswith("/19683768"):
            value["id"] = 123
        return value
    result = probe(wrong)
    assert result["article"]["state"] == "IDENTITY_MISMATCH_HELD"
    assert result["pr0006_execution"] == "NOT_ATTEMPTED"


def test_versioned_doi_matches_its_declared_source_version():
    def versioned(path):
        record = _fake_fetch(path)
        if path.endswith("/19683768"):
            record["doi"] = "10.6084/m9.figshare.19683768.v1"
        return record
    result = probe(versioned)
    assert result["article"]["state"] == "IDENTITY_MATCH_METADATA_ONLY"


def test_wrong_version_suffix_does_not_match():
    def version_conflict(path):
        record = _fake_fetch(path)
        if path.endswith("/19683768"):
            record["doi"] = "10.6084/m9.figshare.19683768.v2"
        return record
    result = probe(version_conflict)
    assert result["article"]["state"] == "IDENTITY_MISMATCH_HELD"
