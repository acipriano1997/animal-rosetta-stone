from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ars_workbench.producer import WorkspaceCanonicalProducer
from test_workbench_canonical_producer import FakeReader, _small_manifest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export_workbench_canonical_bundle.py"
spec = importlib.util.spec_from_file_location("workbench_export", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
TOKEN = "synthetic-export-token-not-a-credential"


@pytest.fixture
def output_pair(monkeypatch):
    manifest = _small_manifest()
    first = WorkspaceCanonicalProducer(FakeReader(manifest), manifest).build_bundle()
    second = deepcopy(first)
    second["captured_at_utc"] = "2099-01-02T00:00:00Z"
    second["snapshot"]["snapshot_id"] = "separate-capture"
    second["snapshot"]["captured_date"] = "2099-01-02"
    class Producer:
        def __init__(self, reader):
            self.manifest = manifest
            self.calls = 0
        def build_bundle(self):
            self.calls += 1
            return first if self.calls == 1 else second
    monkeypatch.setattr(exporter, "WorkspaceCanonicalProducer", Producer)
    monkeypatch.setattr(exporter, "clean_repository_sha", lambda: "a" * 40)
    return first, second


def test_verified_export_preserves_two_captures_and_exact_content_receipt(tmp_path, output_pair):
    out = tmp_path / "bundle.json"
    summary = exporter.export_bundle(TOKEN, out, verify_live=True)
    receipt = json.loads(Path(summary["receipt"]).read_text())
    assert receipt["repository_sha"] == "a" * 40
    assert receipt["deterministic_rerun"] == "PASS_EXCLUDING_CAPTURE_METADATA_ONLY"
    assert receipt["bundle_sha256"] != receipt["rerun_sha256"]
    assert receipt["authority_state"] == "CURRENT"
    assert receipt["biological_evidence"] is False
    for file in tmp_path.iterdir():
        assert file.stat().st_mode & 0o777 == 0o600
        assert TOKEN not in file.read_text()


@pytest.mark.parametrize("change", ["metric", "provenance", "binding", "inventory", "state"])
def test_rerun_difference_cannot_be_ignored(tmp_path, output_pair, change):
    _, second = output_pair
    if change == "metric":
        second["snapshot"]["runs"][0]["metrics"] = {"value": 99}
    elif change == "provenance":
        second["snapshot"]["provenance"]["PROV-SPECIES"]["drive_revision_id"] = "other"
    elif change == "binding":
        second["bindings"]["species"]["drive_id"] = "other"
    elif change == "inventory":
        second["snapshot"]["event_inventory"]["D0018"]["canonical_total"] = 99
    else:
        second["authority_state"] = "STALE"
    with pytest.raises(ValueError, match="reruns disagree"):
        exporter.export_bundle(TOKEN, tmp_path / "bundle.json", verify_live=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("leak", ["value", "field", "key"])
def test_credential_output_is_rejected_before_any_file(tmp_path, output_pair, leak):
    first, _ = output_pair
    if leak == "value":
        first["snapshot"]["question"]["text"] = TOKEN
    elif leak == "field":
        first["nested"] = [{"refresh_token": "synthetic"}]
    else:
        first[TOKEN] = "must not serialize"
    with pytest.raises(ValueError, match="credential|Credential"):
        exporter.export_bundle(TOKEN, tmp_path / "bundle.json", verify_live=True)
    assert not list(tmp_path.iterdir())


def test_old_receipt_is_not_reused_or_overwritten(tmp_path, output_pair):
    receipt = tmp_path / "bundle_receipt.json"
    receipt.write_text("old")
    with pytest.raises(ValueError, match="unused output"):
        exporter.export_bundle(TOKEN, tmp_path / "bundle.json", verify_live=True)
    assert receipt.read_text() == "old"
    assert not (tmp_path / "bundle.json").exists()


def test_missing_runtime_authorization_is_real_cli_failure(tmp_path):
    env = dict(os.environ, ARS_GOOGLE_OAUTH_ACCESS_TOKEN="")
    result = subprocess.run([sys.executable, str(SCRIPT), "--verify-live", "--out",
                             str(tmp_path / "bundle.json")], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Missing runtime credential" in result.stderr
    assert not list(tmp_path.iterdir())


def test_private_atomic_write_replaces_symlink_without_touching_target(tmp_path):
    target = tmp_path / "unrelated.json"
    target.write_text("preserve")
    output = tmp_path / "bundle.json"
    output.symlink_to(target)
    exporter.write_private_json(output, {"authority_state": "CURRENT"})
    assert target.read_text() == "preserve"
    assert not output.is_symlink()
    assert output.stat().st_mode & 0o777 == 0o600
