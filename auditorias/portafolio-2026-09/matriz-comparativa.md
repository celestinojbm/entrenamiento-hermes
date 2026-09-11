# Matriz comparativa del portafolio — 2026-09

Base: línea base verificada de `evidencia/comandos-y-resultados.md` y los informes
por repositorio de `informes/`. Las cifras técnicas son medidas; las de negocio
están marcadas como **estimación** y se justifican.

---

## 1. Qué es cada cosa (y para quién)

| Producto | Categoría real | Usuario comprador | Relación con los demás |
|---|---|---|---|
| **Dona** | Producto: plataforma-agente de ejecución para pequeñas empresas | Dueño de negocio pequeño (LatAm/EEUU hispano, vía WhatsApp) | Consumidor potencial de Nova Context e de infraestructura Donalabs |
| **Nova Context** | Producto-plataforma: infraestructura de contexto humano | Individuo con alta carga de contexto; después, asistentes/empresas vía API | Puede ser capa de memoria de Dona y de otros agentes |
| **Fluvia** | Infraestructura: orquestación de pagos | Comercio/plataforma que cobra (decisor técnico-financiero) | Infraestructura de cobro potencial para Dona y para terceros |
| **EvolveOS** | Sistema operativo interno de empresa (no producto) | Fundadores/operadores propios | Marco de gobernanza para decidir sobre todo lo anterior |
| **Donalabs** | Plataforma de servicios compartidos self-hosted (no producto) | Los propios proyectos del portafolio y el operador | Base técnica de todos los demás |

Distinción que la matriz conserva explícitamente: **dos productos vendibles
(Dona, Nova Context), una infraestructura vendible a futuro (Fluvia) y dos
habilitadores internos (EvolveOS, Donalabs).** Tratarlos como cinco productos
equiparables es lo que hoy dispersa la energía.

---

## 2. Estado técnico medido

| Dimensión | Dona | Nova Context | Fluvia | EvolveOS | Donalabs |
|---|---|---|---|---|---|
| Lenguaje / runtime | Python 3.11+ (probado en 3.14) | TypeScript / Node ≥22 | TypeScript / Node ≥20 | TypeScript / Node ≥20 | TypeScript / Node ≥20 |
| LOC (código) | ~117.900 | ~36.600 | ~62.300 | ~14.700 | design system + infra |
| Archivos de test | 132 | 80 | 111 | 10 | sin suite |
| Tests verificados | 2360 pass / 1 fail / 61 err | unit 12/12 ws verdes; integración 245 pass / 0 fail | todas las suites verdes con PG+Redis | 432 pass / 0 fail | — |
| Install reproducible | sí | sí | sí | sí | sí |
| Build | n/a | sí | sí | sí | sí |
| Lint | **458 hallazgos** | n/a | limpio | n/a | limpio |
| CI en rama por defecto | Tests verde / **Security rojo** | verde | verde | verde | verde |
| Rama por defecto | `main` | `main` | **`claude/new-session-haeo7h`** | `main` | **`claude/donalabs-…`** |
| PRs abiertos | **24** | 1 | **12** | 0 | 1 |
| Issues abiertos | 0 | 0 | 0 | 11 | 0 |

---

## 3. Qué funciona hoy / qué bloquea qué

### 3.1 Funciona hoy (verificado)

- **Dona:** backend FastAPI completo y probado (2360 tests), billing con créditos
  Stripe, Action Center con niveles de riesgo, audit trail, landing + dashboard
  Next.js con checkout embebido. Pipeline de automatización operable.
- **Nova Context:** pipeline completo captura→redacción→media→timeline→búsqueda→
  aprobación→export/borrado, con cifrado AES-256-GCM, backups sellados, suites de
  aislamiento y de seguridad verdes, incluida la integración real con Postgres.
- **Fluvia:** ledger de doble partida con invariantes forzadas en el motor, RLS
  multi-tenant, idempotencia durable, outbox/inbox con DLQ y replay, MFA TOTP,
  API keys con pepper, conciliación, checkout hospedado con i18n y WCAG AA.
- **EvolveOS:** event log append-only verificable con cadena de hash, gate system
  v0, DRs inmutables, G-00 (stop manual) y CLI de auditoría; consistencia de spec
  validada en CI. **No existe UI todavía**: `app/` es un esqueleto de servicio
  TypeScript que solo expone `GET /health` (`docs/DEVELOPMENT.md`: "No UI
  (Next.js enters in Phase 1)").
- **Donalabs:** design system con tokens OKLCH, showcase, y orquestación de 7
  servicios self-hosted con backups y health checks.

### 3.2 Bloquea una demostración

| Producto | Bloqueo de demo | Gravedad |
|---|---|---|
| Dona | Producción suspendida + `ENVIRONMENT` fail-closed: la demo pública requiere infraestructura con secretos reales | Alta |
| Nova Context | Nunca desplegado; sin infraestructura los modos "en vivo" no se pueden mostrar con datos reales | Media |
| Fluvia | Requiere levantar Postgres+Redis y migrar (documentado y reproducible) | Baja |
| EvolveOS | Ninguno relevante: la consola corre con una base Postgres | Baja |
| Donalabs | Requiere Docker + ~8 GB RAM para el stack completo | Baja |

### 3.3 Bloquea cobrar

| Producto | Bloqueo de cobro | Gravedad |
|---|---|---|
| Dona | **Rotación de secretos pendiente**; quiet hours TCPA y detección STOP con hallazgos abiertos (riesgo legal directo al mensajear en EEUU); auth web provisional; `cryptography` con CVE sin poder actualizar por el techo de versión | **Alta** |
| Nova Context | Sin LICENSE y sin cadena de título verificada; sin despliegue real; sin evidencia de mercado | Alta |
| Fluvia | Sin proveedor real (Fase 5 bloqueada) y matriz de jurisdicción sin verificación legal | **Alta** (por diseño: es sandbox) |
| EvolveOS | No aplica hoy: su propio spec prohíbe mover dinero antes de la ratificación fundacional | — |
| Donalabs | No aplica: plataforma interna, no se vende | — |

### 3.4 Deuda antes de producción vs. deuda posponible

| Antes de producción (P0/P1) | Posponible (P2) |
|---|---|
| Dona: rotación de secretos, TCPA/STOP, auth web, techo de `cryptography`, ruido de gitleaks en tests, matriz de CI que incluya 3.14 (o pin explícito ≤3.13) | Dona: limpieza de `enhanced/`, `knowledge/`, `start.sh`, `config/business.yaml` huérfano, `migration.py` |
| Nova Context: LICENSE + postura de licencia, despliegue real con los gates de operador, revisión de cadena de título | Nova Context: API pública, marketplace, apps móviles, E2EE completo |
| Fluvia: decisión humana de Fase 5, verificación legal de la matriz de jurisdicción, arreglar ramas de Dependabot | Fluvia: multi-país, proveedores múltiples, disputas completas, routing |
| EvolveOS: ratificación fundacional (acto humano de lectura), extracción de esquemas machine-readable | EvolveOS: 60 de los 68 agentes, kernel completo, treasury, células por venture |
| Donalabs: no publicar backups, rotar credenciales de servicios, cerrar signups | Donalabs: Postgres para Vaultwarden/Open WebUI, Caddy para exposición pública |

---

## 4. Frontend: estado y distancia al objetivo

El propietario pidió "empezar a ver frontends de alta calidad en todos los
productos". Situación real por producto:

| Producto | Superficie frontend | Estado | Distancia a "premium demostrable" |
|---|---|---|---|
| Dona | `landing/` (Next.js 16 + NextAuth): landing, dashboard con chat, checkout, legales | Rediseño de hero sin mergear; auth provisional; env de Vercel vacías | **Media** — hay base (shadcn/Radix) y falta cerrar el flujo demostrable |
| Nova Context | `apps/web`, `apps/extension` (MV3), `apps/browser-shell` (Electron) | Funcional, orientado a alpha con 25 usuarios conocidos | **Media** — falta pulido de producto, no construcción |
| Fluvia | `apps/checkout` (Next.js 15, i18n, WCAG AA), `apps/dashboard` | El más maduro del portafolio en accesibilidad y contrato de UI | **Baja** — lo que falta es contenido de demo, no interfaz |
| EvolveOS | **No existe UI todavía.** `app/` es un esqueleto que expone `GET /health`; la consola Next.js está declarada para Fase 1 | Sin interfaz | **Alta** — hay que construirla, no rediseñarla |
| Donalabs | `design-system/apps/showcase` | Tokens OKLCH + componentes shadcn documentados | **Baja** — ya es el sistema, no un producto |

Lectura clave: **ningún producto está "sin frontend"**. El problema no es falta de
construcción, es falta de **coherencia y de cierre del flujo que se va a
demostrar**. Por eso el `sistema-diseno-compartido.md` propone fundamentos y
componentes, no una reconstrucción.

---

## 5. Viabilidad comercial comparada

| Dimensión | Dona | Nova Context | Fluvia | EvolveOS | Donalabs |
|---|---|---|---|---|---|
| Evidencia de mercado | Primeros usuarios reales (beta controlada) | Ninguna (sin usuarios) | Ninguna (sandbox) | Ninguna (interno) | Ninguna (interno) |
| Usuario comprador definido | Sí, claro | Sí, claro (2 segmentos) | Sí, claro | No aplica | No aplica |
| Alcance mínimo cobrable definible ya | **Sí** (créditos prepago + plan) | Sí (suscripción Pro) | No (requiere proveedor real) | No | No |
| Dependencia de terceros críticos | WhatsApp/Whapi, Anthropic, OpenAI, Stripe, Render, Supabase | Anthropic/OpenAI, Notion, Fly.io | Proveedor de pagos real (sin elegir), marcos legales | LLM | Docker, 7 upstreams |
| Tiempo hasta primera venta (estimación) | **4–8 semanas** si se reactiva producción y se cierra el hardening | 8–16 semanas (despliegue + alpha de 6 semanas) | 4–8 meses (Fase 5 + legal) | n/a | n/a |
| Riesgo principal de lanzamiento | Legal/cumplimiento (TCPA) y secretos | Despliegue nunca ejecutado + IP/licencia | Cumplimiento regulatorio de pagos | Teatralidad de proceso en n=1 | Ninguno comercial |
| ¿Debe lanzarse ahora? | **Sí, es el candidato nº1** | Después de Dona | No todavía | No | No |

Estimaciones: se basan en el trabajo ya identificado en cada repo (para Dona,
`docs/CURRENT_STATE.md` §"Próxima fase recomendada"; para Fluvia, la secuencia
F5.0→F5.4 documentada en `docs/phases/f5-preparation-plan.md`). No son
compromisos de fecha.

---

## 6. Secuencia recomendada

**Orden de lanzamiento: Dona → Nova Context → Fluvia. EvolveOS y Donalabs no se
lanzan; se usan.**

### Por qué Dona primero

1. Es el único producto con **usuarios reales** y con un camino de ingresos ya
   construido (créditos prepago + Stripe).
2. Su deuda de lanzamiento es **enumerada, acotada y conocida**, no difusa:
   rotación de secretos, TCPA/STOP, auth web y el techo de `cryptography`.
3. Ya tiene una suite de 2360 tests verdes: el riesgo de tocarla no es de
   regresión estructural sino de configuración y cumplimiento.
4. Es el proyecto más antiguo: lanzarlo primero también cierra la deuda histórica
   más cara de arrastrar (ver `decision-dona.md`).

### Por qué Nova Context segundo

1. Es el que **más rápido** produce una demo visualmente premium (extensión +
   web + captura en vivo) y el que valida una tesis de plataforma.
2. Su bloqueo no es técnico: es **despliegue real + LICENSE + cadena de título**,
   tres cosas administrativas con dependencia humana.
3. Tiene el mejor aparato de validación del portafolio (criterios de kill/pivot
   numéricos, alpha de 6 semanas, 25 usuarios objetivo): es un test falsable
   barato, que es exactamente lo que falta en el resto.

### Por qué Fluvia tercero

1. Es la **infraestructura más valiosa a largo plazo** y la mejor construida del
   portafolio, pero su tiempo hasta la primera venta se mide en meses y depende de
   un proveedor real y de verificación legal de jurisdicción (Fase 5).
2. Meterla antes que Dona consumiría el capital de atención en el producto con el
   camino de ingresos más largo.

### Por qué EvolveOS y Donalabs no se lanzan

- **EvolveOS** es un sistema operativo interno con usuarios declarados
  (fundadores). Su propio `docs/MVP_SCOPE.md` §2 prohíbe alcance externo. Su
  siguiente paso no es código: es la **ratificación fundacional** (lectura humana
  de Part 0 + Apéndice C + auditoría, ~30–40 min según
  `docs/BUILDABILITY_AUDIT.md` §8).
- **Donalabs** es plataforma de servicios internos. Su "lanzamiento" es
  operativo (cerrar signups, rotar credenciales, asegurar backups), no comercial.
  Es la base del `sistema-diseno-compartido.md`.

---

## 7. Qué frontend construir primero

Alineado con la secuencia de producto, no con la visibilidad:

1. **Dona — landing + flujo demostrable del dashboard** (`landing/`). Es lo que
   se enseña a un comprador en las próximas semanas, y ya existe la base
   (shadcn/Radix, modo oscuro) y un rediseño de hero sin mergear.
2. **Nova Context — web + extensión**: es el frontend que mejor comunica una idea
   nueva y el que menos trabajo necesita porque ya está construido.
3. **Fluvia — dashboard comercial**: ya está por encima del listón del
   portafolio en accesibilidad; lo que falta es material de demo.
- **Donalabs (showcase)** adopta los tokens, no se rediseña. **EvolveOS no tiene
  frontend todavía** (`app/` es un esqueleto con `GET /health`; la consola
  Next.js está declarada para Fase 1 y depende de la ratificación fundacional).
  Cuando se construya, debe nacer ya sobre los tokens compartidos.

---

## 8. Riesgo agregado del portafolio (visión de conjunto)

1. **Concentración en un solo humano** (bus factor 1) en los cinco repos.
2. **Cinco productos, una sola capacidad de atención**: es el riesgo estratégico
   real, no técnico. La secuencia de §6 existe precisamente para reducirlo.
3. **Dependencia de proveedores de IA** con coste variable en Dona y Nova Context.
4. **Documentación que supera sistemáticamente al código** en Nova Context y
   EvolveOS: excelente para diseño, peligrosa si se confunde con estado.
5. **Higiene de repositorio despareja**: dos repos con ramas por defecto
   `claude/…`, 36 PRs abiertos acumulados, Dependabot roto en dos repos.
