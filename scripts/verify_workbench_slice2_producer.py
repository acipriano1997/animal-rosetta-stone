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


def _claim(claim_id, study_id):
    return {
        "Claim_ID": claim_id,
        "Claim_Short": claim_id + " bounded claim",
        "Species": "Pan troglodytes",
        "Scope_Boundary": "bounded",
        "Status": "bounded",
        "Claim_Type": "bounded",
        "Evidence_Channels": "bounded",
        "Behavioral_Validation": "bounded",
        "Independent_Replication": "not established",
        "ARS_Confidence": "bounded",
        "Confidence_Rationale": "bounded",
        "Do_Not_Overclaim": "No semantic promotion.",
        "Population_Boundary": "bounded",
        "Method_Boundary": "bounded",
        "Alternative_Explanations": "context remains possible",
        "Null_Evidence_IDs": "",
        "Source_Study_IDs": study_id,
        "Reproducibility_Status": "bounded",
    }


class VerificationReader:
    def __init__(self, manifest):
        self.m = manifest
        docs = manifest["documents"]
        self.docs = {
            docs["species"]["document_id"]: _doc(docs["species"], [
                "Activation status","ACTIVE - pilot.","Focal taxon: Pan troglodytes.",
                "Primary population anchors currently represented: bounded populations.",
            ]),
            docs["run001"]["document_id"]: _doc(docs["run001"], [
                "Run_ID: RUN-PT-RQ0001-001","Dataset: D0018",
                "Status: DEVELOPMENT_ONLY_PASS_MIXED_SIGNAL",
            ]),
            docs["run002"]["document_id"]: _doc(docs["run002"], [
                "Run_ID: RUN-PT-RQ0001-002","Dataset: D0018",
                "Status: LOCKED_INTERNAL_EVALUATION_COMPLETE_NOT_CONFIRMATORY",
            ]),
            docs["run003"]["document_id"]: _doc(docs["run003"], [
                "Run_ID: RUN-PT-RQ0001-003","Dataset: D0020",
                "Status: DEVELOPMENT_SEQUENCE_CRITERION_NOT_MET",
                "B0 = 0.455698","B1 = 0.460562","B1 − B0 = +0.004864",
                "Scientific disposition","Development criterion not met.",
            ]),
            docs["run004"]["document_id"]: _doc(docs["run004"], [
                "Run_ID: RUN-PT-RQ0001-004","Dataset: D0020",
                "Status: LOCKED_CROSS_COMMUNITY_EVALUATION_COMPLETE",
                "B0 = 0.445215","B1 = 0.452642","B1 − B0 = +0.007428",
                "Registered disposition: NULL_OR_CONTEXT_SUFFICIENT.",
            ]),
            docs["run005006"]["document_id"]: _doc(docs["run005006"], [
                "Status","FROZEN_EXECUTION_CONTRACT / EMPIRICAL_RUN_HELD_AT_SECRET_BACKED_MATERIALIZATION.",
                "Current external blocker","Empirical execution remains held.",
            ]),
            docs["harness_verify"]["document_id"]: _doc(docs["harness_verify"], [
                "Status","OPERATIONALLY_VERIFIED / ZERO_SYNTHETIC / EMPIRICAL_EXECUTION_UNEARNED.",
                "RHF result: 35/35 PASS; biological_evidence=false.",
            ]),
        }

        self.ranges = {}
        aceb = manifest["aceb"]["spreadsheet_id"]
        r = manifest["aceb"]["ranges"]
        self.ranges[(aceb, r["research_questions"])] = _table([{
            "Question_ID":"RQ0001","Research_Question":"Bounded question.",
            "Primary_Outcome_or_Discriminator":"Held-out prediction.",
            "Ethics_Welfare_Gate":"Passive/archive first.","Status":"active_exploratory",
        }])
        self.ranges[(aceb, r["hypotheses"])] = _table([
            {"Hypothesis_ID":hid,"Hypothesis_Type":kind,"Hypothesis_Statement":hid,"Outcome_Summary":"bounded"}
            for hid,kind in (("H0001","primary"),("H0002","alternative"),("H0003","null"))
        ])
        self.ranges[(aceb, r["datasets"])] = _table([
            {
                "Dataset_ID":did,"Name":did,"Primary_Use":"bounded",
                "Ingestion_Status":status,"Rights_or_Restrictions":rights,
                "License_or_Access":"bounded","Scale":"bounded",
                "Annotation_Grain":"event","Notes":"bounded",
            }
            for did,status,rights in (
                ("D0018","COMPLETE","D0018 rights"),
                ("D0019","READY_FOR_SECRET_BACKED_MATERIALIZATION","D0019 rights"),
                ("D0020","COMPLETE","D0020 rights"),
                ("D0025","HELD_SCHEMA","D0025 rights"),
            )
        ])
        self.ranges[(aceb, r["comparison_gate"])] = _table([
            {"Criterion_ID":"CRG-C","Current_Status":"NOT_PASS","Current_Evidence":"held"},
            {"Criterion_ID":"CRG-D","Current_Status":"PARTIAL","Current_Evidence":"partial"},
            {"Criterion_ID":"CRG-OVERALL","Current_Status":"NOT_COMPARISON_READY","Current_Evidence":"CRG-C"},
        ])
        self.ranges[(aceb, r["claim_propagation"])] = _table([
            {"Disposition":"KNOWN_SIDE_CALIBRATION","Permitted_Core_Interpretation":"known-side only"},
            {"Disposition":"NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT","Permitted_Core_Interpretation":"bounded null"},
            {"Disposition":"EMPIRICAL_EXECUTION_HELD","Permitted_Core_Interpretation":"no empirical disposition"},
        ])
        self.ranges[(aceb, r["claims"])] = _table([
            _claim("C0062","S0057"),_claim("C0083","S0083"),
            _claim("C0084","S0084; S0085"),_claim("C0085","S0085"),
            _claim("C0086","S0018"),
        ])
        self.ranges[(aceb, r["claim_evidence_links"])] = _table([
            {
                "Link_ID":"L0057","Claim_ID":"C0062","Evidence_Direction":"supports",
                "Experiment_ID":"E0062","Study_ID":"S0057","Dataset_ID":"",
                "Evidence_Channel":"bounded","Population_Scope":"bounded",
                "Method_Scope":"bounded","Independence_Level":"same-study",
                "Replication_Relation":"bounded","Correction_State":"current",
                "Weight_or_Confidence_Basis":"bounded",
                "Alternative_Explanation_Addressed":"no semantics",
                "Source_Provenance_Verified":"yes","Notes":"",
            },
            {
                "Link_ID":"L0078","Claim_ID":"C0086","Evidence_Direction":"supports",
                "Experiment_ID":"E0086","Study_ID":"S0018","Dataset_ID":"D0020",
                "Evidence_Channel":"registered null","Population_Scope":"five communities",
                "Method_Scope":"bounded","Independence_Level":"within-study transfer",
                "Replication_Relation":"not independent study","Correction_State":"current",
                "Weight_or_Confidence_Basis":"frozen criteria",
                "Alternative_Explanation_Addressed":"richer representations remain possible",
                "Source_Provenance_Verified":"yes","Notes":"",
            },
        ])
        self.ranges[(aceb, r["contradictions"])] = _table([{
            "Record_ID":"CC-OTHER","Target_Study_or_Claim":"UNRELATED","Type":"other",
            "Date_or_Year":"2026","What_Changed":"","Effect_on_Conclusion":"",
            "ARS_Action":"","Source_or_Link":"","Status":"current",
        }])
        self.ranges[(aceb, r["disagreements"])] = _table([{
            "Disagreement_ID":"DG-OTHER","Research_Question_ID":"RQ-OTHER",
            "Claim_or_Hypothesis_ID":"C-OTHER","Run_IDs":"",
            "Disagreement_Dimension":"other","Position_A":"","Position_B":"",
            "Other_Positions":"","Common_Ground":"","Key_Assumption_Difference":"",
            "Evidence_Needed":"","Empirical_Discriminator":"","Priority":"low",
            "Status":"open","Resolution_or_Current_State":"",
        }])

        for did, event in (
            ("D0018", {
                "Event_ID":"EVT-D18-1","Dataset_ID":"D0018","Taxon_ID":"SP001",
                "Population_or_Group_ID":"Sonso","Source_Study_ID":"S0017",
                "Source_Experiment_ID":"E0019","Event_Type":"controlled",
                "Source_File":"Source-data-snake.csv","Source_Blob_SHA":"b18","Source_Row":"2",
                "Sender_IDs":"S1","Receiver_IDs":"R1","Context_ID":"CTX",
                "Source_Condition":"back","Trigger_or_Anchor":"anchor",
                "Signal_Component_1":"a","Signal_Component_2":"b","Signal_Order":"a→b",
                "Combination_Flag":"yes","Receiver_Response":"response",
                "Consequence_or_Outcome":"outcome","Sender_Followup_Repair_Cessation":"NA",
                "Observation_Window":"120s","Event_Confidence":"HIGH",
                "Missingness_Codes":"FOLLOWUP_NOT_RECORDED","Provenance_Record_ID":"P18",
                "Split":"DEVELOPMENT","Split_Eligibility":"DEVELOPMENT_ONLY","Notes":"",
            }),
            ("D0020", {
                "Event_ID":"EVT-D20-1","Dataset_ID":"D0020","Taxon_ID":"SP001",
                "Population_or_Group_ID":"Waibira","Source_Study_ID":"S0018",
                "Source_Experiment_ID":"E0021","Event_Type":"natural",
                "Source_Communication_ID":"300390","Source_Row_Min":"2","Source_Row_Max":"2",
                "Source_Row_Count":"1","Relative_Start_s":"2","Relative_End_s":"4",
                "Initial_Sender_ID":"A","Initial_Receiver_ID":"B","Participant_IDs":"A;B",
                "Gesture_Token_Count":"1","Exchange_Status":"NO","Declared_Turn_Count":"1",
                "Final_Outcome_Label":"GoalRecipient","Final_Outcome_Time_s":"4",
                "Continuation_Structure":"single","Event_Confidence":"HIGH",
                "Missingness_Codes":"GESTURE_FORM_NOT_RELEASED;GOAL_LABEL_ANONYMIZED",
                "Provenance_Record_ID":"P20","Split":"LOCKED_CROSS_COMMUNITY_EVALUATION",
                "Split_Eligibility":"PROSPECTIVE_SECONDARY_CROSS_COMMUNITY_EVAL_NOT_FULLY_BLIND",
                "Sender_Alternation_Count":"0","Initial_Goal_Anon":"Goal_1",
            }),
        ):
            spec = manifest["event_sources"][did]
            self.ranges[(spec["spreadsheet_id"], spec["event_range"])] = _table([event])
            source_prov_id = "PRV-D0018-SNAKE-SOURCE" if did == "D0018" else "PRV-D0020-CSV"
            self.ranges[(spec["spreadsheet_id"], spec["provenance_range"])] = _table([{
                "Provenance_Record_ID":source_prov_id,"Object":"source",
                "Type":"public source data","Persistent_ID_or_URL":"https://example.invalid",
                "Version_or_Branch":"v","Content_ID":"blob","Rights":"bounded",
                "Retrieved_Date":"2026-09-29","Transformation":"row-preserving",
                "Raw_vs_Derived":"source data","Stored_Bytes":"no","Notes":"",
            }])
            self.ranges[(spec["spreadsheet_id"], spec["missingness_range"])] = _table([{
                "Issue":"Raw media","Scope":"all","Status":"NOT_INGESTED",
                "Scientific_Consequence":"Cannot independently recode media.",
                "Required_Action":"No synthesized preview; preserve provenance.",
            }])

    def drive_metadata(self, file_id):
        if file_id == self.m["aceb"]["spreadsheet_id"]:
            return {
                "id":file_id,"name":self.m["aceb"]["title"],
                "modifiedTime":self.m["aceb"]["observed_modified_time"],
            }
        for spec in self.m["event_sources"].values():
            if file_id == spec["spreadsheet_id"]:
                return {
                    "id":file_id,"name":spec["title"],
                    "modifiedTime":spec["observed_modified_time"],
                }
        raise KeyError(file_id)

    def document(self, document_id):
        return deepcopy(self.docs[document_id])

    def spreadsheet_values(self, spreadsheet_id, range_name):
        return deepcopy(self.ranges[(spreadsheet_id, range_name)])


def main() -> None:
    manifest = deepcopy(load_source_manifest())
    manifest["event_sources"]["D0018"]["expected_event_count"] = 1
    manifest["event_sources"]["D0020"]["expected_event_count"] = 1

    bundle = WorkspaceCanonicalProducer(
        VerificationReader(manifest), manifest
    ).build_bundle()
    snapshot, _ = canonical_bundle_to_snapshot(bundle, source="<memory>")
    run004 = next(
        r for r in snapshot["runs"] if r["run_id"] == "RUN-PT-RQ0001-004"
    )

    checks = {
        "producer_manifest_bound": bundle["producer_manifest"] == manifest["manifest_id"],
        "authority_current": bundle["authority_state"] == "CURRENT",
        "adapter_contract_accepts_output": snapshot["mode"] == "CANONICAL_READ_ADAPTER",
        "run_result_disposition_preserved": run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT",
        "claim_propagation_layer_separate": run004["claim_propagation_disposition"] == "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT",
        "held_empirical_runs_remain_unexecuted": all(
            r["state"] == "EMPIRICAL_EXECUTION_HELD" and r["disposition"] is None
            for r in snapshot["runs"] if r["dataset_id"] == "D0019"
        ),
        "event_projection_present": len(snapshot["events"]) == 2,
        "event_provenance_resolves": all(
            pid in snapshot["event_provenance"]
            for event in snapshot["events"] for pid in event["provenance_ids"]
        ),
        "evidence_projection_present": len(snapshot["evidence_items"]) == 5,
        "evidence_registry_absence_is_bounded": (
            snapshot["evidence_registry_status"]["matching_contradiction_rows"] == 0
            and snapshot["evidence_registry_status"]["matching_disagreement_rows"] == 0
            and "not evidence" in snapshot["evidence_registry_status"]["absence_rule"].lower()
        ),
        "media_placeholders_are_nonpreview": all(
            m["bytes_available"] is False and m["preview_allowed"] is False
            for m in snapshot["media_placeholders"]
        ),
        "dataset_semantic_authority_none": all(
            d["semantic_authority"] == "NONE" for d in snapshot["datasets"]
        ),
        "synthetic_nonevidentiary": all(
            v["biological_evidence"] is False
            for v in snapshot["software_verification"]
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
