from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from ars_workbench.canonical import canonical_bundle_to_snapshot
from ars_workbench.producer import WorkspaceCanonicalProducer, load_source_manifest


def _doc(spec, lines):
    return {
        "title": spec["title"],
        "revisionId": spec["revision_id"],
        "body": {
            "content": [
                {"paragraph": {"elements": [{"textRun": {"content": line + "\n"}}]}}
                for line in lines
            ]
        },
    }


def _table(rows):
    headers = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return [headers] + [[row.get(h, "") for h in headers] for row in rows]


class VerificationReader:
    def __init__(self, manifest):
        self.m = manifest
        docs = manifest["documents"]
        self.docs = {
            docs["species"]["document_id"]: _doc(
                docs["species"],
                [
                    "Activation status",
                    "ACTIVE - pilot.",
                    "Focal taxon: Pan troglodytes.",
                    "Primary population anchors currently represented: bounded test populations.",
                ],
            ),
            docs["run001"]["document_id"]: _doc(
                docs["run001"],
                [
                    "Run_ID: RUN-PT-RQ0001-001",
                    "Dataset: D0018",
                    "Status: DEVELOPMENT_ONLY_PASS_MIXED_SIGNAL",
                ],
            ),
            docs["run002"]["document_id"]: _doc(
                docs["run002"],
                [
                    "Run_ID: RUN-PT-RQ0001-002",
                    "Dataset: D0018",
                    "Status: LOCKED_INTERNAL_EVALUATION_COMPLETE_NOT_CONFIRMATORY",
                ],
            ),
            docs["run003"]["document_id"]: _doc(
                docs["run003"],
                [
                    "Run_ID: RUN-PT-RQ0001-003",
                    "Dataset: D0020",
                    "Status: DEVELOPMENT_SEQUENCE_CRITERION_NOT_MET",
                    "B0 = 0.455698",
                    "B1 = 0.460562",
                    "B1 − B0 = +0.004864",
                    "Scientific disposition",
                    "Development criterion not met.",
                ],
            ),
            docs["run004"]["document_id"]: _doc(
                docs["run004"],
                [
                    "Run_ID: RUN-PT-RQ0001-004",
                    "Dataset: D0020",
                    "Status: LOCKED_CROSS_COMMUNITY_EVALUATION_COMPLETE",
                    "B0 = 0.445215",
                    "B1 = 0.452642",
                    "B1 − B0 = +0.007428",
                    "Registered disposition: NULL_OR_CONTEXT_SUFFICIENT.",
                ],
            ),
            docs["run005006"]["document_id"]: _doc(
                docs["run005006"],
                [
                    "Status",
                    "FROZEN_EXECUTION_CONTRACT / EMPIRICAL_RUN_HELD_AT_SECRET_BACKED_MATERIALIZATION.",
                    "Current external blocker",
                    "Empirical execution remains held.",
                ],
            ),
            docs["harness_verify"]["document_id"]: _doc(
                docs["harness_verify"],
                [
                    "Status",
                    "OPERATIONALLY_VERIFIED / ZERO_SYNTHETIC / EMPIRICAL_EXECUTION_UNEARNED.",
                    "RHF result: 35/35 PASS; biological_evidence=false.",
                ],
            ),
        }
        self.ranges = {}
        r = manifest["aceb"]["ranges"]
        self.ranges[r["research_questions"]] = _table(
            [{
                "Question_ID":"RQ0001",
                "Research_Question":"Bounded question.",
                "Primary_Outcome_or_Discriminator":"Held-out prediction.",
                "Ethics_Welfare_Gate":"Passive/archive first.",
                "Status":"active_exploratory",
            }]
        )
        self.ranges[r["hypotheses"]] = _table([
            {
                "Hypothesis_ID":hid,
                "Hypothesis_Type":kind,
                "Hypothesis_Statement":hid+" statement",
                "Outcome_Summary":"bounded",
            }
            for hid,kind in (("H0001","primary"),("H0002","alternative"),("H0003","null"))
        ])
        self.ranges[r["datasets"]] = _table([
            {
                "Dataset_ID":did,
                "Name":did,
                "Primary_Use":"bounded",
                "Ingestion_Status":status,
                "Rights_or_Restrictions":"bounded rights",
                "License_or_Access":"bounded",
                "Scale":"bounded",
                "Annotation_Grain":"event",
                "Notes":"bounded gate",
            }
            for did,status in (
                ("D0018","COMPLETE"),
                ("D0019","READY_FOR_SECRET_BACKED_MATERIALIZATION"),
                ("D0020","COMPLETE"),
                ("D0025","HELD_SCHEMA"),
            )
        ])
        self.ranges[r["comparison_gate"]] = _table([
            {"Criterion_ID":"CRG-C","Current_Status":"NOT_PASS","Current_Evidence":"empirical held"},
            {"Criterion_ID":"CRG-D","Current_Status":"PARTIAL","Current_Evidence":"partial"},
            {"Criterion_ID":"CRG-OVERALL","Current_Status":"NOT_COMPARISON_READY","Current_Evidence":"CRG-C"},
        ])
        self.ranges[r["claim_propagation"]] = _table([
            {"Disposition":"KNOWN_SIDE_CALIBRATION","Permitted_Core_Interpretation":"known-side only"},
            {"Disposition":"NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT","Permitted_Core_Interpretation":"bounded null"},
            {"Disposition":"EMPIRICAL_EXECUTION_HELD","Permitted_Core_Interpretation":"no empirical disposition"},
        ])

    def drive_metadata(self, file_id):
        return {
            "id":file_id,
            "name":self.m["aceb"]["title"],
            "mimeType":"application/vnd.google-apps.spreadsheet",
            "modifiedTime":self.m["aceb"]["observed_modified_time"],
        }

    def document(self, document_id):
        return deepcopy(self.docs[document_id])

    def spreadsheet_values(self, spreadsheet_id, range_name):
        return deepcopy(self.ranges[range_name])


def main() -> None:
    manifest = load_source_manifest()
    bundle = WorkspaceCanonicalProducer(VerificationReader(manifest), manifest).build_bundle()
    snapshot, _ = canonical_bundle_to_snapshot(bundle, source="<memory>")
    run004 = next(r for r in snapshot["runs"] if r["run_id"] == "RUN-PT-RQ0001-004")

    checks = {
        "producer_manifest_bound": bundle["producer_manifest"] == manifest["manifest_id"],
        "authority_current": bundle["authority_state"] == "CURRENT",
        "adapter_contract_accepts_output": snapshot["mode"] == "CANONICAL_READ_ADAPTER",
        "run_result_disposition_preserved": run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT",
        "claim_propagation_layer_separate": (
            run004["claim_propagation_disposition"]
            == "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
        ),
        "held_empirical_runs_remain_unexecuted": all(
            r["state"] == "EMPIRICAL_EXECUTION_HELD" and r["disposition"] is None
            for r in snapshot["runs"]
            if r["dataset_id"] == "D0019"
        ),
        "dataset_semantic_authority_none": all(
            d["semantic_authority"] == "NONE" for d in snapshot["datasets"]
        ),
        "synthetic_nonevidentiary": all(
            v["biological_evidence"] is False for v in snapshot["software_verification"]
        ),
    }
    receipt = {
        "slice": "Rosetta Research Workbench Phase I Slice 2B canonical producer",
        "repository_sha": os.getenv("GITHUB_SHA") or "LOCAL_UNCOMMITTED",
        "checks": checks,
        "all_passed": all(checks.values()),
        "external_live_drive_exercised": False,
        "scientific_effect": "NONE",
        "biological_evidence": False,
    }
    out = Path("build/workbench_slice2_producer_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    if not receipt["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
