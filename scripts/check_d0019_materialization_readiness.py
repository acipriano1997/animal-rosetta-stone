"""Preflight D0019 empirical materialization without exposing the HMAC secret."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

REQUIRED_CONTRACTS = (
    "contracts/d0019_v1_verified_source_snapshot.json",
    "contracts/d0019_rdc004_source_crosswalk_v0_2.json",
    "contracts/pr0005_pd_001_grouping_amendment.json",
    "contracts/d0019_group2_eligibility_rules_v0_1.json",
    "contracts/pr0005_pd_002_split_policy.json",
    "contracts/d0019_rdc004_final_admission_v0_1.json",
    "contracts/d0019_group1_transfer_procedure_v0_1.json",
)
REQUIRED_SOURCE_SHA = "26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e"
REQUIRED_ROW_DIGEST = "d6d004eb5a685eed1875e5a430cfb7bb0b6638bb315cf5bf2e2b998588c2be63"


def namespace_fingerprint(secret: bytes) -> str:
    if len(secret) < 32:
        raise ValueError("ARS_D0019_HMAC_KEY must contain at least 32 bytes")
    return hashlib.sha256(
        b"D0019_NAMESPACE_PUBLIC_FINGERPRINT|" + hashlib.sha256(secret).digest()
    ).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _unsafe_sync_path(path: Path) -> bool:
    tokens = {part.lower().replace(" ","") for part in path.expanduser().parts}
    markers = {
        "googledrive","google-drive","dropbox","onedrive",
        "icloud","iclouddrive","mobile documents",
    }
    return any(marker.replace(" ","") in token for token in tokens for marker in markers)


def _git_state(repo_root: Path) -> tuple[str | None, bool | None]:
    try:
        head = subprocess.run(
            ["git","rev-parse","HEAD"], cwd=repo_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git","status","--porcelain"], cwd=repo_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip())
        return head, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def readiness(
    *,
    repo_root: Path,
    output_dir: Path,
    secret: bytes,
    expected_head: str | None = None,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    failures: list[str] = []

    try:
        fingerprint = namespace_fingerprint(secret)
        checks["secret_configured"] = True
        checks["secret_minimum_bytes"] = True
        checks["identity_namespace_fingerprint"] = fingerprint
    except ValueError as exc:
        checks["secret_configured"] = bool(secret)
        checks["secret_minimum_bytes"] = False
        checks["identity_namespace_fingerprint"] = None
        failures.append(str(exc))

    if secret and (len(set(secret)) < 4 or secret.strip().lower() in {
        b"changeme", b"password", b"secret", b"test", b"placeholder"
    }):
        checks["secret_obvious_placeholder"] = True
        failures.append("ARS_D0019_HMAC_KEY resembles a placeholder/low-diversity value")
    else:
        checks["secret_obvious_placeholder"] = False

    missing = [p for p in REQUIRED_CONTRACTS if not (repo_root/p).is_file()]
    checks["required_contracts_present"] = not missing
    checks["missing_contracts"] = missing
    if missing:
        failures.append("Required frozen contracts are missing")

    if not missing:
        source = json.loads((repo_root/REQUIRED_CONTRACTS[0]).read_text())
        admission = json.loads((repo_root/"contracts/d0019_rdc004_final_admission_v0_1.json").read_text())
        checks["source_sha256_matches_frozen"] = source.get("file",{}).get("sha256") == REQUIRED_SOURCE_SHA
        checks["eligible_row_digest_matches_frozen"] = (
            admission.get("dependencies",{}).get("eligible_source_row_set_sha256")
            == REQUIRED_ROW_DIGEST
        )
        checks["eligible_rows_frozen_104"] = admission.get("dependencies",{}).get("eligible_rows") == 104
        checks["unordered_dyads_frozen_69"] = admission.get("dependencies",{}).get("primary_unordered_dyads") == 69
        for key in (
            "source_sha256_matches_frozen",
            "eligible_row_digest_matches_frozen",
            "eligible_rows_frozen_104",
            "unordered_dyads_frozen_69",
        ):
            if not checks[key]:
                failures.append(f"Frozen contract mismatch: {key}")

    output = output_dir.expanduser().resolve()
    root = repo_root.resolve()
    checks["output_outside_repository"] = not _inside(output,root)
    checks["output_not_common_sync_folder"] = not _unsafe_sync_path(output)
    if not checks["output_outside_repository"]:
        failures.append("Restricted materialization output must be outside the Git repository")
    if not checks["output_not_common_sync_folder"]:
        failures.append("Restricted materialization output must not be in a common cloud-sync folder")

    head, dirty = _git_state(root)
    checks["git_head"] = head
    checks["git_worktree_clean"] = None if dirty is None else not dirty
    if dirty is True:
        failures.append("Git working tree is dirty; empirical materialization requires an exact reviewed state")
    if expected_head:
        checks["expected_head"] = expected_head
        checks["git_head_matches_expected"] = head == expected_head
        if head != expected_head:
            failures.append("Git HEAD does not match the explicitly reviewed commit")
    else:
        checks["expected_head"] = None
        checks["git_head_matches_expected"] = False
        failures.append("Explicit reviewed Git commit SHA is required for empirical materialization")

    return {
        "dataset_id":"D0019",
        "phase":"EMPIRICAL_MATERIALIZATION_READINESS",
        "ready":not failures,
        "state":"READY_FOR_SECRET_BACKED_MATERIALIZATION" if not failures else "HELD_MATERIALIZATION_READINESS",
        "checks":checks,
        "failures":failures,
        "secret_value_emitted":False,
        "group1_accessed":False,
        "pr0005_executed":False,
        "scientific_effect":"NONE",
    }


def main() -> None:
    ap=argparse.ArgumentParser(description="Check D0019 empirical materialization readiness without printing the secret")
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--expected-head",required=True)
    ap.add_argument("--out",default=None,help="Optional JSON receipt path; must not contain secret")
    args=ap.parse_args()

    secret=os.environ.get("ARS_D0019_HMAC_KEY","").encode()
    result=readiness(
        repo_root=Path(args.repo_root),
        output_dir=Path(args.output_dir),
        secret=secret,
        expected_head=args.expected_head,
    )
    if args.out:
        path=Path(args.out)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "state":result["state"],
        "ready":result["ready"],
        "secret_configured":result["checks"]["secret_configured"],
        "secret_minimum_bytes":result["checks"]["secret_minimum_bytes"],
        "identity_namespace_fingerprint":result["checks"]["identity_namespace_fingerprint"],
        "output_outside_repository":result["checks"]["output_outside_repository"],
        "output_not_common_sync_folder":result["checks"]["output_not_common_sync_folder"],
        "git_head_matches_expected":result["checks"]["git_head_matches_expected"],
        "failures":result["failures"],
        "secret_value_emitted":False,
    }))
    raise SystemExit(0 if result["ready"] else 2)


if __name__=="__main__":
    main()
