# Plan de 90 días — portafolio 2026-09

Base: `matriz-comparativa.md` §6 (secuencia) y `decision-dona.md` §4.1 (ruta
strangler para DONA). El plan asume **una sola persona con capacidad de atención
repartida**: por eso es secuencial donde hay conflicto de foco y paralelo solo
donde el trabajo es aditivo y de bajo riesgo.

**Principio rector del trimestre:** un producto a producción con primeros cobros
(Dona), un producto desplegado y validando tesis (Nova Context), una
infraestructura desbloqueada por decisión humana (Fluvia). No cinco frentes.

---

## Días 1–30 — "Cerrar la deuda que bloquea cobrar y ver el primer frontend"

Objetivo del mes: Dona deja de tener motivos para no cobrar.

| # | Tarea | Producto | Esfuerzo | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|
| 1.1 | Rotar secretos por proveedor (Anthropic, OpenAI, Stripe, Whapi, Supabase, R2, admin token) con fecha registrada | Dona | M | decisión humana (¿todos o por proveedor?) | Ningún secreto previo a la rotación sigue activo; registro con fecha |
| 1.2 | Subir el techo de `cryptography` a `<51` y verificar `pip-audit` | Dona | XS | — | Workflow `Security` → job `pip-audit` verde |
| 1.3 | Allowlist de fixtures de test en `.gitleaks.toml` | Dona | XS | — | Job `gitleaks` verde con hallazgos = 0 |
| 1.4 | Corregir quiet hours TCPA + robustecer detección STOP (más allá del set cerrado) | Dona | M | — | Suite verde + casos de prueba nuevos |
| 1.5 | Retirar `metadata.create_all()` del lifespan; Alembic como fuente única | Dona | M | 1.1 | Prueba de equivalencia en base limpia |
| 1.6 | `arq`/Redis como camino por defecto; `inproc` solo explícito | Dona | S | 1.1 | Test de supervivencia a restart |
| 1.7 | Limpiar `ruff`: aplicar las 446 correcciones automáticas y decidir las 12 restantes | Dona | S | — | `ruff check .` sin hallazgos |
| 1.8 | Corregir el test de observabilidad roto en Python 3.14 y fijar la matriz de CI (3.11/3.12/3.13 + 3.14 opcional) | Dona | S | — | Suite verde en la matriz declarada |
| 1.9 | **Fase A del sistema de diseño**: publicar el **contrato de tokens copiable** (no un paquete: `@donalabs/ui` es `private` con deps `workspace:*`) y añadir los grupos que faltan (estado, radios, elevación, movimiento) | Donalabs → todos | M | — | `tokens.css` versionado copiado en Dona/Fluvia/Nova; showcase actualizado |
| 1.10 | ~~Levantar los frontends y producir el mapa de pantallas~~ **HECHO en esta auditoría** (65 capturas, axe-core, móvil y escritorio). Queda: corregir los 4 defectos de accesibilidad del sistema de diseño (V2–V5) **antes** de propagarlo | Donalabs | S | 1.9 | 0 violaciones axe en el showcase |
| 1.12 | Cerrar el flujo demostrable del dashboard de Dona (I1) — **prerequisito para reactivar producción**, no posterior | Dona | L | — | Demo grabable < 5 min |
| 1.11 | Cerrar/actualizar los 24 PRs abiertos de Dona (mayoría Dependabot) y podar ramas remotas | Dona | S | — | PRs abiertos < 5; ramas remotas < 15 |

**Avance visible al día 30:** workflow `Security` de Dona completamente verde,
`ruff` limpio, el sistema de diseño sin defectos de accesibilidad, y el flujo del
dashboard de Dona cerrado y grabable. La auditoría visual ya está hecha: no hay
que levantarlos, hay que corregir lo que se midió.

---

## Días 31–60 — "Poner Dona en producción y desplegar Nova Context"

Objetivo del mes: hay un producto cobrando y un segundo producto con usuarios
reales.

| # | Tarea | Producto | Esfuerzo | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|
| 2.1 | **B4 — Auth web endurecido**, sustituyendo el provisional sin cambiar el contrato de sesión | Dona | L | 1.1 | Suite de auth web verde + revisión de seguridad sin hallazgos P1 |
| 2.2 | Reactivar producción: Render (backend) + Vercel (landing) con env vars y webhook Stripe verificado. **Condición de entrada: 1.12 (flujo del dashboard) cerrado** | Dona | M | 1.1–1.6, 1.12, 2.1 | Smoke test end-to-end contra producción real |
| 2.3 | Verificar el cobro end-to-end en producción (checkout → webhook → créditos → acción pagada) | Dona | S | 2.2 | Al menos un pago real registrado con su fila en `transacciones_credito` |
| 2.4 | **Fase C-bis del sistema de diseño**: cerrar el flujo demostrable del dashboard de Dona con los componentes base (AppShell, DataTable, StatusBadge, ApprovalCard, estados) | Dona | L | 1.9, 1.10 | Demo grabable del flujo principal en < 5 min |
| 2.5 | Decidir la fusión del rediseño de hero pendiente (`design/landing-hero-v2`) | Dona | XS | 1.9 | Decisión registrada (fusionar o descartar) |
| 2.6 | Arreglar CI de Dependabot en Fluvia (bumps agrupados y `node:22→25`) | Fluvia | M | — | Al menos un PR de Dependabot verde y fusionable |
| 2.7 | **Nova Context: LICENSE + postura de licencia** y NOTICE/atribución | Nova Context | S | decisión humana | LICENSE presente y postura registrada |
| 2.8 | **Nova Context: despliegue real** con los gates de operador (`validate:predeploy`) y backups sellados | Nova Context | L | 2.7 | `validate:predeploy` PASS contra infraestructura real; un deploy con smoke verde |
| 2.9 | Fluvia: llevar la matriz de jurisdicción (Colombia) a revisión legal | Fluvia | M | decisión humana | Checklist entregado a abogado; estado registrado (sin conclusiones legales) |
| 2.10 | EvolveOS: **ratificación fundacional** — el propietario lee Part 0 + Apéndice C + auditoría y aprueba o pide cambios | EvolveOS | S | decisión humana | PR #1 sale de draft o se registran los cambios pedidos |
| 2.11 | Donalabs: hardening operativo (cerrar signups, rotar credenciales, verificar restauración de backup) | Donalabs | M | — | `./scripts/health.sh` verde + una restauración probada |

**Avance visible al día 60:** Dona cobrando en producción, Nova Context desplegado
con datos de un usuario real, Fluvia con la vía legal iniciada.

---

## Días 61–90 — "Validar la tesis y desbloquear la infraestructura"

Objetivo del mes: evidencia de mercado para el segundo producto y decisión
tomada para el tercero.

| # | Tarea | Producto | Esfuerzo | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|
| 3.1 | Onboarding de los primeros usuarios de Dona tras reactivación; medir activación, uso y conversión | Dona | M | 2.2–2.4 | Métricas instrumentadas y leídas (no solo capturadas) |
| 3.2 | Nova Context: inicio del alpha de 6 semanas con ~25 usuarios instrumentados (`docs/MVP_SCOPE.md` §9) | Nova Context | M | 2.8 | Funnel `invoke → capture → link → action → return` medido por usuario |
| 3.3 | Nova Context: cerrar la documentación de bugs y el loop de feedback de alpha | Nova Context | S | 3.2 | `alpha_feedback` operativo; categorías revisadas semanalmente |
| 3.4 | Fluvia: **Fase 5.0** (verificación legal/matriz) y decisión humana sobre F5.1 (proveedor real) | Fluvia | M | 2.9 | Decisión registrada: avanzar a F5.1 o mantener freeze |
| 3.5 | Dona: **B6 higiene** — decidir restos huérfanos (`knowledge/`, `start.sh`, `config/business.yaml`, `migration.py`); `enhanced/` no se toca | Dona | S | 2.2 | Decisión registrada por archivo |
| 3.6 | Sistema de diseño: **Fase D** — propagar tokens y componentes base a Nova Context y Fluvia | Nova Context, Fluvia | L | 1.9 | Ambos usan los tokens compartidos; sin regresión visual |
| 3.7 | Revisión trimestral de go/no-go (ver §Gates) | todos | S | todo | Decisión escrita: qué se acelera, qué se mantiene, qué se detiene |

**Avance visible al día 90:** un producto cobrando con métricas leídas, un
producto con 25 usuarios reales en validación falsable, y una decisión explícita
sobre el producto de pagos.

---

## Gates de go/no-go

| Gate | Momento | Criterio cuantificable | Acción si falla |
|---|---|---|---|
| G-1: Dona puede cobrar | día 30 | `Security` verde + TCPA cerrado + secretos rotados | No reactivar producción; seguir en B1–B4 |
| G-2: Dona aguanta producción | día 60 | Un pago real end-to-end con su fila de créditos, sin incidentes P0 en 2 semanas | Volver a suspender producción y reabrir B2/B3 |
| G-3: Nova Context es desplegable | día 60 | `validate:predeploy` PASS en infra real + un deploy con smoke verde | Mantener alpha bloqueada (regla dura del propio repo) |
| G-4: Nova Context vale la pena escalar | día 90 | ≥ 2 de los 3 objetivos de la Tesis 1 de `docs/MVP_SCOPE.md` §1 en camino | Pivotar la wedge (integración como asistente primero) o parar |
| G-5: Fluvia avanza | día 90 | Decisión humana registrada sobre F5.1 | Mantener freeze de Fase 5; ningún trabajo de Fase 5 sin autorización |
| G-6: El portafolio no se dispersó | día 90 | No se abrió ningún frente nuevo fuera de este plan | Cerrar el frente abierto y volver al plan |

## Presupuesto de atención (la restricción real)

El factor limitante no es el dinero ni el código: es la atención de una persona
más la de sus agentes. El plan asigna por mes **un producto protagonista**:

- Mes 1: **Dona** (con Donalabs/design-system como soporte transversal).
- Mes 2: **Dona → producción** y **Nova Context → despliegue**.
- Mes 3: **Nova Context → alpha** (protagonista) con **Fluvia** desbloqueada solo
  por decisión humana, sin trabajo de construcción.

EvolveOS no consume capacidad de construcción en este trimestre: solo la lectura
de ratificación (días 31–60, ~40 min). Donalabs consume solo lo de 1.9 y 2.11.

## Lo que este plan NO hace

- No reescribe DONA (ver `decision-dona.md` §4).
- No construye features nuevas en ningún producto.
- No lanza los cinco productos a la vez, ni sugiere que se pueda.
- No mueve dinero, no despliega a producción ni compra nada: todo lo que toca
  infraestructura real está marcado como **decisión humana** y queda fuera de
  esta auditoría.
