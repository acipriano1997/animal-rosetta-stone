const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const badge = (x) => '<span class="badge">' + esc(x) + '</span>';
const prov = (ids) => '<div class="provenance">Provenance: ' + (ids || []).map((id) =>
  '<a href="/api/provenance/' + encodeURIComponent(id) + '" target="_blank" rel="noopener">' + esc(id) + '</a>'
).join(' · ') + '</div>';
const card = (title, body, cls='') => '<article class="card ' + cls + '"><h3>' + esc(title) + '</h3>' + body + '</article>';
const keyvals = (obj) => Object.entries(obj || {}).filter(([,v]) => v !== '' && v != null)
  .map(([k,v]) => '<div><strong>' + esc(k.replaceAll('_',' ')) + ':</strong> ' + esc(v) + '</div>').join('');

const eventCard = (e) => card(
  e.event_id + ' · ' + e.population_or_group_id,
  '<p>' + badge(e.dataset_id) + badge(e.event_type) + badge(e.split) + '</p>' +
  '<p><strong>Sender → receiver:</strong> ' + esc((e.sender_ids || []).join(', ') || 'MISSING') + ' → ' + esc((e.receiver_ids || []).join(', ') || 'MISSING') + '</p>' +
  '<p><strong>Context:</strong></p><div class="muted">' + keyvals(e.context) + '</div>' +
  '<p><strong>Signal / interaction structure:</strong></p><div class="muted">' + keyvals(e.signal) + '</div>' +
  '<p><strong>Receiver response:</strong> ' + esc(e.receiver_response || 'MISSING') + '</p>' +
  '<p><strong>Outcome:</strong> ' + esc(e.consequence_or_outcome || 'MISSING') + '</p>' +
  '<p><strong>Missingness:</strong> ' + esc((e.missingness_codes || []).join(' · ') || 'none recorded') + '</p>' +
  '<details><summary>Source locator</summary><div class="muted">' + keyvals(e.source_locator) + '</div></details>' +
  (e.notes ? '<p class="muted"><strong>Boundary:</strong> ' + esc(e.notes) + '</p>' : '') +
  prov(e.provenance_ids)
);

const renderEvents = (datasetId) => {
  const target = document.querySelector('#event-results');
  target.innerHTML = '<p class="muted">Loading ' + esc(datasetId) + ' events…</p>';
  fetch('/api/events?dataset_id=' + encodeURIComponent(datasetId) + '&limit=12').then((r) => r.json()).then((result) => {
    const coverage = result.inventory?.[datasetId] || {};
    target.innerHTML =
      '<p><strong>' + esc(datasetId) + ':</strong> showing ' + result.items.length + ' of ' + result.total +
      ' available rows in this source · canonical total ' + esc(coverage.canonical_total ?? 'unknown') +
      ' · ' + badge(coverage.coverage || 'UNKNOWN_COVERAGE') + '</p>' +
      '<div class="grid">' + result.items.map(eventCard).join('') + '</div>';
  }).catch((err) => {
    target.textContent = 'Failed to load events: ' + err;
  });
};

fetch('/api/snapshot').then((r) => r.json()).then((s) => {
  document.querySelector('#status').innerHTML = '<strong>' + esc(s.snapshot_id) + '</strong> · ' + esc(s.mode) + '<br><span class="muted">' + esc(s.scientific_boundary) + '</span>';
  const sp = s.species;
  document.querySelector('#species').innerHTML = '<h2>Species landing</h2>' + card(sp.common_name + ' · ' + sp.taxon,
    '<p>' + badge(sp.activation_state) + badge(sp.comparison_readiness.overall) + badge('CRG-C ' + sp.comparison_readiness['CRG-C']) + badge('CRG-D ' + sp.comparison_readiness['CRG-D']) + '</p>' +
    '<p><strong>Comparison gate:</strong> ' + esc(sp.comparison_readiness.controlling_reason) + '</p>' +
    '<p><strong>Receiver harness:</strong> ' + esc(sp.receiver_harness.implementation_state) + ' · empirical exercise ' + esc(sp.receiver_harness.empirical_exercise_state) + '</p>' +
    '<p><strong>Populations:</strong> ' + sp.population_scope.map(esc).join('; ') + '</p>' + prov(sp.provenance_ids));

  const q = s.question;
  const hypotheses = s.hypotheses.map((h) => card(h.hypothesis_id + ' · ' + h.type,
    '<p>' + esc(h.statement) + '</p><p class="muted"><strong>Current scope:</strong> ' + esc(h.current_scope) + '</p>' + prov(h.provenance_ids))).join('');
  document.querySelector('#question').innerHTML = '<h2>RQ0001</h2>' + card(q.question_id,
    '<p>' + esc(q.text) + '</p><p><strong>Primary discriminator:</strong> ' + esc(q.primary_discriminator) + '</p><p><strong>Ethics boundary:</strong> ' + esc(q.ethics_boundary) + '</p>' + prov(q.provenance_ids)) + '<div class="grid">' + hypotheses + '</div>';

  document.querySelector('#datasets').innerHTML = '<h2>Corpora</h2><div class="grid">' + s.datasets.map((d) => card(d.dataset_id + ' · ' + d.name,
    '<p>' + badge(d.role) + badge(d.availability) + badge(d.empirical_state) + '</p>' +
    '<p><strong>Scope:</strong> ' + esc(d.scope || 'Metadata-only; see gate.') + '</p>' +
    '<p><strong>Rights:</strong> ' + esc(d.rights_state) + '</p>' +
    (d.gate ? '<p><strong>Gate:</strong> ' + esc(d.gate) + '</p>' : '') +
    (d.known_exposure ? '<p><strong>Known exposure:</strong> ' + esc(d.known_exposure) + '</p>' : '') +
    '<p><strong>Semantic authority:</strong> ' + esc(d.semantic_authority) + '</p>' + prov(d.provenance_ids),
    d.availability === 'GATED_METADATA_ONLY' ? 'blocked' : '')).join('') + '</div>';

  const inventory = s.event_inventory || {};
  document.querySelector('#events').innerHTML =
    '<h2>Situated event explorer</h2>' +
    '<p class="muted">Source-preserved event fields only. Missing fields remain missing; anonymized goal codes are not meanings.</p>' +
    '<div class="controls"><button data-event-dataset="D0018">D0018 events</button><button data-event-dataset="D0020">D0020 events</button></div>' +
    '<p class="muted">D0018 canonical rows: ' + esc(inventory.D0018?.canonical_total ?? 'unknown') +
    ' · D0020 canonical rows: ' + esc(inventory.D0020?.canonical_total ?? 'unknown') + '</p>' +
    '<div id="event-results"></div>';

  document.querySelectorAll('[data-event-dataset]').forEach((btn) => btn.addEventListener('click', () => renderEvents(btn.dataset.eventDataset)));
  renderEvents('D0018');

  const empirical = s.runs.map((r) => card(r.run_id + ' · ' + r.dataset_id,
    '<p>' + badge(r.evidence_class) + badge(r.state) + (r.disposition ? badge(r.disposition) : '') + '</p>' +
    (r.metrics ? '<p><strong>Metrics:</strong> B0 ' + r.metrics.B0_log_loss + '; B1 ' + r.metrics.B1_log_loss + '; Δ ' + r.metrics.delta_log_loss + '</p>' : '') +
    '<p><strong>Interpretation ceiling:</strong> ' + esc(r.interpretation_ceiling || r.gate) + '</p>' + prov(r.provenance_ids),
    r.state.includes('HELD') ? 'blocked' : '')).join('');
  const software = s.software_verification.map((v) => card(v.verification_id + ' · software verification only',
    '<p>' + badge(v.class) + badge(v.state) + '</p><p>' + esc(v.result) + '</p><p><strong>Biological evidence:</strong> ' + esc(v.biological_evidence) + '</p>' + prov(v.provenance_ids))).join('');
  document.querySelector('#runs').innerHTML = '<h2>Empirical / planned runs</h2><div class="grid">' + empirical + '</div><h2>Software verification — segregated</h2><div class="grid">' + software + '</div>';

  document.querySelector('#provenance').innerHTML = '<h2>Core provenance index</h2><p class="muted">Event-level provenance is resolved on demand from each event card.</p><table><thead><tr><th>ID</th><th>Authority</th><th>Pointer</th></tr></thead><tbody>' +
    Object.entries(s.provenance).map(([id,p]) => '<tr><td><a href="/api/provenance/' + encodeURIComponent(id) + '" target="_blank" rel="noopener">' + esc(id) + '</a></td><td>' + esc(p.authority) + '</td><td><code>' + esc(p.drive_id || p.spreadsheet_id || p.github_repo || '') + (p.registry ? ' · ' + esc(p.registry) : '') + '</code></td></tr>').join('') + '</tbody></table>';
}).catch((err) => { document.querySelector('#status').textContent = 'Failed to load Workbench state: ' + err; });

document.querySelectorAll('nav button').forEach((btn) => btn.addEventListener('click', () => {
  document.getElementById(btn.dataset.target).scrollIntoView({behavior:'smooth'});
}));
