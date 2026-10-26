"""Source safety only: all fixture bytes are artificial, no animal observations."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reproduce_shorland_models as audit


def inputs(tmp_path, monkeypatch):
    source_dir = tmp_path / 'sources'
    source_dir.mkdir()
    csv = source_dir / 'source.csv'
    csv.write_bytes(b'synthetic source')
    package = source_dir / 'source.gz'
    with tarfile.open(package, 'w:gz') as archive:
        for name in ['shorlandetal/data/dataset.RData',
                     'shorlandetal/inst/shinybonobos-app/app.R']:
            content = b'synthetic non-executable fixture'
            item = tarfile.TarInfo(name)
            item.size = len(content)
            archive.addfile(item, BytesIO(content))
    sources = {'csv': csv, 'package': package}
    frozen = {k: p.read_bytes() for k, p in sources.items()}
    monkeypatch.setattr(audit, 'SOURCES', {k: hashlib.sha256(b).hexdigest()
        for k, b in frozen.items()})
    return sources, frozen


def args(monkeypatch, sources, out):
    monkeypatch.setattr(sys, 'argv', ['audit', '--csv', str(sources['csv']),
        '--package', str(sources['package']), '--rscript', '/unused/Rscript',
        '--library', '/unused/library', '--out-dir', str(out)])


def test_aliases_existing_outputs_and_ancestor_cannot_overwrite_sources(tmp_path, monkeypatch):
    sources, frozen = inputs(tmp_path, monkeypatch)
    symlink = tmp_path / 'symbolic'
    symlink.symlink_to(sources['csv'])
    hardlink = tmp_path / 'hard'
    hardlink.hardlink_to(sources['csv'])
    existing = tmp_path / 'existing'
    existing.mkdir()
    marker = existing / 'preserve'
    marker.write_bytes(b'previous result')
    for out in [sources['csv'], sources['package'], symlink, hardlink, existing, tmp_path,
                sources['csv'].parent / 'nested-output']:
        args(monkeypatch, sources, out)
        with pytest.raises((SystemExit, FileExistsError)):
            audit.main()
        assert all(p.read_bytes() == frozen[k] for k, p in sources.items())
        assert marker.read_bytes() == b'previous result'


def test_source_drift_rejected_before_output_creation(tmp_path, monkeypatch):
    sources, _ = inputs(tmp_path, monkeypatch)
    sources['csv'].write_bytes(b'changed source')
    out = tmp_path / 'new'
    args(monkeypatch, sources, out)
    with pytest.raises(SystemExit):
        audit.main()
    assert not out.exists()
    assert sources['csv'].read_bytes() == b'changed source'


def test_timeout_preserves_sources_and_cannot_report_completion(tmp_path, monkeypatch):
    sources, frozen = inputs(tmp_path, monkeypatch)
    out = tmp_path / 'timeout'
    args(monkeypatch, sources, out)
    def timeout(*a, **kw):
        raise subprocess.TimeoutExpired('synthetic', 600)
    monkeypatch.setattr(audit.subprocess, 'run', timeout)
    with pytest.raises(SystemExit, match='HELD'):
        audit.main()
    receipt = json.loads((out / 'preservation.json').read_text())
    assert receipt['timeout'] is True
    assert receipt['R_exit_code'] is None
    assert receipt['source_unchanged'] is True
    assert not (out / 'aggregate.json').exists()
    assert all(p.read_bytes() == frozen[k] for k, p in sources.items())
