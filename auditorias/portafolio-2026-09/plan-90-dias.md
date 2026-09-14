# Plan de 90 días — portafolio 2026-09

Base: `matriz-comparativa.md` §6 (secuencia) y `decision-dona.md` §4.1 (ruta
strangler para DONA). El plan asume **una sola persona con capacidad de atención
repartida**: por eso es secuencial donde hay conflicto de foco y paralelo solo
donde el trabajo es aditivo y de bajo riesgo.

**Principio rector del trimestre:** un producto a producción con primeros cobros
(Dona), un producto desplegado y validando tesis (Nova Context), una
infraestructura desbloqueada por decisión humana (Fluvia). No cinco frentes.

---

## Días 1–30 — la cadena mínima hasta poder cobrar

**Reconstruido desde el resultado, no desde la deuda.** Antes mezclaba
mantenimiento con lanzamiento (Ruff, poda de PRs, propagación de tokens, Alembic),
y eso no es la ruta a ingresos. Ahora sólo hay tres bloques, **en este orden**, y
todo lo demás vive en §"Mantenimiento posterior".

### Bloque A — Un dashboard de Dona que se puede enseñar (semanas 1–3)

Primero, porque **es el prerequisito de reactivar producción**, no su consecuencia.

| # | Tarea | Esfuerzo | Criterio de aceptación |
|---|---|---|---|
| A1 | Implementar el flujo demostrable del dashboard de Dona: login → oportunidad/tarea → acción de riesgo → aprobación → ejecución → audit trail | L | Demo grabable en menos de 5 min, con los seis estados (carga, vacío, error, permisos, sesión vencida, confirmación) |
| A2 | Sistema de diseño aplicado a ese flujo: contratar los tokens **corregidos** (V2–V5) como contrato copiable, no como paquete | M | El flujo de A1 usa el contrato; 0 violaciones axe en las pantallas del flujo |

**A2 depende de A1**, no al revés: se corrigen los tokens **al construir la primera
pantalla real**, no propagando un contrato sin consumidor.

### Bloque B — Lo imprescindible de seguridad y legal (semanas 2–4, en paralelo a A)

Sin esto no se expone nada a Internet, pero **no incluye** limpieza de estilo ni
mantenimiento de repos.

| # | Tarea | Esfuerzo | Criterio de aceptación |
|---|---|---|---|
| B1 | Rotar secretos por proveedor (Anthropic, OpenAI, Stripe, Whapi, Supabase, R2, admin token) con fecha registrada | M | Ningún secreto previo sigue activo; registro con fecha |
| B2 | Quiet hours TCPA + detección STOP robustecida (más allá del set cerrado) | M | Suite verde + casos nuevos que cubren STOP fuera del set |
| B3 | Auth web endurecido sustituyendo el provisional, **sin cambiar el contrato de sesión** | L | Suite de auth web verde; sin hallazgos P1 en revisión de seguridad |
| B4 | Techo de `cryptography` a un rango que permita el fix (`PYSEC-2026-3552`) | XS | Job `pip-audit` verde — **es la puerta del gate de seguridad**, por eso está en el camino y no en mantenimiento |

### Bloque C — Preparar la reactivación (semana 4)

| # | Tarea | Esfuerzo | Criterio de aceptación |
|---|---|---|---|
| C1 | Preparar la reactivación: env vars, webhook de Stripe verificado y smoke test definido | M | Smoke test reproducible escrito y en verde en local contra el flujo de A1 |

**Avance visible al día 30:** el dashboard de Dona cerrado y grabable (A1+A2), los
secretos rotados, TCPA/STOP cubiertos y el auth web endurecido (B), y la
reactivación lista para ejecutarse (C). **Nada más.** Ruff, la poda de PRs, Alembic
y la propagación del sistema de diseño no aparecen aquí a propósito.

---

## Días 31–60 — "Poner Dona en producción y desplegar Nova Context"

Objetivo del mes: hay un producto cobrando y un segundo producto con usuarios
reales.

| # | Tarea | Producto | Esfuerzo | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|
| 2.1 | **Auth web endurecido** (= B3, ejecutado) | Dona | L | B1 | Suite de auth web verde + revisión de seguridad sin hallazgos P1 |
| 2.2 | Reactivar producción: Render (backend) + Vercel (landing) con env vars y webhook Stripe verificado. **Condición de entrada: el flujo del dashboard (A1) cerrado** | Dona | M | B1–B3, A1, C1, 2.1 | Smoke test end-to-end contra producción real |
| 2.3 | Verificar el cobro end-to-end en producción (checkout → webhook → créditos → acción pagada) | Dona | S | 2.2 | Al menos un pago real registrado con su fila en `transacciones_credito` |
| 2.4 | ~~Cerrar el flujo demostrable del dashboard de Dona~~ **DUPLICADO de A1**: estaba en los días 1–30 y aquí otra vez. Eliminado | — | — | — | — |
| 2.5 | Decidir la fusión del rediseño de hero pendiente (`design/landing-hero-v2`) | Dona | XS | 1.9 | Decisión registrada (fusionar o descartar) |
| 2.6 | Arreglar CI de Dependabot en Fluvia (bumps agrupados y runtime a **Node 24 LTS**, no 25: 25 está EOL — ver `node-lts.md`) | Fluvia | M | — | Al menos un PR de Dependabot verde y fusionable |
| 2.7 | **Nova Context: LICENSE + postura de licencia** y NOTICE/atribución | Nova Context | S | decisión humana | LICENSE presente y postura registrada |
| 2.8 | **Nova Context: despliegue real** con los gates de operador (`validate:predeploy`) y backups sellados | Nova Context | L | 2.7 | `validate:predeploy` PASS contra infraestructura real; un deploy con smoke verde |
| 2.9 | Fluvia: llevar la matriz de jurisdicción (Colombia) a revisión legal | Fluvia | M | decisión humana | Checklist entregado a abogado; estado registrado (sin conclusiones legales) |
| 2.10 | EvolveOS: **ratificación fundacional** — el propietario lee Part 0 + Apéndice C + auditoría y aprueba o pide cambios | EvolveOS | S | decisión humana | PR #1 sale de draft o se registran los cambios pedidos |
| 2.11 | Donalabs: hardening operativo (cerrar signups, rotar credenciales, verificar restauración de backup) | Donalabs | M | — | `./scripts/health.sh` verde + una restauración probada |

**Avance visible al día 60:** Dona cobrando en producción, Nova Context desplegado
**con datos sintéticos primero** (el gate del propio repo exige empezar por ahí y
autorización explícita antes de datos reales — ver corrección 4 de la revisión),
y Fluvia con la vía legal iniciada.

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
| 3.6 | Sistema de diseño: propagar tokens y componentes base a Nova Context y Fluvia | Nova Context, Fluvia | L | A2 | Ambos usan los tokens compartidos; sin regresión visual. **Sólo después de probarlos sobre componentes reales**, no antes |
| 3.7 | Revisión trimestral de go/no-go (ver §Gates) | todos | S | todo | Decisión escrita: qué se acelera, qué se mantiene, qué se detiene |

**Avance visible al día 90:** un producto cobrando con métricas leídas, un
producto con 25 usuarios reales en validación falsable, y una decisión explícita
sobre el producto de pagos.

---

## Mantenimiento posterior (fuera de la ruta a ingresos)

Estas tareas **se retiraron de los primeros 30 días** porque no bloquean cobrar con
Dona. Ninguna se borra: se aparcan con dueño y criterio, para que no vuelvan a
colarse en la cadena por parecer «de limpieza rápida».

| # | Tarea | Por qué NO bloquea cobrar |
|---|---|---|
| M-1 | `ruff` limpio (458 hallazgos) | Es estilo y consistencia, no comportamiento |
| M-2 | Retirar `metadata.create_all()` del lifespan; Alembic como fuente única | La suite pasa hoy; el riesgo es de evolución, no de cobro |
| M-3 | `arq`/Redis como camino por defecto en lugar de `inproc` | Afecta a la supervivencia a reinicios, no a cobrar el primer euro |
| M-4 | Cerrar/actualizar los 24 PRs y podar ramas remotas | Higiene de repositorio |
| M-5 | Matriz de CI con 3.11/3.12/3.13 (+3.14 opcional) | El runtime del entorno no es el desplegado |
| M-6 | `gitleaks` como gate aplicado y verificado (criterio en `evidencia-gitleaks-estado.md`) | **Seguridad**: importante, pero el gate puede cerrarse en paralelo sin frenar la demo |
| M-7 | Corregir los 4 defectos de accesibilidad del sistema de diseño (V2–V5) | Entra en A2 **sólo** para las pantallas del flujo; el resto puede esperar |
| M-8 | Runtime a **Node 24 LTS** en Fluvia, EvolveOS y Donalabs, con inventario completo (Dockerfile, CI, hosting) | Node 20 está EOL, pero esos repos no son la ruta de ingreso (ver `node-lts.md`) |
| M-9 | **Deuda de los 38 warnings de Dona** (`PytestUnhandledThreadExceptionWarning`, `aiosqlite`/event loop) | La suite pasa; es deuda de calidad asíncrona, no de disponibilidad |
| M-10 | V23 (falta de `h1`) y V26 (contraste, `select-name`) en Nova | Ya hay un PR para V25; estos son la continuación natural y no bloquean cobrar |

**Regla de entrada a esta lista:** si una tarea no cambia el resultado «un cliente
puede pagar», su sitio es esta tabla y no los días 1–30.

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
