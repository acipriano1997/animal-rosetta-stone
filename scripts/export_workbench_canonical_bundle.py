from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

from ars_workbench.producer import WorkspaceCanonicalProducer
from ars_workbench.workspace import GoogleWorkspaceReadError, GoogleWorkspaceRESTReader


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def deterministic_bytes(bundle: dict) -> bytes:
    """Compare all authority and scientific fields; exclude capture metadata only."""
    value = deepcopy(bundle)
    value.pop("captured_at_utc", None)
    value["snapshot"].pop("snapshot_id", None)
    value["snapshot"].pop("captured_date", None)
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()


def check_credentials(value: dict, token: str) -> None:
    sensitive = {"authorization", "access_token", "oauth_access_token", "bearer_token",
                 "refresh_token", "client_secret", "ars_google_oauth_access_token"}
    def walk(child):
        if isinstance(child, dict):
            for key, item in child.items():
                if key.lower() in sensitive:
                    raise ValueError("Credential-bearing output field rejected")
                walk(key)
                walk(item)
        elif isinstance(child, list):
            for item in child:
                walk(item)
        elif isinstance(child, str) and token in child:
            raise ValueError("Runtime credential found in output")
    walk(value)


def write_private_json(path: Path, value: dict) -> None:
    # Start at 0600, then atomically replace: never expose a partial/0644 bundle
    # and never follow an existing output symlink into an unrelated file.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".workbench-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_json_bytes(value))
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def clean_repository_sha() -> str:
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root):
        raise ValueError("Live verification requires a clean committed checkout")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def export_bundle(token: str, out: Path, *, verify_live: bool = False) -> dict:
    repository_sha = clean_repository_sha() if verify_live else None
    receipt_path = out.with_name(out.stem + "_receipt.json")
    second_path = out.with_name(out.stem + "_rerun.json")
    # A failed new run must never leave an older success receipt at its target.
    if verify_live and any(p.exists() or p.is_symlink() for p in (out, second_path, receipt_path)):
        raise ValueError("Live verification requires unused output paths")
    producer = WorkspaceCanonicalProducer(GoogleWorkspaceRESTReader(token))
    first = producer.build_bundle()
    check_credentials(first, token)
    second = None
    if verify_live:
        second = producer.build_bundle()
        check_credentials(second, token)
        if deterministic_bytes(first) != deterministic_bytes(second):
            raise ValueError("Canonical producer reruns disagree; no receipt emitted")
        if clean_repository_sha() != repository_sha:
            raise ValueError("Repository changed during live verification")
    summary = {
        "snapshot_id": first["snapshot"]["snapshot_id"],
        "producer_manifest": first["producer_manifest"],
        "authority_state": first["authority_state"],
        "output": str(out),
        "credentials_embedded": False,
        "scientific_effect": "NONE",
    }
    check_credentials(summary, token)
    check_credentials({"rerun_output": str(second_path), "receipt_output": str(receipt_path)}, token)
    write_private_json(out, first)
    if second is not None:
        write_private_json(second_path, second)
        receipt = {
            **summary,
            "verification": "Workbench live-authenticated canonical producer",
            "repository_sha": repository_sha,
            "captured_at_utc": first["captured_at_utc"],
            "bundle_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "rerun_sha256": hashlib.sha256(second_path.read_bytes()).hexdigest(),
            "deterministic_content_sha256": hashlib.sha256(deterministic_bytes(first)).hexdigest(),
            "deterministic_rerun": "PASS_EXCLUDING_CAPTURE_METADATA_ONLY",
            "authority_pins_sha256": hashlib.sha256(_json_bytes(producer.manifest)).hexdigest(),
            "event_inventory": first["snapshot"]["event_inventory"],
            "adapter_and_provenance_validation": "PASS",
            "biological_evidence": False,
        }
        check_credentials(receipt, token)
        write_private_json(receipt_path, receipt)
        summary["receipt"] = str(receipt_path)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Export a fail-closed Rosetta Research Workbench canonical-read bundle "
            "from pinned Google Drive/ACEB authorities."
        )
    )
    ap.add_argument("--out", required=True, help="Output JSON path.")
    ap.add_argument("--verify-live", action="store_true",
                    help="Run the same REST producer twice and persist a bounded exact-commit receipt.")
    ap.add_argument(
        "--access-token-env",
        default="ARS_GOOGLE_OAUTH_ACCESS_TOKEN",
        help="Environment variable containing a short-lived OAuth bearer token.",
    )
    args = ap.parse_args()

    token = os.getenv(args.access_token_env, "")
    if not token.strip():
        raise SystemExit(
            f"Missing runtime credential in environment variable {args.access_token_env}. "
            "Do not pass access tokens on the command line."
        )

    try:
        summary = export_bundle(token.strip(), Path(args.out), verify_live=args.verify_live)
    except GoogleWorkspaceReadError as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
