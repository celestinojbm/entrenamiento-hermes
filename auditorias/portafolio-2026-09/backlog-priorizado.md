# Backlog priorizado — portafolio 2026-09 (v2, reestructurado)

Responde a los bloqueadores nº5 y nº6 de la revisión:

- **nº5:** "el P0 no representa el camino mínimo hasta ingresos". La v1 mezclaba
  en P0 cosas que no bloquean cobrar (lint, poda de ramas, Dependabot, paquete de
  diseño, auditoría visual de todo el portafolio). Esta v2 **separa tres
  categorías** y deja claro cuál es la ruta mínima a ingresos.
- **nº6:** la propuesta de publicar `@donalabs/ui` como paquete consumible **no
  es consumible como está** (`private: true`, dependencias `workspace:*` en otro
  repositorio). Se sustituye por un **contrato de tokens copiable** hasta validar
  dos consumidores.

Convención de responsable: **Propietario** = decisión humana, no delegable ·
**Claude Code** = implementador primario · **Codex** = revisión no roja ·
**Hermes** = orquestación, evidencia y verificación.

---

## P0-I — Camino mínimo hasta ingresos (Dona)

**Definición de done de esta categoría:** un cliente real paga, el cobro se
registra, y el dashboard que se le enseña es presentable. Nada más entra aquí.

| # | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| I1 | **Cerrar el flujo demostrable del dashboard** (login → oportunidades → acción con riesgo → aprobación → ejecución → audit trail) sobre una demo con datos reales | L | — | Demo grabable < 5 min; capturas de cada pantalla del flujo | Claude Code |
| I2 | **Arreglar los 4 defectos visuales de la landing** (contraste de texto secundario, `link-in-text-block`, elemento decorativo roto del hero, tarjeta incompleta de "Seis módulos") | S | — | 0 violaciones axe *serious* en la landing; captura comparativa | Claude Code |
| I3 | Subir `cryptography` a `>=50` (quitar el techo `<50.0.0`) | XS | — | `pip-audit` sin PYSEC-2026-3552 | Claude Code |
| I4 | Subir `next` a 16.3.5 en `landing/` | S | — | `npm audit --omit=dev` sin critical/high | Claude Code |
| I5 | Subir `pytest` a `>=9.0.3` en `requirements-dev.txt` | XS | — | `pip-audit` sin PYSEC-2026-1845 | Claude Code |
| I6 | **Rotar secretos por proveedor** (Anthropic, OpenAI, Stripe, Whapi, Supabase, R2, admin token), empezando por dinero y mensajería | M | decisión del propietario | Ningún secreto previo activo; registro fechado | Propietario + Hermes |
| I7 | **Cerrar el flujo del dashboard ANTES de reactivar producción pública** — no después | M | I1 | Producción no se reabre mientras I1 no esté cerrado | Propietario |
| I8 | Reactivar producción (Render + Vercel) con env vars, webhook Stripe y provider WhatsApp verificados | M | I1, I3–I6 | Smoke test E2E contra producción real | Propietario + Hermes |
| I9 | Verificar el cobro E2E en producción | S | I8 | Un pago real con su fila en `transacciones_credito` | Hermes |

**Por qué I1 va antes que I8 (cambio respecto a la v1):** cobrar sin un dashboard
presentable significa vender con una demo que resta confianza. El orden correcto
es *cerrar el flujo → rotar secretos → reactivar → cobrar*.

### Lo que NO está en P0-I, aunque la v1 lo pusiera ahí

Lint limpio, poda de ramas, arreglo de Dependabot, paquete de diseño compartido y
auditoría visual de los cinco productos **no bloquean cobrar**. Bajan a
mantenimiento (§M) o a seguridad/legal (§P0-SL) según corresponda.

---

## P0-SL — Seguridad y legal (bloquean operar con seguridad o cumplir)

| # | Ítem | Repo | Esf. | CA | Resp. |
|---|---|---|---|---|---|
| S1 | **Aplicar la config de gitleaks por valor literal** (`propuestas/gitleaks-dona.toml`): suprimir 5 fixtures sintéticos sin cegar el gate | Dona | XS | Gate verde **y** un secreto sembrado sigue fallando (evidencia en `evidencia-gitleaks.md`) | Claude Code + Hermes |
| S2 | Corregir el comentario falso del workflow `security.yml` ("cryptography ya esta parchada") | Dona | XS | El comentario refleja el estado real | Claude Code |
| S3 | **Decisión sobre repositorios públicos**: hacer privados los que exponen diseño financiero (Fluvia) o lógica anti-abuso (Dona), o registrar por qué siguen públicos | todos | XS | Decisión escrita por repo | Propietario |
| S4 | **Decisión sobre la licencia de Dona (MIT)**: producto propietario o contribución abierta. Hoy convive con 4 repos sin licencia | Dona | XS | Decisión registrada | Propietario |
| S5 | Corregir quiet hours TCPA y robustecer la detección de STOP | Dona | M | Suite verde + casos nuevos | Claude Code + Codex |
| S6 | Endurecer el auth web (hoy provisional) | Dona | L | Suite de auth verde + revisión sin P1 | Claude Code |
| S7 | Arreglar el **guard CSRF**: no derivar el origen permitido de `request.url` en dev, o documentar el uso obligatorio de `localhost`; y dar un error distinguible al usuario | Fluvia | S | Acceder por `127.0.0.1` deja de romper mutaciones, o el error lo explica | Claude Code |
| S8 | `LICENSE` + postura de licencia + NOTICE en nova-context (pregunta de diligencia, **no** bloqueo de alpha) | Nova | S | Postura registrada | Propietario |
| S9 | Llevar el checklist legal de Colombia a revisión profesional | Fluvia | M | Checklist entregado; estado por fila | Propietario |

---

## P0-D — Desbloqueos de despliegue (alpha / demo de terceros)

| # | Ítem | Repo | Esf. | CA | Resp. |
|---|---|---|---|---|---|
| D1 | Arrancar los servicios reales y ejecutar los gates de operador (`validate:predeploy`) contra infraestructura real | Nova | L | `validate:predeploy` PASS; un deploy con smoke verde | Claude Code + Hermes |
| D2 | Higiene de la rama por defecto: mover Fluvia y Donalabs de `claude/…` a `main` (o justificar la excepción) | Fluvia, Donalabs | S | Rama por defecto convencional o excepción documentada | Propietario |
| D3 | Decisión humana sobre Fase 5.1 (proveedor real) | Fluvia | XS | Decisión escrita | Propietario |
| D4 | Ratificación fundacional (Part 0 + Ap. C + auditoría, ~40 min) | EvolveOS | XS | PR #1 sale de draft o se registran cambios | Propietario |

---

## P1 — Necesario antes de escalar

| # | Ítem | Repo | Esf. | CA | Resp. |
|---|---|---|---|---|---|
| P1.1 | Añadir Python 3.12 y 3.13 a la matriz de CI | Dona | S | Suite verde en 3.12 y 3.13 | Claude Code |
| P1.2 | Instrumentar y **leer** métricas de activación/uso/conversión de Dona | Dona | M | Métricas con acción asociada | Hermes |
| P1.3 | Onboarding + inicio del alpha de Nova (~25 usuarios) con funnel medido | Nova | M | Funnel por usuario | Propietario + Hermes |
| P1.4 | Operar el loop de feedback de alpha semanalmente | Nova | S | Revisión semanal registrada | Hermes |
| P1.5 | **Contrato de tokens copiable** (ver §contrato) aplicado a Fluvia y Nova | Fluvia, Nova | M | Ambos consumen el mismo archivo de tokens | Claude Code |
| P1.6 | **Diseñar el dashboard de Fluvia**: hoy la identidad visual es la del navegador (V17) | Fluvia | L | Dashboard con sistema, no con enlaces azules; axe sigue en 0 | Claude Code |
| P1.7 | **Dar identidad a Nova Context**: pantalla de login y shell de la app (V15) | Nova | L | Identidad propia; `h1` presente (V14) | Claude Code |
| P1.8 | Decidir `design/landing-hero-v2` (fusionar o descartar) | Dona | XS | Decisión registrada | Propietario |
| P1.9 | Corregir el `pattern` inválido del slug y poblar el selector de país del onboarding | Fluvia | S | Patrón válido; selector con opciones | Claude Code |
| P1.10 | Higiene de restos huérfanos de Dona (`knowledge/`, `start.sh`, `config/business.yaml`, `migration.py`); `enhanced/` no se toca | Dona | S | Decisión por archivo | Propietario |

---

## M — Mantenimiento (no bloquea cobrar; hacer cuando sobre capacidad)

| # | Ítem | Repo | Esf. | Nota |
|---|---|---|---|---|
| M1 | `ruff check .` limpio (446 correcciones automáticas + 12 manuales) | Dona | S | Deuda de lint, medida igual en 3.12 y 3.14 |
| M2 | Arreglar el CI de Dependabot (bumps agrupados, `node:22→25`) | Fluvia | M | Desbloquea el mantenimiento futuro, no el ingreso presente |
| M3 | Cerrar/actualizar los 24 PRs de Dona y 12 de Fluvia; podar ramas remotas | Dona, Fluvia | S | Higiene |
| M4 | `metadata.create_all()` fuera del lifespan; Alembic como fuente única | Dona | M | Con snapshot autogenerado + prueba de equivalencia |
| M5 | `arq`/Redis por defecto; `inproc` solo explícito | Dona | S | Test de supervivencia a restart |
| M6 | Actualizar `engines.node` a `>=22` (Node 20 **ya está EOL**) | Fluvia, EvolveOS, Donalabs | XS | Único ítem con fecha vencida; ver `matriz-actualizacion.md` §1 |
| M7 | Corregir los 4 defectos de accesibilidad del design system (V2–V5) | Donalabs | S | **Antes** de propagar tokens a otros productos |
| M8 | Extraer esquemas machine-readable con validación de drift | EvolveOS | M | Gap (e) de su `BUILDABILITY_AUDIT` |
| M9 | Hardening operativo de Donalabs (cerrar signups, rotar credenciales, probar restauración) | Donalabs | M | Operativo |

---

## P2 — Posponible sin bloquear nada

| # | Ítem | Repo | Nota |
|---|---|---|---|
| P2.1 | Saltos mayores de dependencias (`typescript` 7, `vitest` 5, `zod` 4, `next` 16 en Fluvia/nova, `pnpm` 12) | todos | **No actualizar ahora**: no compran seguridad ni lanzamiento. Ver `matriz-actualizacion.md` §2 |
| P2.2 | API pública, SDK, marketplace, plugins, apps móviles, E2EE completo | Nova | Fuera de MVP por decisión documentada |
| P2.3 | Multi-país, proveedores múltiples, routing, disputas completas | Fluvia | Fuera de MVP; requiere Fase 5 resuelta |
| P2.4 | 60 de los 68 agentes; kernel completo (SPIFFE/OPA); treasury; células por venture | EvolveOS | Después de Fase 3 |
| P2.5 | Postgres gestionado para Vaultwarden y Open WebUI; Caddy con dominios reales | Donalabs | Rutas ya documentadas |
| P2.6 | Librería de componentes publicada fuera del workspace | todos | Sin consumidores externos: coste sin usuario |

---

## Contrato de tokens copiable (sustituye a la propuesta de paquete)

**Lo que NO se hace:** publicar `@donalabs/ui` como paquete consumible desde los
otros repositorios. Es `private: true` y sus dependencias son `workspace:*`,
resueltas solo dentro del workspace de Donalabs. "Publicarlo consumible" no
describe un mecanismo real y crearía acoplamiento transversal que retrasaría el
primer lanzamiento.

**Lo que sí se hace (P1.5), en tres pasos:**

1. **Copiar el contrato, no depender de él.** Dona, Fluvia y Nova reciben un
   archivo `tokens.css` versionado (el mismo `globals.css` de Donalabs, con los
   grupos que faltan añadidos). Se copia, no se instala: cero acoplamiento de
   build y cero coste de publicación.
2. **Versionar con un número visible** (`/* tokens v1 (2026-09) */`) y registrar
   en cada repo de qué versión parte. Actualizar = diff manual consciente.
3. **Promover a paquete solo cuando existan dos consumidores validados** en
   producción con el archivo copiado. Ahí el paquete sí compra algo
   (evita el drift de tres copias) y el coste de mantenerlo se justifica.

**Coste:** XS por producto. **Rollback:** borrar el archivo; nada depende de él
en el build. **Riesgo:** drift entre copias — mitigado por el paso 3.

---

## Criterio de uso

1. Nada de P1 antes de P0 en el mismo producto.
2. **P0-I es la única categoría que produce ingresos.** Si hay que elegir, se
   elige P0-I.
3. Los ítems de **P0-SL** con responsable `Propietario` no se ejecutan sin
   decisión humana explícita.
4. Ningún ítem de este backlog introduce features nuevas.
