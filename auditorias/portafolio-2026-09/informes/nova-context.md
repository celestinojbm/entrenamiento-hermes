# Informe de auditoría — Nova Context

Parte de la auditoría de portafolio 2026-09 (H-014). Línea base y comandos:
`../evidencia/comandos-y-resultados.md`.

---

## 1. Ficha del repositorio

| Campo | Valor |
|---|---|
| Repositorio | `celestinojbm/nova-context` |
| Rama por defecto | `main` |
| HEAD auditado | `c49ef4d` — merge PR #17, 2026-07-22 |
| Primer commit | 2026-07-09 · **53 commits** |
| Ramas remotas | 20 · tags: 0 |
| Autores principales | Claude (33), celestinojbm (20) |
| Lenguaje / runtime | TypeScript · Node ≥ 22 (`.nvmrc`) |
| Framework | Fastify (API) + Next.js (web) + extensión Chromium MV3 + Electron (browser-shell) |
| Monorepo | pnpm + Turborepo · `apps/*`, `services/*`, `packages/*`, `tools/*` |
| Base de datos | PostgreSQL 16 + **pgvector** (13 migraciones) |
| Cola | Redis (enriquecimiento / worker) |
| Storage | filesystem local o S3-compatible (MinIO, R2) |
| Integraciones | Notion (única, por OAuth) |
| Deploy | Fly.io (configs listas en `infra/`), preflight/smoke/maintenance/report |
| Licencia | **no hay archivo LICENSE** — riesgo R-13 documentado |
| Tamaño | 246 archivos de código, **~36.598 LOC**, 80 archivos de test |
| Documentación | ~40 documentos: manifiesto, principios, arquitectura por engine, MVP, roadmap, build plan, AUTH, seguridad/gobernanza, runbooks, guía de alpha, paquete de adquisición |
| CI | `ci.yml` (un workflow) |
| PRs / issues abiertos | 1 PR / 0 issues |
| Estado declarado | **M15 — Alpha Blocker Remediation**; alpha privada **bloqueada** |

## 2. Línea base reproducible

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | — |
| `pnpm run typecheck` | exit 0 | — |
| `pnpm run build` | exit 0 | ~15 s |
| `pnpm run test` (unit, 12 workspaces) | **exit 0** (`@nova/api` 109 tests; `@nova/validation-gate` 106 tests) | 16 s |
| `pnpm db:migrate` (PG 18.6 + pgvector 0.8.6) | exit 0 — **13 migraciones** | 2 s |
| `pnpm test:integration` (PG 18 + pgvector + Redis) | **exit 0 — 245 passed, 17 skipped, 0 failed** | 78 s |

Nota de método: la primera pasada de integración dio 6 fallos, todos en
`test/integration/m18a-backup-sh.test.ts`, por `pg_dump: command not found` — un
problema de `PATH` del arnés, no del código. Con `pg_dump` en `PATH` la suite
quedó **completamente verde**. Queda registrado precisamente porque demuestra que
el fallo era del entorno de ejecución.

CI real: workflow `ci` en `main` → **success** (push 2026-07-22, 9m37s). Sin runs
fallidos recientes.

## 3. Arquitectura y límites de módulos

Estructura real (verificada en el árbol):

- `packages/context-engine` — **existe de verdad**, y es la pieza más rica:
  `capture-mode.ts`, `consent.ts`, `live-buffer.ts`, `local-enrichment.ts`,
  `media-gate.ts`, `object-store.ts`, `redaction.ts`, `visual-redaction.ts`,
  `secret-box.ts`, `suggest.ts`, `notion-mapping.ts`, `notion-page.ts`,
  `data-url.ts` (la mayoría con su `.test.ts` al lado).
- `packages/model-router` — **existe parcialmente**: `intent/`, `embedding/`,
  `enrichment/`, `live/`, `transcription/`, `types.ts`.
- `packages/schema`, `packages/config` — reales.
- `services/api` — Fastify + PostgreSQL + migraciones + `auth/`, `media/`,
  `backup/`, `integrations/`, `ops/`, analítica y rutas `routes-m1…m4`.
- `services/worker` — `enrich.ts`, `actions.ts`, `notion-client.ts`,
  `media-reader.ts`, `heartbeat.ts`.
- `tools/validation-gate` — orquestador `validate:pr` con semántica go/no-go y
  reportes JSON/Markdown/JUnit.
- `apps/web`, `apps/extension` (MV3), `apps/browser-shell` (Electron).

**Fortaleza:** el design-first está disciplinado — cuatro "engines" declaradas
(contexto, memoria, inteligencia, acción) con contratos escritos antes que código,
y el API como contrato (`docs/API_AND_SDK_SPEC.md`).

**Punto frágil real — y el más importante de este informe.** Existe una brecha
**verificable** entre la arquitectura documentada y los límites reales del código:

- Se documentan **cuatro engines**: Context, Memory, Intelligence y Action
  (`docs/CONTEXT_ENGINE.md`, `MEMORY_ENGINE.md`, `INTELLIGENCE_ENGINE.md`,
  `ACTION_ENGINE.md`, y el diagrama de `README.md`).
- El código solo tiene **dos paquetes** que correspondan a esa idea:
  `packages/context-engine` y `packages/model-router`. **No existen
  `packages/memory-*` ni `packages/action-*`** (verificado con `ls packages`).
  La memoria y las acciones viven dentro de `services/api` (`routes-m1…m4`,
  `media/`, `auth/`, `integrations/`) y `services/worker` (`actions.ts`,
  `enrich.ts`), no como subsistemas con límite propio.

Además, el propio repo declara estado de "walking-skeleton" (`README.md`
§Contributing) y `MVP_SCOPE.md` §5 deja fuera knowledge graph, consensus routing,
marketplace, API pública y apps móviles. **El riesgo no es que falte código: es que
la documentación se lea como estado.** Este informe no confunde una cosa con la
otra: la línea base de §2 prueba que lo que existe funciona, y esta sección acota
lo que no existe todavía.

## 4. Riesgos técnicos

### (a) Funciona hoy — verificado

Pipeline completo y probado end-to-end: captura → redacción visual por OCR →
media cifrada AES-256-GCM → timeline → búsqueda híbrida → tareas/aprobaciones →
export/borrado de cuenta. Además, verificado por suite: aislamiento por usuario
(cross-user 404), middleware fail-closed, redacción visual fail-safe (un screenshot
cuya redacción falla **nunca** se guarda legible), backups sellados con
`NOVA_BACKUP_KEY` separada y verificación de descifrado, rate limiter que falla
**cerrado** si Redis cae, `/readyz` que no filtra detalle interno, y la suite de
integración real (245 tests) verde.

Es un aparato de privacidad y seguridad **por encima de la media del portafolio**,
y contrasta con su estado comercial: hay producto técnico sin mercado.

### (b) Bloquea una demostración

1. **Nunca desplegado a infraestructura real.** El propio repo es honesto: M14 fue
   un "dress rehearsal" en modo producción sin credenciales cloud
   (`docs/ALPHA_RUN.md`), y M18 "no provisioning, no costs".
2. **Regla dura autodeclarada**: "no real user data until the operator explicitly
   approves" (`README.md`). Es correcta y también el bloqueo de la demo con datos
   reales.

### (c) Bloqueos comerciales — hay que separar tres cosas que no son la misma

La fuente de estos riesgos es `docs/acquisition/ACQUISITION_READINESS.md` y su
`RISK_REGISTER.md`, que son un paquete de **acquisition readiness**. Ese paquete
evalúa **vender o transferir el activo**, no operar el producto. Mezclarlas lleva a
conclusiones equivocadas, así que aquí quedan separadas.

**(c.1) Bloquea la demo / la alpha privada**

- **Infraestructura real nunca ejecutada.** El propio repo lo dice sin adornos:
  M14 fue un *dress rehearsal* en modo producción sin credenciales cloud
  (`docs/ALPHA_RUN.md`) y M18 se describe como "no provisioning, no costs".
  Sin despliegue no hay alpha con datos reales.
- **Regla dura autodeclarada:** "no real user data until the operator explicitly
  approves" (`README.md`). Correcta, y también el freno de la demo.
- **Ninguno de los dos es un problema de licencia ni de cadena de título.**

**(c.2) Bloquea vender suscripciones (SaaS)**

- **Ausencia de `LICENSE`.** Con matiz importante y citable: sin licencia aplica
  el régimen por defecto de *todos los derechos reservados*. Para **vender un
  servicio** eso no es un bloqueo: el titular no necesita licenciarse a sí mismo
  para operar su propio software. Es una **pregunta de diligencia y de postura
  declarada**, no un impedimento operativo.
- **Cobro no implementado.** No hay pasarela ni flujo de pago en el código
  revisado. Esto sí bloquea cobrar, y es trabajo, no papeleo.
- **Sin evidencia de demanda** (R-04): cero usuarios, cero waitlist, cero LOIs.
  Bloquea *decidir* cobrar, no *poder* cobrar.

**(c.3) Bloquea vender o transferir el activo (adquisición)**

Aquí — y solo aquí — los hallazgos del paquete de adquisición son bloqueadores:

- **R-01, cadena de título no verificada (P0).** Propiedad personal
  `operator_attested`, sin paquete documental ni revisión profesional. El propio
  documento advierte: *"do not treat attestation as documentary evidence"*. Capa el
  score de adquisición en ≤70 y puede bloquear una compra por sí solo.
- **R-13, postura de licencia sin decidir.** Distinto de la propiedad: es qué
  licencia se concede al comprador. Sin decidir es una pregunta de diligencia.
- **R-05, transferibilidad de proveedores** (Anthropic/OpenAI/Notion/Fly):
  bloqueador condicional de transferencia.
- **R-03, bus factor 1** en cuentas, claves y decisiones.

**(c.4) Riesgo omitido en la versión anterior de este informe: repositorios
públicos.** Los cinco repos auditados son **públicos** (`isPrivate: false` en la
API de GitHub, verificado en la línea base). Consecuencias que esta auditoría debe
nombrar y no nombraba:

- El código, los hallazgos de seguridad y la arquitectura son visibles para
  cualquiera, incluidos competidores. En Fluvia hay documentación de diseño de un
  ledger financiero; en Dona, el aparato de cobro y anti-abuso.
- **`gitleaks` corriendo en un repo público no es higiene: es control de daño
  activo.** Un secreto filtrado en un repo público se considera comprometido de
  inmediato, y el gate de Dona lleva tres semanas en rojo (§4c del informe de Dona).
- Para Nova Context, el paquete de adquisición exige *"no exponer secretos ni datos
  sensibles"*: hoy no los hay, pero la superficie pública hace que cualquier error
  futuro sea irreversible.
- **Mitigación concreta:** mantener públicos solo los repos que aporten valor de
  portafolio o contratación, y hacer privados los que contengan diseño financiero
  sensible (Fluvia) o lógica anti-abuso (Dona) si no hay una razón de negocio para
  exponerlos. Decisión del propietario; coste cero.

### (d) Deuda antes de producción

- Despliegue real nunca ejecutado (R-02).
- `bus factor 1` (R-03): una persona sostiene cuentas, claves y decisiones.
- Inventario de licencias transitivas incompleto (212 paquetes de producción
  enumerados, revisión transitiva incompleta).
- Falta `NOTICE`/atribución para datos CC-BY y componentes empaquetados.

### (e) Deuda posponible (y correctamente pospuesta)

API pública, SDK para terceros, marketplace, plugins, multi-model consensus,
knowledge-graph UI, apps móviles iOS/Android, E2EE completo, LLM local, navegadores
no-Chromium, i18n — todo explícitamente fuera de MVP (`docs/MVP_SCOPE.md` §5) con
justificación de una línea por ítem. Es la mejor disciplina de alcance del
portafolio.

### Observabilidad, analítica y costo

- Eventos permitidos por allowlist, props numéricas/cortas, switch
  `NOVA_ANALYTICS=off`.
- `ops:report` con conteos, fricción, acciones fallidas con razón, gasto por
  proveedor, storage, umbrales de aviso.
- Coste de IA: **observado, no controlado**. No hay presupuesto ni cap por
  proveedor en el código revisado; el gasto se reporta a posteriori.

## 5. Frontend y producto

**`apps/web`** — Next.js. Rutas reales:

| Ruta | Función |
|---|---|
| `/` | Timeline de memoria (búsqueda híbrida) |
| `/login`, `/reset` | Sesión y reseteo de contraseña |
| `/projects`, `/projects/[id]` | Proyectos y su detalle |
| `/approvals` | Cola de aprobación de acciones Tier-1 |
| `/tasks` | Tareas propias de Nova (Tier-0) |
| `/audit` | Log de auditoría legible por el usuario |
| `/settings` | Ajustes, conexión Notion, exportación, borrado |
| `/status` | Estado autenticado (colas, salud, features) |
| `/api/pairing`, `/export`, `/export/account`, `/integrations/notion/*`, `/media/[id]` | Emparejamiento, export, OAuth Notion, media autenticada |

**`apps/extension`** — MV3: `Onboarding.tsx` (gate de consentimiento),
`Connect.tsx` (emparejamiento por código de 8 dígitos), `App.tsx` (captura),
`LivePanel.tsx` (modo vivo acotado).

**Flujo principal demostrable:**
`onboarding/consentimiento → emparejar extensión → captura con instrucción por voz
→ Context Moment → sugerencia de proyecto → acción Tier-0 o Tier-1 → aprobación →
timeline → búsqueda → export/borrado`.

**Inventario de pantallas faltantes** (para un alpha creíble con 25 usuarios):

1. Estado de "primera captura" con guía paso a paso (el onboarding actual es
   consentimiento, no activación).
2. Explicación visual del Context Moment (qué se capturó, qué se redactó, qué se
   subió) — es el diferencial de privacidad y hoy no se ve.
3. Vista de proyecto con grafo/colección legible (hoy es lista).
4. Estado degradado honesto cuando un proveedor cloud no está configurado
   (existe el dato, falta superficie).
5. Pantalla de consumo/cuota si el alpha empieza a medir gasto.
6. Estados vacío / carga / error consistentes en toda la web.
7. Vista de confianza: qué captura Nova, qué nunca captura, qué es local —
   ya existe en `docs/ALPHA_GUIDE.md`, no en la interfaz.

**Dirección visual recomendada:** preciso y etéreo — "infraestructura", no
"asistente". Acento frío alto (azul-violeta), kickers en mayúsculas editoriales,
movimiento de flujo que haga visible el ciclo captura→acción (es el único producto
del portafolio donde el motion tiene función pedagógica real).

**Recomendación de imágenes:** UI product shots del ciclo de captura +
diagramas del Context Moment + un motion corto de 5–10 s que muestre
"capturo → se redacta → se convierte en acción". **Sin** metáforas de cerebro,
nubes o redes neuronales: el producto es infraestructura medible.

## 5.1 Estado visual medido con navegador (ronda 2)

Las 4 rutas capturadas (`/login`, `/reset`, `/`, `/approvals`) **renderizan todas
la misma pantalla de login**: no existe superficie pública. Detalle en
[`../auditoria-visual.md`](../auditoria-visual.md) §4.

| # | Hallazgo | Evidencia |
|---|---|---|
| V14 | **No hay `h1` en ninguna página**: el encabezado "Sign in to Nova" es un **`<h2>`**, así que el documento no tiene H1 | volcado de DOM |
| V15 | La pantalla es **visualmente genérica**: formulario centrado con bordes por defecto, sin sistema de diseño ni marca más allá del texto "Nova Context", enlace azul subrayado del navegador | captura `nova__login__desktop.png` |
| V16 | **Idioma del producto en inglés** (`lang="en"`) mientras Dona, Fluvia y Donalabs están en español | métrica `lang` |

**Lo que está bien y está medido:** 0 violaciones axe en las 4 rutas, 0 errores de
consola, sin desbordes horizontales en escritorio ni móvil, y un mensaje de
privacidad honesto y específico ("your captured context is private to your
account: sessions expire, and you can revoke any device from Settings").

### Corrección de un falso positivo propio

En la primera medición reporté **"3 inputs sin etiqueta"** en `/login` y `/reset`.
**Era un falso positivo de mi heurística**: solo comprobaba `label[for]`,
`aria-label` y `placeholder`, pero los campos usan **`<label>` envolvente**, que
sí produce nombre accesible ("Email", "Password", "Account email"). axe-core, que
calcula el nombre accesible real, **no reportó ninguna violación**, y tenía razón.
Se deja constancia porque la primera medición estaba mal.

**Limitación de alcance:** la timeline, proyectos, aprobaciones, tareas,
auditoría y settings **no son auditables visualmente** sin sesión, y el propio
repo exige aprobación explícita del operador antes de usar datos reales
(`README.md`). Queda como **no verificado**, no como "sin problemas".

## 6. Viabilidad de lanzamiento

| Dimensión | Definición |
|---|---|
| Usuario comprador | (1) Individuo con alta carga de contexto que vive en el navegador y ya usa Notion; (2) a futuro, asistentes/empresas vía API |
| Problema vendible | "Lo que veo y me importa se pierde; las capturas no preservan intención y las notas no las escribo" |
| Propuesta de valor | Captura explícita en <30 s que preserva percepción + intención + conexión, con memoria que sobrevive a cualquier asistente |
| Alcance mínimo cobrable | Suscripción Pro de la extensión+web (un usuario, inglés, Notion, tarea propia). **Definible hoy**, pero no ejecutable sin despliegue |
| Demo mínima | Captura de pestaña con instrucción de voz → Context Moment → acción → aparece en timeline y búsqueda |
| Pricing inicial sugerido | **Decisión del propietario.** El repo ya define Free → Pro → Teams → Enterprise y fee de plataforma (`docs/BUSINESS_MODEL.md`) |
| Landing y materiales | No hay landing comercial; `docs/WHY_NOW.md` y el manifesto son material de inversión, no de venta |
| Pagos / onboarding / soporte | Onboarding y guía de alpha existen; **falta cobro** (sin Stripe/pasarela en el código revisado) |
| Métricas de activación / uso / conversión / retención / costo | **Las mejores del portafolio**: el `MVP_SCOPE.md` §9 define el funnel, los targets y los umbrales numéricos de kill/pivot antes de construir |
| Condiciones go/no-go | Ver `../plan-90-dias.md` §Gates (G-3 y G-4) |

**El activo más valioso de Nova Context no es el código: es tener criterios de
falsación numérica decididos de antemano.** Eso lo hace el test más barato del
portafolio. Su bloqueo es administrativo (LICENSE, cadena de título, despliegue),
no técnico.

**Secuencia recomendada:** **producto nº2**, después de Dona. Ver
`../matriz-comparativa.md` §6.

## 7. Backlog P0/P1/P2

Referencia completa en `../backlog-priorizado.md`. Resumen:

- **P0:** `LICENSE` + postura de licencia + NOTICE; ejecutar los gates de operador
  contra infraestructura real (`validate:predeploy`) y un deploy con smoke verde;
  iniciar la verificación documental de la cadena de título.
- **P1:** onboarding e inicio del alpha (~25 usuarios) con funnel instrumentado;
  loop de feedback operado semanalmente; inventario transitivo de dependencias;
  propagar tokens y componentes base a `apps/web`.
- **P2:** API pública/SDK/marketplace/plugins; apps móviles; E2EE completo; ampliar
  cobertura de integración.
