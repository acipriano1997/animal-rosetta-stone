# Workbench live-authenticated canonical producer runbook

Status: operator procedure only. Scientific effect: NONE. A missing credential,
connector read, fixture pass or metadata audit does not close Phase I.

## Runtime and authorization

Use Python 3.13 and Node.js 22+ on any approved local or remote runtime. The
existing REST producer is platform-independent. It reads a short-lived Google
OAuth bearer token only from `ARS_GOOGLE_OAUTH_ACCESS_TOKEN` (or the explicitly
named environment variable passed via `--access-token-env`). It does not need a
Mac, browser login, refresh token, service account, embedded credential or new
authentication architecture.

The approved token must permit read-only Drive metadata/revision-history,
Docs content and Sheets values requests for the manifest's seven documents and
three spreadsheets in the canonical personal Drive. Use read-only Workspace
scopes through an approved OAuth flow/secret injector. A connected Drive chat
session provides connector reads; it does not supply a bearer token to this
process. Do not extract connector credentials or substitute a connector replay
for the live REST run. Never send credentials through chat, Git, Drive documents,
command-line arguments, shell-history assignments or CI artifacts.

## Repository-side preparation

From a clean canonical checkout, synchronize current main, install pinned
dependencies and run the credential-independent gates before supplying a token:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
test -z "$(git status --porcelain)"
python -m pip install -r requirements-lock.txt
python -m pip install -e .
python -m pytest -q
python scripts/verify_workbench_slice2_producer.py
python scripts/verify_workbench_document_authority.py
python scripts/verify_workbench_slice5_firewall.py
```

Use the latest complete GitHub CI result for that exact commit as complementary
evidence. Do not silently update authority pins: inspect legitimate source edits,
review the projection, reconcile the manifest and tests, and commit the change
before retrying. The authenticated producer itself checks exact live pins before
source reads and rechecks all authorities before returning each bundle, including
rights/missingness reads and edits to earlier documents during later reads.

## Final authenticated run

With the approved secret already injected into the environment:

```bash
python scripts/export_workbench_canonical_bundle.py --verify-live \
  --out build/live_authority/workbench_canonical_bundle.json
unset ARS_GOOGLE_OAUTH_ACCESS_TOKEN
```

If an interactive approved runtime is used, this portable hidden-input sequence
avoids shell-history-visible assignments and removes the token after the child
process exits, including failures:

```bash
python - <<'PY'
import getpass
import os
import subprocess
import sys

os.environ["ARS_GOOGLE_OAUTH_ACCESS_TOKEN"] = getpass.getpass(
    "Short-lived approved Google OAuth access token: "
)
try:
    subprocess.run([
        sys.executable, "scripts/export_workbench_canonical_bundle.py",
        "--verify-live", "--out",
        "build/live_authority/workbench_canonical_bundle.json",
    ], check=True)
finally:
    os.environ.pop("ARS_GOOGLE_OAUTH_ACCESS_TOKEN", None)
PY
```

`--verify-live` uses the same canonical REST producer twice, validates each output
through the existing adapter/provenance firewall, checks credential-bearing fields
and actual token values before writing, and compares every output field except
`captured_at_utc`, `snapshot.snapshot_id` and `snapshot.captured_date` (capture
metadata). Source identity, pins, bindings, events, metrics, rights and provenance
remain part of the deterministic comparison. Each capture uses one UTC timestamp.

The output paths must be unused. Success writes the first bundle, an independent
`*_rerun.json` capture and a `*_receipt.json` containing the clean repository SHA,
manifest digest, two byte hashes, deterministic-content hash and event inventory.
Files are atomically written at mode 0600. A failed read, drift, rerun difference,
credential check or changed checkout produces no success receipt. An existing
receipt is never overwritten/reused as proof of a new attempt; use a fresh output
basename after resolving a failed attempt. Keep bundles private: canonical event
rows have source-rights restrictions and are not Git/CI publication artifacts.

## Gate review and persistence

Review the receipt together with the exact-commit automated test/CI results and
private artifacts. Require CURRENT authority; D0018=36 and D0020=4,223 full event
rows; source-preserved identifiers/locators; all required bindings; no unresolved
provenance; ZERO_SYNTHETIC non-biological segregation; no preview/media invention;
and a passing deterministic rerun. Verify the recorded SHA-256 hashes against the
private files. Exercise the Workbench from that exported file as an as-of bundle:

```bash
ARS_WORKBENCH_CANONICAL_SOURCE=build/live_authority/workbench_canonical_bundle.json \
  ars-workbench --host 127.0.0.1 --port 8765
```

Do not call file transport live. The receipt proves the preceding live producer
read as of its capture. Only after review/readback persist the bounded result and
exact GitHub/CI references in existing ACEB Ingestion Queue Q0023 and the canonical
project-control audit record. A receipt alone does not approve scientific claims.

Missing/expired/insufficient authorization, inaccessible source, malformed content,
pin drift, non-CURRENT state, provenance failure, credential leakage and output
differences remain fail-closed outcomes. Missing runtime authorization remains an
external gate; record it honestly and continue unrelated executable project work.
