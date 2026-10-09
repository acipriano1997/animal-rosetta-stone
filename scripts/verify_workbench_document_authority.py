"""Offline regression verification of the durable document authority contract."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from ars_workbench.producer import CanonicalProducerError, WorkspaceCanonicalProducer, load_source_manifest
from verify_workbench_slice2_producer import VerificationReader


def main() -> None:
    manifest = load_source_manifest()
    checks = {}
    for key, spec in manifest["documents"].items():
        reader = VerificationReader(manifest)
        producer = WorkspaceCanonicalProducer(reader, manifest)
        producer._read_pinned_document(key)
        reader.docs[spec["document_id"]]["revisionId"] = "new-user-or-format-transient-token"
        producer._read_pinned_document(key)
        checks[f"{key}_unchanged_drive_accepts_new_docs_token"] = True

    for case in ("revision", "modified_time", "file_id", "document_id", "type", "title", "during_read"):
        class AlteredReader(VerificationReader):
            extracted = False

            def drive_metadata(self, file_id):
                value = super().drive_metadata(file_id)
                changes = {
                    "modified_time": ("modifiedTime", "changed"),
                    "file_id": ("id", "wrong"),
                    "type": ("mimeType", "application/pdf"),
                    "title": ("name", "wrong"),
                }
                if case in changes:
                    field, replacement = changes[case]
                    value[field] = replacement
                if case == "during_read" and self.extracted:
                    value["modifiedTime"] = "changed-during-extraction"
                return value

            def drive_head_revision(self, document_id):
                return "changed" if case == "revision" else super().drive_head_revision(document_id)

            def document(self, document_id):
                value = super().document(document_id)
                self.extracted = True
                if case == "document_id":
                    value["documentId"] = "wrong"
                return value

        try:
            WorkspaceCanonicalProducer(AlteredReader(manifest), manifest)._read_pinned_document("species")
        except CanonicalProducerError:
            checks[f"{case}_fails_closed"] = True
        else:
            raise AssertionError(f"{case} unexpectedly accepted")

    legacy = deepcopy(manifest)
    legacy["documents"]["species"]["revision_id"] = "legacy-transient-token"
    try:
        WorkspaceCanonicalProducer(VerificationReader(manifest), legacy)
    except CanonicalProducerError:
        checks["legacy_token_pin_not_reinterpreted"] = True
    else:
        raise AssertionError("legacy token authority unexpectedly accepted")
    receipt = {
        "verification": "Durable Workbench document authority regression",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks, "all_passed": all(checks.values()),
        "external_live_drive_exercised": False,
        "scientific_effect": "NONE", "biological_evidence": False,
    }
    out = Path("build/workbench_document_authority_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
