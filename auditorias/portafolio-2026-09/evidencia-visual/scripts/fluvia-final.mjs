import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import path from 'node:path';

const BASE = 'http://localhost:3200';
const OUT = '/home/celestinojbm/h014-work/visual/out';
const EMAIL = `audit-fin-${Date.now()}@fluvia.local`;
const PASS = 'AuditoriaH014!2026';
const SLUG = `fin-${Date.now().toString(36)}`;
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', reducedMotion: 'reduce' });
const page = await ctx.newPage();
const mutaciones = [];
const erroresConsola = [];
page.on('response', (r) => { if (r.request().method() !== 'GET') mutaciones.push(`${r.request().method()} ${new URL(r.url()).pathname} -> ${r.status()}`); });
page.on('console', (m) => { if (m.type() === 'error') erroresConsola.push(m.text().slice(0, 220)); });
const txt = () => page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 400));
const shot = (n) => page.screenshot({ path: path.join(OUT, `fluvia__${n}.png`), fullPage: true }).catch(() => {});
const click = async (re) => { for (const b of await page.$$('button')) { const x = ((await b.textContent()) || '').trim(); if (re.test(x)) { await b.click(); return x; } } return null; };

// --- alta + onboarding ---
await page.goto(`${BASE}/signup`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500);
await page.fill('#email', EMAIL); await page.fill('#password', PASS); await page.fill('#confirm-password', PASS);
await page.click('button[type=submit]'); await page.waitForTimeout(4000);
await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500);
await page.fill('#email', EMAIL); await page.fill('#password', PASS);
await page.click('button[type=submit]'); await page.waitForTimeout(5000);
await page.goto(`${BASE}/onboarding`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000);
await page.fill('#org-name', 'Org Auditoria H-014');
await page.fill('#org-slug', SLUG);
await click(/continuar/i); await page.waitForTimeout(5000);
const paisesVacio = await page.evaluate(() => { const s = document.querySelector('#merchant-country'); return s ? s.querySelectorAll('option').length : null; });
await page.fill('#merchant-name', 'Comercio Auditoria H-014').catch(() => {});
await click(/finalizar|crear|completar/i); await page.waitForTimeout(8000);

// --- descubrir orgId ---
let orgId = (page.url().match(/\/o\/([0-9a-f-]{36})/i) || [])[1];
if (!orgId) {
  await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500);
  orgId = await page.evaluate(() => {
    const a = [...document.querySelectorAll('a[href*="/o/"]')].map((x) => x.getAttribute('href')).find(Boolean);
    return a ? (a.match(/\/o\/([0-9a-f-]{36})/i) || [])[1] : null;
  });
  // si no hay enlace directo, entrar por "Configurar / continuar"
  if (!orgId) {
    for (const l of await page.$$('a')) {
      const t = ((await l.textContent()) || '').trim();
      if (/configurar|continuar/i.test(t)) { await l.click(); await page.waitForTimeout(4000); break; }
    }
    orgId = (page.url().match(/\/o\/([0-9a-f-]{36})/i) || [])[1];
  }
}
if (!orgId) {
  const html = await page.content();
  orgId = (html.match(/\/o\/([0-9a-f-]{36})/i) || [])[1];
}
console.log('orgId =', orgId, '| opciones de país en el select =', paisesVacio);

const rutas = [
  ['', 'org-overview'], ['/payments', 'org-payments'], ['/refunds', 'org-refunds'],
  ['/checkout-sessions', 'org-checkout-sessions'], ['/payment-links', 'org-payment-links'],
  ['/payouts', 'org-payouts'], ['/disputes', 'org-disputes'], ['/reconciliation', 'org-reconciliation'],
  ['/cases', 'org-cases'], ['/webhook-events', 'org-webhook-events'],
  ['/webhook-endpoints', 'org-webhook-endpoints'], ['/api-keys', 'org-api-keys'], ['/events', 'org-events'],
];
const paginas = [];
for (const [r, label] of rutas) {
  if (!orgId) break;
  await page.goto(`${BASE}/o/${orgId}${r}`, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1300);
  const t = await txt();
  const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, h1: [...document.querySelectorAll('h1')].map((e) => e.textContent.trim()), tablas: document.querySelectorAll('table').length, vacios: /no hay|aún no|sin |vacío|todavía/i.test(document.body.innerText) }));
  const f = path.join(OUT, `fluvia__${label}.png`);
  await page.screenshot({ path: f, fullPage: true }).catch(() => {});
  let axe = null;
  try {
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    axe = { violations: res.violations.length, byImpact: res.violations.reduce((a, v) => ((a[v.impact] = (a[v.impact] || 0) + 1), a), {}), top: res.violations.slice(0, 6).map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, example: v.nodes[0]?.html?.slice(0, 130) })) };
  } catch (e) { axe = { error: String(e).slice(0, 120) }; }
  paginas.push({ label, url: page.url(), h1: m.h1, tablas: m.tablas, overflow: m.sw > m.cw + 1, px: `${m.sw}/${m.cw}`, axe, texto: t.slice(0, 240), captura: f });
  console.log(`[${label}] axe=${axe?.violations} ovf=${m.sw > m.cw + 1} h1=${JSON.stringify(m.h1)} :: ${t.slice(0, 70)}`);
}

// --- móvil ---
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'es-ES' });
const mp = await mctx.newPage();
const movil = [];
for (const [r, label] of [['', 'org-overview'], ['/payments', 'org-payments']]) {
  if (!orgId) break;
  await mp.goto(`${BASE}/o/${orgId}${r}`, { waitUntil: 'networkidle' }).catch(() => {});
  await mp.waitForTimeout(1500);
  const m = await mp.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  const f = path.join(OUT, `fluvia__${label}__mobile.png`);
  await mp.screenshot({ path: f, fullPage: true }).catch(() => {});
  movil.push({ label, ...m, overflow: m.sw > m.cw + 1, captura: f });
  console.log(`[${label} mobile] ${m.sw}/${m.cw} overflow=${m.sw > m.cw + 1}`);
}

fs.writeFileSync(path.join(OUT, 'fluvia-e2e.json'), JSON.stringify({ email: EMAIL, orgId, paisesEnSelectMerchant: paisesVacio, paginas, movil, mutaciones, erroresConsola: [...new Set(erroresConsola)] }, null, 2));
console.log('\nMutaciones:', mutaciones.join(' | '));
console.log('Errores consola:', [...new Set(erroresConsola)].map((c) => c.slice(0, 150)));
await browser.close();
