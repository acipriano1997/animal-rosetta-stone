"""Offline provenance tests; fixtures are synthetic and no deposited R runs."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import probe_d0029_source_history as probe


def archive(entries):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as z:
        for name, value in entries.items():
            z.writestr(name, value)
    return stream.getvalue()


def source_file(fid, name, raw):
    return {"id": fid, "name": name, "size": len(raw), "is_link_only": False,
            "supplied_md5": hashlib.md5(raw).hexdigest(),
            "computed_md5": hashlib.md5(raw).hexdigest(),
            "download_url": f"https://ndownloader.figshare.com/files/{fid}"}


def fixture_api():
    # A hostile command in source R stays inert during static inspection.
    code = 'library(brms)\nsystem("DO_NOT_EXECUTE")\nread.table("input.txt")\nset.seed(8)\n'
    raw = archive({"input.txt": "Subject\tOutcome\nprivate-id\tNA\n", "source.R": code})
    doc = archive({"word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Data_and_R_script.zip https://doi.org/10.6084/m9.figshare.16910173.v3</w:t></w:r></w:p></w:body></w:document>'})
    zip_file = source_file(123, "source.zip", raw)
    media = source_file(456, "demo.wav", b"never-download-media")
    versions = []
    for version in range(1, 5):
        versions.append({"endpoint": f"{probe.BASE}/articles/{probe.ITEM}/versions/{version}",
                         "retrieved_utc": "fixture", "response_sha256": "fixture",
                         "record": {"id": probe.ITEM, "version": version,
                                    "doi": f"10.6084/m9.figshare.{probe.ITEM}.v{version}",
                                    "files": [deepcopy(zip_file), deepcopy(media)]}})
    supplement = {"endpoint": f"{probe.BASE}/articles/20131650/versions/2",
                  "retrieved_utc": "fixture", "response_sha256": "fixture",
                  "record": {"id": 20131650, "version": 2, "doi": "10.6084/m9.figshare.20131650.v2",
                             "files": [source_file(789, "supp.docx", doc)]}}
    api = {"versions": versions, "supplement": supplement,
           "version_history": {"record": [{"version": v, "url": env["endpoint"]}
                                           for v, env in enumerate(versions, 1)]}}
    return api, {123: raw, 789: doc}


def test_all_versions_required_before_any_byte_acquisition():
    api, _ = fixture_api()
    api["versions"].pop(1)
    calls = []
    with pytest.raises(ValueError, match="retrieval incomplete"):
        probe.build_receipt(api, lambda f: calls.append(f["id"]))
    assert calls == []


def test_wrong_version_identity_fails_closed():
    api, _ = fixture_api()
    api["versions"][2]["record"]["doi"] = "10.6084/m9.figshare.16910173.v4"
    with pytest.raises(ValueError, match="versions/3"):
        probe.validate_history(api)


def test_history_gap_is_not_replaced_by_an_inferred_version():
    api, _ = fixture_api()
    api["version_history"]["record"].pop(1)
    with pytest.raises(ValueError, match="gaps"):
        probe.validate_history(api)


def test_same_name_replacement_and_same_id_rename_are_distinct():
    first = source_file(1, "data.zip", b"old")
    replacement = source_file(2, "data.zip", b"new")
    renamed = {**first, "name": "renamed.zip", "size": 4}
    diff = probe.manifest_diff([first], [replacement])
    assert diff["removed_file_ids"] == [1] and diff["added_file_ids"] == [2]
    assert diff["same_name_replacements"][0]["same_bytes_established"] is False
    diff = probe.manifest_diff([first], [renamed])
    assert set(diff["same_id_changes"][0]["changed_fields"]) == {"name", "size"}


def test_different_names_are_not_inferred_to_be_renames():
    diff = probe.manifest_diff([source_file(1, "old.zip", b"x")],
                               [source_file(2, "new.zip", b"x")])
    assert diff["same_name_replacements"] == []
    assert diff["added_file_ids"] == [2] and diff["removed_file_ids"] == [1]


@pytest.mark.parametrize("alter", ["computed_md5", "supplied_md5", "size", "download_url"])
def test_byte_integrity_or_route_drift_cannot_pass(alter):
    f = source_file(1, "source.zip", b"abc")
    f[alter] = {"computed_md5": "0" * 32, "supplied_md5": "0" * 32,
                "size": 2, "download_url": "https://example.org/files/1"}[alter]
    with pytest.raises(ValueError):
        probe.verify_bytes(f, b"abc")


def test_nonmedia_deduplicated_by_id_media_never_acquired_and_code_inert():
    api, files = fixture_api()
    calls = []
    def read(f):
        calls.append(f["id"])
        return files[f["id"]]
    result = probe.build_receipt(api, read)
    assert calls == [123, 789]
    assert len(result["scientific_files"][0]["associations"]) == 4
    assert result["outcome"] == "A" and result["state"] == probe.HELD
    assert result["rdc006_empirical_admission"] is False
    assert result["deposited_code_executed"] is False
    assert result["confirmatory_rq0005_run"] == "NOT_STARTED"
    assert "private-id" not in json.dumps(result)
    assert all(f["file_license_as_reported"] is None for f in result["scientific_files"])


def test_no_archive_outcome_b_retains_source_hold():
    api, files = fixture_api()
    for env in api["versions"]:
        env["record"]["files"] = [env["record"]["files"][1]]
    result = probe.build_receipt(api, lambda f: files[f["id"]])
    assert result["outcome"] == "B"
    assert result["state"] == "HELD_R0011_DATA_CODE_UNLOCATED_AFTER_ROUTE_ENUMERATION"


def test_implicit_r_row_labels_do_not_shift_headers_or_become_event_ids():
    summary, rows = probe.inspect_tsv(b'"PC_ID"\t"Victim"\n"1"\t"event-a"\t"pseudonym"\n')
    assert summary["column_count"] == 2 and summary["row_count"] == 1
    assert summary["unnamed_leading_row_label"] is True
    assert rows == [{"PC_ID": "event-a", "Victim": "pseudonym"}]
    assert "pseudonym" not in json.dumps(summary)


def test_ragged_schema_is_held_instead_of_silently_truncated():
    with pytest.raises(ValueError, match="ragged"):
        probe.inspect_tsv(b"a\tb\n1\t2\n1\t2\t3\n")


def test_postresponse_fields_are_only_inventory_not_predictor_admission():
    summary, _ = probe.inspect_tsv(b"Bout_persistence\tConsolation_afterbout\tPiloerection_bout\nNA\t0\t1\n")
    assert summary["missing_count_by_column"]["Bout_persistence"] == 1
    assert summary["missing_count_by_column"]["Consolation_afterbout"] == 0
    assert summary["missingness_is_not_zero_imputation"] is True
    assert "baseline_predictors" not in summary


def test_static_seed_and_model_settings_keep_source_line_scope():
    result = probe.inspect_code(b'library(brms)\nmodel <- brm(formula = y ~ x, family=bernoulli(), chains=4, iter=10000, warmup=2000)\nset.seed(8)\n')
    assert result["dependencies_as_coded"] == ["brms"]
    assert result["cues"]["seed_commands"][0]["line"] == 3
    assert result["cues"]["model_declarations"][0]["line"] == 2
    assert result["inspection"] == "STATIC_TEXT_ONLY_NOT_EXECUTED"


def test_duplicate_bout_key_and_filesource_mismatch_not_silently_repaired():
    headers = ["Analysis_level", "Study_group", "Study_year", "PC_ID", "Bout_number", "Victim", "Aggressor", "FileSource"]
    display = dict(zip(headers, ["Display", "g", "2022", "c", "NA", "v", "a", "file1"]))
    bout = {**display, "Analysis_level": "Bout", "Bout_number": "1", "FileSource": "file2"}
    summary, _ = probe.table_summary(headers, [list(bout.values()), list(bout.values())], [2, 3])
    assert summary["duplicate_bout_key_excess"] == 1
    links = probe.link_inspection([display, bout], [bout, bout])
    assert links["tables"]["main"]["conflict_metadata_mismatches"][0]["columns"] == ["FileSource"]
    assert links["key_match_is_not_semantic_or_timing_admission"] is True


def test_frozen_snapshot_preserves_all_manifests_hashes_and_r0011_history():
    path = Path(__file__).resolve().parents[1] / "contracts/d0029_version_history_source_snapshot.json"
    snap = json.loads(path.read_text())
    assert [(v["version"], len(v["files"])) for v in snap["versions"]] == [(1, 19), (2, 19), (3, 19), (4, 18)]
    for file in snap["scientific_files"]:
        assert file["md5"] == file["metadata_as_reported"]["computed_md5"] == file["metadata_as_reported"]["supplied_md5"]
        assert len(file["sha256"]) == 64 and file["file_license_as_reported"] is None
        assert all(a["item_license_as_reported"]["name"] == "CC BY 4.0" for a in file["associations"])
    assert snap["contradiction_history"]["record_id"] == "R0011"
    assert snap["contradiction_history"]["prior_registry_row_as_read"][0] == "R0011"
    assert snap["scientific_firewall"]["R0010"] == "UNCHANGED_CHIMPANZEE_CANON_STATE_CORRECTION"
    assert snap["admission_assessment"]["final_D0029_state"] == probe.HELD
    assert len(snap["rdc006_field_assessment"]) == 20
    assert all(f["empirical_admission_granted"] is False for f in snap["rdc006_field_assessment"])
    files = {f["metadata_as_reported"]["id"]: f for f in snap["scientific_files"]}
    assert "demographic_info.txt" in files[35025694]["expected_read_files_absent_from_archive"]
    assert "demographic_info.txt" not in files[36230763]["expected_read_files_absent_from_archive"]
    assert "Data_and_R_script.zip" in json.dumps(files[36314798]["document_inspection"])


def test_offline_cli_does_not_use_network_and_incomplete_cache_fails_closed(tmp_path, monkeypatch):
    api, files = fixture_api()
    (tmp_path / "api.json").write_text(json.dumps(api))
    for fid, raw in files.items():
        f = next(f for env in api["versions"] + [api["supplement"]] for f in env["record"]["files"] if f["id"] == fid)
        folder = tmp_path / str(fid)
        folder.mkdir()
        (folder / f["name"]).write_bytes(raw)
    output = tmp_path / "receipt.json"
    monkeypatch.setattr("sys.argv", ["probe", "--cache", str(tmp_path), "--out", str(output)])
    monkeypatch.setattr(probe, "urlopen", lambda *a, **k: pytest.fail("offline replay used network"))
    probe.main()
    assert json.loads(output.read_text())["outcome"] == "A"
    (tmp_path / "123/source.zip").unlink()
    with pytest.raises(SystemExit) as error:
        probe.main()
    assert error.value.code == 1
    receipt = json.loads(output.read_text())
    assert receipt["outcome"] == "C" and "123" in receipt["error"]
