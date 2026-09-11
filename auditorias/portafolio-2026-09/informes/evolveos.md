# Informe de auditoría — EvolveOS

Parte de la auditoría de portafolio 2026-09 (H-014). Línea base y comandos:
`../evidencia/comandos-y-resultados.md`.

---

## 1. Ficha del repositorio

| Campo | Valor |
|---|---|
| Repositorio | `celestinojbm/EvolveOS` |
| Rama por defecto | `main` |
| HEAD auditado | `88103ee` — merge PR #34, 2026-07-19 |
| Primer commit | 2026-07-08 · **59 commits** |
| Ramas remotas | 14 · tags: 0 |
| Autores | Claude (46), celestinojbm (13) |
| Lenguaje / runtime | TypeScript · Node ≥ 20 |
| Naturaleza | **Especificación fundacional + esqueleto ejecutable**, no un producto |
| Monorepo | pnpm, workspace = `app/` |
| Base de datos | PostgreSQL 16 (7 migraciones) |
| Deploy | no hay despliegue: solo CI |
| Licencia | **no hay archivo LICENSE** |
| Tamaño | 40 archivos de código, **~14.714 LOC**; spec: 19 archivos, **~6.714 líneas** |
| Documentación | `spec/` (Partes 0–XV + Apéndices A/B/C), `docs/` (19 documentos: roadmap, MVP, backlogs, ADRs, schemas, event log, gate system, DR, auth, ratificación, stop, convenciones de auditoría) |
| CI | `app-ci.yml` y `spec-consistency.yml` |
| PRs / issues abiertos | 0 PRs / **11 issues** (backlogs de Fase 0/1) |
| Estado declarado | Draft v0.1: especificación completa, plan Fase 0–3, **esperando ratificación humana** |

## 2. Línea base reproducible

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | 2 s |
| `pnpm run build` (`prebuild` typegen + `tsc`) | exit 0 | 2 s |
| `pnpm test` — **sin PostgreSQL** | exit 1 — `Connection terminated unexpectedly` | 5 s |
| `pnpm migrate` (PostgreSQL 16 real) | exit 0 — **7 migraciones** aplicadas | — |
| `pnpm test` (PostgreSQL 16 real) | **exit 0 — 9 archivos, 432 tests passed, 0 failed** | 22 s |
| `python scripts/run_all_checks.py` | **RESULT: PASS** | <1 s |

Checks de consistencia de spec ejecutados y verdes: `expected files`,
`fenced blocks`, `gate range`, `agent references`, `taxonomies`, `table
integrity`, `markdown links`, `no placeholders`.

Desglose de la suite con base real: `audit-conventions` 127 tests,
`flags` 97, `gates` 57, `stop` 51, `dr` 48, `venture` 23, `auth` 18,
`eventlog` 9, `generated-types` 2. Los tests de `stop` incluyen escenarios de
concurrencia y de agotamiento de generación contra base aislada.

CI real: push a `main` (2026-07-19) → `app-ci` success (1m01s),
`spec-consistency` success (14s). El CI de app corre install → typegen → build →
guards de single-writer y drift → migrate (dos veces, para probar idempotencia) →
`verify:events` sobre cadena limpia → test, contra PostgreSQL real
(`docs/DEVELOPMENT.md` §CI). Es un CI de calidad alta.

## 3. Arquitectura y límites de módulos

**Corrección importante respecto a una lectura superficial:** **EvolveOS no tiene
interfaz de usuario.** `docs/DEVELOPMENT.md` §"Out of scope (deliberate)" dice
literalmente: *"No UI (Next.js enters in Phase 1)"*. `app/src/index.ts` es un
esqueleto de servicio con `GET /health`.

Lo que existe de verdad (`app/src/lib/`):

| Módulo | Rol |
|---|---|
| `eventlog.ts` | Log append-only con cadena de hash; sin UPDATE/DELETE por trigger |
| `gates.ts` | Gate registry como dato + mecánica de paso |
| `dr.ts` | Decision Records inmutables con id `DR-yyyy-seq` y canonización/digest compartido |
| `stop.ts` | G-00: stop manual de singleton, fail-closed, con generación y orden |
| `venture.ts` | Máquina de estados lineal de stages 1–12 con checklist de análisis y kill path |
| `auth.ts` | roles operator/approver/viewer con **proposer ≠ approver forzado en la capa de datos** |
| `ratification-core.ts` | Flag `real_money` **puramente derivado** de firmas humanas, sin override |
| `audit-conventions.ts` | Taxonomía de eventos y CLI `verify-log` |

`schemas/` (7 JSON) generan tipos TypeScript en `app/src/generated/` (git-ignored,
regenerados en cada build) para que los tipos **no puedan divergir** del esquema
canónico. `ops/` contiene typegen, el runner de migraciones y las migraciones SQL;
`scripts/` contiene los checks de consistencia en Python estándar (sin dependencias).

**Fortaleza estructural:** el diseño separa lo que es **dato** (gates, taxonomías,
esquemas) de lo que es **código**, y verifica la coherencia spec↔código↔docs en CI.
Es la arquitectura más ingeniosa del portafolio en términos de gobernanza.

**Punto frágil:** el sistema es **desproporcionado para su etapa**. El propio
`docs/BUILDABILITY_AUDIT.md` §3 lo reconoce: calibration-weighted consensus,
portfolio optimization, self-evolution, 60 de los 68 agentes y el kernel completo
**no son construibles ahora** porque dependen de datos o de estructura que no
existen (n=1 venture, sin historial etiquetado, sin entidad legal). El repo ya
tiene la respuesta correcta escrita: **implementar 8 gates, 7 roles de agente y un
"Minimal Kernel"** (ADR-001).

## 4. Riesgos técnicos

### (a) Funciona hoy — verificado

Event log append-only con hash chain **verificable y detectado en manipulación**
(los tests prueban detección de payload, actor, event_type, previous_hash y hash
alterados; y que `extract` se niega a extraer de una cadena globalmente inválida).
Gate system con evidencia obligatoria y exactamente un `gate_passed` por paso.
DRs inmutables con brief determinista ≤2 páginas. G-00 con asimetría de stop
(parar es inmediato, reiniciar requiere aprobador con razón). Separación
proposer≠approver forzada por datos. Consistencia de spec verificada en CI.

### (b) Bloquea una demostración

1. **No hay UI**: no hay nada que mostrar visualmente. Cualquier demo de EvolveOS
   hoy es una demo de CLI y de base de datos.
2. **PR #1 de la spec sigue en draft** esperando un acto humano de lectura
   (`docs/BUILDABILITY_AUDIT.md` §8).

### (c) Bloquea cobrar

No aplica: **EvolveOS no es un producto vendible**, es el sistema operativo interno
de la empresa. Además su propia especificación **prohíbe mover dinero antes de la
ratificación fundacional** (`docs/MVP_SCOPE.md` §2: "No treasury, payments, or any
money movement; no agent-adjacent spend before the Founding Ratification Pack is
signed").

### (d) Deuda antes de producción

- **Ratificación fundacional pendiente**: los umbrales de dinero del Apéndice C
  son `[ASSUMPTION]` sin ratificar; hasta que un humano los firme, el sistema
  mantiene **cero gasto agente-adyacente**.
- **Esquemas en prosa dentro de la spec** en lugar de archivos machine-readable
  versionados (el gap (e) del `BUILDABILITY_AUDIT` propone extraerlos; parte ya
  está hecho: existen 7 `schemas/*.json`, falta cerrar la validación de drift).
- **Sin LICENSE**.
- `G-07…G-15` inalcanzables por construcción (requieren entidad legal, banco y
  capital): correcto, no es deuda.

### (e) Deuda posponible

Kafka (Postgres basta hasta ~10⁵ eventos/día), SPIFFE/OPA/capability tokens,
motor de 19 gates (8 son ejercitables hoy), runtime de 68 agentes, metering de
tokens, knowledge graph + vector + marts, células por venture. El repo los
clasifica en el "Overengineering risk register" con disparador de reactivación
para cada uno — es exactamente la tabla que este informe habría escrito.

### Riesgo de proceso (el más relevante)

`docs/MVP_SCOPE.md` §7 nombra los **failure metrics** del sistema, y el más
peligroso es explícito: *"Two consecutive skipped weekly reviews (oversight
theater, the spec's named failure mode)"*. El sistema está diseñado para detectar
su propio modo de fallo — pero **solo si hay un humano ejecutando la revisión
semanal**. Con bus factor 1 y cinco productos abiertos, ese es el riesgo real.

## 5. Frontend y producto

**No hay frontend.** Verificado: `find EvolveOS/app/src -name "*.tsx"` no devuelve
nada; no existe `page.tsx` ni `route.ts`; el único endpoint es `GET /health`.
La consola Next.js está declarada para Fase 1 (`docs/MVP_SCOPE.md` §5) y su
construcción depende de ADR-008 (ya ratificado) y de la ratificación fundacional.

**Mapa de experiencia actual:** inexistente.

**Flujo principal que debe poder demostrarse (cuando exista la consola):**
`operator escribe opportunity brief → G-01 → agentes de investigación producen
borradores → G-02 → plan de validación → resultados → veredicto G-03 (go/kill) →
checklist de análisis → G-04 → prototipo → G-05 (primer R3, capital real)**.

Un **kill en G-03 es un resultado exitoso** del MVP (`docs/MVP_SCOPE.md` §3): el
entregable es el rastro de decisión, no la venture.

**Inventario de pantallas faltantes** (todas: es Fase 1):

1. Venture record con la máquina de estados 1–12 y el checklist de análisis.
2. Cola de gates con evidencia requerida y estado de aprobación.
3. Detalle y creación de DRs, con brief ≤2 páginas.
4. Base de conocimiento con provenance, confianza y validación humana.
5. Timeline del event log con verificación de cadena visible.
6. Estado del stop flag (G-00) siempre visible.
7. Cola de revisión semanal (la que evita la "teatralidad de proceso").

**Dirección visual recomendada:** institucional y serio — monocromo con un único
acento de aprobación; tipografía neutra densa (son tablas de gobernanza, no
marketing); **movimiento casi nulo**. La densidad y la legibilidad son la
estética: cada gate y cada DR debe poder leerse como documento, no como tarjeta.

**Recomendación de imágenes:** **diagramas de gobernanza** (gates, DR, cadena de
eventos, separación proposer/approver) y, más adelante, capturas de la consola con
datos de demo. **Nada de fotografía**: la fotografía de "startup" restaría
seriedad a un sistema cuya propuesta es el control.

**Nota crítica para el sistema de diseño:** cuando la consola se construya, debe
**nacer ya sobre los tokens compartidos** (`../sistema-diseno-compartido.md`),
no crear una quinta capa visual.

## 6. Viabilidad de lanzamiento

| Dimensión | Definición |
|---|---|
| Usuario comprador | **No aplica.** Los usuarios son los fundadores (2–5 personas): operator, approver, viewer, un `CURATOR` humano |
| Problema vendible | No aplica: es infraestructura de decisión interna |
| Propuesta de valor | Convertir la creación de empresas en un proceso con rastro auditable, gates nombrados y humanos obligatorios en lo irreversible |
| Alcance mínimo cobrable | No aplica |
| Demo mínima | CLI: crear venture → pasar G-01 con DR y kill criteria preregistradas → verificar cadena de eventos → extraer audit trail por fecha/venture |
| Pricing inicial sugerido | No aplica |
| Landing y materiales | No aplica |
| Pagos / onboarding / soporte | No aplica (prohibido por spec hasta ratificación) |
| Métricas de éxito | Sí definidas (`docs/MVP_SCOPE.md` §6): 100% de gate passes con DR + kill criteria; ≥20 KIs validadas humanamente; ≥50% de borradores de agente aceptados con ediciones menores; **0 acciones externas sin rastro humano** |
| Condiciones go/no-go | Ver `../plan-90-dias.md` §Gates. El siguiente paso **no es código**: es la ratificación fundacional |

**Secuencia recomendada:** EvolveOS **no entra en la secuencia de lanzamiento**.
Consume una sola acción en el trimestre: la **ratificación fundacional**
(lectura humana de Part 0 + Apéndice C + `docs/BUILDABILITY_AUDIT.md`, ~30–40 min
según el propio repo), tras la cual el PR #1 sale de draft y Fase 1 puede comenzar.
Ver `../matriz-comparativa.md` §6.

## 7. Backlog P0/P1/P2

Referencia completa en `../backlog-priorizado.md`. Resumen:

- **P0:** ninguna intervención urgente. El estado actual (spec completa, PR en
  draft, Fase 0 ejecutada) es coherente.
- **P1:** **ratificación fundacional** (decisión humana, ~40 min) — es el único
  desbloqueador; extraer esquemas machine-readable con validación de drift en CI.
- **P2:** 60 de los 68 agentes; kernel completo (SPIFFE/OPA/capability tokens);
  treasury; células por venture.

**Lo que no se propone:** construir la consola antes de la ratificación. El propio
`docs/BUILDABILITY_AUDIT.md` §8 es explícito: *"PR #1 should remain in draft until
one specific human act occurs"*. Construir UI antes de que los umbrales estén
firmados sería exactamente la "planning theater" que el repo nombra como riesgo.
