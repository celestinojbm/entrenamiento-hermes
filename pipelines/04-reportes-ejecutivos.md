# Pipeline 04 — Reparación Automática y Reportes Ejecutivos

**Objetivo:** que las incidencias comunes se reparen solas (con aprobación humana solo para lo destructivo) y que el usuario reciba un reporte ejecutivo periódico sin pedirlo.

## Parte A — Playbooks de reparación (H-009)

Cada playbook es un procedimiento documentado + script. Los tres iniciales:

| Playbook | Disparador | Acción | ¿Requiere aprobación? |
|---|---|---|---|
| Servicio caído | puerto cerrado en monitor | `systemctl restart <servicio>` vía SSH + re-chequeo | No (reinicio de servicio propio) |
| Scraper fallido | exit code ≠ 0 o log con error | reintento con backoff; si falla 2ª vez → diagnóstico (pipeline 02) | No |
| Disco crítico | > 95% en monitor | limpiar rutas seguras declaradas en config (logs rotados, tmp) | **Sí** — borrar siempre pide confirmación |

Regla: todo playbook re-verifica tras actuar y registra en `bitacora/` qué hizo, con salida literal de comandos.

## Parte B — Reporte ejecutivo

- **Generador:** `scripts/generar-reporte.ps1` (lee el último `estado/status-*.json`).
- **Cadencia:** bajo demanda al principio; semanal automatizado al cerrar H-007.
- **Contenido:** semáforo global → incidencias y acciones tomadas → estado por componente (VPS, servicios, Market Castilla, scrapers) → tendencias → tarjetas bloqueadas que necesitan al usuario.
- **Estilo:** primero lo que está mal y qué se hizo; después el detalle. Sin optimismo sin evidencia.

## Salidas
- `reportes/reporte-<fecha>.md`
- Entradas de bitácora por cada reparación.

## Criterio de éxito
MTTR < 30 min para incidencias con playbook; reporte semanal generado sin intervención durante 4 semanas seguidas.
