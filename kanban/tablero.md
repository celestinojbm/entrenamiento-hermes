# Tablero de Orquestación — Hermes

> Única fuente de verdad del trabajo pendiente. Hermes lo lee al abrir sesión y lo actualiza al cerrar.
> Formato de tarjeta: `[H-###] Título — pipeline — prioridad (P1 alta / P2 media / P3 baja)`

---

## 🔍 Triage

- **[H-001] Inventariar el ecosistema** — Fase 0 — P1
  Copiar `config/ecosistema.example.json` → `config/ecosistema.json` y rellenar VPS (IPs Tailscale), servicios, Market Castilla, scrapers, dashboards y APIs. *Requiere datos del usuario.*
- **[H-002] Verificar acceso a todos los nodos** — Fase 0 — P1
  Ping Tailscale + SSH + HTTP a cada componente inventariado. Evidencia en `estado/`.
- **[H-008] Definir umbrales de alerta** — pipeline 01 — P3
  ¿Qué es "caído"? ¿Cuánto disco es "crítico"? Documentar en la spec del pipeline 01.

## 📋 Todo

- **[H-003] Primer barrido del monitor** — pipeline 01 — P1
  Ejecutar `scripts/monitor-vps.ps1` con la config real y corregir lo que falle. *Depende de H-001.*
- **[H-004] Auditoría de scrapers existentes** — pipeline 02 — P2
  Por cada scraper: última ejecución, tasa de éxito, errores en logs, frescura de datos. Informe en `reportes/`. *Depende de H-001.*
- **[H-005] Chequeo de salud de Market Castilla** — pipeline 03 — P2
  Verificar panel, API y flujos críticos; integrar el chequeo al monitor. *Depende de H-001.*
- **[H-006] Primer reporte ejecutivo** — pipeline 04 — P2
  Ejecutar `scripts/generar-reporte.ps1` sobre el primer status real y ajustar el formato. *Depende de H-003.*

## 🔄 En Curso

- **[H-011] Dar a Hermes acceso al centro de orquestación** — integración — P1
  Rutas elegidas por el usuario (2026-07-04): GitHub privado + adoptar app de escritorio.
  ✅ Repo privado creado y subido: `https://github.com/celestinojbm/entrenamiento-hermes`.
  ⬜ **Usuario**: crear un fine-grained PAT limitado a ese repo (Contents: read/write) y dárselo a Hermes en su sandbox para que pueda clonar/push.
  ⬜ **Usuario**: instalar la skill en la app de escritorio (un comando, ver `integracion\README.md`) — el clasificador de permisos exige que lo ejecute el humano.

## ⏰ Programados

- **[H-007] Programar monitor recurrente** — pipeline 01 — P2
  Task Scheduler (Windows) o cron (VPS) cada 15 min. *Bloqueada hasta que H-003 pase en verde.*
- **[H-009] Playbooks de reparación automática** — pipeline 04 — P2
  Reinicio de servicio, reintento de scraper, limpieza de disco. *Bloqueada hasta tener monitor estable (H-007).*
- **[H-010] Dashboard centralizado** — pipeline 05 — P3
  *Bloqueada hasta acumular histórico en `estado/` (≥ 1 semana).*

## ✅ Hecho

- **[H-000] Scaffold del sistema** — 2026-07-04
  Estructura del repo, carta operativa, plan maestro, specs de pipelines, scripts de monitor y reporte, config de ejemplo.
