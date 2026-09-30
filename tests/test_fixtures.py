from ars_receiver_harness.fixtures import run_suite


def test_all_rhf_001_035_pass():
    receipt = run_suite()
    assert receipt["all_passed"]
    assert receipt["passed"] == 35
    assert receipt["total"] == 35
    assert [x["fixture_id"] for x in receipt["results"]] == [f"RHF-{i:03d}" for i in range(1,36)]
    assert not receipt["biological_evidence"]
