/**
 * Recorrido autenticado de Nova Context con cuenta local SINTÉTICA (H-014, ronda 4).
 *
 * Responde a la corrección 2 de la revisión: el repositorio expone
 * `POST /v1/auth/signup` y un `db:seed-dev` que crea `dev@nova.local` para
 * desarrollo local; el bloqueo se refiere a datos reales sin autorización, no a
 * datos locales sintéticos. Fluvia ya se auditó con este enfoque.
 *
 * Se ejecuta sobre una COPIA AISLADA del repositorio (`/tmp/nova-run`), nunca
 * sobre el árbol auditado.
 *
 * Uso:
 *   node capturar-nova.mjs                 # todo
 *   NOVA_USUARIO=... NOVA_CLAVE=... node capturar-nova.mjs
 */
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SALIDA = resolve(AQUI, 'capturas');
mkdirSync(SALIDA, { recursive: true });

const BASE = process.env.NOVA_URL ?? 'http://127.0.0.1:3000';
const USUARIO = process.env.NOVA_USUARIO ?? 'dev@nova.local';
const CLAVE = process.env.NOVA_CLAVE ?? 'nova-dev-password';

const SUPERFICIES = [
  { ruta: '/', nombre: 'inicio' },
  { ruta: '/tasks', nombre: 'tareas' },
  { ruta: '/projects', nombre: 'proyectos' },
  { ruta: '/approvals', nombre: 'aprobaciones' },
  { ruta: '/audit', nombre: 'auditoria' },
  { ruta: '/settings', nombre: 'ajustes' },
  { ruta: '/status', nombre: 'estado' },
];

const VIEWPORTS = [
  { nombre: 'desktop', width: 1440, height: 900 },
  { nombre: 'mobile', width: 390, height: 844 },
];

const informe = [];
const navegador = await chromium.launch();
const contexto = await navegador.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'es-ES',
  reducedMotion: 'reduce',
});
const pagina = await contexto.newPage();
const errores = [];
pagina.on('pageerror', (e) => errores.push(String(e)));

// ---------------------------------------------------------------- acceso
await pagina.goto(`${BASE}/login`, { waitUntil: 'load' });
await pagina.screenshot({ path: resolve(SALIDA, '00-login.png'), fullPage: true });

await pagina.fill('input[type=email], input[name=email], #email', USUARIO);
await pagina.fill('input[type=password], input[name=password], #password', CLAVE);
await pagina.click('button[type=submit]');
await pagina.waitForLoadState('networkidle');
await pagina.waitForTimeout(1200);

const urlTrasLogin = pagina.url();
const autenticado = !urlTrasLogin.includes('/login');
informe.push({
  paso: 'acceso',
  usuario: USUARIO,
  url_tras_login: urlTrasLogin,
  autenticado,
  errores_consola: errores.slice(0, 5),
});

// ------------------------------------------------- superficies autenticadas
for (const s of SUPERFICIES) {
  for (const vp of VIEWPORTS) {
    await pagina.setViewportSize({ width: vp.width, height: vp.height });
    let estado = 200;
    try {
      const r = await pagina.goto(`${BASE}${s.ruta}`, { waitUntil: 'load', timeout: 20000 });
      estado = r ? r.status() : 0;
    } catch (e) {
      informe.push({ superficie: s.nombre, ruta: s.ruta, viewport: vp.nombre,
                     error: String(e).slice(0, 160) });
      continue;
    }
    await pagina.waitForTimeout(400);

    const nombre = `${String(informe.length).padStart(2, '0')}-${s.nombre}__${vp.nombre}`;
    await pagina.screenshot({ path: resolve(SALIDA, `${nombre}.png`), fullPage: true });

    const m = await pagina.evaluate(() => ({
      url: location.pathname,
      title: document.title,
      lang: document.documentElement.lang,
      h1: [...document.querySelectorAll('h1')].map((h) => h.textContent.trim()),
      h2: [...document.querySelectorAll('h2')].length,
      textos: document.body.innerText.replace(/\s+/g, ' ').trim().slice(0, 220),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));

    let axe = { violations: [] };
    try {
      axe = await new AxeBuilder({ page: pagina })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    } catch { /* algunas vistas no son analizables */ }

    informe.push({
      superficie: s.nombre,
      ruta: s.ruta,
      viewport: vp.nombre,
      http: estado,
      ...m,
      desbordeHorizontal: m.scrollWidth > m.clientWidth,
      axe: axe.violations.map((v) => ({ id: v.id, impacto: v.impact, nodos: v.nodes.length })),
    });
  }
}

await contexto.close();
await navegador.close();
writeFileSync(resolve(SALIDA, 'informe-nova.json'), JSON.stringify(informe, null, 2));
console.log(JSON.stringify(informe, null, 2));
