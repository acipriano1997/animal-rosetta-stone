from __future__ import annotations

from copy import deepcopy
from typing import Any


class EvidenceProjectionError(RuntimeError):
    """Raised when canonical evidence/rights registries cannot be projected safely."""


def _split_ids(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def _one(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise EvidenceProjectionError(
            f"expected exactly one {key}={value!r} row, found {len(matches)}"
        )
    return matches[0]


def _rows(values: list[list[Any]]) -> list[dict[str, str]]:
    if not values:
        raise EvidenceProjectionError("rights/missingness range is empty")
    headers = [str(x).strip() for x in values[0]]
    if not headers or any(not h for h in headers):
        raise EvidenceProjectionError("rights/missingness header is invalid")
    out: list[dict[str, str]] = []
    for row in values[1:]:
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        item = {h: str(padded[i]).strip() for i, h in enumerate(headers)}
        if any(item.values()):
            out.append(item)
    return out


def build_evidence_projection(
    aceb: dict[str, list[dict[str, str]]],
    reader: Any,
    manifest: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    selection = manifest["evidence_selection"]
    claim_ids = selection["claim_ids"]
    question_id = selection["research_question_id"]

    claims_by_id = {
        row.get("Claim_ID"): row
        for row in aceb["claims"]
        if row.get("Claim_ID")
    }
    links = [
        row for row in aceb["claim_evidence_links"]
        if row.get("Claim_ID") in claim_ids
    ]

    evidence_provenance: dict[str, dict[str, Any]] = {}
    evidence_items: list[dict[str, Any]] = []

    for claim_id in claim_ids:
        if claim_id not in claims_by_id:
            raise EvidenceProjectionError(f"selected claim missing from ACEB: {claim_id}")
        row = claims_by_id[claim_id]
        claim_links = [link for link in links if link.get("Claim_ID") == claim_id]

        claim_prov = f"PROV-CLAIM-{claim_id}"
        evidence_provenance[claim_prov] = {
            "authority": "ACEB Claims",
            "spreadsheet_id": manifest["aceb"]["spreadsheet_id"],
            "registry": f"Claims:{claim_id}",
        }

        link_views: list[dict[str, Any]] = []
        claim_provenance_ids = [claim_prov]
        for link in claim_links:
            link_id = link["Link_ID"]
            link_prov = f"PROV-LINK-{link_id}"
            evidence_provenance[link_prov] = {
                "authority": "ACEB Claim-Evidence Links",
                "spreadsheet_id": manifest["aceb"]["spreadsheet_id"],
                "registry": f"Claim-Evidence Links:{link_id}",
            }
            claim_provenance_ids.append(link_prov)
            link_views.append(
                {
                    "link_id": link_id,
                    "evidence_direction": link["Evidence_Direction"],
                    "experiment_id": link["Experiment_ID"],
                    "study_id": link["Study_ID"],
                    "dataset_id": link["Dataset_ID"],
                    "evidence_channel": link["Evidence_Channel"],
                    "population_scope": link["Population_Scope"],
                    "method_scope": link["Method_Scope"],
                    "independence_level": link["Independence_Level"],
                    "replication_relation": link["Replication_Relation"],
                    "correction_state": link["Correction_State"],
                    "weight_or_confidence_basis": link["Weight_or_Confidence_Basis"],
                    "alternative_explanation_addressed": link[
                        "Alternative_Explanation_Addressed"
                    ],
                    "source_provenance_verified": link["Source_Provenance_Verified"],
                    "notes": link["Notes"],
                    "provenance_ids": [link_prov],
                }
            )

        evidence_items.append(
            {
                "claim_id": claim_id,
                "claim_short": row["Claim_Short"],
                "species": row["Species"],
                "scope_boundary": row["Scope_Boundary"],
                "status": row["Status"],
                "claim_type": row["Claim_Type"],
                "evidence_channels": row["Evidence_Channels"],
                "behavioral_validation": row["Behavioral_Validation"],
                "independent_replication": row["Independent_Replication"],
                "ars_confidence": row["ARS_Confidence"],
                "confidence_rationale": row["Confidence_Rationale"],
                "do_not_overclaim": row["Do_Not_Overclaim"],
                "population_boundary": row["Population_Boundary"],
                "method_boundary": row["Method_Boundary"],
                "alternative_explanations": row["Alternative_Explanations"],
                "null_evidence_ids": _split_ids(row["Null_Evidence_IDs"]),
                "source_study_ids": _split_ids(row["Source_Study_IDs"]),
                "reproducibility_status": row["Reproducibility_Status"],
                "evidence_links": link_views,
                "explicit_link_state": (
                    "LINKED_ROWS_PRESENT"
                    if link_views
                    else "NO_EXPLICIT_CLAIM_EVIDENCE_LINK_ROW_IN_SELECTED_REGISTRY"
                ),
                "provenance_ids": claim_provenance_ids,
            }
        )

    selected_studies = {
        study_id
        for item in evidence_items
        for study_id in item["source_study_ids"]
    }

    corrections: list[dict[str, Any]] = []
    for row in aceb["contradictions"]:
        target = row.get("Target_Study_or_Claim", "")
        if not target:
            continue
        if not (
            any(claim_id in target for claim_id in claim_ids)
            or any(study_id in target for study_id in selected_studies)
        ):
            continue
        record_id = row["Record_ID"]
        prov_id = f"PROV-CORRECTION-{record_id}"
        evidence_provenance[prov_id] = {
            "authority": "ACEB Contradictions & Corrections",
            "spreadsheet_id": manifest["aceb"]["spreadsheet_id"],
            "registry": f"Contradictions & Corrections:{record_id}",
        }
        corrections.append(
            {
                "record_id": record_id,
                "target_study_or_claim": target,
                "type": row["Type"],
                "date_or_year": row["Date_or_Year"],
                "what_changed": row["What_Changed"],
                "effect_on_conclusion": row["Effect_on_Conclusion"],
                "ars_action": row["ARS_Action"],
                "source_or_link": row["Source_or_Link"],
                "status": row["Status"],
                "provenance_ids": [prov_id],
            }
        )

    disagreements: list[dict[str, Any]] = []
    for row in aceb["disagreements"]:
        if not row.get("Disagreement_ID"):
            continue
        if not (
            row.get("Research_Question_ID") == question_id
            or row.get("Claim_or_Hypothesis_ID") in claim_ids
        ):
            continue
        disagreement_id = row["Disagreement_ID"]
        prov_id = f"PROV-DISAGREEMENT-{disagreement_id}"
        evidence_provenance[prov_id] = {
            "authority": "ACEB Disagreement Maps",
            "spreadsheet_id": manifest["aceb"]["spreadsheet_id"],
            "registry": f"Disagreement Maps:{disagreement_id}",
        }
        disagreements.append(
            {
                "disagreement_id": disagreement_id,
                "research_question_id": row["Research_Question_ID"],
                "claim_or_hypothesis_id": row["Claim_or_Hypothesis_ID"],
                "run_ids": _split_ids(row["Run_IDs"]),
                "dimension": row["Disagreement_Dimension"],
                "position_a": row["Position_A"],
                "position_b": row["Position_B"],
                "other_positions": row["Other_Positions"],
                "common_ground": row["Common_Ground"],
                "key_assumption_difference": row["Key_Assumption_Difference"],
                "evidence_needed": row["Evidence_Needed"],
                "empirical_discriminator": row["Empirical_Discriminator"],
                "priority": row["Priority"],
                "status": row["Status"],
                "resolution_or_current_state": row["Resolution_or_Current_State"],
                "provenance_ids": [prov_id],
            }
        )

    registry_status = {
        "research_question_id": question_id,
        "selected_claim_ids": deepcopy(claim_ids),
        "contradictions_registry_checked": True,
        "matching_contradiction_rows": len(corrections),
        "disagreement_registry_checked": True,
        "matching_disagreement_rows": len(disagreements),
        "absence_rule": (
            "Zero matching registry rows means only that no matching canonical row is "
            "currently registered; it is not evidence that contrary evidence or "
            "scientific disagreement does not exist."
        ),
        "selection_rule": selection["rule"],
    }

    datasets_by_id = {
        row.get("Dataset_ID"): row
        for row in aceb["datasets"]
        if row.get("Dataset_ID")
    }
    media_placeholders: list[dict[str, Any]] = []
    for dataset_id in ("D0018", "D0020"):
        spec = manifest["event_sources"][dataset_id]
        dataset = _one(aceb["datasets"], "Dataset_ID", dataset_id)
        missingness_rows = _rows(
            reader.spreadsheet_values(
                spec["spreadsheet_id"], spec["missingness_range"]
            )
        )
        raw_media = _one(missingness_rows, "Issue", "Raw media")
        prov_id = f"PROV-MEDIA-{dataset_id}"
        evidence_provenance[prov_id] = {
            "authority": spec["title"] + " — Missingness & Limits",
            "spreadsheet_id": spec["spreadsheet_id"],
            "registry": "Missingness & Limits:Raw media",
        }
        rights_state = (
            dataset.get("Rights_or_Restrictions")
            or dataset.get("License_or_Access")
            or "UNKNOWN"
        )
        media_placeholders.append(
            {
                "dataset_id": dataset_id,
                "media_type": "RAW_AUDIO_VIDEO",
                "availability_status": raw_media["Status"],
                "rights_state": rights_state,
                "bytes_available": False,
                "preview_allowed": False,
                "scientific_consequence": raw_media["Scientific_Consequence"],
                "required_action": raw_media["Required_Action"],
                "placeholder_message": (
                    "Raw media is not available in the Workbench. Metadata and "
                    "provenance may be shown, but no preview is synthesized."
                ),
                "provenance_ids": [prov_id, f"PROV-{dataset_id}"],
            }
        )

    return (
        deepcopy(evidence_items),
        deepcopy(corrections),
        deepcopy(disagreements),
        deepcopy(registry_status),
        deepcopy(media_placeholders),
        deepcopy(evidence_provenance),
    )
