"""Fail-closed PR0006 admission: verify source bytes before empirical analysis."""
from __future__ import annotations
from dataclasses import replace
import hashlib
from pathlib import Path

import pandas as pd

from .preflight import preflight
from .pr0006 import PR0006Config


class AdmissionError(ValueError):
    def __init__(self, state: str, reason: str):
        self.state = state
        super().__init__(f"{state}: {reason}")


def _require(section: dict, key: str, state: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AdmissionError(state, f"Missing auditable {key} reference.")
    return value


def _hash_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise AdmissionError("QUARANTINED_PROVENANCE", f"{label} file not found.")
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    observed = digest.hexdigest()
    if not isinstance(expected, str) or observed.lower() != expected.lower():
        raise AdmissionError("QUARANTINED_PROVENANCE", f"{label} SHA-256 mismatch.")
    return observed


def validate_admission(
    frame: pd.DataFrame, normalized_csv: Path, raw_source: Path,
    manifest: dict, cfg: PR0006Config,
) -> tuple[PR0006Config, dict]:
    """Return run configuration and receipt, never permission or biological credit."""
    verdict = preflight(manifest)
    if not verdict.passed:
        raise AdmissionError(verdict.state, verdict.reason)
    rights = manifest["rights"]
    schema = manifest["schema"]
    mapping = manifest["mapping"]
    source = manifest["source"]
    normal = manifest["normalization"]
    identity = manifest["event_identity"]
    grouping = manifest["grouping"]
    nuisance = manifest["nuisance"]
    for section, key, state in (
        (rights, "evidence_ref", "HELD_RIGHTS"),
        (rights, "attribution_ref", "HELD_RIGHTS"),
        (schema, "codebook_ref", "HELD_SCHEMA"),
        (mapping, "review_ref", "HELD_SCHEMA"),
        (normal, "eligibility_ledger_ref", "HELD_SCHEMA"),
        (identity, "derivation_rule_ref", "QUARANTINED_PROVENANCE"),
        (nuisance, "review_ref", "HELD_SCHEMA"),
    ):
        _require(section, key, state)
    if manifest.get("protocol_id") != "PR0006" or manifest.get("receiver_contract") != "RDC-005":
        raise AdmissionError("HELD_SCHEMA", "Unrecognized registered protocol/contract.")
    if manifest["sanity"].get("protocol_id") != "PD-PR0006-003":
        raise AdmissionError("HELD_SANITY", "Registered permutation protocol is not pinned.")
    if identity.get("collision_check_passed") is not True:
        raise AdmissionError("QUARANTINED_PROVENANCE", "Event identity audit not complete.")
    if mapping.get("pre_outcome_checked") is not True:
        raise AdmissionError("QUARANTINED_OUTCOME_LEAKAGE", "Predictor timing not checked.")
    if normal.get("eligible_only") is not True:
        raise AdmissionError("HELD_SCHEMA", "Eligibility/exclusion review incomplete.")
    if raw_source.name != source.get("filename"):
        raise AdmissionError("QUARANTINED_PROVENANCE", "Raw source filename mismatch.")
    raw_sha = _hash_file(raw_source, source.get("sha256"), "Raw source")
    norm_sha = _hash_file(normalized_csv, normal.get("normalized_sha256"), "Normalized")
    canonical_frame = pd.read_csv(normalized_csv)
    if not frame.reset_index(drop=True).equals(canonical_frame):
        raise AdmissionError("QUARANTINED_PROVENANCE", "Analysis frame differs from hashed normalized CSV.")

    if not (cfg.n_splits == 5 and cfg.c == 1.0 and cfg.seed == 20260929
            and cfg.bootstrap_resamples == 2000 and cfg.sanity_permutations == 200
            and cfg.outcome_col == "Recipient_Response" and cfg.modality_col == "Communication_Type"
            and cfg.primary_group_col == "Dyad_ID" and cfg.signaller_col == "Signaller_ID"):
        raise AdmissionError("HELD_SCHEMA", "PR0006's frozen analytic settings must not change.")
    num = tuple(mapping.get("approved_baseline_numeric", ()))
    cat = tuple(mapping.get("approved_baseline_categorical", ()))
    if num != cfg.baseline_numeric or cat != cfg.baseline_categorical:
        raise AdmissionError("HELD_SCHEMA", "Configured baseline differs from approved source mapping.")
    baseline = num + cat
    prohibited = {"Recipient_Response", "Communication_Type", "Dyad_ID", "Signaller_ID",
                  "Recipient_ID", "Source_Record_Locator", "Event_ID"}
    if len(baseline) != len(set(baseline)) or set(baseline) & prohibited:
        raise AdmissionError("QUARANTINED_OUTCOME_LEAKAGE", "Identity/outcome/modality used as B0.")
    if not baseline and not mapping.get("intercept_only_justification_ref"):
        raise AdmissionError("HELD_SCHEMA", "No approved B0 covariates.")
    if set(baseline) & {"Response_Waiting", "Elaboration"} and not mapping.get("post_signal_timing_proof_ref"):
        raise AdmissionError("QUARANTINED_OUTCOME_LEAKAGE", "Post-signal timing unverified.")
    if "Audience_Checking" in baseline and not mapping.get("audience_timing_proof_ref"):
        raise AdmissionError("QUARANTINED_OUTCOME_LEAKAGE", "Audience timing unverified.")

    required = {"Event_ID", "Source_Record_Locator", "Recipient_Response",
                "Communication_Type", "Signaller_ID"} | set(baseline)
    if not required.issubset(frame.columns):
        raise AdmissionError("HELD_SCHEMA", "Normalized file lacks required audited columns.")
    for col in ("Event_ID", "Source_Record_Locator", "Recipient_Response",
                "Communication_Type", "Signaller_ID"):
        if frame[col].isna().any():
            raise AdmissionError("HELD_SCHEMA", f"{col} contains unavailable primary data.")
    if frame["Event_ID"].duplicated().any() or frame["Source_Record_Locator"].duplicated().any():
        raise AdmissionError("QUARANTINED_PROVENANCE", "Duplicated event/source locators.")
    if set(frame["Recipient_Response"].unique()) != {"approach", "avoidance"}:
        raise AdmissionError("HELD_SCHEMA", "Receiver classes must be approach/avoidance.")
    if set(frame["Communication_Type"].unique()) != {"gesture", "vocalization", "bimodal"}:
        raise AdmissionError("HELD_SCHEMA", "Required three broad modality levels absent.")

    fallback = "Dyad_ID" not in frame or frame["Dyad_ID"].isna().all()
    if fallback:
        if grouping.get("fallback_activated") is not True:
            raise AdmissionError("HELD_GROUPING", "Unregistered Signaller_ID fallback.")
        _require(grouping, "fallback_approval_ref", "HELD_GROUPING")
    elif frame["Dyad_ID"].isna().any() or grouping.get("fallback_activated") is True:
        raise AdmissionError("HELD_GROUPING", "Mixed/contradictory grouping evidence.")
    key = "Signaller_ID" if fallback else "Dyad_ID"
    if frame[key].nunique() < 5:
        raise AdmissionError("HELD_SPLIT", "Fewer groups than frozen five folds.")

    return replace(cfg, primary_group_col=key), {
        "state": "ADMITTED_FOR_REGISTERED_ANALYSIS_ONLY",
        "source_sha256": raw_sha,
        "normalized_sha256": norm_sha,
        "rights_evidence_ref": rights["evidence_ref"],
        "mapping_review_ref": mapping["review_ref"],
        "grouping_key": key,
        "fallback_activated": fallback,
        "rows": len(frame),
        "evidence_weight": manifest.get("evidence_weight", "EMPIRICAL_CANDIDATE_UNADJUDICATED"),
        "claim_admissible": False,
    }
