# Entrenamiento Hermes — Sistema Autónomo Integral del Ecosistema

Este repositorio operacionaliza el **Plan Ejecutivo para escalar a Hermes al nivel Olímpico**, adaptado al ecosistema real: infraestructura VPS, Tailscale, Market Castilla, scrapers, dashboards, automatizaciones y servicios externos.

## Estructura

```
entrenamiento hermes/
├── CLAUDE.md                  # Carta operativa de Hermes (se carga automáticamente en cada sesión)
├── PLAN-MAESTRO.md            # Plan maestro adaptado, con fases y KPIs
├── kanban/
│   └── tablero.md             # Tablero de orquestación (Triage / Todo / En Curso / Programados / Hecho)
├── pipelines/                 # Especificaciones de cada pipeline del sistema
│   ├── 01-monitor-infraestructura.md
│   ├── 02-scraper-inteligente.md
│   ├── 03-market-castilla.md
│   ├── 04-reportes-ejecutivos.md
│   └── 05-dashboard-central.md
├── scripts/
│   ├── monitor-vps.ps1        # Chequeo de salud de hosts/servicios → estado/status-*.json
│   └── generar-reporte.ps1    # Genera reporte ejecutivo desde el último status
├── config/
│   └── ecosistema.example.json  # Inventario del ecosistema (copiar a ecosistema.json y rellenar)
├── estado/                    # Salidas de monitoreo (JSON)
├── reportes/                  # Reportes ejecutivos generados (Markdown)
└── bitacora/                  # Registro de sesiones de Hermes
```

## Puesta en marcha (3 pasos)

1. **Inventariar el ecosistema**: copia `config/ecosistema.example.json` a `config/ecosistema.json` y rellena tus VPS (IPs Tailscale), servicios, URLs de Market Castilla, scrapers y APIs. Esta es la primera tarjeta del Kanban.
2. **Probar el monitor**: `powershell -File scripts/monitor-vps.ps1` — genera `estado/status-<fecha>.json` con el resultado de cada chequeo.
3. **Activar a Hermes**: abre una sesión de Claude Code en esta carpeta y dile: *"Lee el tablero Kanban y ejecuta las tarjetas en orden de prioridad siguiendo tu carta operativa."* CLAUDE.md hace el resto.

## Quién es Hermes (y dónde vive)

Hay **un solo Hermes**: el agente de Nous Research que el usuario utiliza **desde el panel web** — el mismo que trabajó en el proyecto Dona. Tres hechos que definen la arquitectura:

1. **El panel web corre en un sandbox remoto.** Hermes tiene ahí sus propias herramientas (terminal, navegador, búsqueda web, scripts), pero ese sandbox **no ve este PC ni la red Tailscale**. Hermes no puede ejecutar directamente los scripts de este repo ni hacer SSH por el tailnet.
2. **La app de escritorio está descargada pero nunca usada.** Si algún día se adopta, la skill propuesta en `integracion\hermes-skill\` le daría acceso local con el protocolo de este centro. Hasta entonces, es solo una opción.
3. **Claude Code es el ejecutor local actual**: al abrir sesión en esta carpeta carga `CLAUDE.md` y sí puede tocar el PC, el Task Scheduler y la red Tailscale.

**División de trabajo resultante:** Hermes (web) = estratega y brazo en internet (investigación, scraping, APIs, redacción de código y reportes en su sandbox); Claude Code (PC) = brazo local (monitor, SSH vía Tailscale, tareas programadas). El puente diario `apply-hermes-scout` (10:00) ya conecta los hallazgos de Hermes con Claude. La tarjeta **H-011** del tablero define cómo darle a Hermes acceso de lectura/escritura a este centro.

No confundir con `Dona-agent\hermes-poc` (el "segundo cerebro" de captura de pantalla): es un proyecto en el que Hermes trabajó, no el agente mismo.

## Repo público y datos sensibles

Este repositorio es **público** para que Hermes (panel web) pueda clonarlo sin token y para que sea revisable. Por eso hay una frontera estricta:

| Público (en el repo) | Solo local (git-ignored) |
|---|---|
| Specs de pipeline, scripts, plan, tablero, bitácora | `config/ecosistema.json` (IPs Tailscale, hosts) |
| Config de **ejemplo** con datos ficticios | `estado/*.json` (monitoreo real) |
| Skill de integración | `reportes/*.md` (reportes con datos reales) |

**Regla de oro:** ninguna IP, hostname ni secreto real entra en un archivo versionado. En la bitácora, refiérete a los nodos por nombre (`hermes-dona-vps`), nunca por IP. Si algún día necesitas versionar el inventario real, vuelve el repo privado primero.

## Principio rector

Los "logros" (autonomía, variedad de herramientas, volumen) **no se persiguen directamente: son el subproducto de trabajo real**. Este repositorio está diseñado para que cada sesión de Hermes sea larga, multi-herramienta y autónoma *porque el trabajo lo exige*, no porque se infle artificialmente.
