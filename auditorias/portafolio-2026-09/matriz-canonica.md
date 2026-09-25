# Tabla canónica por producto (H-014, ronda 4)

**Fuente única de verdad del portafolio.** Si algún otro documento contradice esta
tabla, el documento está mal y hay que corregirlo, no esta tabla.

Responde al punto 1 de la revisión 5185022108: *"debe existir una única tabla
canónica por producto: prueba técnica, cobertura visual, demo, cobro,
limitaciones y evidencia"*.

Toda cifra de aquí tiene su fuente. **Lo que es estimación va marcado como
estimación.** Nada se presenta como medido si no está medido.

---

## Dona-agent

| Dimensión | Estado |
|---|---|
| **Prueba técnica** | En **Python 3.12**: `2422 pasan, 38 warnings, exit 0` (control positivo, `Dona-agent-python312.log`). En **Python 3.14** (el runtime del entorno): 1 fallo / 2360 pasan / 61 errores, por lo que la suite **no** está verde en el entorno ejecutado |
| **Cobertura visual** | Landing y login capturados con axe. **El dashboard autenticado NO está cubierto**: el gate exige un customer real de Stripe con suscripción activa y el secreto que deriva su contraseña. Se entrega **maqueta** del flujo prioritario (`dona-dashboard/`) |
| **Demo** | **No demostrable sin credenciales de Stripe.** No es un descuido: el login falla cerrado por diseño |
| **Cobro** | **Implementado en el código** (créditos + Stripe). No verificado de extremo a extremo en este entorno |
| **Limitaciones** | (a) La suite no pasa en el runtime del entorno; el control positivo en 3.12 sí. (b) El dashboard no es verificable sin Stripe. (c) `npm audit` de la landing: 7 vulnerabilidades (3 críticas, 3 altas), resolubles con `next 16.3.5`. (d) Dependencia con techo de versión que impide el fix (`cryptography` / PYSEC-2026-3552) |
| **Evidencia** | `informes/dona-agent.md`, `evidencia/Dona-agent-python312.log`, `evidencia/npm-audit.log`, `dona-dashboard/`, `propuestas/gitleaks-dona.toml` |

## Nova Context

| Dimensión | Estado |
|---|---|
| **Prueba técnica** | Integración **245 pasan / 0 fallan / 17 saltadas** con servicios reales (PG18 + pgvector, Redis). El primer intento dio 6 fallos por `pg_dump` ausente: era el entorno, no el código |
| **Cobertura visual** | **Sí, autenticada.** Recorrido real con cuenta sintética local (`dev@nova.local`) sobre copia aislada: 7 superficies, escritorio y móvil, con axe. Hallazgos **V23–V26** |
| **Demo** | **Sí, local.** Sesión sintética que atraviesa las APIs protegidas reales (`/v1/auth/me`, `/v1/sessions`, `/v1/integrations`, `/v1/media/usage`, `/v1/ops/status`), todas 200 |
| **Cobro** | **No implementado**: no hay pasarela en el código |
| **Limitaciones** | (a) **Ninguna superficie tiene `h1`** (V23). (b) Desborde móvil; **resuelto en 6 de 7** por el PR #19, con 1 px sub-píxel en `/settings`. (c) **Tarjetas de tarea ilegibles en móvil (V25), ya corregidas en PR #19**. (d) `color-contrast` serio (4 superficies) y `select-name` crítico (`/audit`) sin corregir (V26). (e) `lang="en"` en producto en español. (f) Sin `LICENSE`: es **pregunta de diligencia, no bloqueo operativo** |
| **Evidencia** | `informes/nova-context.md`, `nova-recorrido/` (15 capturas + JSON), PR `celestinojbm/nova-context#19` |

## Fluvia

| Dimensión | Estado |
|---|---|
| **Prueba técnica** | Suites verdes con PostgreSQL 16 y Redis reales |
| **Cobertura visual** | **Sí**, 13 rutas con **0 violaciones axe** — y **sin identidad visual**: navegación de enlaces por defecto y tarjetas planas (V17). Se entrega maqueta (`vistas-previas/fluvia-dashboard.html`) |
| **Demo** | **Técnicamente accesible, visualmente no presentable.** Con PostgreSQL y Redis arranca y sirve; lo que falta es producto, no funcionamiento |
| **Cobro** | Pasarela presente en el código; no verificada E2E en este entorno |
| **Limitaciones** | (a) **Bug de CSRF/`origin`**: el guard deriva el origen de `request.url`, así que `127.0.0.1` da 403 y `localhost` da 201 — verificado. (b) **Node 20 en fin de soporte** (desde 2026-04-30). (c) 36 PRs abiertos y Dependabot fallando. (d) Rama por defecto no convencional (`claude/...`) |
| **Evidencia** | `informes/fluvia.md`, `evidencia/Fluvia-*.log`, capturas en `evidencia-visual/` |

## EvolveOS

| Dimensión | Estado |
|---|---|
| **Prueba técnica** | **432 pasan / 0 fallan** con PostgreSQL real |
| **Cobertura visual** | **No aplica: no hay interfaz.** `app/src/index.ts` expone solo `GET /health`; `docs/DEVELOPMENT.md` lo dice: *"No UI (Next.js enters in Phase 1)"*. Se entrega **wireframe** priorizado, **no** una implementación |
| **Demo** | **No hay demo visual posible**: no existe UI que mostrar |
| **Cobro** | No aplica al alcance actual |
| **Limitaciones** | (a) Carece de interfaz. (b) La spec prohíbe mover dinero sin ratificación. (c) **Node 20 en fin de soporte** |
| **Evidencia** | `informes/evolveos.md`, `informes/evolveos-wireframe-console.svg` |

## Donalabs

| Dimensión | Estado |
|---|---|
| **Prueba técnica** | **Sin suite de comportamiento.** Su infraestructura Docker **quedó sin verificar** |
| **Cobertura visual** | **Sí**: showcase levantado y capturado, con axe |
| **Demo** | Showcase arranca y sirve. **No se declara "verde de extremo a extremo"**: no hay pruebas de comportamiento que lo respalden |
| **Cobro** | No aplica: es el sistema de diseño compartido |
| **Limitaciones** | (a) **Cuatro defectos de accesibilidad en el propio sistema de diseño** (V2–V5), que se propagarían a cuatro productos. (b) Sin suite. (c) Docker sin verificar. (d) La propuesta de tokens es **propuesta**, no está probada sobre los componentes reales del showcase |
| **Evidencia** | `informes/donalabs.md`, `sistema-diseno-compartido.md`, `vistas-previas/`, `propuestas/gitleaks-dona.toml` |

---

## Correcciones de coherencia aplicadas (punto 1)

| Afirmación previa | Dónde estaba | Corrección |
|---|---|---|
| *"el quinto no tiene suite y sí una interfaz sin auditar"* | `resumen-ejecutivo.md` | **Falso.** Donalabs **sí** fue auditado visualmente; **EvolveOS** es el que carece de interfaz |
| *"la atribución a 3.14 es una hipótesis fuerte pendiente de control positivo"* | `resumen-ejecutivo.md` §2.5 | **Ya no está pendiente**: el control positivo existe (`2422 pasan, exit 0`) |
| *"2360 tests verdes"* como descripción de la suite | `resumen-ejecutivo.md`, `matriz-comparativa.md` | Sustituido por la formulación exacta: **"2360 pasan dentro de una ejecución global fallida"** en 3.14, y **"2422 pasan con 38 warnings"** en 3.12 |
| *"Fluvia: nada, es accesible"* | `resumen-ejecutivo.md` | **Incompleto.** Es accesible y **visualmente no presentable** |
| *"EvolveOS: la consola corre"* | `resumen-ejecutivo.md` | **Falso.** No hay consola ni UI: solo `GET /health` |
