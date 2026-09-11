# Informe de auditoría — Fluvia

Parte de la auditoría de portafolio 2026-09 (H-014). Línea base y comandos:
`../evidencia/comandos-y-resultados.md`.

---

## 1. Ficha del repositorio

| Campo | Valor |
|---|---|
| Repositorio | `celestinojbm/Fluvia` |
| Rama por defecto | **`claude/new-session-haeo7h`** (no `main`) |
| HEAD auditado | `ed2f368` — merge PR #46, 2026-07-17 |
| Primer commit | 2026-07-04 · **273 commits** |
| Ramas remotas | **48** · tags: 0 |
| Autores principales | Claude (238), celestinojbm (33), Hermes Agent / Hermes Audit Agent (1 cada uno) |
| Lenguaje / runtime | TypeScript · Node ≥ 20 |
| Framework | Fastify + Zod (ADR-0010: sin NestJS) |
| Monorepo | pnpm + Turborepo · `packages/*`, `apps/*` |
| Base de datos | PostgreSQL 16 con **RLS forzado** y roles por plano de privilegio mínimo |
| Cola / eventos | outbox + inbox en PostgreSQL (sin Kafka por decisión) |
| Pagos | `MockProvider` únicamente; sin proveedor real, credenciales `live` bloqueadas por código |
| Deploy | Docker (`Dockerfile`, `docker-compose.yml`), CI con PG real + drills |
| Licencia | **no hay archivo LICENSE** (postura de licencias documentada en `docs/compliance/license-policy.md`) |
| Tamaño | 368 archivos de código, **~62.297 LOC**, 111 archivos de test |
| Documentación | 80+ documentos: `docs/adr/` (12 ADRs), `docs/architecture/`, `docs/security/`, `docs/compliance/`, `docs/audits/`, `docs/ops/runbooks/` (13 runbooks), `docs/agents/` |
| CI | `ci.yml`: jobs `quality` y `security` |
| PRs / issues abiertos | **12 PRs** / 0 issues |

## 2. Línea base reproducible

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | 7 s |
| `pnpm run build` (`turbo run build`) | exit 0 | 16 s |
| `pnpm run lint` (`eslint .`) | exit 0 | 4 s |
| `pnpm test` — **sin servicios** | exit 1 — 9 passed / 80 skipped (`ECONNREFUSED 127.0.0.1:5432`) | 8 s |
| `pnpm migrate` (PostgreSQL 16 real) | exit 0 — **45 migraciones** aplicadas | 4 s |
| `pnpm test` (PG 16, sin Redis) | exit 1 — 257 passed / 3 skipped; único fallo `test/rate-limit-redis.test.ts` (hook timeout por falta de Redis) | 76 s |
| `pnpm test` (**PG 16 + Redis reales**) | **exit 0 — todas las suites verdes** | 40 s |

Suites verdes con servicios reales: `@fluvia/api` (257+ tests), `@fluvia/worker`
(46), `@fluvia/sdk` (10), más los paquetes de ledger, money, outbox, inbox,
idempotencia, auth, identity, audit, observability.

**Conclusión de la línea base:** los dos únicos rojos fueron falta de PostgreSQL y
falta de Redis. **No hay suites rotas**: hay suites que no se estaban ejecutando
con sus dependencias reales. Ese es un hallazgo de proceso.

## 3. Arquitectura y límites de módulos

`packages/` (cada uno con límite y rol explícito):

| Paquete | Rol |
|---|---|
| `money` | Value Object `Money`: bigint en unidades menores, sin float, `allocate` sin pérdida |
| `db` | Migraciones (DDL + RLS forzado + inmutabilidad + invariantes del ledger a nivel de motor), runner, `withTenantTransaction`, roles por plano |
| `auth` | scrypt versionado, sesiones, verificación de email, lockout, anti-enumeración, MFA TOTP (RFC 6238, secreto cifrado, backup codes), step-up |
| `identity` | organizaciones, merchants, membresías, RBAC declarativo, API keys con scopes, customers |
| `audit` | log append-only con redacción de secretos; operaciones de plataforma con razón obligatoria |
| `ledger` | doble partida: `postTransaction` idempotente, proyecciones versionadas, Chart of Accounts cerrado, reglas de posting tipadas |
| `events` / `outbox` / `inbox` | envelope Zod; relay claim-lease con `SKIP LOCKED`, backoff+jitter, DLQ, replay auditado; inbox con firma HMAC verificada **pre-persistencia** |
| `idempotency` | claim en la misma transacción que el efecto, hash canónico, replay exacto, crash-safe |
| `payments-core` | FSMs declarativas (intent/attempt/refund/checkout session) forzadas **en el motor**, con meta-test doc↔TS↔DDL; `MockProvider` + `ResilientProvider` (timeout duro + circuit breaker) |
| `webhooks` | topics, firma versionada `v1=` con rotación dual, secretos cifrados, SSRF guard con pinning de IP |
| `observability` | counter/gauge/histogram propios + exposición Prometheus con guard de cardinalidad |

`apps/`: `api` (Fastify, health/readiness, dos planos de seguridad, catálogo de
errores v1 con golden), `worker` (relay, deliverer, inbox processor, watchdogs,
purga auditada, `/health`+`/metrics`), `checkout` (Next.js 15), `dashboard`
(Next.js 15).

**Fortaleza estructural:** los límites entre paquetes son reales y hay
**meta-tests** que impiden que la documentación y el código diverjan (FSM
doc↔TS↔DDL, chart↔SQL). Es la arquitectura mejor contenida del portafolio.

**Punto frágil:** el número de roles y planos de base de datos (app, worker,
relay, inbox, webhook, auth) es correcto en seguridad y caro en operación: cada
plano necesita su URL y su password gestionada. Ya está documentado, pero es el
coste estructural que más crecerá al escalar.

## 4. Riesgos técnicos

### (a) Funciona hoy — verificado

Ledger de doble partida con invariantes forzadas en PostgreSQL (balanceo diferido,
no-negatividad, inmutabilidad), reposteo/reversals compensatorios con reglas de
motor, proyecciones versionadas con rebuild y drift check programado, idempotencia
durable probada con carreras reales, outbox/inbox con DLQ y replay auditado, RLS
multi-tenant con suite de escape y meta-tests sobre `pg_catalog`, MFA TOTP
verificado contra vectores del RFC, API keys con HMAC + pepper y rotación,
checkout hospedado con i18n es/en y WCAG AA, conciliación con las cuatro clases de
discrepancia, SBOM + grype + gitleaks + auditoría de licencias transitivas en CI.

### (b) Bloquea una demostración

Nada relevante. Con PostgreSQL y Redis se levanta y se demuestra por completo
(verificado).

### (c) Bloquea cobrar — por diseño

1. **No hay proveedor real.** Fase 5 está bloqueada: `docs/compliance/production-gates.md`
   y `docs/product/mvp-scope.md` §2 establecen `MockProvider` únicamente.
2. **Credenciales `live` bloqueadas por código** hasta pasar los production gates.
3. **Matriz de jurisdicción sin verificación legal**: `docs/compliance/jurisdiction-matrix.md`
   tiene columna "Verificación" con **ninguna fila cerrada legalmente**
   (país inicial decidido: Colombia). Sin conclusiones legales por diseño.
4. **Aviso legal explícito**: Fluvia no es banco, adquirente, emisor, custodio ni
   procesador certificado (`README.md`), lo cual es correcto declararlo y también
   lo que impide cobrar hoy.

### (d) Deuda antes de producción

- **CI de Dependabot en rojo sistemático**: bumps agrupados (`minor-y-patch` con
  15 y 14 updates) y `node:22-slim → 25-slim` fallan todos. Hoy ninguna
  actualización de dependencias puede entrar sin trabajo de arreglo.
- **Rama por defecto no convencional** (`claude/new-session-haeo7h`): 48 ramas
  remotas, 12 PRs abiertos.
- **Rate limiter in-memory "Nivel C"**: documentado como suficiente para sandbox,
  insuficiente para sandbox compartido (PEND-006 abierta).
- **OTel diferido** hasta collector real; hoy la correlación extremo a extremo es
  `request_id` en logs y auditoría (desviación ya registrada en el repo).

### (e) Deuda posponible

Multi-país, proveedores múltiples, routing, disputas completas, billing complejo,
apps móviles, multirregión — todo explícitamente fuera del MVP
(`docs/product/mvp-scope.md` §4) y correctamente no construido.

### Auditoría independiente y su estado

El repo tiene un historial de auditoría serio y trazable, no decorativo:

- `docs/audits/independent-audit-v1/Fluvia_Independent_Audit_v1.md` (1.176 líneas)
  con hallazgos **inmutables**, plan de integración y registro de cierre con
  evidencia por hallazgo.
- `docs/audits/re-audit-v2-delta.md` y la re-auditoría F6 delta: los hallazgos
  RA-F6-001…005 y F6-DELTA-001 aparecen **cerrados con PR, commit y run de CI**
  (`docs/agents/BACKLOG.md` §RA-F6).
- F6 quedó aprobada para "sandbox cerrado" con ratificación explícita, y el
  `BACKLOG.md` deja escrito que **no autoriza producción/Fase 5/live**.

Esto es evidencia directa de que la disciplina de auditoría de este producto
funciona: los hallazgos se cierran con evidencia, no con prosa.

## 5. Frontend y producto

**`apps/checkout`** — Next.js 15 App Router, React 19, i18n es/en, WCAG AA,
tests jsdom + axe en CI y E2E de navegador local.
Rutas: `/c/[id]` (checkout hospedado) y `/l/[id]` (payment link), con route
handlers server-side `/api/checkout/[id]/status` y `/confirm` por `client_secret`.

**`apps/dashboard`** — Next.js 15. Mapa real de pantallas:

| Área | Rutas |
|---|---|
| Raíz y sesión | `/`, `/login`, `/signup`, `/onboarding`, `/logout` |
| Organización | `/o/[orgId]` (overview), `/o/[orgId]/merchants` |
| Pagos | `/payments`, `/payments/[paymentId]` |
| Reembolsos | `/refunds`, `/refunds/[refundId]` |
| Checkout sessions | `/checkout-sessions`, `/[sessionId]` |
| Payment links | `/payment-links`, `/[linkId]` |
| Payouts | `/payouts`, `/[payoutId]` |
| Disputas | `/disputes`, `/[disputeId]` |
| Conciliación | `/reconciliation`, `/[reportId]` |
| Casos operativos | `/cases`, `/cases/[caseId]` |
| Eventos de webhook | `/webhook-events`, `/[eventId]` |
| Endpoints de webhook | `/webhook-endpoints`, `/[endpointId]` |
| API keys | `/api-keys` |
| Eventos de auditoría | `/events` |

**Flujo principal demostrable:**
`signup → onboarding (organización + merchant) → API key sandbox → payment intent
→ checkout hospedado → confirmación → asiento en el ledger → webhook firmado →
dashboard → refund → conciliación`.

**Inventario de pantallas faltantes** (para una demo comercial completa):

1. Página de "estado del sandbox" honesta (qué es simulado y qué no) — crítico
   para no vender algo que parece producción.
2. Onboarding guiado tipo "primer pago en 30 minutos" con progreso visible
   (el criterio ya existe en `docs/product/mvp-scope.md` §5.4).
3. Vista de desarrollador consolidada (API keys + webhooks + eventos + SDK).
4. Panel de observabilidad operativa para el comercio (latencia, entregas
   fallidas, DLQ) más allá de la lista de eventos.
5. Estados vacío / carga / error explícitos y consistentes en las ~30 rutas.
6. Explicación visual del ledger (asientos de un pago y su refund) — es el
   diferencial técnico del producto y hoy no se muestra.

**Dirección visual recomendada:** sobrio y bancario; acento verde/teal profundo
sobre neutros fríos; tipografía neutra sin display; **movimiento mínimo, solo
confirmación**. Es un producto transaccional: la animación decorativa erosiona
confianza. La mono es obligatoria para ids, hashes y montos.

**Recomendación de imágenes:** UI product shots del dashboard y checkout con datos
de demo reales (el seed determinista ya existe: `pnpm seed`) + diagramas técnicos
(ledger, outbox/inbox, RLS, conciliación). **Sin fotografía genérica**: el
comprador es técnico-financiero y evalúa seriedad, no emoción.

**Nota de accesibilidad:** es el único producto del portafolio con WCAG AA
declarado y verificado con axe en CI (`axe-core` en `apps/dashboard` y
`apps/checkout`). Debe ser el estándar del portafolio, no la excepción.

## 6. Viabilidad de lanzamiento

| Dimensión | Definición |
|---|---|
| Usuario comprador | Plataforma o comercio digital que necesita cobrar y conciliar en Colombia, con equipo técnico capaz de consumir API |
| Problema vendible | Orquestar cobros, conciliación y webhooks con garantías contables reales es caro de construir y fácil de hacer mal |
| Propuesta de valor | Núcleo financiero con invariantes forzadas en el motor, idempotencia durable y trazabilidad de auditoría — vender "no pierdo dinero ni duplico cobros" |
| Alcance mínimo cobrable | **No definido todavía**: requiere proveedor real (Fase 5) y verificación legal de jurisdicción |
| Demo mínima | Flujo E2E del `docs/product/mvp-scope.md` §1 completo, con datos de demo (`pnpm seed`) — **sí es demostrable hoy** |
| Pricing inicial sugerido | **Decisión del propietario.** Insumo: la referencia es un modelo de plataforma (fee por transacción + suscripción), y el repo ya evalúa Lago para billing |
| Landing y materiales | No existe landing comercial; hay `apps/checkout` y `apps/dashboard`. Requiere una web de producto aparte |
| Pagos / onboarding / soporte | Onboarding sandbox ya construido (F6.5C); soporte y runbooks existen (13 runbooks operativos) |
| Métricas de activación / uso / conversión / retención / costo | Observabilidad técnica (Prometheus) y métricas de worker, pero **ninguna métrica de negocio** |
| Condiciones go/no-go | Ver `../plan-90-dias.md` §Gates (G-5) |

**Secuencia recomendada:** Fluvia es la **infraestructura más valiosa a largo
plazo y la mejor construida del portafolio**, pero su tiempo hasta la primera
venta se mide en meses y depende de un proveedor real y de verificación legal.
**No debe lanzarse antes que Dona** (ver `../matriz-comparativa.md` §6).

## 7. Backlog P0/P1/P2

Referencia completa en `../backlog-priorizado.md`. Resumen:

- **P0:** arreglar el CI de Dependabot (desbloquear el mantenimiento);
  checklist legal a revisión en Colombia; decisión humana registrada sobre Fase 5.1.
- **P1:** cerrar la verificación legal de la matriz de jurisdicción (F5.0);
  propagar tokens y componentes base a dashboard y checkout sin romper WCAG AA.
- **P2:** multi-país, proveedores múltiples, routing, disputas completas; OTel con
  collector real y tablero.

**Lo que no se propone:** ninguna intervención sobre el núcleo financiero (ledger,
idempotencia, outbox/inbox, RLS). Es la parte más auditada y mejor probada del
portafolio, y ninguna intervención de esta auditoría la requiere.
