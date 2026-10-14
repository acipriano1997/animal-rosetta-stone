# Workbench live-authenticated canonical producer runbook

Status: operator procedure only. This document does not change scientific state, authority, evidence, or the canonical-producer contract.

## Purpose

Close the remaining Workbench Phase I operational gate by executing the existing canonical producer against the live, pinned Google Drive/ACEB authorities with a short-lived OAuth bearer token. The producer must continue to fail closed on authority-pin drift.

## Security boundary

- Use a short-lived Google OAuth access token that is authorized for the Drive/Docs/Sheets reads required by the canonical producer.
- Never place the token on the command line, in Git, in a shell-history-visible assignment, in a receipt, or in an issue/PR comment.
- The canonical exporter reads the token only from `ARS_GOOGLE_OAUTH_ACCESS_TOKEN`.
- The exported canonical bundle and verification metadata must not contain the credential.
- Unset the environment variable immediately after the run.

## Preconditions

1. Use the canonical local repository checkout.
2. Fetch `origin` and require local `main` to fast-forward cleanly to current `origin/main`.
3. Confirm there are no local changes that would contaminate the operator run.
4. Activate the project Python environment and install only the repository-pinned dependencies if they are not already present.
5. Recheck the live canonical authority pins immediately before authenticated execution. Any pin drift is a stop condition; reconcile the source authority and repository pins before retrying.

## Bounded operator sequence

From the project root:

```zsh
set -euo pipefail

git fetch origin
git checkout main
git pull --ff-only origin main
test -z "$(git status --porcelain)"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

python -m pip install -r requirements-lock.txt
python -m pip install -e .

# Offline structural gate first. This must pass before any live credential is used.
python scripts/verify_workbench_slice2_producer.py

mkdir -p build/live_authority

# Enter the short-lived token without echoing it or putting it on the command line.
read -s "ARS_GOOGLE_OAUTH_ACCESS_TOKEN?Paste short-lived Google OAuth access token: "
print
export ARS_GOOGLE_OAUTH_ACCESS_TOKEN

cleanup_token() {
  unset ARS_GOOGLE_OAUTH_ACCESS_TOKEN
}
trap cleanup_token EXIT INT TERM

python scripts/export_workbench_canonical_bundle.py \
  --out build/live_authority/workbench_canonical_bundle.json

unset ARS_GOOGLE_OAUTH_ACCESS_TOKEN
trap - EXIT INT TERM

python - <<'PY'
import hashlib
import json
import subprocess
from pathlib import Path

path = Path("build/live_authority/workbench_canonical_bundle.json")
bundle = json.loads(path.read_text(encoding="utf-8"))

assert bundle["authority_state"] == "CURRENT", bundle["authority_state"]
assert bundle.get("snapshot", {}).get("snapshot_id")
assert bundle.get("producer_manifest")

# Defensive credential-leak check: canonical output must not expose bearer/header/token fields.
def walk(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{prefix}.{key}" if prefix else key
            lowered = key.lower()
            assert lowered not in {
                "authorization",
                "access_token",
                "oauth_access_token",
                "bearer_token",
            }, here
            walk(child, here)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            walk(child, f"{prefix}[{i}]")
walk(bundle)

sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
repo_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
receipt = {
    "verification": "Workbench live-authenticated canonical producer",
    "repository_sha": repo_sha,
    "snapshot_id": bundle["snapshot"]["snapshot_id"],
    "authority_state": bundle["authority_state"],
    "producer_manifest": bundle["producer_manifest"],
    "bundle_sha256": sha256,
    "credentials_embedded": False,
    "scientific_effect": "NONE",
    "biological_evidence": False,
}
receipt_path = Path("build/live_authority/workbench_live_auth_receipt.json")
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
try:
    receipt_path.chmod(0o600)
except OSError:
    pass
print(json.dumps(receipt, indent=2))
PY
```

## Acceptance criteria

The live gate passes only if all of the following are true:

- the local repository was clean and synchronized to current canonical `main` before execution;
- the offline producer-boundary verifier passed;
- the live producer completed without authority-pin drift or source-read failure;
- `authority_state` is `CURRENT`;
- a non-empty `snapshot_id` and `producer_manifest` were produced;
- the bundle contains no credential-bearing fields;
- the bundle and bounded receipt are persisted with an exact repository SHA and bundle SHA-256;
- the resulting receipt is reviewed before project-control surfaces are changed from gate-open to gate-closed.

## Fail-closed outcomes

Do **not** reinterpret these as software success:

- missing/expired/insufficient OAuth token;
- authority revision or spreadsheet-state drift;
- source permission/read failures;
- incomplete canonical bindings;
- `authority_state` other than `CURRENT`;
- any indication that a credential was serialized into output.

Resolve the specific operational defect, recheck live pins, and rerun from the beginning. Do not loosen the producer contract to make the gate pass.
