/**
 * Captura y auditoría de las vistas previas de H-014 (ronda 3).
 *
 * Para cada vista: captura full-page en escritorio (1440×900) y móvil (390×844),
 * y mide con axe-core (WCAG 2.0/2.1 A y AA) más comprobaciones funcionales de
 * DOM: h1 único, desborde horizontal, imágenes sin alt, botones sin nombre
 * accesible, tamaño de los objetivos táctiles.
 *
 * Uso: node capturar-previa.mjs            (desde este directorio)
 * Requiere: playwright + @axe-core/playwright disponibles en NODE_PATH.
 */
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SALIDA = resolve(AQUI, 'capturas');
mkdirSync(SALIDA, { recursive: true });

const VISTAS = [
  'fluvia-dashboard.html',
  'nova-shell.html',
  '../dona-dashboard/flujo-principal.html',
];
const VIEWPORTS = [
  { nombre: 'desktop', width: 1440, height: 900 },
  { nombre: 'mobile', width: 390, height: 844 },
];

const informe = [];

const navegador = await chromium.launch();

for (const vista of VISTAS) {
  const url = 'file://' + resolve(AQUI, vista);
  for (const vp of VIEWPORTS) {
    const contexto = await navegador.newContext({
      viewport: { width: vp.width, height: vp.height },
      locale: 'es-ES',
      reducedMotion: 'reduce',
    });
    const pagina = await contexto.newPage();
    const errores = [];
    pagina.on('pageerror', (e) => errores.push(String(e)));

    await pagina.goto(url, { waitUntil: 'load' });
    await pagina.waitForTimeout(300);

    const nombre = `${vista.split('/').pop().replace('.html', '')}__${vp.nombre}`;
    await pagina.screenshot({ path: resolve(SALIDA, `${nombre}.png`), fullPage: true });

    const metricas = await pagina.evaluate(() => {
      const h1s = [...document.querySelectorAll('h1')].map((h) => h.textContent.trim());
      const imgsSinAlt = [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length;
      const botonesSinNombre = [...document.querySelectorAll('button')].filter((b) => {
        const t = (b.textContent || '').trim();
        return !t && !b.getAttribute('aria-label') && !b.getAttribute('title');
      }).length;
      const inputsSinEtiqueta = [...document.querySelectorAll('input:not([type=hidden])')].filter((i) => {
        const porFor = i.id && document.querySelector(`label[for="${i.id}"]`);
        const envolvente = i.closest('label');
        return !porFor && !envolvente && !i.getAttribute('aria-label');
      }).length;
      const enlaces = [...document.querySelectorAll('a')];
      const enlacesSinTexto = enlaces.filter(
        (a) => !(a.textContent || '').trim() && !a.getAttribute('aria-label'),
      ).length;
      return {
        lang: document.documentElement.lang,
        title: document.title,
        h1s,
        imgsSinAlt,
        botonesSinNombre,
        inputsSinEtiqueta,
        enlacesSinTexto,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        // ¿La tipografía declarada resuelve de verdad o cayó en el respaldo?
        fuente_titulo: getComputedStyle(document.querySelector('h1, h2')).fontFamily,
        inter_disponible: document.fonts.check('16px Inter'),
        mono_disponible: document.fonts.check('16px "JetBrains Mono"'),
      };
    });

    const axe = await new AxeBuilder({ page: pagina })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    informe.push({
      vista,
      viewport: vp.nombre,
      ancho: vp.width,
      ...metricas,
      desbordeHorizontal: metricas.scrollWidth > metricas.clientWidth,
      erroresConsola: errores,
      axeViolaciones: axe.violations.map((v) => ({
        id: v.id,
        impacto: v.impact,
        nodos: v.nodes.length,
        ayuda: v.help,
      })),
    });

    await contexto.close();
  }
}

await navegador.close();
writeFileSync(resolve(SALIDA, 'informe-vistas-previas.json'), JSON.stringify(informe, null, 2));
console.log(JSON.stringify(informe, null, 2));
