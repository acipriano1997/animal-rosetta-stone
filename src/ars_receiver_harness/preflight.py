from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any, Mapping

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class HarnessDecision:
    state: str
    stage: str
    passed: bool
    reason: str
    claim_limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["claim_limitations"] = list(self.claim_limitations)
        return d


def _get(m: Mapping[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = m
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            return default
        cur = cur[key]
    return cur


def preflight(manifest: Mapping[str, Any]) -> HarnessDecision:
    """Fail-closed H0-H9/H7-hardening preflight.

    This validates declared evidence about a source/run package; it does not infer
    missing rights, provenance, biological meaning, or source facts.
    """
    if _get(manifest, "rights", "research_use_storage") is not True:
        return HarnessDecision("HELD_RIGHTS", "H0", False, "Research use/storage rights are not explicitly established.")

    sha = str(_get(manifest, "source", "sha256", default=""))
    source_fields = ["provider", "dataset_id", "version", "filename"]
    if any(not _get(manifest, "source", k) for k in source_fields) or not SHA256_RE.match(sha):
        return HarnessDecision("QUARANTINED_PROVENANCE", "H1", False, "Pinned source identity or SHA-256 is incomplete/invalid.")

    if _get(manifest, "schema", "inventory_complete") is not True:
        return HarnessDecision("HELD_SCHEMA", "H2", False, "Pre-outcome schema inventory is incomplete.")

    if _get(manifest, "mapping", "required_primary_unmappable") is True:
        return HarnessDecision("HELD_SCHEMA", "H3", False, "A required-primary source field is unmappable under the frozen contract.")

    if _get(manifest, "event_identity", "source_locator_present") is not True or _get(manifest, "event_identity", "deterministic") is not True:
        return HarnessDecision("QUARANTINED_PROVENANCE", "H4", False, "Immutable source locator / deterministic Event_ID evidence is incomplete.")

    if _get(manifest, "missingness", "primary_outcome_imputed") is True:
        return HarnessDecision("QUARANTINED_OUTCOME_LEAKAGE", "H5", False, "Primary outcome was imputed/coerced.")
    if _get(manifest, "missingness", "states_preserved") is not True:
        return HarnessDecision("QUARANTINED_SEMANTIC_ESCALATION", "H5", False, "Missing/unknown/not-visible/negative states are not faithfully preserved.")

    if _get(manifest, "split", "sealed") is not True:
        return HarnessDecision("HELD_SPLIT", "H6", False, "Frozen development/evaluation split is not sealed.")

    if _get(manifest, "grouping", "rowwise_fallback") is True:
        return HarnessDecision("HELD_GROUPING", "H7", False, "Prohibited row-wise validation fallback is active.")
    if _get(manifest, "grouping", "valid_registered_key") is not True:
        return HarnessDecision("HELD_GROUPING", "H7", False, "No valid registered grouping key/fallback is available.")
    if _get(manifest, "grouping", "outcome_or_locked_leakage") is True:
        return HarnessDecision("QUARANTINED_OUTCOME_LEAKAGE", "H7", False, "Outcome/post-response/locked-evaluation information enters development.")
    if _get(manifest, "nuisance", "inventory_recorded") is not True:
        return HarnessDecision("HELD_SCHEMA", "H7", False, "Nuisance-structure availability/absence has not been recorded.")

    limitations: list[str] = []
    if _get(manifest, "nuisance", "material_shortcut_risk") is True:
        if _get(manifest, "nuisance", "mitigation_or_claim_limit_recorded") is not True:
            return HarnessDecision("HELD_SPLIT", "H7", False, "Material shortcut structure is present without blocked evaluation or explicit claim limitation.")
        limitations.append("MATERIAL_NUISANCE_STRUCTURE")
    if _get(manifest, "nuisance", "metadata_incomplete") is True:
        limitations.append("NUISANCE_METADATA_INCOMPLETE")

    if _get(manifest, "normalization", "row_preserving") is not True:
        return HarnessDecision("QUARANTINED_PROVENANCE", "H8", False, "Normalized rows are not reversibly traceable to source records.")
    if _get(manifest, "normalization", "semantic_escalation") is True:
        return HarnessDecision("QUARANTINED_SEMANTIC_ESCALATION", "H8", False, "Normalization introduces unsupported biological meaning.")

    if _get(manifest, "run_package", "complete") is not True:
        return HarnessDecision("HELD_SCHEMA", "H9", False, "Immutable run package is incomplete.")
    if _get(manifest, "sanity", "registered") is not True:
        return HarnessDecision("HELD_SANITY", "H9", False, "Applicable pipeline sanity control is not registered.")

    state = "PASS_WITH_CLAIM_LIMITATION" if limitations else "PASS_ANALYSIS_PREFLIGHT"
    return HarnessDecision(state, "H9", True, "Receiver analysis preflight passed.", tuple(limitations))


def postflight(run_record: Mapping[str, Any]) -> HarnessDecision:
    """H10-H11 closeout. A failed registered sanity control blocks biology."""
    if _get(run_record, "sanity", "passed") is not True:
        return HarnessDecision("HELD_SANITY", "H10", False, "Registered pipeline sanity control did not pass.")
    if _get(run_record, "result", "preserved") is not True:
        return HarnessDecision("QUARANTINED_PROVENANCE", "H11", False, "Complete result package was not preserved.")
    limitations = tuple(run_record.get("claim_limitations", ()) or ())
    return HarnessDecision("CLOSED_SOURCE_SPECIFIC_RUN", "H11", True, "Run package closed and preserved.", limitations)
