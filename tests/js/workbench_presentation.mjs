// Socket-free tests of the actual ES modules. These DOM doubles test behavior,
// not browser layout or assistive-technology rendering.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createContext, SourceTextModule} from 'node:vm';

const input = JSON.parse(readFileSync(0, 'utf8'));
const source = (name) => readFileSync(new URL(`../../src/ars_workbench/static/${name}`, import.meta.url), 'utf8');
const en = JSON.parse(source('locales/en.json'));
const xa = JSON.parse(source('locales/en-XA.json'));
const freeze = (value) => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};
freeze(input);

class Element {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.attributes = {};
    this.textContent = '';
    this.innerHTML = '';
    this.listeners = {};
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  closest() { return this.canonicalAncestor ? this : null; }
  querySelector() { return this.canonicalChild ? this : null; }
  focus(options) { this.focusOptions = options; this.focused = true; }
  scrollIntoView(options) { this.scrollOptions = options; }
}

async function runtime({saved = null, storageFails = false, fetchCatalog, reducedMotion = true, fastTimeout = false} = {}) {
  const nodes = Object.fromEntries([
    'presentation-messages', 'presentation-locale', 'locale-status', 'status',
    'species', 'question', 'datasets', 'events', 'event-results', 'evidence', 'runs', 'provenance',
  ].map((id) => [id, new Element()]));
  nodes['presentation-messages'].textContent = JSON.stringify(en);
  const chrome = new Element({i18n: 'app.title'});
  const parameter = new Element({i18n: 'events.counts', i18nParams: '{"shown":0,"total":4223,"canonical":4223}'});
  const aria = new Element({i18nAria: 'nav.label'});
  const title = new Element({i18nTitle: 'common.new_tab'});
  const numeric = new Element({number: '4223'});
  const protectedNodes = ['self', 'ancestor', 'child'].map((kind) => {
    const node = new Element({i18n: 'app.title', i18nAria: 'app.title', number: '12'});
    node.textContent = 'NOT_PASS · Pan troglodytes · “原文”';
    node.canonicalAncestor = kind !== 'child';
    node.canonicalChild = kind === 'child';
    return node;
  });
  const nav = new Element({target: 'evidence'});
  const eventButtons = ['D0018', 'D0020'].map((id) => new Element({eventDataset: id}));
  const document = {
    documentElement: new Element(),
    activeElement: nodes['presentation-locale'],
    getElementById: (id) => nodes[id],
    querySelector: (selector) => nodes[selector.slice(1)],
    querySelectorAll: (selector) => ({
      '[data-i18n]': [chrome, parameter, ...protectedNodes],
      '[data-i18n-aria]': [aria, ...protectedNodes],
      '[data-i18n-title]': [title],
      '[data-number]': [numeric, ...protectedNodes],
      'nav button': [nav],
      '[data-event-dataset]': eventButtons,
    })[selector] || [],
  };
  const calls = [];
  const storage = new Map(saved ? [['ars.workbench.presentationLocale', saved]] : []);
  const context = createContext({
    document, Intl, AbortController,
    setTimeout: fastTimeout ? (fn) => setTimeout(fn, 0) : setTimeout,
    clearTimeout,
    matchMedia: () => ({matches: reducedMotion}),
    localStorage: {
      getItem(key) { if (storageFails) throw new Error('storage unavailable'); return storage.get(key); },
      setItem(key, value) { if (storageFails) throw new Error('storage unavailable'); storage.set(key, value); },
    },
    fetch: async (url, options) => {
      calls.push(url);
      if (url === '/locales/en-XA.json') return fetchCatalog ? fetchCatalog(options) : {ok: true, json: async () => xa};
      assert.ok(Object.hasOwn(input.responses, url), `Unexpected request: ${url}`);
      return {ok: true, json: async () => input.responses[url]};
    },
  });
  const i18n = new SourceTextModule(source('i18n.js'), {context});
  await i18n.link(() => { throw new Error('Unexpected i18n import'); });
  await i18n.evaluate();
  const api = i18n.namespace;
  return {
    api, nodes, chrome, parameter, aria, title, numeric, protectedNodes,
    document, calls, storage, nav, eventButtons,
    async load() {
      const app = new SourceTextModule(source('app.js'), {context});
      await app.link((specifier) => { assert.equal(specifier, './i18n.js'); return i18n; });
      await app.evaluate();
      await new Promise(setImmediate);
    },
  };
}

const checks = [];
async function check(name, fn) { await fn(); checks.push(name); }

await check('default, allowlist, placeholder validation and unsupported fallback', async () => {
  const {api} = await runtime();
  for (const requested of [undefined, null, '', 'fr', 'ar', 'en-US', '../en-XA', '__proto__']) {
    assert.equal(api.resolveLocale(requested), 'en');
  }
  assert.equal(api.resolveLocale('EN-xa'), 'en-XA');
  assert.equal(api.LOCALES['en-XA'].testOnly, true);
  assert.equal(api.catalogMessage({en, fr: {'app.title': 'unexpected'}}, 'fr', 'app.title'), en['app.title']);
  assert.equal(api.catalogMessage({en, 'en-XA': {}}, 'en-XA', 'app.title'), `⟦MISSING: app.title⟧ ${en['app.title']}`);
  assert.match(api.catalogMessage({en, 'en-XA': {'events.counts': 'wrong {name}'}}, 'en-XA', 'events.counts'), /^⟦MISSING:/);
  assert.equal(api.catalogMessage({en}, 'en', 'unknown.key'), '⟦MISSING: unknown.key⟧');
});

await check('document language, direction, persistence, focus and protected DOM', async () => {
  const r = await runtime({saved: 'en-XA'});
  await r.api.initializeLocale();
  assert.equal(r.api.currentLocale(), 'en-XA');
  assert.equal(r.document.documentElement.lang, 'en-XA');
  assert.equal(r.document.documentElement.dir, 'ltr');
  assert.equal(r.document.documentElement.dataset.pseudolocale, 'true');
  assert.equal(r.chrome.textContent, xa['app.title']);
  assert.equal(r.aria.attributes['aria-label'], xa['nav.label']);
  assert.equal(r.title.attributes.title, xa['common.new_tab']);
  assert.equal(r.numeric.textContent, '4,223');
  assert.ok(!r.parameter.textContent.includes('MISSING'));
  for (const node of r.protectedNodes) {
    assert.equal(node.textContent, 'NOT_PASS · Pan troglodytes · “原文”');
    assert.deepEqual(node.attributes, {});
  }
  await r.nodes['presentation-locale'].listeners.change({target: {value: 'en'}});
  assert.equal(r.document.documentElement.lang, 'en');
  assert.equal(r.document.documentElement.dir, 'ltr');
  assert.equal(r.storage.get(r.api.STORAGE_KEY), 'en');
  assert.equal(r.document.activeElement, r.nodes['presentation-locale']);
  assert.equal(r.nodes['locale-status'].textContent, en['locale.changed']);
  assert.equal(r.api.number(0), '0');
});

await check('unsupported stored locale and unavailable storage remain usable', async () => {
  for (const options of [{saved: 'ar'}, {saved: 'en-XA', storageFails: true}]) {
    const r = await runtime(options);
    await r.api.initializeLocale();
    assert.equal(r.api.currentLocale(), 'en');
    assert.deepEqual(r.calls, []);
    await r.api.setLocale('en-XA', true);
    assert.equal(r.api.currentLocale(), 'en-XA');
  }
});

await check('missing, invalid, failed and timed-out catalogs fall back to English', async () => {
  for (const fetchCatalog of [
    async () => ({ok: false}),
    async () => ({ok: true, json: async () => []}),
    async () => { throw new Error('offline'); },
    async () => ({ok: true, json: async () => { throw new SyntaxError('JSON'); }}),
    ({signal}) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new Error('timeout')))),
  ]) {
    const r = await runtime({fetchCatalog, fastTimeout: true});
    await r.api.setLocale('en-XA', true);
    assert.equal(r.api.currentLocale(), 'en');
    assert.equal(r.document.documentElement.lang, 'en');
    assert.equal(r.nodes['presentation-locale'].value, 'en');
    assert.equal(r.nodes['locale-status'].textContent, en['locale.error']);
    assert.equal(r.storage.get(r.api.STORAGE_KEY), 'en');
  }
});

await check('last locale selection wins across in-flight fetches', async () => {
  let finish;
  const r = await runtime({fetchCatalog: () => new Promise((resolve) => { finish = resolve; })});
  const pending = r.api.setLocale('en-XA', true);
  await r.api.setLocale('en', true);
  finish({ok: true, json: async () => xa});
  await pending;
  assert.equal(r.api.currentLocale(), 'en');
  assert.equal(r.document.documentElement.lang, 'en');
  assert.equal(r.storage.get(r.api.STORAGE_KEY), 'en');
});

const renders = {};
await check('actual application renders immutable API records with locale-independent requests', async () => {
  let apiCalls;
  for (const saved of ['en', 'en-XA']) {
    const r = await runtime({saved});
    await r.load();
    assert.ok(r.nodes.species.innerHTML.includes('Pan troglodytes'));
    assert.ok(r.nodes['event-results'].innerHTML.includes('data-canonical'));
    assert.equal(r.nodes.evidence.attributes['aria-busy'], 'false');
    assert.equal(r.eventButtons[0].attributes['aria-pressed'], 'true');
    const firstEvents = r.nodes['event-results'].innerHTML;
    await r.eventButtons[1].listeners.click();
    assert.equal(r.eventButtons[0].attributes['aria-pressed'], 'false');
    assert.equal(r.eventButtons[1].attributes['aria-pressed'], 'true');
    assert.ok(r.nodes['event-results'].innerHTML.includes('GOAL_LABEL_ANONYMIZED'));
    const requests = r.calls.filter((url) => url.startsWith('/api/'));
    if (apiCalls) assert.deepEqual(requests, apiCalls);
    apiCalls = requests;
    const before = [...r.calls];
    await r.api.setLocale('en', true);
    assert.deepEqual(r.calls, before); // Changing language never re-requests API data.
    r.nav.listeners.click();
    assert.equal(r.nodes.evidence.focused, true);
    assert.equal(r.nodes.evidence.focusOptions.preventScroll, true);
    assert.equal(r.nodes.evidence.scrollOptions.behavior, 'instant');
    renders[saved] = Object.fromEntries(Object.entries(r.nodes).filter(([,node]) => node.innerHTML).map(([id,node]) => [id, node.innerHTML]));
    renders[saved]['first-events'] = firstEvents;
  }
});

process.stdout.write(JSON.stringify({checks, renders}));
