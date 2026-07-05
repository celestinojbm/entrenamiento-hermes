# Tablero de Orquestación — Hermes

> Única fuente de verdad del trabajo pendiente. Hermes lo lee al abrir sesión y lo actualiza al cerrar.
> Formato de tarjeta: `[H-###] Título — pipeline — prioridad (P1 alta / P2 media / P3 baja)`

---

## 🔍 Triage

## 📋 Todo

- **[H-004] Auditoría de scrapers existentes** — pipeline 02 — P2
  Por cada scraper: última ejecución, tasa de éxito, errores en logs, frescura de datos. Informe en `reportes/`. *Depende de H-001.*
- **[H-005] Chequeo de salud de Market Castilla** — pipeline 03 — P2
  Verificar panel, API y flujos críticos; integrar el chequeo al monitor. *Depende de H-001.*

## 🔄 En Curso

- **[H-001] Inventariar el ecosistema** — Fase 0 — P1
  ✅ `config/ecosistema.json` creado (local, git-ignored) con los 2 VPS descubiertos vía Tailscale (`hermes-dona-vps`, `openclaw-vps`) + SSH:22.
  ⬜ **Usuario/Hermes**: completar los `TODO` del archivo — usuarios SSH reales, puertos HTTP/servicios de cada VPS, URLs de Market Castilla, scrapers y APIs externas.
- **[H-011] Dar a Hermes acceso al centro de orquestación** — integración — P1
  ✅ Skill instalada y verificada en la app local (`~/.hermes/skills/entrenamiento-hermes`) junto a `personas`.
  ✅ Repo público clonado/actualizado: `https://github.com/celestinojbm/entrenamiento-hermes`.
  ⬜ **Usuario**: si el panel sigue mostrando Gateway detenido, pulsar **Reiniciar Gateway** para abrir sesiones de chat.

## ⏰ Programados

- **[H-009] Playbooks de reparación automática** — pipeline 04 — P2
  Reinicio de servicio, reintento de scraper, limpieza de disco. *Bloqueada hasta tener monitor estable (H-007).*
- **[H-010] Dashboard centralizado** — pipeline 05 — P3
  *Bloqueada hasta acumular histórico en `estado/` (≥ 1 semana).*

## ✅ Hecho

- **[H-007] Programar monitor recurrente** — 2026-07-04
  Task Scheduler creado en Windows: `EntrenamientoHermes\MonitorInfraestructura`, cada 15 minutos. Verificado con ejecución manual: último resultado `0` y nuevo `estado/status-2026-07-04-2324.json` generado.
- **[H-006] Primer reporte ejecutivo** — 2026-07-04
  `scripts/generar-reporte.ps1` ejecutado sobre el primer status real. Ajustado el formato para mostrar chequeos `OMITIDO` como "Pendiente de inventario / acceso" y generado `reportes/reporte-2026-07-04-2323.md`.
- **[H-008] Definir umbrales de alerta** — 2026-07-04
  Definiciones operativas añadidas a `pipelines/01-monitor-infraestructura.md`: nodo/servicio caído, endpoint degradado/caído, disco, memoria y significado de `OMITIDO`.
- **[H-003] Primer barrido del monitor** — 2026-07-04
  `scripts/monitor-vps.ps1` ejecutado contra los VPS reales por Tailscale: **ambos OK** (ping + SSH:22). Reporte ejecutivo generado. Bug corregido en el camino (falsos CRÍTICO con valores placeholder).
- **[H-002] Verificar acceso a los nodos** — 2026-07-04
  Ping + puerto SSH confirmados en `hermes-dona-vps` y `openclaw-vps`. (Pendiente el acceso SSH autenticado para chequeos de recursos — requiere `ssh_habilitado:true` + clave.)
- **[H-000] Scaffold del sistema** — 2026-07-04
  Estructura del repo, carta operativa, plan maestro, specs de pipelines, scripts de monitor y reporte, config de ejemplo.
