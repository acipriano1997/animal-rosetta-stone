"""Exercise actual offline CLIs: output aliases must never destroy source bytes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["audit_d0037_playback_csv.py", "audit_d0029_rdc006.py", "audit_d0026_source_bytes.py"])
@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_source_bytes_survive_output_aliases(tmp_path, script, alias):
    source = tmp_path / "source"
    if script == "audit_d0037_playback_csv.py":
        source.write_text("individual_id,playback_type,switch_off_response,switch_off_duration (s),switch_off_playback_amplitude\n1,silence,no,NA,NA\n")
        args = [str(source)]
    elif script == "audit_d0029_rdc006.py":
        source.write_bytes(b"synthetic archive deliberately rejected by frozen source pin")
        args = ["--snapshot", str(ROOT / "contracts/d0029_version_history_source_snapshot.json"), "--archive", str(source)]
    else:
        source.write_text(json.dumps({"dataset_id": "D0026", "file_count": 0, "files": []}))
        raw = tmp_path / "raw"
        raw.mkdir()
        args = ["--snapshot", str(source), "--root", str(raw)]
    original = source.read_bytes()
    out = source if alias == "same" else tmp_path / "report.json"
    if alias == "symlink":
        out.symlink_to(source)
    elif alias == "hardlink":
        os.link(source, out)
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args, "--out", str(out)],
                         cwd=ROOT, capture_output=True)
    assert run.returncode != 0
    assert source.read_bytes() == original
