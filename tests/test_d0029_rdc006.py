"""Offline v4 admission firewall and descriptive provenance checks."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import audit_d0029_rdc006 as audit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'contracts/d0029_version_history_source_snapshot.json'
RECEIPT = ROOT / 'contracts/d0029_rdc006_v4_crosswalk.json'


def receipt():
    return json.loads(RECEIPT.read_text())


def row(n, **values):
    return {'_source_row': n, **values}


def timed(n, begin, end):
    r = row(n)
    for prefix, value in zip(('Begin Time', 'End Time', 'Duration'), (begin, end, end - begin)):
        r[prefix + ' - msec'] = str(value)
        r[prefix + ' - ss.msec'] = str(value / 1000)
        hours, remainder = divmod(value, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, ms = divmod(remainder, 1000)
        r[prefix + ' - hh:mm:ss.ms'] = f'{hours:02}:{minutes:02}:{seconds:02}.{ms:03}'
    return r


def test_frozen_source_and_every_inventory_hash_remain_v4_only():
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == audit.SNAPSHOT_SHA256
    original, frozen = json.loads(SNAPSHOT.read_text()), receipt()
    source = frozen['active_source']
    assert (source['item_id'], source['version'], source['file_id']) == (16910173, 4, 36230763)
    v4 = next(x for x in original['scientific_files'] if x['metadata_as_reported']['id'] == 36230763)
    assert source['sha256'] == v4['sha256'] and source['md5'] == v4['md5']
    assert source['file_licence_as_reported'] is None
    assert source['item_licence_as_reported'] == v4['associations'][0]['item_license_as_reported']
    pins = {x['path']: x for x in original['archive_members']['36230763'] if x['role'] == 'SOURCE_MEMBER'}
    assert len(pins) == len(frozen['source_inventory']) == 19
    for f in frozen['source_inventory']:
        assert all(f[k] == pins[f['member']][k] for k in ('sha256', 'md5', 'size'))
    assert len(frozen['rdc006_field_crosswalk']) == 20


def test_historical_association_and_corrupt_v4_bytes_fail_before_inspection():
    original = json.loads(SNAPSHOT.read_text())
    wrong = deepcopy(original)
    f = next(x for x in wrong['scientific_files'] if x['metadata_as_reported']['id'] == audit.ARCHIVE_ID)
    f['associations'][0]['version'] = 3
    with pytest.raises(ValueError, match='exclusively'):
        audit.load_v4(wrong, b'not opened')
    with pytest.raises(ValueError):
        audit.load_v4(original, b'corrupt')


def test_join_retains_both_directions_nonidentical_duplicate_and_metadata_difference():
    left = [row(2, ID='a', value='old'), row(3, ID='b', value='b')]
    right = [row(5, ID='a', value='old'), row(6, ID='a', value='changed'), row(7, ID='c', value='c')]
    result = audit.join_diagnostics(left, right, ['ID'], ['value'])
    assert result['multiplicity_pairs'] == {'1:2': 1}
    assert result['left_unmatched'] == [{'key': {'ID': 'b'}, 'source_rows': [3]}]
    assert result['right_unmatched'] == [{'key': {'ID': 'c'}, 'source_rows': [7]}]
    assert result['right_profile']['duplicate_keys'][0]['source_values_identical_excluding_locator'] is False
    assert result['metadata_mismatches'][0]['right_source_row'] == 6
    assert result['keys_repaired'] is False
    assert result == audit.join_diagnostics(left, right, ['ID'], ['value'])


def test_missing_keys_are_not_silently_joined():
    result = audit.join_diagnostics([row(2, ID='NA')], [row(3, ID='NA')], ['ID'])
    assert result['intersection_unique_keys'] == 0
    assert result['left_profile']['missing_key_source_rows'] == [2]
    assert result['right_profile']['missing_key_source_rows'] == [3]


@pytest.mark.parametrize('event_start,expected', [
    (1, 'BEFORE_DISPLAY_START'), (10, 'TIED_DISPLAY_START'),
    (15, 'DURING_ONGOING_DISPLAY'), (20, 'TIED_DISPLAY_END'), (21, 'AFTER_DISPLAY_COMPLETION'),
])
def test_receiver_annotation_order_preserves_ties(event_start, expected):
    assert audit.receiver_display_relation(timed(2, event_start, event_start + 1), timed(3, 10, 20)) == expected


def test_invalid_times_and_redundant_unit_disagreement_are_held():
    missing = timed(2, 100, 200)
    missing['Begin Time - msec'] = ''
    reversed_time = timed(3, 200, 100)
    inconsistent = timed(4, 100, 200)
    inconsistent['Begin Time - ss.msec'] = '100'
    result = audit.time_quality([missing, reversed_time, inconsistent])
    assert result['counts']['missing_or_invalid_ms_rows'] == 1
    assert result['counts']['negative_or_reversed_interval_rows'] == 1
    assert len(result['anomalies']) == 3
    assert audit.receiver_display_relation(missing, timed(5, 10, 20)) == 'INVALID_INTERVAL_HELD'
    wrong_duration = timed(6, 10, 20)
    wrong_duration['Duration - msec'] = '11'
    assert audit.receiver_display_relation(wrong_duration, timed(5, 10, 20)) == 'INVALID_INTERVAL_HELD'


def test_same_file_bout_tiers_are_not_joined_by_order_or_filled():
    raw = [timed(2, 10, 20) | {'File': 'PC1_AA_01.01.11.eaf', audit.RAW_BOUT: '1'},
           timed(3, 11, 20) | {'File': 'PC1_AA_01.01.11.eaf', 'Post_bout_event': 'Consolation'},
           timed(4, 20, 21) | {'_unheaded_column_45': 'orphan.eaf'},
           timed(5, 30, 40) | {'File': 'PC1_AA_01.01.11.eaf', 'Gesture': 'A'},
           timed(6, 30, 40) | {'File': 'PC1_AA_01.01.11.eaf', 'Gesture': 'B'}]
    result, _ = audit.raw_structure(raw, [])
    link = result['exact_interval_bout_tier_joins']['Post_bout_event']
    assert link['intersection_unique_keys'] == 0
    assert len(link['left_unmatched']) == len(link['right_unmatched']) == 1
    assert result['orphan_file_annotations'][0]['source_row'] == 4
    assert result['annotation_file_tier_interval_profile']['duplicate_keys'][0]['source_values_identical_excluding_locator'] is False


@pytest.mark.parametrize('field', sorted(audit.DOWNSTREAM | audit.OUTCOME_DERIVED | audit.OUTCOMES))
def test_downstream_and_outcomes_cannot_be_reclassified_even_when_not_selected(field):
    with pytest.raises(ValueError):
        audit.validate_eligibility({'source_field': field, 'classification': 'BASELINE_STATIC', 'baseline_eligible': False})


def test_baseline_selection_requires_endpoint_proof_and_is_forbidden_for_timing_held_class():
    for cls in ['UNKNOWN_TIMING_HELD', 'TIMING_DEPENDENT_REQUIRES_EVENT_ORDER', 'BASELINE_STATIC']:
        with pytest.raises(ValueError):
            audit.validate_eligibility({'source_field': 'candidate', 'classification': cls, 'baseline_eligible': True})
    assert audit.classification('Total_signals')[0] == 'TIMING_DEPENDENT_REQUIRES_EVENT_ORDER'
    assert audit.classification('Display_duration(s)')[0] == 'TIMING_DEPENDENT_REQUIRES_EVENT_ORDER'
    assert audit.classification('Piloerection_display')[0] == 'UNKNOWN_TIMING_HELD'
    assert audit.classification('Victim')[0] == 'IDENTITY_OR_CLUSTERING_ONLY'


def test_frozen_real_cardinalities_and_exact_anomalies_remain_auditable():
    p = receipt()
    c, joins = p['cardinality_reconciliation'], p['relational_crosswalk']
    assert [c[k] for k in ('display_rows', 'unique_display_conflicts', 'main_bout_rows', 'persistence_rows',
                           'unique_persistence_bout_keys', 'audience_model_candidate_complete_rows')] == [144, 144, 325, 329, 328, 142]
    assert c['display_Total_bouts_sum'] == 326
    assert [r['source_key']['Bout_number'] for r in c['unmatched_persistence_rows']] == ['4', '5', '6', '7']
    assert all(r['source_key']['PC_ID'] == '101' for r in c['unmatched_persistence_rows'])
    dup = c['duplicate_persistence_keys'][0]
    assert dup['source_key'] == {'Study_group': '1', 'Study_year': '2011', 'PC_ID': '66', 'Bout_number': '2'}
    assert dup['source_rows'] == [285, 286] and dup['identical_on_named_fields'] is False
    assert joins['main_bout_to_persistence']['left_unmatched'][0]['key']['Bout_number'] == '6'
    assert len(joins['main_bout_to_persistence']['metadata_mismatches']) == 7
    assert {r['key']['PC_ID'] for r in c['audience_missing_records']} == {'61', '156'}
    for model in c['audience_model_completeness'].values():
        assert model['descriptive_complete_row_count'] == 142
        assert 'N_dominants_within10m' not in model['required_formula_fields']
    assert p['six_exclusions']['all_six_source_reproducible'] is False
    assert p['six_exclusions']['unlocated_record_keys'] is None
    assert p['six_exclusions']['unlocated_excluded_record_count'] == 5


def test_static_code_inspection_keeps_hostile_source_inert_and_probe_has_no_execution_transport(tmp_path):
    target = tmp_path / 'must_not_exist'
    raw = f'system("touch {target}")\nlibrary(brms)\nread.table("input.txt")\n'.encode()
    result = audit.code_crosswalk(raw)
    assert result['executed'] is False and not target.exists()
    assert result['sections']['loading'][0]['line_start'] == 3
    tree = ast.parse(Path(audit.__file__).read_text())
    forbidden = {'subprocess', 'socket', 'requests', 'urllib', 'rpy2'}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
            assert not any(m.split('.')[0] in forbidden for m in modules)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {'eval', 'exec', 'compile'}


def test_frozen_firewall_allows_no_baseline_selection_and_preserves_provenance_roles():
    p = receipt()
    assert p['state'] == audit.HELD and p['admission']['granted'] is False
    for entry in p['variable_eligibility']:
        audit.validate_eligibility(entry)
        assert entry['baseline_eligible'] is False
    assert p['provenance_corrections']['R0011']['role'] != p['provenance_corrections']['R0012']['role']
    assert p['provenance_corrections']['R0011']['history_mutated'] is False
    assert p['firewall']['EMPIRICAL_CONFIRMATORY_RUN'] == 'NOT_STARTED'
    assert p['firewall']['SEMANTIC_COMPOSITIONALITY'] == 'CONTESTED_UNRESOLVED'
    for field in ('deposited_statistical_code_executed', 'inferential_models_executed', 'historical_analysis_bytes_used'):
        assert p['firewall'][field] is False
    t = p['temporal_coverage']
    assert t['all_annotation_time_quality']['counts']['all_redundant_units_and_interval_identity_valid_rows'] == 9051
    assert t['receiver_display_start_relations'] == {'AFTER_DISPLAY_COMPLETION': 108, 'DURING_ONGOING_DISPLAY': 176, 'TIED_DISPLAY_END': 3}
    assert t['coverage']['conflicts_with_verified_conflict_end_timestamp'] == 0


def test_cached_v4_regenerates_frozen_receipt_exactly_when_available():
    archive = ROOT / 'build/d0029_source_history/36230763/Data and R code.zip'
    if not archive.is_file():
        pytest.skip('Research bytes intentionally outside Git; offline frozen and synthetic tests still run')
    regenerated = audit.audit(json.loads(SNAPSHOT.read_text()), archive.read_bytes())
    assert regenerated == receipt()
