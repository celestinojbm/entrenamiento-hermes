# Tablero de Orquestación — Hermes

> Única fuente de verdad del trabajo pendiente. Hermes lo lee al abrir sesión y lo actualiza al cerrar.
> Formato de tarjeta: `[H-###] Título — pipeline — prioridad (P1 alta / P2 media / P3 baja)`

---

## 🔍 Triage

## 📋 Todo

- **[H-013] Auditoría del proyecto Fluvia** — pipeline 06 — P2
  Clonar `celestinojbm/Fluvia` (público), ejecutar las 6 fases del pipeline 06 y entregar `reportes/auditoria-fluvia-<fecha>.md` + tarjetas de hallazgos críticos/altos en Triage. Extra: averiguar y añadir al inventario la URL de despliegue.
- **[H-004] Auditoría de scrapers/automatizaciones** — pipeline 02 — P2
  El descubrimiento SSH no encontró scrapers en crons de root; sí 2 automatizaciones Dona en `openclaw-vps` (inventariadas). Auditar sus logs/resultados y preguntar al usuario si existen scrapers en otro lado (pm2, otros usuarios, proyectos locales).
- **[H-005] Chequeo funcional de Market Castilla** — pipeline 03 — P2
  ✅ Chequeo superficial integrado al monitor (panel responde 200; URL en inventario local).
  ⬜ Flujos críticos (login, listado): requiere decidir cómo probarlos sin escribir datos reales. *La API propia, si existe, falta inventariar.*

## 🔄 En Curso

- **[H-011] Dar a Hermes acceso al centro de orquestación** — integración — P1
  ✅ Skill instalada y verificada en la app local (`~/.hermes/skills/entrenamiento-hermes`) junto a `personas`.
  ✅ Repo público clonado/actualizado: `https://github.com/celestinojbm/entrenamiento-hermes`.
  ⬜ **Usuario**: si el panel sigue mostrando Gateway detenido, pulsar **Reiniciar Gateway** para abrir sesiones de chat.

## ⏰ Programados

- **[H-009] Playbooks de reparación automática** — pipeline 04 — P2
  ✅ Scripts creados y validados. ✅ SSH autorizado por el usuario a ambos VPS. ✅ `limpiar-disco` probado en dry-run real contra `openclaw-vps` (midió 40M liberables y se negó a borrar sin `-Confirmar`). Corregido bug de `$PSScriptRoot` vacío en `param()` (PS 5.1).
  ⬜ Probar `reiniciar-servicio` con un servicio no crítico cuando haya ocasión (reiniciar el gateway de Hermes interrumpiría al agente: elegir momento con el usuario).
- **[H-010] Dashboard centralizado** — pipeline 05 — P3
  *Bloqueada hasta acumular histórico en `estado/` (≥ 1 semana).*

## ✅ Hecho

- **[H-001] Inventariar el ecosistema** — 2026-07-04
  Completado por descubrimiento autorizado (SSH root vía Tailscale + GitHub): 2 VPS con recursos y servicios reales (gateway de Hermes como systemd, gateway de OpenClaw como proceso, 2 automatizaciones Dona), 4 endpoints cloud (Market Castilla, Dona, Dona Founders, Manos Venezuela) y proyectos cloud inventariados. Todo en `config/ecosistema.json` (local). Pendientes menores: API de Market Castilla, URL de Fluvia, APIs externas.
- **[H-012] Monitor ampliado a servicios y procesos** — 2026-07-04
  El monitor ahora vigila servicios systemd (`systemctl is-active`) y procesos (`pgrep -f`) vía SSH, con `accept-new` para host keys del tailnet y alerta explícita si SSH no responde. **Barrido completo: 15/15 OK.**
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
