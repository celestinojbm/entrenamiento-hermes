/**
 * Auditoría visual H-014 — captura de pantallas, consola, responsive y accesibilidad.
 * Uso: node capturar.mjs <json-con-lista-de-targets> <directorio-salida>
 */
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import path from 'node:path';

const targetsFile = process.argv[2];
const outDir = process.argv[3] || '/home/celestinojbm/h014-work/visual';
const targets = JSON.parse(fs.readFileSync(targetsFile, 'utf8'));

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
};

fs.mkdirSync(outDir, { recursive: true });
const report = [];

const browser = await chromium.launch();

for (const t of targets) {
  const entry = { producto: t.producto, ruta: t.ruta, url: t.url, viewports: {}, notas: [] };
  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    const ctx = await browser.newContext({
      viewport: vp,
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      locale: 'es-ES',
    });
    const page = await ctx.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300));
    });
    page.on('pageerror', (e) => pageErrors.push(String(e).slice(0, 300)));
    page.on('requestfailed', (r) => failedRequests.push(`${r.failure()?.errorText} ${r.url().slice(0, 160)}`));

    let status = null;
    const vpResult = {};
    try {
      const resp = await page.goto(t.url, { waitUntil: 'networkidle', timeout: 45000 });
      status = resp?.status() ?? null;
      await page.waitForTimeout(1200);

      const slug = t.ruta.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'root';
      const file = path.join(outDir, `${t.producto}__${slug}__${vpName}.png`);
      await page.screenshot({ path: file, fullPage: true });

      const metrics = await page.evaluate(() => ({
        title: document.title,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyHeight: document.body.scrollHeight,
        h1: [...document.querySelectorAll('h1')].map((e) => e.textContent?.trim().slice(0, 120)),
        h1Count: document.querySelectorAll('h1').length,
        imgCount: document.querySelectorAll('img').length,
        imgWithoutAlt: document.querySelectorAll('img:not([alt])').length,
        buttonsWithoutName: [...document.querySelectorAll('button')].filter(
          (b) => !(b.textContent || '').trim() && !b.getAttribute('aria-label')
        ).length,
        inputsWithoutLabel: [...document.querySelectorAll('input:not([type=hidden])')].filter((i) => {
          const id = i.getAttribute('id');
          const hasLabel = id && document.querySelector(`label[for="${id}"]`);
          return !hasLabel && !i.getAttribute('aria-label') && !i.getAttribute('placeholder');
        }).length,
        lang: document.documentElement.lang || null,
        firstText: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 400),
      }));
      vpResult.metrics = metrics;
      vpResult.overflowHorizontal = metrics.scrollWidth > metrics.clientWidth + 1;

      let axe = null;
      if (vpName === 'desktop') {
        try {
          const res = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
            .analyze();
          const byImpact = {};
          for (const v of res.violations) byImpact[v.impact] = (byImpact[v.impact] || 0) + 1;
          axe = {
            violations: res.violations.length,
            byImpact,
            top: res.violations.slice(0, 12).map((v) => ({
              id: v.id,
              impact: v.impact,
              help: v.help,
              nodes: v.nodes.length,
              example: v.nodes[0]?.html?.slice(0, 160),
            })),
            passes: res.passes.length,
          };
        } catch (e) {
          axe = { error: String(e).slice(0, 200) };
        }
      }
      vpResult.axe = axe;
      vpResult.screenshot = file;
    } catch (e) {
      vpResult.error = String(e).slice(0, 300);
    }
    vpResult.status = status;
    vpResult.consoleErrors = consoleErrors.slice(0, 10);
    vpResult.pageErrors = pageErrors.slice(0, 5);
    vpResult.failedRequests = failedRequests.slice(0, 8);
    entry.viewports[vpName] = vpResult;
    await ctx.close();
  }
  report.push(entry);
  console.log(`OK ${t.producto} ${t.ruta}`);
}

await browser.close();
fs.writeFileSync(path.join(outDir, 'informe-visual.json'), JSON.stringify(report, null, 2));
console.log(`\nInforme: ${path.join(outDir, 'informe-visual.json')}`);
