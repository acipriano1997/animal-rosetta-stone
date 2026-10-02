from __future__ import annotations

from copy import deepcopy

import pytest

from ars_workbench.canonical import canonical_bundle_to_snapshot
from ars_workbench.producer import (
    CanonicalProducerError,
    WorkspaceCanonicalProducer,
    extract_google_doc_text,
    load_source_manifest,
)


def _doc(spec, lines, *, tabbed=False):
    content = [
        {
            "paragraph": {
                "elements": [{"textRun": {"content": line + "\n"}}]
            }
        }
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


def _fake_payloads(manifest):
    docs = manifest["documents"]
    document_payloads = {
        docs["species"]["document_id"]: _doc(
            docs["species"],
            [
                "Chimpanzee - Species Activation Record v0.1",
                "Activation status",
                "ACTIVE - first pilot.",
                "Focal taxon: Pan troglodytes.",
                "Primary population anchors currently represented: Sonso/Budongo and Taï; later validation.",
            ],
            tabbed=True,
        ),
        docs["run001"]["document_id"]: _doc(
            docs["run001"],
            [
                docs["run001"]["title"],
                "Status",
                "Run_ID: RUN-PT-RQ0001-001",
                "Dataset: D0018 — corpus",
                "Status: DEVELOPMENT_ONLY_PASS_MIXED_SIGNAL",
                "Scientific disposition",
                "Known-side calibration only.",
            ],
        ),
        docs["run002"]["document_id"]: _doc(
            docs["run002"],
            [
                docs["run002"]["title"],
                "Status",
                "Run_ID: RUN-PT-RQ0001-002",
                "Dataset: D0018",
                "Status: LOCKED_INTERNAL_EVALUATION_COMPLETE_NOT_CONFIRMATORY",
                "Scientific disposition",
                "Internal evaluation only.",
            ],
        ),
        docs["run003"]["document_id"]: _doc(
            docs["run003"],
            [
                docs["run003"]["title"],
                "Status",
                "Run_ID: RUN-PT-RQ0001-003",
                "Dataset: D0020 — corpus",
                "Status: DEVELOPMENT_SEQUENCE_CRITERION_NOT_MET",
                "Development result",
                "B0 = 0.455698",
                "B1 = 0.460562",
                "B1 − B0 = +0.004864",
                "Scientific disposition",
                "Preregistered development criterion 1 is NOT MET.",
            ],
        ),
        docs["run004"]["document_id"]: _doc(
            docs["run004"],
            [
                docs["run004"]["title"],
                "Status",
                "Run_ID: RUN-PT-RQ0001-004",
                "Dataset: D0020 — corpus",
                "Status: LOCKED_CROSS_COMMUNITY_EVALUATION_COMPLETE",
                "Locked result",
                "B0 = 0.445215",
                "B1 = 0.452642",
                "B1 − B0 = +0.007428",
                "Preregistered decision",
                "Registered disposition: NULL_OR_CONTEXT_SUFFICIENT.",
            ],
        ),
        docs["run005006"]["document_id"]: _doc(
            docs["run005006"],
            [
                docs["run005006"]["title"],
                "Status",
                "FROZEN_EXECUTION_CONTRACT / EMPIRICAL_RUN_HELD_AT_SECRET_BACKED_MATERIALIZATION.",
                "RUN-005 — development",
                "Frozen development path.",
                "RUN-006 — one-time locked evaluation",
                "Frozen locked transfer path.",
                "Current external blocker",
                "Securely provision one persistent HMAC key; empirical RUN-005/RUN-006 remain NOT_RUN.",
            ],
        ),
        docs["harness_verify"]["document_id"]: _doc(
            docs["harness_verify"],
            [
                docs["harness_verify"]["title"],
                "Status",
                "OPERATIONALLY_VERIFIED / ZERO_SYNTHETIC / EMPIRICAL_EXECUTION_UNEARNED.",
                "RHF result: 35/35 PASS. Synthetic results are biological_evidence=false.",
            ],
        ),
    }

    q_rows = _table(
        [
            {
                "Question_ID": "RQ0001",
                "Research_Question": "Do combinations improve receiver prediction?",
                "Primary_Outcome_or_Discriminator": "Held-out prediction gain.",
                "Ethics_Welfare_Gate": "Passive/archive first.",
                "Status": "active_exploratory",
            }
        ]
    )
    h_rows = _table(
        [
            {
                "Hypothesis_ID": hid,
                "Question_ID": "RQ0001",
                "Hypothesis_Type": kind,
                "Hypothesis_Statement": statement,
                "Outcome_Summary": summary,
            }
            for hid, kind, statement, summary in (
                ("H0001", "primary", "Combination adds information.", "Bounded."),
                ("H0002", "alternative", "Context explains effect.", "Bounded."),
                ("H0003", "null", "Components suffice.", "Bounded."),
            )
        ]
    )
    d_rows = _table(
        [
            {
                "Dataset_ID": did,
                "Name": f"Dataset {did}",
                "Primary_Use": f"Primary use {did}",
                "Ingestion_Status": status,
                "Rights_or_Restrictions": "ATTRIBUTION_REQUIRED",
                "License_or_Access": "CC BY 4.0",
                "Scale": "bounded",
                "Annotation_Grain": "event",
                "Notes": f"Gate note {did}",
            }
            for did, status in (
                ("D0018", "KNOWN_SIDE_COMPLETE"),
                ("D0019", "RDC004_PREMODEL_GATES_PASS_READY_FOR_SECRET_BACKED_MATERIALIZATION"),
                ("D0020", "SEQUENCE_ARM_COMPLETE"),
                ("D0025", "HELD_SCHEMA"),
            )
        ]
    )
    gate_rows = _table(
        [
            {
                "Criterion_ID": "CRG-C",
                "Current_Status": "NOT_PASS",
                "Current_Evidence": "Receiver empirical run not yet executed.",
            },
            {
                "Criterion_ID": "CRG-D",
                "Current_Status": "PARTIAL",
                "Current_Evidence": "Independent source incomplete.",
            },
            {
                "Criterion_ID": "CRG-OVERALL",
                "Current_Status": "NOT_COMPARISON_READY",
                "Current_Evidence": "CRG-C controls.",
            },
        ]
    )
    propagation_rows = _table(
        [
            {
                "Disposition": "KNOWN_SIDE_CALIBRATION",
                "Permitted_Core_Interpretation": "Pipeline may recover or fail to recover bounded known-side effect.",
            },
            {
                "Disposition": "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT",
                "Permitted_Core_Interpretation": "Under the registered representation, added terms do not improve the primary criterion.",
            },
            {
                "Disposition": "EMPIRICAL_EXECUTION_HELD",
                "Permitted_Core_Interpretation": "No empirical disposition exists yet.",
            },
        ]
    )
    range_payloads = {
        manifest["aceb"]["ranges"]["research_questions"]: q_rows,
        manifest["aceb"]["ranges"]["hypotheses"]: h_rows,
        manifest["aceb"]["ranges"]["datasets"]: d_rows,
        manifest["aceb"]["ranges"]["comparison_gate"]: gate_rows,
        manifest["aceb"]["ranges"]["claim_propagation"]: propagation_rows,
    }
    return document_payloads, range_payloads


class FakeReader:
    def __init__(self, manifest):
        self.manifest = manifest
        self.documents, self.ranges = _fake_payloads(manifest)
        self.modified_time = manifest["aceb"]["observed_modified_time"]

    def drive_metadata(self, file_id):
        return {
            "id": file_id,
            "name": self.manifest["aceb"]["title"],
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "modifiedTime": self.modified_time,
        }

    def document(self, document_id):
        return deepcopy(self.documents[document_id])

    def spreadsheet_values(self, spreadsheet_id, range_name):
        assert spreadsheet_id == self.manifest["aceb"]["spreadsheet_id"]
        return deepcopy(self.ranges[range_name])


def test_extract_google_doc_text_supports_tabs():
    manifest = load_source_manifest()
    doc = _doc(manifest["documents"]["species"], ["alpha", "beta"], tabbed=True)
    assert extract_google_doc_text(doc).splitlines() == ["alpha", "beta"]


def test_producer_builds_adapter_valid_bundle_and_preserves_disposition_layers():
    manifest = load_source_manifest()
    producer = WorkspaceCanonicalProducer(FakeReader(manifest), manifest)
    bundle = producer.build_bundle()

    snapshot, status = canonical_bundle_to_snapshot(bundle, source="<memory>")
    assert status["authority_state"] == "CURRENT"
    assert snapshot["question"]["question_id"] == "RQ0001"
    assert {x["hypothesis_id"] for x in snapshot["hypotheses"]} == {
        "H0001",
        "H0002",
        "H0003",
    }
    assert all(d["semantic_authority"] == "NONE" for d in snapshot["datasets"])

    run004 = next(r for r in snapshot["runs"] if r["run_id"] == "RUN-PT-RQ0001-004")
    assert run004["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    assert (
        run004["claim_propagation_disposition"]
        == "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
    )
    assert run004["metrics"]["delta_log_loss"] == pytest.approx(0.007428)

    held = [r for r in snapshot["runs"] if r["dataset_id"] == "D0019"]
    assert {r["run_id"] for r in held} == {
        "RUN-PT-RQ0001-005",
        "RUN-PT-RQ0001-006",
    }
    assert all(r["state"] == "EMPIRICAL_EXECUTION_HELD" for r in held)
    assert all(r["disposition"] is None for r in held)


def test_aceb_modified_time_drift_fails_closed():
    manifest = load_source_manifest()
    reader = FakeReader(manifest)
    reader.modified_time = "2099-01-01T00:00:00.000Z"
    with pytest.raises(CanonicalProducerError, match="ACEB modified time drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


def test_document_revision_drift_fails_closed():
    manifest = load_source_manifest()
    reader = FakeReader(manifest)
    species_id = manifest["documents"]["species"]["document_id"]
    reader.documents[species_id]["revisionId"] = "DRIFTED"
    with pytest.raises(CanonicalProducerError, match="species authority revision drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()


def test_document_title_drift_fails_closed():
    manifest = load_source_manifest()
    reader = FakeReader(manifest)
    run004_id = manifest["documents"]["run004"]["document_id"]
    reader.documents[run004_id]["title"] = "Wrong authority"
    with pytest.raises(CanonicalProducerError, match="run004 authority title drift"):
        WorkspaceCanonicalProducer(reader, manifest).build_bundle()
