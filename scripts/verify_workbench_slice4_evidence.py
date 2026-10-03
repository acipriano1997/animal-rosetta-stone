from __future__ import annotations

import json
import os
from pathlib import Path

from ars_workbench.store import WorkbenchStore


def main() -> None:
    store = WorkbenchStore()
    evidence = store.evidence_get("RQ0001")
    claims = store.claims_list()
    media = store.media_placeholders()

    checks = {
        "bounded_claim_set_present": {c["claim_id"] for c in claims}
        == {"C0062", "C0083", "C0084", "C0085", "C0086"},
        "claim_ceilings_visible": all(c.get("do_not_overclaim") for c in claims),
        "explicit_link_state_visible": all(c.get("explicit_link_state") for c in claims),
        "empty_registry_state_bounded": (
            evidence["registry_status"]["matching_contradiction_rows"] == 0
            and evidence["registry_status"]["matching_disagreement_rows"] == 0
            and "not evidence" in evidence["registry_status"]["absence_rule"].lower()
        ),
        "media_never_exposes_bytes_or_preview": all(
            item["bytes_available"] is False
            and item["preview_allowed"] is False
            and "media_url" not in item
            and "preview_url" not in item
            and "image_url" not in item
            and "bytes" not in item
            for item in media
        ),
        "claim_and_media_provenance_resolve": all(
            store.provenance_get(pid) is not None
            for claim in claims
            for pid in claim["provenance_ids"]
        ) and all(
            store.provenance_get(pid) is not None
            for item in media
            for pid in item["provenance_ids"]
        ),
        "overview_omits_bulk_evidence": all(
            key not in store.overview()
            for key in (
                "evidence_items",
                "corrections",
                "disagreements",
                "evidence_provenance",
                "media_placeholders",
            )
        ),
        "software_verification_stays_segregated": all(
            item["biological_evidence"] is False
            for item in evidence["software_verification"]
        ),
    }

    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 4 evidence/contradiction navigation and rights-aware media placeholders",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks,
        "all_passed": all(checks.values()),
        "registry_absence_semantics": "zero matching contradiction/disagreement rows are registry state only, never evidence of absence",
        "media_boundary": "metadata/provenance placeholders only; no bytes, preview, or synthesized media",
        "scientific_effect": "NONE",
        "biological_evidence": False,
    }
    out = Path("build/workbench_slice4_evidence_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
