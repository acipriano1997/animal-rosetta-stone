#!/usr/bin/env python3
"""Read-only source-model audit; trusted original package, private new output only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

from research_integrity import fingerprint, write_private

SOURCES = {
    'csv': 'ca3de1351a6a4548fec86bc48130e71212f4b0f64e100e58e299afcd3b76cda8',
    'package': '4a6c2b184d4c692be248b03591e3c44e9180901094d7a78ed8efa9b125b934c8',
}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv', type=Path, required=True)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--rscript', type=Path, required=True)
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    args = p.parse_args()
    sources = {k: getattr(args, k).resolve(strict=True) for k in SOURCES}
    out = args.out_dir.resolve()
    for src in sources.values():
        if out == src or out in src.parents or src.parent in out.parents:
            p.error('output must be outside source directories and must not contain a source')
    before = {k: fingerprint(v) for k, v in sources.items()}
    for k, src in sources.items():
        if hashlib.sha256(src.read_bytes()).hexdigest() != SOURCES[k]:
            p.error('original source fingerprint mismatch: ' + k)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    worker = Path(__file__).with_suffix('.R')
    with tarfile.open(sources['package']) as archive:
        # Read this one member; never extract paths or execute package functions.
        data = archive.extractfile('shorlandetal/data/dataset.RData').read()
        app = archive.extractfile('shorlandetal/inst/shinybonobos-app/app.R').read()
    datafile = out / 'package-data.RData'
    with datafile.open('xb') as f:
        os.chmod(datafile, 0o600)
        f.write(data)
    write_private(out / 'started.json', {
        'sources': before, 'source_sha256': SOURCES,
        'worker_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(),
        'launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'package_data_sha256': hashlib.sha256(data).hexdigest(),
        'package_app_sha256': hashlib.sha256(app).hexdigest(),
        'sensitivity_plan': 'All 10 leave-subject-out and 12 leave-session-out; '
            'drop zero-time rows separately as estimand sensitivity; default and bobyqa fits. '
            'No outcome-selected deletions or confirmatory inference.',
    })
    outcome = {'R_exit_code': None, 'timeout': False, 'interrupted': False}
    try:
        with (out / 'R.log').open('x') as log:
            result = subprocess.run([str(args.rscript), '--vanilla', str(worker),
                str(sources['csv']), str(datafile), str(args.library.resolve()), str(out)],
                stdout=log, stderr=subprocess.STDOUT, timeout=600)
            outcome['R_exit_code'] = result.returncode
    except subprocess.TimeoutExpired:
        outcome['timeout'] = True
    except KeyboardInterrupt:
        outcome['interrupted'] = True
    finally:
        after = {k: fingerprint(v) for k, v in sources.items()}
        write_private(out / 'preservation.json', {'source_unchanged': before == after,
            'before': before, 'after': after, **outcome})
    if outcome['R_exit_code'] != 0 or outcome['timeout'] or outcome['interrupted'] or before != after:
        raise SystemExit('HELD: inspect private R.log and preservation.json')
    print(json.dumps({'status': 'COMPLETED_BOUNDED_SOURCE_MODEL_AUDIT',
        'source_unchanged': True, 'out_dir': str(out),
        'historical_runtime_equivalence': 'NOT_ESTABLISHED'}))


if __name__ == '__main__':
    main()
