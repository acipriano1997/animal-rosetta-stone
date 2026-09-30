from ars_receiver_harness.d0019_ids import (
    canonical_event_id,
    pseudonymize_source_id,
    unordered_dyad_id,
)


def test_unordered_dyad_is_direction_invariant():
    secret=b"test-only-secret"
    a=pseudonymize_source_id("Alice",secret)
    b=pseudonymize_source_id("Bob",secret)
    assert unordered_dyad_id(a,b)==unordered_dyad_id(b,a)


def test_pseudonymization_requires_runtime_secret_and_is_deterministic():
    secret=b"test-only-secret"
    assert pseudonymize_source_id("A",secret)==pseudonymize_source_id("A",secret)
    assert pseudonymize_source_id("A",secret)!=pseudonymize_source_id("B",secret)


def test_event_id_is_source_row_bound_and_stable():
    sha="26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e"
    first=canonical_event_id(source_sha256=sha,sheet="Rawdata",original_row=2)
    again=canonical_event_id(source_sha256=sha,sheet="Rawdata",original_row=2)
    next_row=canonical_event_id(source_sha256=sha,sheet="Rawdata",original_row=3)
    assert first==again
    assert first!=next_row


def test_event_id_rejects_derived_or_unpinned_location():
    sha="26f69ee04f5d017d46f72430c0e18e5be960dd77432542644688acd88317075e"
    try:
        canonical_event_id(source_sha256=sha,sheet="Filtered",original_row=2)
    except ValueError:
        pass
    else:
        raise AssertionError("non-source sheet was admitted")
