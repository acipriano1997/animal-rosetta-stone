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

async function readJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('HTTP_READ_FAILED');
  return response.json();
}

const eventCard = (e) => card(title(e.event_id, e.population_or_group_id),
  '<p>' + badge(e.dataset_id) + badge(e.event_type) + badge(e.split) + '</p>' +
  '<p>' + label('label.sender_receiver') + list(e.sender_ids) + ' → ' + list(e.receiver_ids) + '</p>' +
  '<p>' + label('label.context') + '</p><div class="muted">' + keyvals(e.context) + '</div>' +
  '<p>' + label('label.signal') + '</p><div class="muted">' + keyvals(e.signal) + '</div>' +
  field('label.response', e.receiver_response) + field('label.outcome', e.consequence_or_outcome) +
  field('label.confidence', e.event_confidence) +
  '<p>' + label('label.missingness') + (e.missingness_codes?.length ? e.missingness_codes.map(canonical).join(' · ') : msg('common.none_recorded')) + '</p>' +
  '<details><summary>' + msg('label.source') + '</summary><div class="muted">' + keyvals(e.source_locator) + '</div></details>' +
  (e.notes ? field('label.boundary', e.notes) : '') + prov(e.provenance_ids));

let eventRequest = 0;
async function renderEvents(datasetId) {
  const request = ++eventRequest;
  const target = document.querySelector('#event-results');
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = '<p class="muted" role="status">' + canonical(datasetId) + ' · ' + msg('events.loading') + '</p>';
  document.querySelectorAll('[data-event-dataset]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.eventDataset === datasetId)));
  try {
    const result = await readJSON('/api/events?dataset_id=' + encodeURIComponent(datasetId) + '&limit=12');
    if (request !== eventRequest) return;
    const coverage = result.inventory?.[datasetId] || {};
    target.innerHTML = '<p role="status"><strong>' + canonical(datasetId) + ':</strong> ' +
      msg('events.counts', {shown: result.items.length, total: result.total, canonical: coverage.canonical_total ?? null}) +
      ' · ' + badge(coverage.coverage || 'UNKNOWN_COVERAGE') + '</p>' + (result.items.length ? '<div class="grid">' + result.items.map(eventCard).join('') + '</div>' : '<p>' + msg('events.empty') + '</p>');
  } catch {
    if (request !== eventRequest) return;
    target.innerHTML = '<p role="alert">' + msg('events.error') + '</p>';
  } finally {
    if (request === eventRequest) target.setAttribute('aria-busy', 'false');
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

async function loadWorkbench() {
  await initializeLocale();
  const s = await readJSON('/api/snapshot');
  document.querySelector('#status').innerHTML = '<strong>' + canonical(s.snapshot_id) + '</strong> · ' + canonical(s.mode) + '<br><span class="muted">' + canonical(s.scientific_boundary) + '</span>';
  const sp = s.species;
  document.querySelector('#species').innerHTML = heading('heading.species') + card(title(sp.common_name, sp.taxon),
    '<p>' + badge(sp.activation_state) + badge(sp.comparison_readiness.overall) + badge('CRG-C ' + sp.comparison_readiness['CRG-C']) + badge('CRG-D ' + sp.comparison_readiness['CRG-D']) + '</p>' +
    field('label.comparison', sp.comparison_readiness.controlling_reason) + field('label.harness', sp.receiver_harness.implementation_state) +
    field('label.empirical', sp.receiver_harness.empirical_exercise_state) + '<p>' + label('label.populations') + sp.population_scope.map(canonical).join('; ') + '</p>' + prov(sp.provenance_ids));
  const q = s.question;
  const hypotheses = s.hypotheses.map((h) => card(title(h.hypothesis_id, h.type),
    '<p>' + canonical(h.statement) + '</p>' + field('label.current_scope', h.current_scope) + prov(h.provenance_ids))).join('');
  document.querySelector('#question').innerHTML = '<h2>' + canonical(q.question_id) + '</h2>' + card(canonical(q.question_id),
    '<p>' + canonical(q.text) + '</p>' + field('label.discriminator', q.primary_discriminator) + field('label.ethics', q.ethics_boundary) + prov(q.provenance_ids)) + '<div class="grid">' + hypotheses + '</div>';
  document.querySelector('#datasets').innerHTML = heading('heading.datasets') + '<div class="grid">' + s.datasets.map((d) => card(title(d.dataset_id, d.name),
    '<p>' + badge(d.role) + badge(d.availability) + badge(d.empirical_state) + '</p>' +
    '<p>' + label('label.scope') + (d.scope ? canonical(d.scope) : msg('common.metadata_only')) + '</p>' + field('label.rights', d.rights_state) +
    (d.gate ? field('label.gate', d.gate) : '') + (d.known_exposure ? field('label.exposure', d.known_exposure) : '') +
    field('label.authority', d.semantic_authority) + prov(d.provenance_ids), d.availability === 'GATED_METADATA_ONLY' ? 'blocked' : '')).join('') + '</div>';
  const inventory = s.event_inventory || {};
  document.querySelector('#events').innerHTML = heading('heading.events') + '<p class="muted">' + msg('events.boundary') + '</p>' +
    '<div class="controls"><button data-event-dataset="D0018" aria-controls="event-results">' + canonical('D0018') + ' ' + msg('events.button') + '</button><button data-event-dataset="D0020" aria-controls="event-results">' + canonical('D0020') + ' ' + msg('events.button') + '</button></div>' +
    '<p class="muted">' + canonical('D0018') + ' ' + msg('events.canonical_rows') + ' ' + num(inventory.D0018?.canonical_total) +
    ' · ' + canonical('D0020') + ' ' + msg('events.canonical_rows') + ' ' + num(inventory.D0020?.canonical_total) + '</p><div id="event-results"></div>';
  document.querySelectorAll('[data-event-dataset]').forEach((button) => button.addEventListener('click', () => renderEvents(button.dataset.eventDataset)));
  renderEvents('D0018');
  renderEvidence();
  const empirical = s.runs.map((r) => card(title(r.run_id, r.dataset_id),
    '<p>' + badge(r.evidence_class) + badge(r.state) + (r.disposition ? badge(r.disposition) : '') + '</p>' +
    (r.metrics ? '<p>' + label('label.metrics') + canonical('B0 ' + r.metrics.B0_log_loss + '; B1 ' + r.metrics.B1_log_loss + '; Δ ' + r.metrics.delta_log_loss) + '</p>' : '') +
    field('label.ceiling', r.interpretation_ceiling || r.gate) + prov(r.provenance_ids), r.state.includes('HELD') ? 'blocked' : '')).join('');
  // ZERO_SYNTHETIC software verification stays separate from empirical runs.
  const software = s.software_verification.map((v) => card(canonical(v.verification_id) + ' · ' + msg('software.only'),
    '<p>' + badge(v.class) + badge(v.state) + '</p><p>' + canonical(v.result) + '</p>' + field('label.biological', v.biological_evidence) + prov(v.provenance_ids))).join('');
  document.querySelector('#runs').innerHTML = heading('heading.runs') + '<div class="grid">' + empirical + '</div>' + heading('heading.software') + '<div class="grid">' + software + '</div>';
  document.querySelector('#provenance').innerHTML = heading('heading.provenance') + '<p class="muted">' + msg('provenance.help') + '</p><table><thead><tr><th scope="col">' + msg('label.id') + '</th><th scope="col">' + msg('label.owner') + '</th><th scope="col">' + msg('label.pointer') + '</th></tr></thead><tbody>' +
    Object.entries(s.provenance).map(([id,p]) => '<tr><td>' + provLink(id) + '</td><td>' + canonical(p.authority) + '</td><td><code>' + canonical(p.drive_id || p.spreadsheet_id || p.github_repo || '') + (p.registry ? ' · ' + canonical(p.registry) : '') + '</code></td></tr>').join('') + '</tbody></table>';
  applyMessages();
}
loadWorkbench().catch(() => { document.querySelector('#status').innerHTML = '<p role="alert">' + msg('app.error') + '</p>'; });

document.querySelectorAll('nav button').forEach((button) => button.addEventListener('click', () => {
  const target = document.getElementById(button.dataset.target);
  target.focus({preventScroll: true});
  target.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
}));
