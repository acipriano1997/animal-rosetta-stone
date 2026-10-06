// Presentation only. Catalogs never receive, mutate, or serialize scientific records.
export const STORAGE_KEY = 'ars.workbench.presentationLocale';
export const LOCALES = Object.freeze({
  en: Object.freeze({direction: 'ltr', formatLocale: 'en', testOnly: false}),
  'en-XA': Object.freeze({direction: 'ltr', formatLocale: 'en', testOnly: true}),
});
export function resolveLocale(requested) {
  return Object.keys(LOCALES).find((code) => code.toLowerCase() === String(requested).toLowerCase()) || 'en';
}

export function catalogMessage(catalogs, locale, key) {
  locale = resolveLocale(locale);
  const source = catalogs.en?.[key];
  const value = catalogs[locale]?.[key];
  const placeholders = (text) => (text.match(/\{[a-zA-Z_]+\}/g) || []).sort().join();
  if (typeof source !== 'string' || !source.trim()) return `⟦MISSING: ${key}⟧`;
  if (typeof value === 'string' && value.trim() && placeholders(value) === placeholders(source)) return value;
  return locale === 'en-XA' ? `⟦MISSING: ${key}⟧ ${source}` : source;
}

const catalogs = {en: Object.freeze(JSON.parse(document.getElementById('presentation-messages').textContent))};
let locale = 'en';
let selection = 0;
export const currentLocale = () => locale;
export const t = (key, parameters = {}) => catalogMessage(catalogs, locale, key)
  .replace(/\{([a-zA-Z_]+)\}/g, (_, name) => String(parameters[name] ?? `⟦MISSING: ${name}⟧`));
export const number = (value) => typeof value === 'number' && Number.isFinite(value)
  ? new Intl.NumberFormat(LOCALES[locale].formatLocale, {maximumFractionDigits: 20}).format(value)
  : t('common.unknown');

// Only explicit chrome nodes are translated; never walk arbitrary text or API keys.
export function applyMessages(root = document) {
  // Refuse accidental annotations on canonical nodes, their children, or a
  // container whose text replacement would erase canonical descendants.
  const protectedText = (node) => node.closest('[data-canonical]') || node.querySelector('[data-canonical]');
  root.querySelectorAll('[data-i18n]').forEach((node) => {
    if (protectedText(node)) return;
    const parameters = JSON.parse(node.dataset.i18nParams || '{}');
    for (const key of Object.keys(parameters)) parameters[key] = number(parameters[key]);
    node.textContent = t(node.dataset.i18n, parameters);
  });
  root.querySelectorAll('[data-i18n-aria]').forEach((node) => {
    if (!protectedText(node)) node.setAttribute('aria-label', t(node.dataset.i18nAria));
  });
  root.querySelectorAll('[data-i18n-title]').forEach((node) => {
    if (!node.closest('[data-canonical]')) node.setAttribute('title', t(node.dataset.i18nTitle));
  });
  root.querySelectorAll('[data-number]').forEach((node) => {
    if (!protectedText(node)) node.textContent = number(JSON.parse(node.dataset.number));
  });
}

export async function setLocale(requested, persist = false) {
  const request = ++selection;
  let resolved = resolveLocale(requested);
  let failed = false;
  if (!catalogs[resolved]) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(`/locales/${resolved}.json`, {signal: controller.signal});
      if (!response.ok) throw new Error('CATALOG_UNAVAILABLE');
      const catalog = await response.json();
      if (!catalog || typeof catalog !== 'object' || Array.isArray(catalog)) throw new Error('INVALID_CATALOG');
      catalogs[resolved] = Object.freeze(catalog);
    } catch {
      resolved = 'en';
      failed = true;
    } finally {
      clearTimeout(timeout);
    }
  }
  if (request !== selection) return;
  locale = resolved;
  document.documentElement.lang = locale;
  document.documentElement.dir = LOCALES[locale].direction;
  document.documentElement.dataset.pseudolocale = String(LOCALES[locale].testOnly);
  document.getElementById('presentation-locale').value = locale;
  if (persist) {
    try { localStorage.setItem(STORAGE_KEY, locale); } catch { /* In-memory preference still works. */ }
  }
  applyMessages();
  document.getElementById('locale-status').textContent = failed ? t('locale.error') : persist ? t('locale.changed') : '';
}

export async function initializeLocale() {
  let saved;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch { /* English remains deterministic. */ }
  document.getElementById('presentation-locale').addEventListener('change', (event) => setLocale(event.target.value, true));
  await setLocale(saved);
}
