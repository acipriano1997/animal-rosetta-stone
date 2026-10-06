import {applyMessages, initializeLocale, number, t} from './i18n.js';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
// Scientific strings are isolated verbatim, outside every localization subtree.
const canonical = (value) => '<bdi data-canonical translate="no" lang="en" dir="auto">' + esc(value) + '</bdi>';
const msg = (key, parameters = {}) => '<span data-i18n="' + esc(key) + '" data-i18n-params="' + esc(JSON.stringify(parameters)) + '">' + esc(t(key, Object.fromEntries(Object.entries(parameters).map(([k,v]) => [k, number(v)])))) + '</span>';
const num = (value) => '<span data-number="' + esc(JSON.stringify(value ?? null)) + '">' + esc(number(value)) + '</span>';
const value = (x) => x == null || x === '' ? msg('common.missing') : canonical(x);
const badge = (x) => '<span class="badge">' + value(x) + '</span>';
const label = (key) => '<strong>' + msg(key) + '</strong> ';
const field = (key, x) => '<p>' + label(key) + value(x) + '</p>';
const heading = (key) => '<h2>' + msg(key) + '</h2>';
const provLink = (id) => '<a href="/api/provenance/' + encodeURIComponent(id) + '" target="_blank" rel="noopener" data-i18n-title="common.new_tab" title="' + esc(t('common.new_tab')) + '">' + canonical(id) + '<span class="sr-only"> · ' + msg('common.new_tab') + '</span></a>';
const prov = (ids) => '<div class="provenance">' + msg('label.provenance') + ' ' + (ids || []).map(provLink).join(' · ') + '</div>';
const card = (titleHTML, body, cls='') => '<article class="card ' + cls + '"><h3>' + titleHTML + '</h3>' + body + '</article>';
const title = (...parts) => parts.map(canonical).join(' · ');
const fieldLabels = Object.freeze({
  context_id: 'field.context_id', initial_goal_anon: 'field.initial_goal_anon', relative_end_s: 'field.relative_end_s',
  relative_start_s: 'field.relative_start_s', source_condition: 'field.source_condition', trigger_or_anchor: 'field.trigger_or_anchor',
  combination_flag: 'field.combination_flag', component_1: 'field.component_1', component_2: 'field.component_2',
  declared_turn_count: 'field.declared_turn_count', exchange_status: 'field.exchange_status', gesture_form: 'field.gesture_form',
  gesture_token_count: 'field.gesture_token_count', order: 'field.order', sender_alternation_count: 'field.sender_alternation_count',
  source_blob_sha: 'field.source_blob_sha', source_communication_id: 'field.source_communication_id', source_file: 'field.source_file',
  source_row: 'field.source_row', source_row_count: 'field.source_row_count', source_row_max: 'field.source_row_max',
  source_row_min: 'field.source_row_min', spreadsheet_id: 'field.spreadsheet_id', sheet: 'field.sheet', range: 'field.range',
});
const keyvals = (obj) => Object.entries(obj || {}).map(([key, x]) => '<div><strong>' +
  (fieldLabels[key] ? msg(fieldLabels[key]) : canonical(key)) + ':</strong> ' + value(x) + '</div>').join('');
const list = (items) => items?.length ? items.map(canonical).join(', ') : msg('common.missing');

let currentSnapshot = null;
const eventState = {
  datasetId: 'D0018',
  population: '',
  split: '',
  offset: 0,
  limit: 12,
  selected: new Set(),
};

async function readJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('HTTP_READ_FAILED');
  return response.json();
}

function motionBehavior() {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';
}

function goToSection(id) {
  const target = document.getElementById(id);
  if (!target) return;
  target.focus({preventScroll: true});
  target.scrollIntoView({behavior: motionBehavior()});
}

function restoreEventStateFromURL() {
  if (typeof URLSearchParams === 'undefined' || typeof location === 'undefined') return;
  const params = new URLSearchParams(location.search);
  eventState.datasetId = params.get('event_dataset') || eventState.datasetId;
  eventState.population = params.get('event_population') || '';
  eventState.split = params.get('event_split') || '';
  const offset = Number(params.get('event_offset') || 0);
  eventState.offset = Number.isInteger(offset) && offset >= 0 ? offset : 0;
  const selected = (params.get('compare') || '').split(',').filter(Boolean).slice(0, 4);
  eventState.selected = new Set(selected);
}

function syncEventURL() {
  if (typeof URL === 'undefined' || typeof location === 'undefined' || typeof history === 'undefined') return;
  const url = new URL(location.href);
  url.searchParams.set('event_dataset', eventState.datasetId);
  if (eventState.population) url.searchParams.set('event_population', eventState.population); else url.searchParams.delete('event_population');
  if (eventState.split) url.searchParams.set('event_split', eventState.split); else url.searchParams.delete('event_split');
  if (eventState.offset) url.searchParams.set('event_offset', String(eventState.offset)); else url.searchParams.delete('event_offset');
  if (eventState.selected.size) url.searchParams.set('compare', [...eventState.selected].join(',')); else url.searchParams.delete('compare');
  history.replaceState(null, '', url);
}

function datasetCard(d, runs, inventory) {
  const runCount = runs.filter((r) => r.dataset_id === d.dataset_id).length;
  const eventCount = inventory[d.dataset_id]?.canonical_total || 0;
  const actions = '<div class="card-actions">' +
    (eventCount ? '<button type="button" data-dataset-events="' + esc(d.dataset_id) + '">' + msg('datasets.open_events') + '</button>' : '') +
    (runCount ? '<button type="button" data-dataset-runs="' + esc(d.dataset_id) + '">' + msg('datasets.open_runs') + '</button>' : '') +
    '</div>';
  return '<article class="card ' + (d.availability === 'GATED_METADATA_ONLY' ? 'blocked' : '') + '" id="dataset-' + esc(d.dataset_id) + '">' +
    '<h3>' + title(d.dataset_id, d.name) + '</h3>' +
    '<p>' + badge(d.role) + badge(d.availability) + badge(d.empirical_state) + '</p>' +
    '<p>' + label('label.scope') + (d.scope ? canonical(d.scope) : msg('common.metadata_only')) + '</p>' +
    field('label.rights', d.rights_state) +
    (d.gate ? field('label.gate', d.gate) : '') +
    (d.known_exposure ? field('label.exposure', d.known_exposure) : '') +
    field('label.authority', d.semantic_authority) + actions + prov(d.provenance_ids) + '</article>';
}

function eventCard(e) {
  const checked = eventState.selected.has(e.event_id) ? ' checked' : '';
  return card(title(e.event_id, e.population_or_group_id),
    '<p>' + badge(e.dataset_id) + badge(e.event_type) + badge(e.split) + '</p>' +
    '<div class="card-actions"><label><input type="checkbox" data-event-select="' + esc(e.event_id) + '"' + checked + '> ' +
    msg('events.select') + ' ' + canonical(e.event_id) + '</label>' +
    '<button type="button" data-open-dataset="' + esc(e.dataset_id) + '">' + msg('events.open_dataset') + '</button></div>' +
    '<p>' + label('label.sender_receiver') + list(e.sender_ids) + ' → ' + list(e.receiver_ids) + '</p>' +
    '<p>' + label('label.context') + '</p><div class="muted">' + keyvals(e.context) + '</div>' +
    '<p>' + label('label.signal') + '</p><div class="muted">' + keyvals(e.signal) + '</div>' +
    field('label.response', e.receiver_response) + field('label.outcome', e.consequence_or_outcome) +
    field('label.confidence', e.event_confidence) +
    '<p>' + label('label.missingness') + (e.missingness_codes?.length ? e.missingness_codes.map(canonical).join(' · ') : msg('common.none_recorded')) + '</p>' +
    '<details><summary>' + msg('label.source') + '</summary><div class="muted">' + keyvals(e.source_locator) + '</div></details>' +
    (e.notes ? field('label.boundary', e.notes) : '') + prov(e.provenance_ids),
    eventState.selected.has(e.event_id) ? 'selected-event' : '');
}

function eventControls(result) {
  const canPrevious = eventState.offset > 0;
  const canNext = eventState.offset + eventState.limit < result.total;
  return '<form class="workspace-controls" data-event-filter-form>' +
    '<label>' + msg('events.filter_population') + '<input name="population" value="' + esc(eventState.population) + '"></label>' +
    '<label>' + msg('events.filter_split') + '<input name="split" value="' + esc(eventState.split) + '"></label>' +
    '<button type="submit">' + msg('events.apply_filters') + '</button>' +
    '<button type="button" data-clear-event-filters>' + msg('events.clear_filters') + '</button>' +
    '</form><p class="muted">' + msg('events.filter_help') + '</p>' +
    '<div class="pagination"><button type="button" data-event-page="-1"' + (canPrevious ? '' : ' disabled') + '>' + msg('events.previous') + '</button>' +
    '<span>' + msg('events.page') + ' ' + num(Math.floor(eventState.offset / eventState.limit) + 1) + '</span>' +
    '<button type="button" data-event-page="1"' + (canNext ? '' : ' disabled') + '>' + msg('events.next') + '</button></div>';
}

function comparisonControls() {
  const count = eventState.selected.size;
  return '<div class="comparison-controls"><p id="event-selection-status" role="status" aria-live="polite">' +
    msg('events.selected_count', {count}) + '</p>' +
    '<button type="button" data-compare-events' + (count >= 2 ? '' : ' disabled') + '>' + msg('events.compare') + '</button>' +
    '<button type="button" data-clear-event-selection' + (count ? '' : ' disabled') + '>' + msg('events.clear_selection') + '</button>' +
    (count < 2 ? '<p class="muted">' + msg('events.compare_help') + '</p>' : '') +
    '<div id="event-comparison" role="status" aria-live="polite"></div></div>';
}

let eventRequest = 0;
async function renderEvents(datasetId, resetOffset = false) {
  const request = ++eventRequest;
  if (datasetId !== eventState.datasetId || resetOffset) eventState.offset = 0;
  eventState.datasetId = datasetId;
  const target = document.querySelector('#event-results');
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = '<p class="muted" role="status">' + canonical(datasetId) + ' · ' + msg('events.loading') + '</p>';
  document.querySelectorAll('[data-event-dataset]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.eventDataset === datasetId)));
  let url = '/api/events?dataset_id=' + encodeURIComponent(datasetId) + '&limit=' + eventState.limit;
  if (eventState.population) url += '&population=' + encodeURIComponent(eventState.population);
  if (eventState.split) url += '&split=' + encodeURIComponent(eventState.split);
  if (eventState.offset) url += '&offset=' + eventState.offset;
  try {
    const result = await readJSON(url);
    if (request !== eventRequest) return;
    const coverage = result.inventory?.[datasetId] || {};
    target.innerHTML = eventControls(result) +
      '<p role="status"><strong>' + canonical(datasetId) + ':</strong> ' +
      msg('events.counts', {shown: result.items.length, total: result.total, canonical: coverage.canonical_total ?? null}) +
      ' · ' + badge(coverage.coverage || 'UNKNOWN_COVERAGE') + '</p>' +
      (result.items.length ? '<div class="grid">' + result.items.map(eventCard).join('') + '</div>' : '<p>' + msg('events.empty') + '</p>') +
      comparisonControls();
    syncEventURL();
  } catch {
    if (request !== eventRequest) return;
    target.innerHTML = '<p role="alert">' + msg('events.error') + '</p>';
  } finally {
    if (request === eventRequest) target.setAttribute('aria-busy', 'false');
  }
}

function comparisonEvent(e) {
  return '<article class="comparison-column"><h4>' + canonical(e.event_id) + '</h4>' +
    field('label.dataset', e.dataset_id) +
    '<p>' + label('label.sender_receiver') + list(e.sender_ids) + ' → ' + list(e.receiver_ids) + '</p>' +
    '<p>' + label('label.context') + '</p><div class="muted">' + keyvals(e.context) + '</div>' +
    '<p>' + label('label.signal') + '</p><div class="muted">' + keyvals(e.signal) + '</div>' +
    field('label.response', e.receiver_response) + field('label.outcome', e.consequence_or_outcome) +
    field('label.confidence', e.event_confidence) +
    '<p>' + label('label.missingness') + (e.missingness_codes?.length ? e.missingness_codes.map(canonical).join(' · ') : msg('common.none_recorded')) + '</p>' +
    prov(e.provenance_ids) + '</article>';
}

async function renderEventComparison() {
  const target = document.querySelector('#event-comparison');
  if (!target) return;
  const ids = [...eventState.selected];
  if (ids.length < 2) {
    target.innerHTML = '<p class="muted">' + msg('events.compare_help') + '</p>';
    return;
  }
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = '<p class="muted">' + msg('events.compare_loading') + '</p>';
  try {
    const items = await Promise.all(ids.map((id) => readJSON('/api/events/' + encodeURIComponent(id))));
    target.innerHTML = '<p class="notice">' + msg('events.compare_boundary') + '</p><div class="comparison-grid">' +
      items.map(comparisonEvent).join('') + '</div>';
  } catch {
    target.innerHTML = '<p role="alert">' + msg('events.compare_error') + '</p>';
  } finally {
    target.setAttribute('aria-busy', 'false');
  }
}

const claimCard = (c) => card(title(c.claim_id, c.claim_type),
  '<p>' + badge(c.status) + badge(c.ars_confidence) + '</p>' +
  field('label.claim', c.claim_short) + field('label.scope', c.scope_boundary) +
  field('label.behavioral', c.behavioral_validation) + field('label.replication', c.independent_replication) +
  field('label.overclaim', c.do_not_overclaim) + field('label.alternatives', c.alternative_explanations) +
  field('label.link_state', c.explicit_link_state) +
  ((c.evidence_links || []).length ? '<details><summary>' + msg('label.links') + '</summary>' + c.evidence_links.map((link) =>
    '<div class="muted"><strong>' + canonical(link.link_id) + ':</strong> ' + canonical(link.evidence_direction) + ' · ' + canonical(link.evidence_channel) +
    field('label.method', link.method_scope) + field('label.independence', link.independence_level) + field('label.basis', link.weight_or_confidence_basis) + prov(link.provenance_ids) + '</div>'
  ).join('') + '</details>' : '') + prov(c.provenance_ids));

const mediaCard = (m) => card(canonical(m.dataset_id) + ' · ' + msg('media.placeholder'),
  '<p>' + badge(m.media_type) + badge(m.availability_status) + '</p>' +
  field('label.rights', m.rights_state) + field('label.bytes', m.bytes_available) + field('label.preview', m.preview_allowed) +
  field('label.consequence', m.scientific_consequence) + field('label.action', m.required_action) +
  '<p class="muted">' + canonical(m.placeholder_message) + '</p>' + prov(m.provenance_ids), 'blocked');

async function renderEvidence() {
  const target = document.querySelector('#evidence');
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = heading('heading.evidence') + '<p class="muted" role="status">' + msg('evidence.loading') + '</p>';
  try {
    const [evidence, media] = await Promise.all([readJSON('/api/evidence/RQ0001'), readJSON('/api/media-placeholders')]);
    const status = evidence.registry_status || {};
    const registry = card(msg('heading.registry'),
      '<p>' + label('evidence.contradiction_count') + num(status.matching_contradiction_rows) + ' · ' +
      label('evidence.disagreement_count') + num(status.matching_disagreement_rows) + '</p>' +
      '<p>' + label('label.interpretation_rule') + (status.absence_rule ? canonical(status.absence_rule) : msg('evidence.unavailable')) + '</p>' +
      field('label.selection_rule', status.selection_rule));
    const corrections = (evidence.corrections || []).length
      ? '<h3>' + msg('heading.corrections') + '</h3><div class="grid">' + evidence.corrections.map((x) => card(canonical(x.record_id),
        '<p>' + badge(x.type) + badge(x.status) + '</p>' + field('label.target', x.target_study_or_claim) +
        field('label.changed', x.what_changed) + field('label.effect', x.effect_on_conclusion) + field('label.ars_action', x.ars_action) + prov(x.provenance_ids))).join('') + '</div>'
      : '<p class="notice"><strong>' + msg('evidence.no_corrections') + '</strong><br>' + canonical(status.absence_rule) + '</p>';
    const disagreements = (evidence.disagreements || []).length
      ? '<h3>' + msg('heading.disagreements') + '</h3><div class="grid">' + evidence.disagreements.map((x) => card(canonical(x.disagreement_id),
        '<p>' + badge(x.status) + badge(x.priority) + '</p>' + field('label.dimension', x.dimension) +
        field('label.position_a', x.position_a) + field('label.position_b', x.position_b) + field('label.evidence_needed', x.evidence_needed) + prov(x.provenance_ids))).join('') + '</div>'
      : '<p class="notice"><strong>' + msg('evidence.no_disagreements') + '</strong><br>' + canonical(status.absence_rule) + '</p>';
    target.innerHTML = heading('heading.evidence') + '<p class="muted">' + msg('evidence.boundary') + '</p>' + registry +
      '<h3>' + msg('heading.claims') + '</h3><div class="grid">' + (evidence.claims?.length ? evidence.claims.map(claimCard).join('') : msg('evidence.no_claims')) + '</div>' +
      corrections + disagreements + '<h3>' + msg('heading.media') + '</h3><div class="grid">' + (media.length ? media.map(mediaCard).join('') : msg('media.empty')) + '</div>';
  } catch {
    target.innerHTML = heading('heading.evidence') + '<p role="alert">' + msg('evidence.error') + '</p>';
  } finally {
    target.setAttribute('aria-busy', 'false');
  }
}

function runCard(r) {
  return card(title(r.run_id, r.dataset_id),
    '<p>' + badge(r.evidence_class) + badge(r.state) + (r.disposition ? badge(r.disposition) : '') + '</p>' +
    (r.metrics ? '<p>' + label('label.metrics') + '<span class="muted">' + keyvals(r.metrics) + '</span></p>' : '') +
    field('label.ceiling', r.interpretation_ceiling || r.gate) +
    '<div class="card-actions"><button type="button" data-inspect-run="' + esc(r.run_id) + '">' + msg('runs.inspect') + '</button>' +
    '<button type="button" data-open-dataset="' + esc(r.dataset_id) + '">' + msg('runs.open_dataset') + '</button></div>' +
    prov(r.provenance_ids), r.state.includes('HELD') ? 'blocked' : '');
}

function renderRuns(s, datasetFilter = null) {
  const target = document.querySelector('#runs');
  const runs = datasetFilter ? s.runs.filter((r) => r.dataset_id === datasetFilter) : s.runs;
  const filtered = datasetFilter
    ? '<p class="notice">' + canonical(datasetFilter) + ' · ' + msg('runs.filtered') +
      ' <button type="button" data-clear-run-filter>' + msg('runs.clear_filter') + '</button></p>'
    : '';
  const empirical = runs.map(runCard).join('');
  const software = s.software_verification.map((v) => card(canonical(v.verification_id) + ' · ' + msg('software.only'),
    '<p>' + badge(v.class) + badge(v.state) + '</p><p>' + canonical(v.result) + '</p>' +
    field('label.biological', v.biological_evidence) + prov(v.provenance_ids))).join('');
  target.innerHTML = heading('heading.runs') + '<p class="muted">' + msg('runs.boundary') + '</p>' + filtered +
    '<div class="grid">' + empirical + '</div><div id="run-inspector" role="status" aria-live="polite"></div>' +
    heading('heading.software') + '<div class="grid">' + software + '</div>';
}

async function renderRunInspector(runId) {
  const target = document.querySelector('#run-inspector');
  if (!target) return;
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = '<p class="muted">' + msg('runs.loading') + '</p>';
  try {
    const run = await readJSON('/api/runs/' + encodeURIComponent(runId));
    const dataset = await readJSON('/api/datasets/' + encodeURIComponent(run.dataset_id));
    target.innerHTML = '<article class="run-inspector card"><h3>' + canonical(run.run_id) + '</h3>' +
      '<p>' + badge(run.evidence_class) + badge(run.state) + (run.disposition ? badge(run.disposition) : '') + '</p>' +
      field('label.dataset', run.dataset_id) + field('label.evidence_class', run.evidence_class) +
      field('label.state', run.state) + field('label.disposition', run.disposition) +
      (run.metrics ? '<p>' + label('label.metrics') + '</p><div class="muted">' + keyvals(run.metrics) + '</div>' : field('label.metrics', null)) +
      field('label.ceiling', run.interpretation_ceiling || run.gate) +
      '<h4>' + msg('runs.optional_fields') + '</h4>' +
      field('label.protocol', run.protocol) + field('label.split', run.split) +
      field('label.controls', run.controls) + field('label.environment', run.environment) +
      field('label.reproducibility', run.reproducibility) +
      '<h4>' + canonical(dataset.dataset_id) + '</h4>' +
      '<p>' + badge(dataset.role) + badge(dataset.availability) + badge(dataset.empirical_state) + '</p>' +
      field('label.rights', dataset.rights_state) + (dataset.gate ? field('label.gate', dataset.gate) : '') +
      '<div class="card-actions"><button type="button" data-open-dataset="' + esc(dataset.dataset_id) + '">' + msg('runs.open_dataset') + '</button></div>' +
      prov(run.provenance_ids) + '</article>';
  } catch {
    target.innerHTML = '<p role="alert">' + msg('runs.error') + '</p>';
  } finally {
    target.setAttribute('aria-busy', 'false');
  }
}

async function loadWorkbench() {
  await initializeLocale();
  restoreEventStateFromURL();
  const s = await readJSON('/api/snapshot');
  currentSnapshot = s;
  document.querySelector('#status').innerHTML = '<strong>' + canonical(s.snapshot_id) + '</strong> · ' + canonical(s.mode) +
    '<br><span class="muted">' + canonical(s.scientific_boundary) + '</span>';

  const sp = s.species;
  document.querySelector('#species').innerHTML = heading('heading.species') + card(title(sp.common_name, sp.taxon),
    '<p>' + badge(sp.activation_state) + badge(sp.comparison_readiness.overall) +
    badge('CRG-C ' + sp.comparison_readiness['CRG-C']) + badge('CRG-D ' + sp.comparison_readiness['CRG-D']) + '</p>' +
    field('label.comparison', sp.comparison_readiness.controlling_reason) +
    field('label.harness', sp.receiver_harness.implementation_state) +
    field('label.empirical', sp.receiver_harness.empirical_exercise_state) +
    '<p>' + label('label.populations') + sp.population_scope.map(canonical).join('; ') + '</p>' + prov(sp.provenance_ids));

  const q = s.question;
  const hypotheses = s.hypotheses.map((h) => card(title(h.hypothesis_id, h.type),
    '<p>' + canonical(h.statement) + '</p>' + field('label.current_scope', h.current_scope) + prov(h.provenance_ids))).join('');
  document.querySelector('#question').innerHTML = '<h2>' + canonical(q.question_id) + '</h2>' +
    card(canonical(q.question_id), '<p>' + canonical(q.text) + '</p>' +
    field('label.discriminator', q.primary_discriminator) + field('label.ethics', q.ethics_boundary) + prov(q.provenance_ids)) +
    '<div class="grid">' + hypotheses + '</div>';

  const inventory = s.event_inventory || {};
  document.querySelector('#datasets').innerHTML = heading('heading.datasets') + '<div class="grid">' +
    s.datasets.map((d) => datasetCard(d, s.runs, inventory)).join('') + '</div>';

  document.querySelector('#events').innerHTML = heading('heading.events') +
    '<p class="muted">' + msg('events.boundary') + '</p>' +
    '<div class="controls"><button type="button" data-event-dataset="D0018" aria-controls="event-results">' +
    canonical('D0018') + ' ' + msg('events.button') + '</button>' +
    '<button type="button" data-event-dataset="D0020" aria-controls="event-results">' +
    canonical('D0020') + ' ' + msg('events.button') + '</button></div>' +
    '<p class="muted">' + canonical('D0018') + ' ' + msg('events.canonical_rows') + ' ' + num(inventory.D0018?.canonical_total) +
    ' · ' + canonical('D0020') + ' ' + msg('events.canonical_rows') + ' ' + num(inventory.D0020?.canonical_total) +
    '</p><div id="event-results"></div>';

  document.querySelectorAll('[data-event-dataset]').forEach((button) =>
    button.addEventListener('click', () => renderEvents(button.dataset.eventDataset, true)));

  renderEvents(eventState.datasetId);
  renderEvidence();
  renderRuns(s);

  document.querySelector('#provenance').innerHTML = heading('heading.provenance') +
    '<p class="muted">' + msg('provenance.help') + '</p><table><thead><tr><th scope="col">' + msg('label.id') +
    '</th><th scope="col">' + msg('label.owner') + '</th><th scope="col">' + msg('label.pointer') +
    '</th></tr></thead><tbody>' +
    Object.entries(s.provenance).map(([id,p]) => '<tr><td>' + provLink(id) + '</td><td>' + canonical(p.authority) +
    '</td><td><code>' + canonical(p.drive_id || p.spreadsheet_id || p.github_repo || '') +
    (p.registry ? ' · ' + canonical(p.registry) : '') + '</code></td></tr>').join('') + '</tbody></table>';

  const eventsSection = document.querySelector('#events');
  eventsSection.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-event-filter-form]');
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    eventState.population = String(data.get('population') || '').trim();
    eventState.split = String(data.get('split') || '').trim();
    eventState.offset = 0;
    renderEvents(eventState.datasetId);
  });
  eventsSection.addEventListener('click', (event) => {
    const page = event.target.closest('[data-event-page]');
    if (page) {
      eventState.offset = Math.max(0, eventState.offset + Number(page.dataset.eventPage) * eventState.limit);
      renderEvents(eventState.datasetId);
      return;
    }
    if (event.target.closest('[data-clear-event-filters]')) {
      eventState.population = '';
      eventState.split = '';
      eventState.offset = 0;
      renderEvents(eventState.datasetId);
      return;
    }
    if (event.target.closest('[data-clear-event-selection]')) {
      eventState.selected.clear();
      renderEvents(eventState.datasetId);
      return;
    }
    if (event.target.closest('[data-compare-events]')) {
      renderEventComparison();
      return;
    }
    const dataset = event.target.closest('[data-open-dataset]');
    if (dataset) goToSection('dataset-' + dataset.dataset.openDataset);
  });
  eventsSection.addEventListener('change', (event) => {
    const control = event.target.closest('[data-event-select]');
    if (!control) return;
    const id = control.dataset.eventSelect;
    if (control.checked) {
      if (eventState.selected.size >= 4 && !eventState.selected.has(id)) {
        control.checked = false;
        const status = document.querySelector('#event-selection-status');
        if (status) status.innerHTML = msg('events.selection_limit');
        return;
      }
      eventState.selected.add(id);
    } else {
      eventState.selected.delete(id);
    }
    syncEventURL();
    renderEvents(eventState.datasetId);
  });

  document.querySelector('#datasets').addEventListener('click', (event) => {
    const eventButton = event.target.closest('[data-dataset-events]');
    if (eventButton) {
      renderEvents(eventButton.dataset.datasetEvents, true);
      goToSection('events');
      return;
    }
    const runButton = event.target.closest('[data-dataset-runs]');
    if (runButton) {
      renderRuns(currentSnapshot, runButton.dataset.datasetRuns);
      goToSection('runs');
    }
  });

  document.querySelector('#runs').addEventListener('click', (event) => {
    const inspect = event.target.closest('[data-inspect-run]');
    if (inspect) {
      renderRunInspector(inspect.dataset.inspectRun);
      return;
    }
    const dataset = event.target.closest('[data-open-dataset]');
    if (dataset) {
      goToSection('dataset-' + dataset.dataset.openDataset);
      return;
    }
    if (event.target.closest('[data-clear-run-filter]')) renderRuns(currentSnapshot);
  });

  applyMessages();
}

loadWorkbench().catch(() => {
  document.querySelector('#status').innerHTML = '<p role="alert">' + msg('app.error') + '</p>';
});

document.querySelectorAll('nav button').forEach((button) => button.addEventListener('click', () => {
  goToSection(button.dataset.target);
}));
