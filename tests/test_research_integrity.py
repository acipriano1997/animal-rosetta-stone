"""Synthetic storage failure cases; no biological evidence or media fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import research_integrity as ri
import verify_local_research as batch


def test_roundtrip_duplicates_and_changed_missing_extra(tmp_path):
    root = tmp_path / "raw"
    root.mkdir()
    (root / "original").write_bytes(b"immutable")
    (root / "copy").write_bytes(b"immutable")
    manifest = ri.inventory(root)
    assert manifest["byte_identical_groups"] == [["copy", "original"]]
    assert ri.inventory(root) == manifest
    assert ri.verify(root, manifest)["status"] == "PASS"
    (root / "copy").unlink()
    (root / "original").write_bytes(b"changed")
    (root / "extra").write_bytes(b"new")
    result = ri.verify(root, manifest)
    assert result["status"] == "HELD"
    assert result["changed"] == ["original"]
    assert result["missing"] == ["copy"]
    assert result["extra"] == ["extra"]


def test_symlink_and_special_file_fail_closed(tmp_path):
    (tmp_path / "file").write_bytes(b"source")
    (tmp_path / "link").symlink_to(tmp_path / "file")
    (tmp_path / "directory-link").symlink_to(tmp_path, target_is_directory=True)
    os.mkfifo(tmp_path / "fifo")
    result = ri.inventory(tmp_path)
    assert result["status"] == "HELD"
    assert len(result["errors"]) == 3
    assert [r["path"] for r in result["files"]] == ["file"]


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "a/../../secret", "a//b", "a/./b", "a\\b", ""])
def test_untrusted_manifest_paths_rejected(tmp_path, path):
    m = ri.inventory(tmp_path)
    m["files"] = [{"path": path, "sha256": "0" * 64, "size_bytes": 0}]
    with pytest.raises(ValueError):
        ri.verify(tmp_path, m)


def test_manifest_cannot_attest_partial_or_duplicate_inputs(tmp_path):
    (tmp_path / "file").write_bytes(b"a")
    m = ri.inventory(tmp_path)
    m["files"] *= 2
    with pytest.raises(ValueError, match="DUPLICATE"):
        ri.verify(tmp_path, m)
    m = ri.inventory(tmp_path)
    m["status"] = "HELD"
    with pytest.raises(ValueError, match="INCOMPLETE"):
        ri.verify(tmp_path, m)
    with pytest.raises(json.JSONDecodeError):
        json.loads('{"contract":')


def test_changed_during_hash_rejected(tmp_path, monkeypatch):
    source = tmp_path / "a"
    source.write_bytes(b"abc")
    original_hash = ri.hashlib.sha256
    class MutatingHash:
        def __init__(self):
            self.h = original_hash()
        def update(self, b):
            self.h.update(b)
            source.write_bytes(b"xyz")
        def hexdigest(self):
            return self.h.hexdigest()
    monkeypatch.setattr(ri.hashlib, "sha256", MutatingHash)
    with pytest.raises(ValueError, match="CHANGED"):
        ri.fingerprint(source)


@pytest.mark.parametrize("alias", ["same", "hardlink", "symlink"])
def test_output_never_replaces_input(tmp_path, alias):
    root = tmp_path / "raw"
    root.mkdir()
    source = root / "data"
    source.write_bytes(b"precious")
    out = tmp_path / "receipt"
    if alias == "same":
        out = source
    elif alias == "hardlink":
        os.link(source, out)
    else:
        out.symlink_to(source)
    assert ri.main(["inventory", "--root", str(root), "--out", str(out)]) == 2
    assert source.read_bytes() == b"precious"


def test_private_output_existing_and_interrupted_reports(tmp_path):
    out = tmp_path / "report"
    ri.write_private(out, {"status": "RUNNING"})
    assert out.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        ri.write_private(out, {"status": "PASS"})
    assert json.loads(out.read_text())["status"] == "RUNNING"


def test_cli_from_other_directory(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "a").write_bytes(b"unchanged")
    manifest = tmp_path / "m.json"
    for mode, out in [("inventory", manifest), ("verify", tmp_path / "verified.json")]:
        cmd = [sys.executable, str(SCRIPTS / "research_integrity.py"), mode,
               "--root", str(raw), "--out", str(out)]
        if mode == "verify":
            cmd += ["--manifest", str(manifest)]
        assert subprocess.run(cmd, cwd=tmp_path, capture_output=True).returncode == 0
        assert json.loads(out.read_text())["status"] == "PASS"


def test_batch_timeout_is_held(tmp_path):
    result = batch.execute([sys.executable, "-c", "import time; time.sleep(30)"],
                           os.environ.copy(), tmp_path / "log", 0.1)
    assert result["timeout"] is True
    assert result["exit_code"] != 0


def test_batch_missing_node_cannot_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(batch.shutil, "which", lambda _: None)
    monkeypatch.setattr(batch, "code_state", lambda: {"head": "test", "status": ""})
    monkeypatch.setattr(batch, "execute", lambda *a, **kw: {"exit_code": 0, "timeout": False})
    out = tmp_path / "batch"
    assert batch.main(["--out-dir", str(out)]) == 2
    assert json.loads((out / "receipt.json").read_text())["status"] == "HELD"


def test_batch_drops_live_authority_and_credentials_and_binds_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("ARS_WORKBENCH_CANONICAL_SOURCE", "https://example.invalid/live")
    monkeypatch.setenv("ARS_GOOGLE_OAUTH_ACCESS_TOKEN", "synthetic-test-secret")
    monkeypatch.setenv("GITHUB_SHA", "wrong-head")
    monkeypatch.setattr(batch.shutil, "which", lambda _: "/test/node")
    monkeypatch.setattr(batch, "code_state", lambda: {"head": "expected-head", "status": ""})
    captured = []
    def fake_execute(command, env, log, timeout, cwd):
        assert "ARS_WORKBENCH_CANONICAL_SOURCE" not in env
        assert "ARS_GOOGLE_OAUTH_ACCESS_TOKEN" not in env
        assert env["GITHUB_SHA"] == "expected-head"
        captured.append(cwd)
        return {"exit_code": 0, "timeout": False}
    monkeypatch.setattr(batch, "execute", fake_execute)
    assert batch.main(["--out-dir", str(tmp_path / "batch")]) == 0
    assert captured[-1] == tmp_path / "batch/sandbox"
