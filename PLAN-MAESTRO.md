# Plan Maestro Adaptado — Sistema Autónomo Integral del Ecosistema

**Versión:** 1.0 · **Fecha:** 2026-07-04 · **Agente:** Hermes

Adaptación del *Plan Ejecutivo para escalar Hermes al nivel Olímpico* al ecosistema real del usuario. El original define principios; este documento define **qué se construye, en qué orden y cómo se mide**.

---

## 1. Ecosistema objetivo

| Componente | Descripción | Estado inicial |
|---|---|---|
| VPS | Servidores del usuario, accesibles vía Tailscale | Por inventariar en `config/ecosistema.json` |
| Tailscale | Red overlay que conecta todos los nodos | Por inventariar (tailnet, nodos críticos) |
| Market Castilla | Panel/servicio de negocio | Por inventariar (URLs, API, endpoint de salud) |
| Scrapers | Recolectores de datos existentes | Por inventariar (rutas, programación, logs) |
| Dashboards | Paneles de visualización | Por inventariar |
| APIs externas | Servicios de datos de terceros | Por inventariar |

> **Regla:** ningún pipeline se ejecuta contra un componente que no esté inventariado. La Fase 0 existe precisamente para eso.

## 2. Fases

### Fase 0 — Inventario y acceso (prerequisito de todo)
- Rellenar `config/ecosistema.json` a partir de `config/ecosistema.example.json`.
- Verificar acceso: ping Tailscale a cada nodo, SSH a cada VPS, HTTP a cada panel.
- **Entregable:** `estado/status-*.json` con todos los componentes en verde o con su bloqueo documentado.

### Fase 1 — Monitor de infraestructura (pipeline 01)
- `scripts/monitor-vps.ps1` ejecutándose bajo demanda y luego programado (Task Scheduler / cron).
- Chequeos: ping, puertos de servicio, endpoints HTTP, espacio en disco vía SSH.
- **Entregable:** monitoreo repetible + primer reporte con `scripts/generar-reporte.ps1`.

### Fase 2 — Scrapers y Market Castilla (pipelines 02 y 03)
- Auditar scrapers existentes: tasa de éxito, errores en logs, frescura de datos.
- Verificación de salud del panel de Market Castilla y sus flujos críticos.
- **Entregable:** informe de auditoría por scraper + chequeo automatizado de Market Castilla integrado al monitor.

### Fase 3 — Reparación automática y reportes (pipeline 04)
- Playbooks de reparación: reinicio de servicio caído, reintento de scraper fallido, limpieza de disco.
- Reporte ejecutivo periódico (estado global, incidencias, acciones tomadas).
- **Entregable:** al menos 2 playbooks probados + reporte semanal automatizado.

### Fase 4 — Dashboard centralizado (pipeline 05)
- Panel único que consume `estado/*.json` y muestra la salud de todo el ecosistema.
- **Entregable:** dashboard desplegado (local o en VPS) con histórico.

## 3. KPIs (los "logros" reales)

| KPI | Línea base | Objetivo Olímpico |
|---|---|---|
| Componentes inventariados y verificados | 0 | 100% |
| Tiempo de detección de caída (MTTD) | manual / horas | < 15 min (monitor programado) |
| Tiempo de reparación (MTTR) con playbook | manual | < 30 min |
| Tasa de éxito de scrapers | desconocida | ≥ 95% medida semanalmente |
| Cadencia de reportes ejecutivos | ninguna | semanal, automática |
| Intervención humana por incidencia | alta | solo aprobación de acciones destructivas |

## 4. Sobre los logros del agente

La autonomía, la variedad de herramientas y el volumen de llamadas **emergen de este plan por construcción**: cada sesión de Hermes toca terminal, SSH, archivos, HTTP, análisis de logs y documentación porque las tarjetas lo exigen. No se infla ninguna métrica artificialmente — una sesión larga sin resultado es un fallo, no un logro.

## 5. Gobernanza

- **Orquestación:** `kanban/tablero.md` es la única fuente de verdad del trabajo pendiente.
- **Trazabilidad:** toda sesión deja entrada en `bitacora/`.
- **Seguridad:** secretos fuera del repo; acciones destructivas siempre con confirmación humana.
