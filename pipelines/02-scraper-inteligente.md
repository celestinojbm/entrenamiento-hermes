# Pipeline 02 — Scraper Inteligente con Análisis y Reportes

**Objetivo:** que cada scraper existente sea observable (¿corrió?, ¿tuvo éxito?, ¿los datos son frescos?) y que sus fallos se diagnostiquen automáticamente.

## Entradas
- `config/ecosistema.json` → sección `scrapers` (nombre, ruta/host, programación, ubicación de logs, destino de datos).

## Fases

1. **Auditoría inicial (H-004)** — por cada scraper:
   - Última ejecución y resultado (leer logs con `Get-Content`/`grep` vía SSH si vive en un VPS).
   - Tasa de éxito de los últimos N runs.
   - Frescura del dato de salida (fecha de última fila / archivo).
2. **Diagnóstico de fallos** — clasificar errores de log: cambio de HTML/selector, bloqueo (403/429), timeout de red, error de credencial. Cada clase tiene remedio distinto.
3. **Instrumentación** — añadir a cada scraper una salida de estado mínima (exit code + resumen JSON) para que el monitor (pipeline 01) lo integre.
4. **Reporte** — sección "Scrapers" dentro del reporte ejecutivo (pipeline 04): tabla por scraper con éxito/fallo/frescura.

## Herramientas que usa Hermes
SSH/terminal, análisis de logs, lectura de código de los scrapers, navegador/web (para verificar si el sitio origen cambió), edición de archivos.

## Salidas
- `reportes/auditoria-scrapers-<fecha>.md`
- Estado por scraper integrado en `estado/status-*.json`.

## Criterio de éxito
Tasa de éxito conocida y ≥ 95% mantenida; ningún scraper "silenciosamente muerto" más de 24 h.
