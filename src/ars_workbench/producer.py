from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from importlib.resources import files
from typing import Any

from .canonical import CANONICAL_READ_CONTRACT, canonical_bundle_to_snapshot


class CanonicalProducerError(RuntimeError):
    """Raised when pinned semantic authorities cannot be projected safely."""


def load_source_manifest() -> dict[str, Any]:
    path = files("ars_workbench").joinpath("data/workbench_canonical_sources.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _content_text(content: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for item in content:
        paragraph = item.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        for element in paragraph.get("elements", []):
            run = element.get("textRun")
            if isinstance(run, dict):
                out.append(str(run.get("content", "")))
    return "".join(out)


def extract_google_doc_text(document: dict[str, Any]) -> str:
    chunks: list[str] = []
    body = document.get("body")
    if isinstance(body, dict):
        chunks.append(_content_text(body.get("content", [])))

    for tab in document.get("tabs", []) or []:
        if not isinstance(tab, dict):
            continue
        document_tab = tab.get("documentTab")
        if isinstance(document_tab, dict):
            tab_body = document_tab.get("body")
            if isinstance(tab_body, dict):
                chunks.append(_content_text(tab_body.get("content", [])))
        elif isinstance(tab.get("body"), dict):
            chunks.append(_content_text(tab["body"].get("content", [])))

    return "\n".join(chunk for chunk in chunks if chunk)


def _lines(document: dict[str, Any]) -> list[str]:
    return [line.strip() for line in extract_google_doc_text(document).splitlines() if line.strip()]


def _label(lines: list[str], label: str) -> str:
    prefix = label + ":"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip().rstrip(".")
    raise CanonicalProducerError(f"required document label missing: {label}")


def _after_heading(lines: list[str], heading: str) -> str:
    try:
        index = lines.index(heading)
    except ValueError as exc:
        raise CanonicalProducerError(f"required document heading missing: {heading}") from exc
    if index + 1 >= len(lines):
        raise CanonicalProducerError(f"heading has no content: {heading}")
    return lines[index + 1]


def _line_starting(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line
    raise CanonicalProducerError(f"required document line missing: {prefix}")


def _rows(values: list[list[Any]]) -> list[dict[str, str]]:
    if not values:
        raise CanonicalProducerError("canonical spreadsheet range is empty")
    headers = [str(x).strip() for x in values[0]]
    if not headers or any(not h for h in headers):
        raise CanonicalProducerError("canonical spreadsheet header is invalid")
    out: list[dict[str, str]] = []
    for row in values[1:]:
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        out.append({h: str(padded[i]).strip() for i, h in enumerate(headers)})
    return out


def _one(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise CanonicalProducerError(
            f"expected exactly one {key}={value!r} row, found {len(matches)}"
        )
    return matches[0]


def _doc_dataset_id(lines: list[str]) -> str:
    value = _label(lines, "Dataset")
    return re.split(r"\s+[—-]\s+", value, maxsplit=1)[0].strip()


def _metric_triplet(lines: list[str]) -> dict[str, float]:
    text = "\n".join(lines)
    b0 = re.search(r"(?m)^B0\s*=\s*([0-9.]+)", text)
    b1 = re.search(r"(?m)^B1\s*=\s*([0-9.]+)", text)
    delta = re.search(r"B1\s*[−–-]\s*B0\s*=\s*\+?([0-9.]+)", text)
    if not (b0 and b1 and delta):
        raise CanonicalProducerError("registered B0/B1/delta metrics are missing")
    return {
        "B0_log_loss": float(b0.group(1)),
        "B1_log_loss": float(b1.group(1)),
        "delta_log_loss": float(delta.group(1)),
    }


class WorkspaceCanonicalProducer:
    """Build the Workbench read bundle from pinned Drive/ACEB authorities."""

    def __init__(self, reader: Any, manifest: dict[str, Any] | None = None) -> None:
        self.reader = reader
        self.manifest = deepcopy(manifest or load_source_manifest())

    def _read_pinned_document(self, key: str) -> dict[str, Any]:
        spec = self.manifest["documents"][key]
        document = self.reader.document(spec["document_id"])
        if document.get("title") != spec["title"]:
            raise CanonicalProducerError(
                f"{key} authority title drift: expected {spec['title']!r}, got {document.get('title')!r}"
            )
        if document.get("revisionId") != spec["revision_id"]:
            raise CanonicalProducerError(
                f"{key} authority revision drift; reconcile semantic authority before export"
            )
        return document

    def _aceb_rows(self) -> dict[str, list[dict[str, str]]]:
        spec = self.manifest["aceb"]
        metadata = self.reader.drive_metadata(spec["spreadsheet_id"])
        if metadata.get("name") != spec["title"]:
            raise CanonicalProducerError("ACEB title drift; fail closed")
        if metadata.get("modifiedTime") != spec["observed_modified_time"]:
            raise CanonicalProducerError(
                "ACEB modified time drift; reconcile semantic authority before export"
            )
        return {
            key: _rows(
                self.reader.spreadsheet_values(
                    spec["spreadsheet_id"], range_name
                )
            )
            for key, range_name in spec["ranges"].items()
        }

    def build_bundle(self) -> dict[str, Any]:
        aceb = self._aceb_rows()
        docs = {
            key: self._read_pinned_document(key)
            for key in self.manifest["documents"]
        }
        lines = {key: _lines(doc) for key, doc in docs.items()}

        selection = self.manifest["selection"]
        q = _one(aceb["research_questions"], "Question_ID", selection["question_id"])
        hypotheses = [
            _one(aceb["hypotheses"], "Hypothesis_ID", hypothesis_id)
            for hypothesis_id in selection["hypothesis_ids"]
        ]
        datasets = [
            _one(aceb["datasets"], "Dataset_ID", dataset_id)
            for dataset_id in selection["dataset_ids"]
        ]
        crg_c = _one(aceb["comparison_gate"], "Criterion_ID", "CRG-C")
        crg_d = _one(aceb["comparison_gate"], "Criterion_ID", "CRG-D")
        crg_overall = _one(aceb["comparison_gate"], "Criterion_ID", "CRG-OVERALL")
        propagation = {
            row["Disposition"]: row
            for row in aceb["claim_propagation"]
            if row.get("Disposition")
        }
        for required in (
            "KNOWN_SIDE_CALIBRATION",
            "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT",
            "EMPIRICAL_EXECUTION_HELD",
        ):
            if required not in propagation:
                raise CanonicalProducerError(
                    f"claim-propagation disposition missing: {required}"
                )

        species_lines = lines["species"]
        activation = _after_heading(species_lines, "Activation status").split(" ", 1)[0]
        taxon = _label(species_lines, "Focal taxon")
        populations = _label(
            species_lines, "Primary population anchors currently represented"
        )

        harness_lines = lines["harness_verify"]
        harness_status = _after_heading(harness_lines, "Status")
        harness_state = harness_status.split(" / ", 1)[0]
        empirical_harness_state = (
            "UNEARNED" if "EMPIRICAL_EXECUTION_UNEARNED" in harness_status else "UNKNOWN"
        )
        harness_result = _line_starting(harness_lines, "RHF result:")

        provenance: dict[str, dict[str, Any]] = {
            "PROV-SPECIES": {
                "authority": self.manifest["documents"]["species"]["title"],
                "drive_id": self.manifest["documents"]["species"]["document_id"],
                "revision_id": self.manifest["documents"]["species"]["revision_id"],
            },
            "PROV-COMPARISON-GATE": {
                "authority": "ACEB Chimp Comparison Gate",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": "Chimp Comparison Gate:CRG-C,CRG-D,CRG-OVERALL",
            },
            "PROV-RQ0001": {
                "authority": "ACEB Research Questions",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": f"Research Questions:{selection['question_id']}",
            },
            "PROV-CLAIM-PROPAGATION": {
                "authority": "ACEB RQ0001 Claim Propagation",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": "RQ0001 Claim Propagation",
            },
            "PROV-HARNESS-VERIFY": {
                "authority": self.manifest["documents"]["harness_verify"]["title"],
                "drive_id": self.manifest["documents"]["harness_verify"]["document_id"],
                "revision_id": self.manifest["documents"]["harness_verify"]["revision_id"],
                "github_repo": "acipriano1997/animal-rosetta-stone",
            },
        }

        hypothesis_view: list[dict[str, Any]] = []
        for row in hypotheses:
            prov_id = f"PROV-{row['Hypothesis_ID']}"
            provenance[prov_id] = {
                "authority": "ACEB Hypotheses",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": f"Hypotheses:{row['Hypothesis_ID']}",
            }
            hypothesis_view.append(
                {
                    "hypothesis_id": row["Hypothesis_ID"],
                    "type": row["Hypothesis_Type"],
                    "statement": row["Hypothesis_Statement"],
                    "current_scope": row["Outcome_Summary"],
                    "provenance_ids": [prov_id],
                }
            )

        dataset_view: list[dict[str, Any]] = []
        for row in datasets:
            dataset_id = row["Dataset_ID"]
            prov_id = f"PROV-{dataset_id}"
            provenance[prov_id] = {
                "authority": "ACEB Datasets",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": f"Datasets:{dataset_id}",
            }
            status = row["Ingestion_Status"]
            item: dict[str, Any] = {
                "dataset_id": dataset_id,
                "name": row["Name"],
                "role": row["Primary_Use"],
                "availability": status,
                "empirical_state": status,
                "rights_state": row["Rights_or_Restrictions"] or row["License_or_Access"],
                "scope": "; ".join(
                    part for part in (row["Scale"], row["Annotation_Grain"]) if part
                ),
                "semantic_authority": "NONE",
                "provenance_ids": [prov_id],
            }
            if "HELD" in status or "READY" in status:
                item["gate"] = row["Notes"]
            dataset_view.append(item)

        run_view: list[dict[str, Any]] = []
        run_specs = (
            ("run001", "KNOWN_SIDE_CALIBRATION"),
            ("run002", "KNOWN_SIDE_CALIBRATION"),
            ("run003", "PREREGISTERED_SECONDARY_ANALYSIS"),
            ("run004", "LOCKED_CROSS_COMMUNITY_SECONDARY_ANALYSIS"),
        )
        for key, evidence_class in run_specs:
            run_lines = lines[key]
            run_id = _label(run_lines, "Run_ID")
            prov_id = f"PROV-{run_id}"
            provenance[prov_id] = {
                "authority": self.manifest["documents"][key]["title"],
                "drive_id": self.manifest["documents"][key]["document_id"],
                "revision_id": self.manifest["documents"][key]["revision_id"],
            }
            source_status = _label(run_lines, "Status")
            item: dict[str, Any] = {
                "run_id": run_id,
                "dataset_id": _doc_dataset_id(run_lines),
                "evidence_class": evidence_class,
                "state": "CLOSED",
                "source_status": source_status,
                "provenance_ids": [prov_id],
            }
            if key in {"run001", "run002"}:
                item["disposition"] = "KNOWN_SIDE_CALIBRATION"
                item["claim_propagation_disposition"] = "KNOWN_SIDE_CALIBRATION"
                item["interpretation_ceiling"] = propagation["KNOWN_SIDE_CALIBRATION"][
                    "Permitted_Core_Interpretation"
                ]
                item["provenance_ids"].append("PROV-CLAIM-PROPAGATION")
            elif key == "run003":
                item["disposition"] = source_status
                item["interpretation_ceiling"] = _after_heading(
                    run_lines, "Scientific disposition"
                )
                item["metrics"] = _metric_triplet(run_lines)
            else:
                registered = _label(run_lines, "Registered disposition")
                item["disposition"] = registered
                item["claim_propagation_disposition"] = (
                    "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
                )
                item["interpretation_ceiling"] = propagation[
                    "NULL_OR_COMPONENTS_CONTEXT_SUFFICIENT"
                ]["Permitted_Core_Interpretation"]
                item["metrics"] = _metric_triplet(run_lines)
                item["provenance_ids"].append("PROV-CLAIM-PROPAGATION")
            run_view.append(item)

        held_lines = lines["run005006"]
        held_status = _after_heading(held_lines, "Status")
        held_gate = _after_heading(held_lines, "Current external blocker")
        held_prov = "PROV-D0019-EXECUTION-CONTRACT"
        provenance[held_prov] = {
            "authority": self.manifest["documents"]["run005006"]["title"],
            "drive_id": self.manifest["documents"]["run005006"]["document_id"],
            "revision_id": self.manifest["documents"]["run005006"]["revision_id"],
        }
        for run_id, evidence_class in (
            ("RUN-PT-RQ0001-005", "PLANNED_PREREGISTERED_EMPIRICAL"),
            ("RUN-PT-RQ0001-006", "PLANNED_LOCKED_TRANSFER"),
        ):
            run_view.append(
                {
                    "run_id": run_id,
                    "dataset_id": "D0019",
                    "evidence_class": evidence_class,
                    "state": "EMPIRICAL_EXECUTION_HELD",
                    "source_status": held_status,
                    "disposition": None,
                    "claim_propagation_disposition": "EMPIRICAL_EXECUTION_HELD",
                    "gate": held_gate,
                    "provenance_ids": [
                        held_prov,
                        "PROV-D0019",
                        "PROV-CLAIM-PROPAGATION",
                    ],
                }
            )

        software_verification = [
            {
                "verification_id": "Q0024-RHF-v0.1",
                "class": "ZERO_SYNTHETIC",
                "state": harness_state,
                "result": harness_result,
                "biological_evidence": False,
                "provenance_ids": ["PROV-HARNESS-VERIFY"],
            }
        ]

        snapshot = {
            "snapshot_id": "WORKBENCH-CHIMP-RQ0001-CANONICAL-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "captured_date": datetime.now(timezone.utc).date().isoformat(),
            "mode": "CANONICAL_PRODUCER_OUTPUT",
            "scientific_boundary": (
                "Evidence structure and provenance only; no translation, semantic gloss "
                "generation, independent evidence grading, or claim promotion."
            ),
            "species": {
                "species_id": "SP001",
                "taxon": taxon,
                "common_name": "Chimpanzee",
                "activation_state": activation,
                "population_scope": [populations],
                "active_question_ids": [selection["question_id"]],
                "comparison_readiness": {
                    "overall": crg_overall["Current_Status"],
                    "CRG-C": crg_c["Current_Status"],
                    "CRG-D": crg_d["Current_Status"],
                    "controlling_reason": crg_c["Current_Evidence"],
                },
                "receiver_harness": {
                    "implementation_state": harness_state,
                    "empirical_exercise_state": empirical_harness_state,
                    "fixture_result": harness_result,
                    "biological_evidence": False,
                },
                "provenance_ids": [
                    "PROV-SPECIES",
                    "PROV-COMPARISON-GATE",
                    "PROV-HARNESS-VERIFY",
                ],
            },
            "question": {
                "question_id": q["Question_ID"],
                "text": q["Research_Question"],
                "phase": q["Status"],
                "primary_discriminator": q["Primary_Outcome_or_Discriminator"],
                "ethics_boundary": q["Ethics_Welfare_Gate"],
                "provenance_ids": ["PROV-RQ0001"],
            },
            "hypotheses": hypothesis_view,
            "datasets": dataset_view,
            "runs": run_view,
            "software_verification": software_verification,
            "provenance": provenance,
        }

        bindings = {
            "species": {
                "semantic_owner": self.manifest["documents"]["species"]["title"],
                "drive_id": self.manifest["documents"]["species"]["document_id"],
            },
            "question": {
                "semantic_owner": "ACEB Research Questions",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": f"Research Questions:{selection['question_id']}",
            },
            "hypotheses": {
                "semantic_owner": "ACEB Hypotheses",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": "Hypotheses:" + ",".join(selection["hypothesis_ids"]),
            },
            "datasets": {
                "semantic_owner": "ACEB Datasets",
                "spreadsheet_id": self.manifest["aceb"]["spreadsheet_id"],
                "registry": "Datasets:" + ",".join(selection["dataset_ids"]),
            },
            "runs": {
                "semantic_owner": "RQ0001 frozen run authorities",
                "source": ",".join(
                    self.manifest["documents"][key]["document_id"]
                    for key in ("run001", "run002", "run003", "run004", "run005006")
                ),
            },
            "software_verification": {
                "semantic_owner": self.manifest["documents"]["harness_verify"]["title"],
                "drive_id": self.manifest["documents"]["harness_verify"]["document_id"],
                "github_repo": "acipriano1997/animal-rosetta-stone",
            },
            "provenance": {
                "semantic_owner": "record-specific Drive and ACEB authorities",
                "source": self.manifest["manifest_id"],
            },
        }

        bundle = {
            "adapter_contract": CANONICAL_READ_CONTRACT,
            "producer_manifest": self.manifest["manifest_id"],
            "authority_state": "CURRENT",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "bindings": bindings,
            "snapshot": snapshot,
        }
        canonical_bundle_to_snapshot(bundle, source="<memory>")
        return bundle
