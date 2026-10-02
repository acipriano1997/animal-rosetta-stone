from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ars_workbench.producer import WorkspaceCanonicalProducer
from ars_workbench.workspace import GoogleWorkspaceRESTReader


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Export a fail-closed Rosetta Research Workbench canonical-read bundle "
            "from pinned Google Drive/ACEB authorities."
        )
    )
    ap.add_argument("--out", required=True, help="Output JSON path.")
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

    bundle = WorkspaceCanonicalProducer(GoogleWorkspaceRESTReader(token)).build_bundle()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    try:
        out.chmod(0o600)
    except OSError:
        pass

    print(
        json.dumps(
            {
                "snapshot_id": bundle["snapshot"]["snapshot_id"],
                "producer_manifest": bundle["producer_manifest"],
                "authority_state": bundle["authority_state"],
                "output": str(out),
                "credentials_embedded": False,
                "scientific_effect": "NONE",
            }
        )
    )


if __name__ == "__main__":
    main()
