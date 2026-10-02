from __future__ import annotations

from copy import deepcopy
from typing import Any


class EventProjectionError(RuntimeError):
    """Raised when a pinned event corpus cannot be projected safely."""


def _rows(values: list[list[Any]]) -> list[dict[str, str]]:
    if not values:
        raise EventProjectionError("event source range is empty")
    headers = [str(x).strip() for x in values[0]]
    if not headers or any(not h for h in headers):
        raise EventProjectionError("event source header is invalid")
    rows: list[dict[str, str]] = []
    for row in values[1:]:
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        item = {h: str(padded[i]).strip() for i, h in enumerate(headers)}
        if any(item.values()):
            rows.append(item)
    return rows


def _missingness(value: str) -> list[str]:
    return [x.strip() for x in value.split(";") if x.strip()]


def _provenance_rows(
    values: list[list[Any]], *, spreadsheet_id: str, authority: str
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _rows(values):
        provenance_id = row.get("Provenance_Record_ID", "")
        if not provenance_id:
            continue
        out[provenance_id] = {
            "authority": authority + " — Provenance",
            "spreadsheet_id": spreadsheet_id,
            "registry": f"Provenance:{provenance_id}",
            "object": row.get("Object"),
            "type": row.get("Type"),
            "persistent_id_or_url": row.get("Persistent_ID_or_URL"),
            "version_or_branch": row.get("Version_or_Branch"),
            "content_id": row.get("Content_ID"),
            "rights": row.get("Rights"),
            "retrieved_date": row.get("Retrieved_Date"),
            "transformation": row.get("Transformation"),
            "raw_vs_derived": row.get("Raw_vs_Derived"),
            "stored_bytes": row.get("Stored_Bytes"),
            "notes": row.get("Notes"),
        }
    return out


def _d0018_event(
    row: dict[str, str], *, spreadsheet_id: str, authority: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    event_id = row["Event_ID"]
    event_prov_id = row["Provenance_Record_ID"]
    if not event_prov_id:
        raise EventProjectionError(f"D0018 event {event_id} lacks provenance id")
    source_file = row["Source_File"]
    source_prov = (
        "PRV-D0018-SNAKE-SOURCE"
        if source_file == "Source-data-snake.csv"
        else "PRV-D0018-PB-SOURCE"
    )
    event = {
        "event_id": event_id,
        "dataset_id": "D0018",
        "taxon_id": row["Taxon_ID"],
        "population_or_group_id": row["Population_or_Group_ID"],
        "source_study_id": row["Source_Study_ID"],
        "source_experiment_id": row["Source_Experiment_ID"],
        "event_type": row["Event_Type"],
        "sender_ids": _missingness(row["Sender_IDs"]),
        "receiver_ids": _missingness(row["Receiver_IDs"]),
        "context": {
            "context_id": row["Context_ID"],
            "source_condition": row["Source_Condition"],
            "trigger_or_anchor": row["Trigger_or_Anchor"],
        },
        "signal": {
            "component_1": row["Signal_Component_1"],
            "component_2": row["Signal_Component_2"],
            "order": row["Signal_Order"],
            "combination_flag": row["Combination_Flag"],
        },
        "receiver_response": row["Receiver_Response"],
        "consequence_or_outcome": row["Consequence_or_Outcome"],
        "sender_followup_repair_cessation": row["Sender_Followup_Repair_Cessation"],
        "observation_window": row["Observation_Window"],
        "split": row["Split"],
        "split_eligibility": row["Split_Eligibility"],
        "event_confidence": row["Event_Confidence"],
        "missingness_codes": _missingness(row["Missingness_Codes"]),
        "source_locator": {
            "source_file": source_file,
            "source_blob_sha": row["Source_Blob_SHA"],
            "source_row": row["Source_Row"],
        },
        "notes": row["Notes"],
        "provenance_ids": [event_prov_id, source_prov],
    }
    event_provenance = {
        "authority": authority,
        "spreadsheet_id": spreadsheet_id,
        "registry": f"Events:{event_id}",
        "source_file": source_file,
        "source_blob_sha": row["Source_Blob_SHA"],
        "source_row": row["Source_Row"],
        "source_study_id": row["Source_Study_ID"],
        "source_experiment_id": row["Source_Experiment_ID"],
    }
    return event, event_provenance


def _d0020_event(
    row: dict[str, str], *, spreadsheet_id: str, authority: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    event_id = row["Event_ID"]
    event_prov_id = row["Provenance_Record_ID"]
    if not event_prov_id:
        raise EventProjectionError(f"D0020 event {event_id} lacks provenance id")
    event = {
        "event_id": event_id,
        "dataset_id": "D0020",
        "taxon_id": row["Taxon_ID"],
        "population_or_group_id": row["Population_or_Group_ID"],
        "source_study_id": row["Source_Study_ID"],
        "source_experiment_id": row["Source_Experiment_ID"],
        "event_type": row["Event_Type"],
        "sender_ids": [row["Initial_Sender_ID"]] if row["Initial_Sender_ID"] else [],
        "receiver_ids": [row["Initial_Receiver_ID"]] if row["Initial_Receiver_ID"] else [],
        "participant_ids": _missingness(row["Participant_IDs"]),
        "context": {
            "relative_start_s": row["Relative_Start_s"],
            "relative_end_s": row["Relative_End_s"],
            "initial_goal_anon": row["Initial_Goal_Anon"],
        },
        "signal": {
            "gesture_token_count": row["Gesture_Token_Count"],
            "exchange_status": row["Exchange_Status"],
            "declared_turn_count": row["Declared_Turn_Count"],
            "sender_alternation_count": row["Sender_Alternation_Count"],
            "gesture_form": "NOT_RELEASED_IN_ANON_CSV",
        },
        "receiver_response": "NOT_SEPARATELY_CODED_IN_EVENT_VIEW",
        "consequence_or_outcome": row["Final_Outcome_Label"],
        "final_outcome_time_s": row["Final_Outcome_Time_s"],
        "continuation_structure": row["Continuation_Structure"],
        "split": row["Split"],
        "split_eligibility": row["Split_Eligibility"],
        "event_confidence": row["Event_Confidence"],
        "missingness_codes": _missingness(row["Missingness_Codes"]),
        "source_locator": {
            "source_communication_id": row["Source_Communication_ID"],
            "source_row_min": row["Source_Row_Min"],
            "source_row_max": row["Source_Row_Max"],
            "source_row_count": row["Source_Row_Count"],
        },
        "notes": (
            "Goal labels are anonymized source codes; gesture form is not released in "
            "the anonymized source CSV; continuation structure is descriptive only."
        ),
        "provenance_ids": [event_prov_id, "PRV-D0020-CSV"],
    }
    event_provenance = {
        "authority": authority,
        "spreadsheet_id": spreadsheet_id,
        "registry": f"Interaction Events:{event_id}",
        "source_communication_id": row["Source_Communication_ID"],
        "source_row_min": row["Source_Row_Min"],
        "source_row_max": row["Source_Row_Max"],
        "source_row_count": row["Source_Row_Count"],
        "source_study_id": row["Source_Study_ID"],
        "source_experiment_id": row["Source_Experiment_ID"],
    }
    return event, event_provenance


def build_event_projection(
    reader: Any, manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {}
    event_provenance: dict[str, dict[str, Any]] = {}
    seen_event_ids: set[str] = set()

    for dataset_id in ("D0018", "D0020"):
        spec = manifest["event_sources"][dataset_id]
        metadata = reader.drive_metadata(spec["spreadsheet_id"])
        if metadata.get("name") != spec["title"]:
            raise EventProjectionError(f"{dataset_id} event authority title drift")
        if metadata.get("modifiedTime") != spec["observed_modified_time"]:
            raise EventProjectionError(
                f"{dataset_id} event authority modified-time drift; fail closed"
            )

        raw_event_rows = _rows(
            reader.spreadsheet_values(spec["spreadsheet_id"], spec["event_range"])
        )
        raw_event_rows = [row for row in raw_event_rows if row.get("Event_ID")]
        if len(raw_event_rows) != spec["expected_event_count"]:
            raise EventProjectionError(
                f"{dataset_id} event count mismatch: expected "
                f"{spec['expected_event_count']}, found {len(raw_event_rows)}"
            )

        source_provenance = _provenance_rows(
            reader.spreadsheet_values(
                spec["spreadsheet_id"], spec["provenance_range"]
            ),
            spreadsheet_id=spec["spreadsheet_id"],
            authority=spec["title"],
        )
        event_provenance.update(source_provenance)

        for row in raw_event_rows:
            if dataset_id == "D0018":
                event, provenance = _d0018_event(
                    row,
                    spreadsheet_id=spec["spreadsheet_id"],
                    authority=spec["title"],
                )
            else:
                event, provenance = _d0020_event(
                    row,
                    spreadsheet_id=spec["spreadsheet_id"],
                    authority=spec["title"],
                )
            event_id = event["event_id"]
            provenance_id = event["provenance_ids"][0]
            if event_id in seen_event_ids:
                raise EventProjectionError(f"duplicate event id: {event_id}")
            seen_event_ids.add(event_id)
            if provenance_id in event_provenance:
                raise EventProjectionError(
                    f"event provenance id collides with source provenance: {provenance_id}"
                )
            event_provenance[provenance_id] = provenance
            events.append(event)

        inventory[dataset_id] = {
            "canonical_total": spec["expected_event_count"],
            "available_in_bundle": spec["expected_event_count"],
            "coverage": "FULL_CANONICAL_EVENT_ROWS",
            "authority": spec["title"],
            "spreadsheet_id": spec["spreadsheet_id"],
            "event_sheet": spec["event_sheet"],
            "observed_modified_time": spec["observed_modified_time"],
        }

    return deepcopy(events), deepcopy(inventory), deepcopy(event_provenance)
