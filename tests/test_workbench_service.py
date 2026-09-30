from importlib.resources import files

from ars_workbench.store import WorkbenchStore


def test_required_phase1_service_methods():
    store = WorkbenchStore()
    assert store.species_list()[0]["species_id"] == "SP001"
    assert store.species_get("SP001")["taxon"] == "Pan troglodytes"
    assert store.question_get("RQ0001")["hypotheses"]
    assert store.dataset_get("D0020")["dataset_id"] == "D0020"
    assert store.run_get("RUN-PT-RQ0001-004")["disposition"] == "NULL_OR_CONTEXT_SUFFICIENT"
    assert store.evidence_get("RQ0001")["software_verification"]
    assert store.provenance_get("PROV-RUN004")["drive_id"]


def test_unknown_records_fail_closed_to_none():
    store = WorkbenchStore()
    assert store.species_get("UNKNOWN") is None
    assert store.question_get("RQ9999") is None
    assert store.dataset_get("D9999") is None
    assert store.run_get("RUN-NOPE") is None
    assert store.provenance_get("PROV-NOPE") is None


def test_static_surface_is_packaged():
    root = files("ars_workbench").joinpath("static")
    for name in ("index.html", "app.js", "styles.css"):
        assert root.joinpath(name).is_file()
