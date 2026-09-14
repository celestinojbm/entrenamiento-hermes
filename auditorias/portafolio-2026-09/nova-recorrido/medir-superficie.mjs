/**
 * Medición puntual del desborde móvil de una superficie (por defecto /settings).
 * Uso: node medir-superficie.mjs [/settings]
 */
import { chromium } from 'playwright';
const BASE = process.env.NOVA_URL ?? 'http://127.0.0.1:3000';
const RUTA = process.argv[2] ?? '/settings';
const USUARIO = 'dev@nova.local';
const CLAVE = process.env.NOVA_CLAVE ?? 'nova-dev-password';

const navegador = await chromium.launch();
const ctx = await navegador.newContext({ viewport: { width: 390, height: 844 } });
const p = await ctx.newPage();
await p.goto(`${BASE}/login`, { waitUntil: 'load' });
await p.fill('input[type=email], input[name=email], #email', USUARIO);
await p.fill('input[type=password], input[name=password], #password', CLAVE);
await p.click('button[type=submit]');
await p.waitForLoadState('networkidle');
await p.goto(`${BASE}${RUTA}`, { waitUntil: 'load' });
await p.waitForTimeout(700);

const r = await p.evaluate(() => {
  const doc = document.documentElement;
  const anchos = [...document.querySelectorAll('*')]
    .map((e) => ({ tag: e.tagName.toLowerCase(), clase: e.className?.toString().slice(0, 40), w: Math.round(e.getBoundingClientRect().right) }))
    .filter((x) => x.w > window.innerWidth + 1)
    .sort((a, b) => b.w - a.w).slice(0, 6);
  return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, desborde: doc.scrollWidth > doc.clientWidth, culpables: anchos };
});
console.log(JSON.stringify(r, null, 2));
await ctx.close();
await navegador.close();
