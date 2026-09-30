from ars_receiver_harness.preflight import preflight, postflight


def good_manifest():
    return {
        "rights": {"research_use_storage": True},
        "source": {
            "provider": "example", "dataset_id": "D0025", "version": "v1",
            "filename": "data.csv", "sha256": "a" * 64,
        },
        "schema": {"inventory_complete": True},
        "mapping": {"required_primary_unmappable": False},
        "event_identity": {"source_locator_present": True, "deterministic": True},
        "missingness": {"primary_outcome_imputed": False, "states_preserved": True},
        "split": {"sealed": True},
        "grouping": {"rowwise_fallback": False, "valid_registered_key": True, "outcome_or_locked_leakage": False},
        "nuisance": {"inventory_recorded": True, "material_shortcut_risk": False, "metadata_incomplete": False},
        "normalization": {"row_preserving": True, "semantic_escalation": False},
        "run_package": {"complete": True},
        "sanity": {"registered": True},
    }


def test_preflight_pass():
    d = preflight(good_manifest())
    assert d.passed
    assert d.state == "PASS_ANALYSIS_PREFLIGHT"


def test_rights_fail_closed():
    m = good_manifest(); m["rights"]["research_use_storage"] = False
    assert preflight(m).state == "HELD_RIGHTS"


def test_nuisance_claim_limit():
    m = good_manifest()
    m["nuisance"]["material_shortcut_risk"] = True
    m["nuisance"]["mitigation_or_claim_limit_recorded"] = True
    d = preflight(m)
    assert d.passed and d.state == "PASS_WITH_CLAIM_LIMITATION"


def test_sanity_fail_closed():
    m = good_manifest(); m["sanity"]["registered"] = False
    assert preflight(m).state == "HELD_SANITY"


def test_postflight_sanity_blocks_biology():
    d = postflight({"sanity": {"passed": False}, "result": {"preserved": True}})
    assert d.state == "HELD_SANITY"
