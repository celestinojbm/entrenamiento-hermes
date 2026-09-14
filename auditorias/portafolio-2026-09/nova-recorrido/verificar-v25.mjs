/**
 * Verificación del arreglo de V25 (tarjetas de tarea ilegibles en móvil).
 *
 * Mide, en un viewport móvil real:
 *   1. desborde horizontal del documento (V24);
 *   2. ancho renderizado y número de líneas del título de la primera tarea (V25);
 *   3. que el título sea LEGIBLE: que no caiga en una letra por renglón;
 *   4. INTERACCIÓN: que el botón de estado cambie de verdad el estado de la tarea.
 *
 * Uso: node verificar-v25.mjs [--etiqueta antes|despues]
 */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SALIDA = resolve(AQUI, 'capturas');
mkdirSync(SALIDA, { recursive: true });

const ETIQUETA = process.argv.includes('--etiqueta')
  ? process.argv[process.argv.indexOf('--etiqueta') + 1] : 'despues';
const BASE = process.env.NOVA_URL ?? 'http://127.0.0.1:3000';
const USUARIO = process.env.NOVA_USUARIO ?? 'dev@nova.local';
const CLAVE = process.env.NOVA_CLAVE ?? 'nova-dev-password';

const navegador = await chromium.launch();
const contexto = await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'es-ES' });
const pagina = await contexto.newPage();
const errores = [];
pagina.on('pageerror', (e) => errores.push(String(e)));

// acceso con la cuenta sintética local
await pagina.goto(`${BASE}/login`, { waitUntil: 'load' });
await pagina.fill('input[type=email], input[name=email], #email', USUARIO);
await pagina.fill('input[type=password], input[name=password], #password', CLAVE);
await pagina.click('button[type=submit]');
await pagina.waitForLoadState('networkidle');

await pagina.goto(`${BASE}/tasks`, { waitUntil: 'load' });
await pagina.waitForTimeout(700);

const medir = async () => pagina.evaluate(() => {
  const doc = document.documentElement;
  const titulos = [...document.querySelectorAll('.task-title')];
  const primero = titulos[0];
  const r = primero ? primero.getBoundingClientRect() : null;
  const alto = r ? r.height : 0;
  const lh = primero ? parseFloat(getComputedStyle(primero).lineHeight) || 20 : 20;
  return {
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    desborde: doc.scrollWidth > doc.clientWidth,
    tareas: titulos.length,
    titulo_texto: primero ? primero.textContent.trim() : null,
    titulo_ancho_px: r ? Math.round(r.width) : 0,
    titulo_alto_px: Math.round(alto),
    titulo_lineas: Math.max(1, Math.round(alto / lh)),
    titulo_caracteres: primero ? primero.textContent.trim().length : 0,
    // Una letra por renglón: muchas líneas para pocos caracteres.
    caracteres_por_linea: primero && alto
      ? +(primero.textContent.trim().length / Math.max(1, Math.round(alto / lh))).toFixed(1) : 0,
  };
});

const antes = await medir();
await pagina.screenshot({ path: resolve(SALIDA, `tareas-movil-${ETIQUETA}.png`), fullPage: true });

// ---- interacción: pulsar el botón de estado y comprobar que CAMBIA ----
const boton = pagina.locator('.task-row .task-toggle button').first();
const textoBotonAntes = (await boton.textContent())?.trim();
const fila = pagina.locator('.task-row').first();
const claseAntes = (await fila.getAttribute('class')) ?? '';
await boton.click();
await pagina.waitForTimeout(1800);
await pagina.waitForLoadState('networkidle');

const botonTras = pagina.locator('.task-row .task-toggle button').first();
const textoBotonDespues = (await botonTras.textContent())?.trim();
const claseDespues = (await pagina.locator('.task-row').first().getAttribute('class')) ?? '';
const interaccion = {
  texto_boton_antes: textoBotonAntes,
  texto_boton_despues: textoBotonDespues,
  clase_fila_antes: claseAntes,
  clase_fila_despues: claseDespues,
  cambio: textoBotonAntes !== textoBotonDespues || claseAntes !== claseDespues,
};
await pagina.screenshot({ path: resolve(SALIDA, `tareas-movil-${ETIQUETA}-tras-interaccion.png`), fullPage: true });

const despues = await medir();
const informe = { etiqueta: ETIQUETA, viewport: '390x844', medicion: antes, tras_interaccion: { ...despues, interaccion }, errores_consola: errores };
writeFileSync(resolve(SALIDA, `informe-v25-${ETIQUETA}.json`), JSON.stringify(informe, null, 2));
console.log(JSON.stringify(informe, null, 2));

await contexto.close();
await navegador.close();
