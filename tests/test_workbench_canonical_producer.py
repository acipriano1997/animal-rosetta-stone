from __future__ import annotations

from copy import deepcopy

import pytest

from ars_workbench.canonical import canonical_bundle_to_snapshot
from ars_workbench.event_projection import EventProjectionError
from ars_workbench.producer import (
    CanonicalProducerError,
    WorkspaceCanonicalProducer,
    extract_google_doc_text,
    load_source_manifest,
)


def _doc(spec, lines, *, tabbed=False):
    content = [
        {"paragraph": {"elements": [{"textRun": {"content": line + "\n"}}]}}
        for line in lines
    ]
    base = {"title": spec["title"], "revisionId": spec["revision_id"]}
    if tabbed:
        base["tabs"] = [{"documentTab": {"body": {"content": content}}}]
    else:
        base["body"] = {"content": content}
    return base


def _table(rows):
    headers = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return [headers] + [[row.get(h, "") for h in headers] for row in rows]


def _small_manifest():
    manifest = load_source_manifest()
    manifest = deepcopy(manifest)
    manifest["event_sources"]["D0018"]["expected_event_count"] = 1
    manifest["event_sources"]["D0020"]["expected_event_count"] = 1
    return manifest


def _event_ranges(manifest):
    d18 = manifest["event_sources"]["D0018"]
    d20 = manifest["event_sources"]["D0020"]
    return {
        (d18["spreadsheet_id"], d18["event_range"]): _table([
            {
                "Event_ID":"EVT-D18-1","Dataset_ID":"D0018","Taxon_ID":"SP001",
                "Population_or_Group_ID":"Sonso/Budongo","Source_Study_ID":"S0017",
                "Source_Experiment_ID":"E0019","Event_Type":"controlled_elicitation",
                "Source_File":"Source-data-snake.csv","Source_Blob_SHA":"blob18","Source_Row":"2",
                "Subject_ID":"RE","Context_ID":"CTX-18","Source_Condition":"back",
                "Sender_IDs":"S0017:RE","Receiver_IDs":"UNKNOWN_AGGREGATE_AUDIENCE",
                "Trigger_or_Anchor":"model-snake discovery","Signal_Component_1":"alarm-huu",
                "Signal_Component_2":"waa-bark","Signal_Order":"alarm-huu→waa-bark",
                "Combination_Flag":"yes","Receiver_Response":"recruited=8",
                "Consequence_or_Outcome":"count=8","Sender_Followup_Repair_Cessation":"NOT_RECORDED",
                "Observation_Window":"120 s","Event_Confidence":"HIGH",
                "Missingness_Codes":"START_TIME_NOT_RECORDED;FOLLOWUP_NOT_RECORDED",
                "Provenance_Record_ID":"PRV-D18-E1","Split":"DEVELOPMENT",
                "Split_Eligibility":"DEVELOPMENT_ONLY","Notes":"bounded source label",
            }
        ]),
        (d18["spreadsheet_id"], d18["provenance_range"]): _table([
            {
                "Provenance_Record_ID":"PRV-D0018-SNAKE-SOURCE","Object":"snake csv",
                "Type":"public source data","Persistent_ID_or_URL":"https://example.invalid/d18",
                "Version_or_Branch":"Data","Content_ID":"blob18","Rights":"bounded",
                "Retrieved_Date":"2026-09-29","Transformation":"row-preserving",
                "Raw_vs_Derived":"source data","Stored_Bytes":"no","Notes":"test",
            }
        ]),
        (d20["spreadsheet_id"], d20["event_range"]): _table([
            {
                "Event_ID":"EVT-D20-1","Dataset_ID":"D0020","Taxon_ID":"SP001",
                "Population_or_Group_ID":"Waibira","Source_Study_ID":"S0018",
                "Source_Experiment_ID":"E0021","Event_Type":"natural_gesture_interaction",
                "Source_Communication_ID":"300390","Source_Row_Min":"2","Source_Row_Max":"2",
                "Source_Row_Count":"1","Relative_Start_s":"2.164","Relative_End_s":"4.043",
                "Initial_Sender_ID":"A_F","Initial_Receiver_ID":"ID_5","Participant_IDs":"A_F;ID_5",
                "Gesture_Token_Count":"1","Exchange_Status":"NO","Declared_Turn_Count":"1",
                "Goal_Sequence":"Goal_1","Final_Outcome_Label":"GoalRecipient",
                "Final_Outcome_Time_s":"4.043","Continuation_Structure":"single gesture token",
                "Event_Confidence":"HIGH",
                "Missingness_Codes":"GESTURE_FORM_NOT_RELEASED;GOAL_LABEL_ANONYMIZED",
                "Provenance_Record_ID":"PRV-D20-E1","Split":"LOCKED_CROSS_COMMUNITY_EVALUATION",
                "Split_Eligibility":"PROSPECTIVE_SECONDARY_CROSS_COMMUNITY_EVAL_NOT_FULLY_BLIND",
                "Initial_Sender_Age":"NA","Initial_Recipient_Age":"19",
                "Sender_Alternation_Count":"0","Initial_Goal_Anon":"Goal_1","CV_Fold_v0_1":"LOCKED_WAIBIRA",
            }
        ]),
        (d20["spreadsheet_id"], d20["provenance_range"]): _table([
            {
                "Provenance_Record_ID":"PRV-D0020-CSV","Object":"anon csv",
                "Type":"public source data","Persistent_ID_or_URL":"https://example.invalid/d20",
                "Version_or_Branch":"commit","Content_ID":"blob20","Rights":"NOT_STATED",
                "Retrieved_Date":"2026-09-29","Transformation":"row-preserving",
                "Raw_vs_Derived":"source data","Stored_Bytes":"no","Notes":"test",
            }
        ]),
    }


def _fake_payloads(manifest):
    docs = manifest["documents"]
    documents = {
        docs["species"]["document_id"]: _doc(
            docs["species"],
            [
                "Activation status","ACTIVE - first pilot.","Focal taxon: Pan troglodytes.",
                "Primary population anchors currently represented: Sonso/Budongo and Taï.",
            ],
            tabbed=True,
        ),
        docs["run001"]["document_id"]: _doc(
            docs["run001"],
            ["Run_ID: RUN-PT-RQ0001-001","Dataset: D0018","Status: DEVELOPMENT_ONLY_PASS_MIXED_SIGNAL"],
        ),
        docs["run002"]["document_id"]: _doc(
            docs["run002"],
            ["Run_ID: RUN-PT-RQ0001-002","Dataset: D0018","Status: LOCKED_INTERNAL_EVALUATION_COMPLETE_NOT_CONFIRMATORY"],
        ),
        docs["run003"]["document_id"]: _doc(
            docs["run003"],
            [
                "Run_ID: RUN-PT-RQ0001-003","Dataset: D0020",
                "Status: DEVELOPMENT_SEQUENCE_CRITERION_NOT_MET",
                "B0 = 0.455698","B1 = 0.460562","B1 − B0 = +0.004864",
                "Scientific disposition","Preregistered development criterion 1 is NOT MET.",
            ],
        ),
        docs["run004"]["document_id"]: _doc(
            docs["run004"],
            [
                "Run_ID: RUN-PT-RQ0001-004","Dataset: D0020",
                "Status: LOCKED_CROSS_COMMUNITY_EVALUATION_COMPLETE",
                "B0 = 0.445215","B1 = 0.452642","B1 − B0 = +0.007428",
                "Registered disposition: NULL_OR_CONTEXT_SUFFICIENT.",
            ],
        ),
        docs["run005006"]["document_id"]: _doc(
            docs["run005006"],
            [
                "Status","FROZEN_EXECUTION_CONTRACT / EMPIRICAL_RUN_HELD_AT_SECRET_BACKED_MATERIALIZATION.",
                "Current external blocker","Empirical execution remains held.",
            ],
        ),
        docs["harness_verify"]["document_id"]: _doc(
            docs["harness_verify"],
            [
                "Status","OPERATIONALLY_VERIFIED / ZERO_SYNTHETIC / EMPIRICAL_EXECUTION_UNEARNED.",
                "RHF result: 35/35 PASS; biological_evidence=false.",
            ],
        ),
    }
    r = manifest["aceb"]["ranges"]
    ranges = {
        (manifest["aceb"]["spreadsheet_id"], r["research_questions"]): _table([{
            "Question_ID":"RQ0001","Research_Question":"Do combinations improve receiver prediction?",
            "Primary_Outcome_or_Discriminator":"Held-out prediction gain.",
            "Ethics_Welfare_Gate":"Passive/archive first.","Status":"active_exploratory",
        }]),
        (manifest["aceb"]["spreadsheet_id"], r["hypotheses"]): _table([
            {
                "Hypothesis_ID":hid,"Hypothesis_Type":kind,
                "Hypothesis_Statement":hid+" statement","Outcome_Summary":"bounded",
            }
            for hid,kind in (("H0001","primary"),("H0002","alternative"),("H0003","null"))
        ]),
        (manifest["aceb"]["spreadsheet_id"], r["datasets"]): _table([
            {
                "Dataset_ID":did,"Name":did,"Primary_Use":"bounded","Ingestion_Status":status,
                "Rights_or_Restrictions":"bounded rights","License_or_Access":"bounded",
                "Scale":"bounded","Annotation_Grain":"event","Notes":"bounded gate",
            }
            for did,status in (
                ("D0018","COMPLETE"),("D0019","READY_FOR_SECRET_BACKED_MATERIALIZATION"),
                ("D0020","COMPLETE"),("D0025","HELD_SCHEMA"),
            )
        ]),
        (manifest["aceb"]["spreadsheet_id"], r["comparison_gate"]): _table([
            {"Criterion_ID":"CRG-C","Current_Status":"NOT_PASS","Current_Evidence":"empirical held"},
            {"Criterion_ID":"CRG-D","Current_Status":"PARTIAL","Current_Evidence":"partial"},
            {"Criterion_ID":"CRG-OVERALL","Current_Status":"NOT_COMPARISON_READY","Current_Evidence":"CRG-C"},
        ]),
        (manifest["aceb"]["spreadsheet_id"], r["claim_propagation"]): _table([
            {"Disposition":"KNOWN_SIDE_CALIBRATION","Permitted_Core_Interpretation":"known-side only"},
            {"Disposition":"NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT","Permitted_Core_Interpretation":"bounded null"},
            {"Disposition":"EMPIRICAL_EXECUTION_HELD","Permitted_Core_Interpretation":"no empirical disposition"},
        ]),
    }
    ranges.update(_event_ranges(manifest))
    return documents, ranges


class FakeReader:
    def __init__(self, manifest):
        self.manifest = manifest
        self.documents, self.ranges = _fake_payloads(manifest)
        self.aceb_modified_time = manifest["aceb"]["observed_modified_time"]
        self.event_modified_times = {
            did: spec["observed_modified_time"]
            for did, spec in manifest["event_sources"].items()
        }

    def drive_metadata(self, file_id):
        if file_id == self.manifest["aceb"]["spreadsheet_id"]:
            return {
                "id":file_id,"name":self.manifest["aceb"]["title"],
                "mimeType":"application/vnd.google-apps.spreadsheet",
                "modifiedTime":self.aceb_modified_time,
            }
        for dataset_id, spec in self.manifest["event_sources"].items():
            if file_id == spec["spreadsheet_id"]:
                return {
                    "id":file_id,"name":spec["title"],
                    "mimeType":"application/vnd.google-apps.spreadsheet",
                    "modifiedTime":self.event_modified_times[dataset_id],
                }
        raise AssertionError(file_id)

    def document(self, document_id):
        return deepcopy(self.documents[document_id])

    def spreadsheet_values(self, spreadsheet_id, range_name):
        return deepcopy(self.ranges[(spreadsheet_id, range_name)])


def test_extract_google_doc_text_supports_tabs():
    manifest = _small_manifest()
    doc = _doc(manifest["documents"]["species"], ["alpha", "beta"], tabbed=True)
    assert extract_google_doc_text(doc).splitlines() == ["alpha", "beta"]


def test_producer_builds_adapter_valid_bundle_with_events_and_disposition_layers():
    manifest = _small_manifest()
    bundle = WorkspaceCanonicalProducer(FakeReader(manifest), manifest).build_bundle()

    snapshot, status = canonical_bundle_to_snapshot(bundle, source="<memory>")
    assert status["authority_state"] == "CURRENT"
    assert snapshot["question"]["question_id"] == "RQ0001"
    assert len(snapshot["events"]) == 2
    assert {e["dataset_id"] for e in snapshot["events"]} == {"D0018","D0020"}
    assert all("semantic_gloss" not in e for e in snapshot["events"])
    assert all(d["semantic_authority"] == "NONE" for d in snapshot["datasets"])

    run004 = next(r for r in snapshot["runs"] if r["run_id"] == "RUN-PT-RQ0001-004")
    assert run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    assert run004["claim_propagation_disposition"] == "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
    assert run004["metrics"]["delta_log_loss"] == pytest.approx(0.007428)

    held = [r for r in snapshot["runs"] if r["dataset_id"] == "D0019"]
    assert all(r["state"] == "EMPIRICAL_EXECUTION_HELD" and r["disposition"] is None for r in held)


def test_aceb_modified_time_drift_fails_closed():
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    reader.aceb_modified_time = "2099-01-01T00:00:00.000Z"
    with pytest.raises(CanonicalProducerError, match="ACEB modified time drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


def test_event_source_modified_time_drift_fails_closed():
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    reader.event_modified_times["D0020"] = "2099-01-01T00:00:00.000Z"
    with pytest.raises(EventProjectionError, match="D0020 event authority modified-time drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


def test_document_revision_drift_fails_closed():
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    species_id = manifest["documents"]["species"]["document_id"]
    reader.documents[species_id]["revisionId"] = "DRIFTED"
    with pytest.raises(CanonicalProducerError, match="species authority revision drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()
