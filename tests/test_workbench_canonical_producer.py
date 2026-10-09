from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

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
    base = {"title": spec["title"], "documentId": spec["document_id"], "revisionId": "transient-test-token"}
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
    manifest = deepcopy(load_source_manifest())
    manifest["event_sources"]["D0018"]["expected_event_count"] = 1
    manifest["event_sources"]["D0020"]["expected_event_count"] = 1
    return manifest


def _claim(claim_id, *, study_id, status="bounded", claim_type="bounded_claim"):
    return {
        "Claim_ID": claim_id,
        "Claim_Short": f"{claim_id} bounded claim",
        "Species": "Pan troglodytes",
        "Scope_Boundary": "bounded source/population",
        "Status": status,
        "Claim_Type": claim_type,
        "Evidence_Channels": "bounded evidence channel",
        "Behavioral_Validation": "bounded receiver evidence",
        "Independent_Replication": "not established",
        "ARS_Confidence": "bounded confidence",
        "Confidence_Rationale": "source-scoped rationale",
        "Do_Not_Overclaim": "No semantic or species-wide promotion.",
        "Population_Boundary": "bounded population",
        "Method_Boundary": "bounded method",
        "Alternative_Explanations": "context and measurement remain alternatives",
        "Null_Evidence_IDs": "",
        "Source_Study_IDs": study_id,
        "Reproducibility_Status": "bounded reproducibility state",
    }


def _link(link_id, claim_id, *, study_id, dataset_id=""):
    return {
        "Link_ID": link_id,
        "Claim_ID": claim_id,
        "Evidence_Direction": "supports",
        "Experiment_ID": "E-TEST",
        "Study_ID": study_id,
        "Dataset_ID": dataset_id,
        "Evidence_Channel": "bounded channel",
        "Population_Scope": "bounded population",
        "Method_Scope": "bounded method",
        "Independence_Level": "bounded independence",
        "Replication_Relation": "bounded relation",
        "Correction_State": "current",
        "Weight_or_Confidence_Basis": "bounded basis",
        "Alternative_Explanation_Addressed": "does not establish semantics",
        "Source_Provenance_Verified": "yes",
        "Notes": "",
    }


def _fake_payloads(manifest):
    docs = manifest["documents"]
    documents = {
        docs["species"]["document_id"]: _doc(
            docs["species"],
            [
                "Activation status",
                "ACTIVE - first pilot.",
                "Focal taxon: Pan troglodytes.",
                "Primary population anchors currently represented: Sonso/Budongo and Taï.",
            ],
            tabbed=True,
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

    aceb_id = manifest["aceb"]["spreadsheet_id"]
    r = manifest["aceb"]["ranges"]
    ranges = {
        (aceb_id, r["research_questions"]): _table([{
            "Question_ID": "RQ0001",
            "Research_Question": "Do combinations improve receiver prediction?",
            "Primary_Outcome_or_Discriminator": "Held-out prediction gain.",
            "Ethics_Welfare_Gate": "Passive/archive first.",
            "Status": "active_exploratory",
        }]),
        (aceb_id, r["hypotheses"]): _table([
            {
                "Hypothesis_ID": hid,
                "Hypothesis_Type": kind,
                "Hypothesis_Statement": hid + " statement",
                "Outcome_Summary": "bounded",
            }
            for hid, kind in (
                ("H0001", "primary"),
                ("H0002", "alternative"),
                ("H0003", "null"),
            )
        ]),
        (aceb_id, r["datasets"]): _table([
            {
                "Dataset_ID": did,
                "Name": did,
                "Primary_Use": "bounded",
                "Ingestion_Status": status,
                "Rights_or_Restrictions": rights,
                "License_or_Access": "bounded",
                "Scale": "bounded",
                "Annotation_Grain": "event",
                "Notes": "bounded gate",
            }
            for did, status, rights in (
                ("D0018", "COMPLETE", "D0018 bounded rights"),
                ("D0019", "READY_FOR_SECRET_BACKED_MATERIALIZATION", "D0019 bounded rights"),
                ("D0020", "COMPLETE", "D0020 bounded rights"),
                ("D0025", "HELD_SCHEMA", "D0025 bounded rights"),
            )
        ]),
        (aceb_id, r["comparison_gate"]): _table([
            *[
                {"Criterion_ID": f"CRG-{letter}", "Current_Status": "PASS", "Current_Evidence": "bounded"}
                for letter in "ABEFGHI"
            ],
            {"Criterion_ID": "CRG-C", "Current_Status": "NOT_PASS", "Current_Evidence": "empirical held"},
            {"Criterion_ID": "CRG-D", "Current_Status": "PARTIAL", "Current_Evidence": "partial"},
            {"Criterion_ID": "CRG-OVERALL", "Current_Status": "NOT_COMPARISON_READY", "Current_Evidence": "CRG-C"},
            {"Criterion_ID": "BONOBO-ACT", "Current_Status": "DEFERRED", "Current_Evidence": "gate held"},
        ]),
        (aceb_id, r["claim_propagation"]): _table([
            {"Disposition": "KNOWN_SIDE_CALIBRATION", "Permitted_Core_Interpretation": "known-side only"},
            {"Disposition": "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT", "Permitted_Core_Interpretation": "bounded null"},
            {"Disposition": "EMPIRICAL_EXECUTION_HELD", "Permitted_Core_Interpretation": "no empirical disposition"},
        ]),
        (aceb_id, r["claims"]): _table([
            _claim("C0062", study_id="S0057"),
            _claim("C0083", study_id="S0083", status="receiver_support"),
            _claim("C0084", study_id="S0084; S0085", status="receiver_support"),
            _claim("C0085", study_id="S0085", status="methodological_challenge"),
            _claim("C0086", study_id="S0018", status="registered_null"),
        ]),
        (aceb_id, r["claim_evidence_links"]): _table([
            _link("L0057", "C0062", study_id="S0057"),
            _link("L0078", "C0086", study_id="S0018", dataset_id="D0020"),
        ]),
        (aceb_id, r["contradictions"]): _table([{
            "Record_ID": "CC-OTHER",
            "Target_Study_or_Claim": "UNRELATED",
            "Type": "unrelated",
            "Date_or_Year": "2026",
            "What_Changed": "",
            "Effect_on_Conclusion": "",
            "ARS_Action": "",
            "Source_or_Link": "",
            "Status": "current",
        }]),
        (aceb_id, r["disagreements"]): _table([{
            "Disagreement_ID": "DG-OTHER",
            "Research_Question_ID": "RQ-OTHER",
            "Claim_or_Hypothesis_ID": "C-OTHER",
            "Run_IDs": "",
            "Disagreement_Dimension": "unrelated",
            "Position_A": "",
            "Position_B": "",
            "Other_Positions": "",
            "Common_Ground": "",
            "Key_Assumption_Difference": "",
            "Evidence_Needed": "",
            "Empirical_Discriminator": "",
            "Priority": "low",
            "Status": "open",
            "Resolution_or_Current_State": "",
        }]),
    }

    d18 = manifest["event_sources"]["D0018"]
    d20 = manifest["event_sources"]["D0020"]
    ranges[(d18["spreadsheet_id"], d18["event_range"])] = _table([{
        "Event_ID": "EVT-D18-1",
        "Dataset_ID": "D0018",
        "Taxon_ID": "SP001",
        "Population_or_Group_ID": "Sonso/Budongo",
        "Source_Study_ID": "S0017",
        "Source_Experiment_ID": "E0019",
        "Event_Type": "controlled_elicitation",
        "Source_File": "Source-data-snake.csv",
        "Source_Blob_SHA": "blob18",
        "Source_Row": "2",
        "Sender_IDs": "S0017:RE",
        "Receiver_IDs": "UNKNOWN_AGGREGATE_AUDIENCE",
        "Context_ID": "CTX18",
        "Source_Condition": "back",
        "Trigger_or_Anchor": "model-snake",
        "Signal_Component_1": "alarm-huu",
        "Signal_Component_2": "waa-bark",
        "Signal_Order": "alarm-huu→waa-bark",
        "Combination_Flag": "yes",
        "Receiver_Response": "recruited=8",
        "Consequence_or_Outcome": "count=8",
        "Sender_Followup_Repair_Cessation": "NOT_RECORDED",
        "Observation_Window": "120 s",
        "Event_Confidence": "HIGH",
        "Missingness_Codes": "FOLLOWUP_NOT_RECORDED",
        "Provenance_Record_ID": "PRV-D18-E1",
        "Split": "DEVELOPMENT",
        "Split_Eligibility": "DEVELOPMENT_ONLY",
        "Notes": "bounded",
    }])
    ranges[(d18["spreadsheet_id"], d18["provenance_range"])] = _table([{
        "Provenance_Record_ID": "PRV-D0018-SNAKE-SOURCE",
        "Object": "snake csv",
        "Type": "public source data",
        "Persistent_ID_or_URL": "https://example.invalid/d18",
        "Version_or_Branch": "Data",
        "Content_ID": "blob18",
        "Rights": "bounded",
        "Retrieved_Date": "2026-09-29",
        "Transformation": "row-preserving",
        "Raw_vs_Derived": "source data",
        "Stored_Bytes": "no",
        "Notes": "test",
    }])
    ranges[(d18["spreadsheet_id"], d18["missingness_range"])] = _table([{
        "Issue": "Raw media",
        "Scope": "all events",
        "Status": "NOT_INGESTED",
        "Scientific_Consequence": "Cannot independently recode media.",
        "Required_Action": "No semantic promotion from row data alone.",
    }])

    ranges[(d20["spreadsheet_id"], d20["event_range"])] = _table([{
        "Event_ID": "EVT-D20-1",
        "Dataset_ID": "D0020",
        "Taxon_ID": "SP001",
        "Population_or_Group_ID": "Waibira",
        "Source_Study_ID": "S0018",
        "Source_Experiment_ID": "E0021",
        "Event_Type": "natural_gesture_interaction",
        "Source_Communication_ID": "300390",
        "Source_Row_Min": "2",
        "Source_Row_Max": "2",
        "Source_Row_Count": "1",
        "Relative_Start_s": "2.164",
        "Relative_End_s": "4.043",
        "Initial_Sender_ID": "A_F",
        "Initial_Receiver_ID": "ID_5",
        "Participant_IDs": "A_F;ID_5",
        "Gesture_Token_Count": "1",
        "Exchange_Status": "NO",
        "Declared_Turn_Count": "1",
        "Goal_Sequence": "Goal_1",
        "Final_Outcome_Label": "GoalRecipient",
        "Final_Outcome_Time_s": "4.043",
        "Continuation_Structure": "single",
        "Event_Confidence": "HIGH",
        "Missingness_Codes": "GESTURE_FORM_NOT_RELEASED;GOAL_LABEL_ANONYMIZED",
        "Provenance_Record_ID": "PRV-D20-E1",
        "Split": "LOCKED_CROSS_COMMUNITY_EVALUATION",
        "Split_Eligibility": "PROSPECTIVE_SECONDARY_CROSS_COMMUNITY_EVAL_NOT_FULLY_BLIND",
        "Sender_Alternation_Count": "0",
        "Initial_Goal_Anon": "Goal_1",
    }])
    ranges[(d20["spreadsheet_id"], d20["provenance_range"])] = _table([{
        "Provenance_Record_ID": "PRV-D0020-CSV",
        "Object": "anon csv",
        "Type": "public source data",
        "Persistent_ID_or_URL": "https://example.invalid/d20",
        "Version_or_Branch": "commit",
        "Content_ID": "blob20",
        "Rights": "NOT_STATED",
        "Retrieved_Date": "2026-09-29",
        "Transformation": "row-preserving",
        "Raw_vs_Derived": "source data",
        "Stored_Bytes": "no",
        "Notes": "test",
    }])
    ranges[(d20["spreadsheet_id"], d20["missingness_range"])] = _table([{
        "Issue": "Raw media",
        "Scope": "all events",
        "Status": "NOT_INGESTED",
        "Scientific_Consequence": "Cannot independently recode gestures or outcomes.",
        "Required_Action": "Treat source coding as measurement input; keep provenance.",
    }])

    return documents, ranges


class FakeReader:
    def __init__(self, manifest):
        self.manifest = manifest
        self.documents, self.ranges = _fake_payloads(manifest)
        self.document_metadata = {
            spec["document_id"]: {
                "id": spec["document_id"], "name": spec["title"],
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": spec["observed_modified_time"],
            }
            for spec in manifest["documents"].values()
        }
        self.document_revisions = {
            spec["document_id"]: spec["drive_revision_id"]
            for spec in manifest["documents"].values()
        }
        self.aceb_modified_time = manifest["aceb"]["observed_modified_time"]
        self.event_modified_times = {
            did: spec["observed_modified_time"]
            for did, spec in manifest["event_sources"].items()
        }

    def drive_metadata(self, file_id):
        if file_id in self.document_metadata:
            return deepcopy(self.document_metadata[file_id])
        if file_id == self.manifest["aceb"]["spreadsheet_id"]:
            return {
                "id": file_id,
                "name": self.manifest["aceb"]["title"],
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "modifiedTime": self.aceb_modified_time,
            }
        for dataset_id, spec in self.manifest["event_sources"].items():
            if file_id == spec["spreadsheet_id"]:
                return {
                    "id": file_id,
                    "name": spec["title"],
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "modifiedTime": self.event_modified_times[dataset_id],
                }
        raise AssertionError(file_id)

    def document(self, document_id):
        return deepcopy(self.documents[document_id])

    def drive_head_revision(self, document_id):
        return self.document_revisions[document_id]

    def spreadsheet_values(self, spreadsheet_id, range_name):
        return deepcopy(self.ranges[(spreadsheet_id, range_name)])


def test_extract_google_doc_text_supports_tabs():
    manifest = _small_manifest()
    doc = _doc(manifest["documents"]["species"], ["alpha", "beta"], tabbed=True)
    assert extract_google_doc_text(doc).splitlines() == ["alpha", "beta"]


def test_producer_builds_adapter_valid_bundle_with_event_evidence_and_rights_layers():
    manifest = _small_manifest()
    bundle = WorkspaceCanonicalProducer(FakeReader(manifest), manifest).build_bundle()

    snapshot, status = canonical_bundle_to_snapshot(bundle, source="<memory>")
    assert status["authority_state"] == "CURRENT"
    assert snapshot["question"]["question_id"] == "RQ0001"
    assert len(snapshot["events"]) == 2
    assert {e["dataset_id"] for e in snapshot["events"]} == {"D0018", "D0020"}
    assert len(snapshot["evidence_items"]) == 5
    assert {c["claim_id"] for c in snapshot["evidence_items"]} == {
        "C0062", "C0083", "C0084", "C0085", "C0086"
    }
    assert snapshot["evidence_registry_status"]["matching_contradiction_rows"] == 0
    assert snapshot["evidence_registry_status"]["matching_disagreement_rows"] == 0
    assert all(m["preview_allowed"] is False for m in snapshot["media_placeholders"])
    assert all(m["bytes_available"] is False for m in snapshot["media_placeholders"])
    assert all(d["semantic_authority"] == "NONE" for d in snapshot["datasets"])

    run004 = next(r for r in snapshot["runs"] if r["run_id"] == "RUN-PT-RQ0001-004")
    assert run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    assert run004["claim_propagation_disposition"] == "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
    assert run004["metrics"]["delta_log_loss"] == pytest.approx(0.007428)

    held = [r for r in snapshot["runs"] if r["dataset_id"] == "D0019"]
    assert all(
        r["state"] == "EMPIRICAL_EXECUTION_HELD" and r["disposition"] is None
        for r in held
    )
    gate = snapshot["species"]["comparison_readiness"]
    assert gate["CRG-C"] == "NOT_PASS"
    assert gate["controlling_criterion"] == "CRG-C"
    assert gate["controlling_reason"] == "CRG-C: empirical held"
    assert gate["bonobo_activation"] == "DEFERRED"


def _closed_reader(manifest):
    fixture = json.loads((Path(__file__).parent / "fixtures/workbench_d0019_closed_mixed.json").read_text())
    reader = FakeReader(manifest)
    spec = manifest["documents"]["run005006"]
    assert fixture["source_document_id"] == spec["document_id"]
    assert fixture["source_drive_revision_id"] == spec["drive_revision_id"]
    assert fixture["source_observed_modified_time"] == spec["observed_modified_time"]
    reader.documents[spec["document_id"]] = _doc(spec, fixture["execution_lines"], tabbed=True)
    aceb = manifest["aceb"]["spreadsheet_id"]
    ranges = manifest["aceb"]["ranges"]
    table = reader.ranges[(aceb, ranges["datasets"])]
    d0019 = next(row for row in table[1:] if row[table[0].index("Dataset_ID")] == "D0019")
    d0019[table[0].index("Ingestion_Status")] = fixture["dataset_state"]
    reader.ranges[(aceb, ranges["comparison_gate"])] = _table(fixture["comparison_gate"])
    reader.ranges[(aceb, ranges["claim_propagation"])].append(list(fixture["claim_propagation"].values()))
    return reader


def test_producer_projects_current_closed_mixed_with_bounded_claims_and_no_refit():
    manifest = _small_manifest()
    snapshot = WorkspaceCanonicalProducer(_closed_reader(manifest), manifest).build_bundle()["snapshot"]
    runs = {r["run_id"]: r for r in snapshot["runs"]}
    dev, locked = (runs[f"RUN-PT-RQ0001-{suffix}"] for suffix in ("005", "006"))
    for run in (dev, locked):
        assert run["state"] == "CLOSED"
        assert run["disposition"] == "MIXED"
        assert run["disposition_scope"] == "PR0005_FULL_PATH"
        assert run["claim_propagation_disposition"] == "MIXED"
        assert "gate" not in run
        assert "does not establish replicated H0001 support" in run["interpretation_ceiling"]
        for phrase in ("literal signal meaning", "translation", "causal signal effects", "species-wide compositionality"):
            assert phrase in run["interpretation_ceiling"]
        assert "PROV-D0019-EXECUTION-CONTRACT" in run["provenance_ids"]
    assert dev["eligible_rows"] == 104
    assert dev["unordered_dyads"] == 69
    assert dev["metrics"]["delta_log_loss"] == -0.08026925235617471
    assert locked["eligible_rows"] == 68
    assert locked["model_refit"] is False
    assert locked["preprocessing_refit"] is False
    assert locked["metrics"] == {
        "B1_log_loss": 0.6361435247748188,
        "B2_log_loss": 0.6847920995625079,
        "delta_log_loss": 0.048648574787689025,
    }
    gate = snapshot["species"]["comparison_readiness"]
    assert gate["CRG-A"] == gate["CRG-B"] == gate["CRG-C"] == "PASS"
    assert gate["CRG-D"] == "PARTIAL"
    assert gate["controlling_criterion"] == "CRG-D"
    assert gate["controlling_reason"].startswith("CRG-D:")
    assert gate["overall"] == "NOT_COMPARISON_READY"
    assert gate["bonobo_activation"] == "DEFERRED"
    assert all(not v["biological_evidence"] for v in snapshot["software_verification"])
    assert all(d["semantic_authority"] == "NONE" for d in snapshot["datasets"])


@pytest.mark.parametrize("old,new", [
    ("EMPIRICAL_RUNS_CLOSED_MIXED", "EMPIRICAL_RUNS_CLOSED_UNKNOWN"),
    ("Empirical closure", "Synthetic preflight"),
    ("No model or preprocessing refit occurred on Group 1.", "Model refit occurred on Group 1."),
    ("The registered final PR0005 disposition is MIXED.", "The registered final PR0005 disposition is BOUNDED_H0001_SUPPORT."),
    ("+0.048648574787689025", "-0.048648574787689025"),
    ("0.6361435247748188", "0.1"),
    ("69 unordered dyads", "105 unordered dyads"),
    ("it does not establish replicated H0001 support", "it establishes replicated H0001 support"),
])
def test_incomplete_or_conflicted_closure_fails_closed(old, new):
    manifest = _small_manifest()
    reader = _closed_reader(manifest)
    spec = manifest["documents"]["run005006"]
    text = extract_google_doc_text(reader.documents[spec["document_id"]])
    assert old in text
    reader.documents[spec["document_id"]] = _doc(spec, text.replace(old, new).splitlines())
    with pytest.raises(CanonicalProducerError):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


@pytest.mark.parametrize("closed", [False, True])
def test_d0019_dataset_contract_disagreement_fails_closed(closed):
    manifest = _small_manifest()
    reader = _closed_reader(manifest) if closed else FakeReader(manifest)
    table = reader.ranges[(manifest["aceb"]["spreadsheet_id"], manifest["aceb"]["ranges"]["datasets"])]
    row = next(row for row in table[1:] if row[0] == "D0019")
    row[table[0].index("Ingestion_Status")] = (
        "READY_FOR_SECRET_BACKED_MATERIALIZATION" if closed else "D0019_PR0005_EMPIRICAL_CLOSED_MIXED"
    )
    with pytest.raises(CanonicalProducerError, match="dataset/contract state disagreement"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


def test_mixed_claim_propagation_cannot_be_omitted():
    manifest = _small_manifest()
    reader = _closed_reader(manifest)
    table = reader.ranges[(manifest["aceb"]["spreadsheet_id"], manifest["aceb"]["ranges"]["claim_propagation"])]
    table[:] = [row for row in table if row[0] != "MIXED"]
    with pytest.raises(CanonicalProducerError, match="disposition missing: MIXED"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


@pytest.mark.parametrize("criterion,status,controlling", [
    ("CRG-A", "NOT_PASS", "CRG-A"),
    ("CRG-C", "NOT_PASS", "CRG-C"),
    ("CRG-D", "PASS", "CRG-E"),
])
def test_controlling_criterion_tracks_authority_not_a_hard_coded_gate(criterion, status, controlling):
    manifest = _small_manifest()
    reader = _closed_reader(manifest)
    table = reader.ranges[(manifest["aceb"]["spreadsheet_id"], manifest["aceb"]["ranges"]["comparison_gate"])]
    next(row for row in table[1:] if row[0] == criterion)[1] = status
    gate = WorkspaceCanonicalProducer(reader, manifest).build_bundle()["snapshot"]["species"]["comparison_readiness"]
    assert gate["controlling_criterion"] == controlling
    assert gate["controlling_reason"].startswith(controlling + ":")


@pytest.mark.parametrize("criterion,status", [
    ("CRG-OVERALL", "COMPARISON_READY_BOUNDED"),
    ("BONOBO-ACT", "ACTIVE_COMPARATOR"),
])
def test_gate_cannot_promote_overall_or_bonobo_with_unmet_criteria(criterion, status):
    manifest = _small_manifest()
    reader = _closed_reader(manifest)
    table = reader.ranges[(manifest["aceb"]["spreadsheet_id"], manifest["aceb"]["ranges"]["comparison_gate"])]
    next(row for row in table[1:] if row[0] == criterion)[1] = status
    with pytest.raises(CanonicalProducerError, match="fail closed"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


@pytest.mark.parametrize("key", list(load_source_manifest()["documents"]))
def test_changed_ephemeral_docs_token_with_same_durable_state_passes(key):
    manifest = _small_manifest()
    reader = _closed_reader(manifest)
    producer = WorkspaceCanonicalProducer(reader, manifest)
    before = producer.build_bundle()["snapshot"]
    spec = manifest["documents"][key]
    reader.documents[spec["document_id"]]["revisionId"] = "different-format-next-day-user-token"
    after = producer.build_bundle()["snapshot"]
    # Only the capture timestamp can differ; no ephemeral token enters authority.
    before.pop("captured_date", None)
    after.pop("captured_date", None)
    assert before == after
    assert "different-format-next-day-user-token" not in json.dumps(after)


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


@pytest.mark.parametrize("key", list(load_source_manifest()["documents"]))
def test_drive_revision_drift_fails_closed(key):
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    reader.document_revisions[manifest["documents"][key]["document_id"]] = "changed-drive-revision"
    with pytest.raises(CanonicalProducerError, match=f"{key} authority Drive revision drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


@pytest.mark.parametrize("field,value,message", [
    ("modifiedTime", "2099-01-01T00:00:00.000Z", "modified-time drift"),
    ("id", "wrong-document-id", "file identity drift"),
    ("name", "Wrong authority", "Drive title drift"),
    ("mimeType", "application/pdf", "not a native Google Doc"),
])
def test_invalid_drive_authority_fails_closed(field, value, message):
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    sid = manifest["documents"]["species"]["document_id"]
    reader.document_metadata[sid][field] = value
    with pytest.raises(CanonicalProducerError, match=message):
        WorkspaceCanonicalProducer(reader, manifest)._read_pinned_document("species")


@pytest.mark.parametrize("field,value,message", [
    ("documentId", "wrong-document-id", "document identity drift"),
    ("title", "Wrong authority", "authority title drift"),
    ("body", {}, "content is empty"),
])
def test_invalid_docs_response_fails_closed(field, value, message):
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    sid = manifest["documents"]["species"]["document_id"]
    reader.documents[sid][field] = value
    reader.documents[sid].pop("tabs", None)
    with pytest.raises(CanonicalProducerError, match=message):
        WorkspaceCanonicalProducer(reader, manifest)._read_pinned_document("species")


@pytest.mark.parametrize("change", ["modified_time", "drive_revision"])
def test_document_change_during_bounded_read_fails_closed(change):
    manifest = _small_manifest()
    class EditingReader(FakeReader):
        def document(self, document_id):
            content = super().document(document_id)
            if change == "modified_time":
                self.document_metadata[document_id]["modifiedTime"] = "2099-01-01T00:00:00.000Z"
            else:
                self.document_revisions[document_id] = "changed-during-extraction"
            return content
    with pytest.raises(CanonicalProducerError, match="authority Drive .*drift"):
        WorkspaceCanonicalProducer(EditingReader(manifest), manifest)._read_pinned_document("species")


@pytest.mark.parametrize("legacy", ["version", "field", "missing_durable_pin"])
def test_legacy_transient_authority_manifest_is_not_silently_reinterpreted(legacy):
    manifest = _small_manifest()
    reader = FakeReader(manifest)
    if legacy == "version":
        manifest["manifest_id"] = "WORKBENCH-CANONICAL-SOURCES-v0.1"
    elif legacy == "field":
        manifest["documents"]["species"]["revision_id"] = "legacy-docs-token"
    else:
        del manifest["documents"]["species"]["drive_revision_id"]
    with pytest.raises(CanonicalProducerError, match="manifest|durable Drive"):
        WorkspaceCanonicalProducer(reader, manifest)
