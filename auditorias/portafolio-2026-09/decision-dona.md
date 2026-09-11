# Decisión argumentada para DONA — mejorar, migrar (strangler) o reconstruir

Fecha: 2026-09-11. Base: línea base verificada de
`evidencia/comandos-y-resultados.md`, el informe `informes/dona-agent.md` y los
documentos propios del repositorio (`README.md`, `docs/CURRENT_STATE.md`,
`docs/legacy-inventory.md`, `docs/vision/DONA_CANONICAL_CONTEXT.md`,
`AGENTS.md`, `CLAUDE.md`).

---

## 1. La pregunta

DONA es el proyecto más antiguo del portafolio (primer commit 2026-03-17; 483
commits; 75 ramas remotas) y el propietario pidió decidir con evidencia entre:

- **A. Mejorar el repositorio actual** sin cambio estructural.
- **B. Migración gradual tipo strangler** por dentro del repositorio actual.
- **C. Repositorio nuevo con transferencia controlada.**

Regla explícita del encargo: **no recomendar C "porque el código sea antiguo o
desordenado"**. La antigüedad y el desorden, por sí solos, no son evidencia.

---

## 2. Evidencia recogida

### 2.1 Señales de que el repositorio NO está muerto ni es un desecho

| Evidencia | Fuente |
|---|---|
| 2360 tests pasan en la suite completa | `python -m pytest -q` (ver evidencia) |
| 132 archivos de test; suite usada como gate de CI en cada PR y push a `main` | `pytest.ini`, `.github/workflows/tests.yml` |
| CI **Tests** verde en `main` en los últimos 3 runs (2026-07-15/17/19) | `gh run list -w Tests -b main` |
| Backend modular y coherente: `agent/` con brain, billing, automation, business, creativos, jobs, providers, google_* | `README.md` §Estructura, `docs/CURRENT_STATE.md` |
| Patrón de seguridad maduro: fail-closed por defecto (`agent/entorno.py`), firma de webhooks, `hmac.compare_digest`, Fernet para tokens OAuth, dedupe persistente, rate limiting, redacción de PII | `README.md` §Cumplimiento y seguridad |
| Flujo de dinero auditado: créditos enteros, `cobrar_o_rechazar` antes del trabajo caro, reserva write-ahead, reconciliación post-crash, `transacciones_credito` | `README.md` §Billing, `docs/CURRENT_STATE.md` |
| Fase 0 ya ejecutada como estabilización real, con evidencia por archivo (borrados justificados de `agent/tools.py`, `privacy.html`, `coverage.xml`, `test_dona.db`) | `docs/CURRENT_STATE.md` §Archivos limpiados |
| Único producto del portafolio con usuarios reales (beta controlada) | `README.md` §Estado |

### 2.2 Señales reales de deuda (lo que sí justifica intervención)

| Deuda | Evidencia | Impacto |
|---|---|---|
| **Techo de versión impide un parche de seguridad**: `cryptography 49.0.0` con PYSEC-2026-3552, fijado `>=49.0.0,<50.0.0` | `gh run view` del workflow Security; `requirements.txt` | **Bloquea cobrar** |
| **gitleaks rojo permanente** por 6 falsos positivos en tests | workflow Security, 3 runs fallidos consecutivos | Higiene / ruido que enmascara hallazgos reales |
| **Producción suspendida** y env de Vercel vacías | `docs/CURRENT_STATE.md` §Producción | **Bloquea cobrar** |
| **Rotación de secretos pendiente** | `docs/CURRENT_STATE.md` §Seguridad | **Bloquea cobrar** |
| **Quiet hours TCPA incompletas** y **detección STOP por set cerrado** | `docs/CURRENT_STATE.md` §Riesgos | Riesgo legal (TCPA) |
| **Auth del dashboard provisional** | `docs/CURRENT_STATE.md` §Frontend | Deuda antes de producción |
| **Doble fuente de esquema**: Alembic convive con `metadata.create_all()` | `docs/CURRENT_STATE.md` §Riesgos | Deuda antes de producción |
| **Cola `inproc` pierde jobs** sin Redis | `docs/CURRENT_STATE.md` §Jobs | Deuda antes de producción |
| **`ruff` con 458 hallazgos** (446 auto-fixables) | `ruff check .` (ver evidencia) | Mantenibilidad |
| **75 ramas remotas, 24 PRs abiertos** | `git branch -r`, `gh pr list` | Higiene de repositorio |
| **No verificado en Python 3.14** (61 errors + 1 failed por APIs de asyncio eliminadas) | `pytest` en 3.14.4 (ver evidencia) | Compatibilidad / matriz de CI |
| Árbol con restos huérfanos: `enhanced/`, `knowledge/`, `start.sh`, `config/business.yaml`, `migration.py` | `docs/CURRENT_STATE.md` §Archivos revisados pero NO eliminados | Posponible |

### 2.3 Lo que la evidencia NO sostiene

- **No** hay evidencia de que la arquitectura esté rota: el core (FastAPI +
  brain + billing + automation) es modular, testeado y en uso.
- **No** hay evidencia de acoplamiento patológico que impida evolucionar: los
  problemas detectados son de configuración, cumplimiento y fuente única de
  esquema — todos localizados.
- **No** hay evidencia de que una reescritura fuera a producir un resultado mejor:
  C descartaría 2360 tests verdes, 483 commits de decisiones depuradas, el único
  producto con usuarios, y volvería a exponer al producto a los mismos riesgos de
  TCPA/WhatsApp — pero sin la cobertura que hoy los detecta.

---

## 3. Análisis de las tres opciones

### Opción A — Mejorar el repositorio actual

- **Coste:** bajo (el hardening ya está enumerado).
- **Riesgo:** bajo en lo técnico; **alto en lo estratégico**, porque "A" no fija
  criterio de parada. Es exactamente lo que el propietario señaló como problema:
  prolongar la construcción indefinidamente.
- **Tiempo hasta demo:** inmediato.
- **Tiempo hasta primera venta:** 4–8 semanas (estimación) con reactivación de
  producción.
- **Pérdida de historial:** ninguna.
- **Veredicto:** insuficiente **como marco**, aunque su contenido (el hardening)
  es correcto y necesario.

### Opción B — Migración gradual tipo strangler dentro del repositorio actual

- **Qué significa aquí, concretamente:**
  1. **Esquema:** Alembic pasa a ser fuente única; `metadata.create_all()` se
     retira del lifespan y `migration.py` se depreca tras verificar equivalencia
     (Alembic ya está en el repo y hay migraciones).
  2. **Cola:** `arq`/Redis pasa a camino por defecto; `inproc` queda como modo de
     desarrollo explícito, nunca silencioso.
  3. **Auth web:** se sustituye el auth provisional por el endurecido, detrás del
     mismo contrato de sesión (la landing ya consume `/internal/*` por bridge HMAC).
  4. **Frontend:** se conservan landing y dashboard; se cierran los flujos
     demostrables con los tokens del `sistema-diseno-compartido.md`.
  5. **Core del agente (brain, billing, automation):** no se toca en la
     migración; solo se endurece (TCPA/STOP) y se le añaden pruebas de regresión.
- **Coste:** medio, repartido en incrementos verificables por separado.
- **Riesgo:** bajo. Cada paso es reversible y está cubierto por la suite actual.
- **Tiempo hasta demo:** inmediato (no bloquea la demo).
- **Tiempo hasta primera venta:** 4–8 semanas (estimación), solapando la
  migración con el hardening en vez de secuenciarlos.
- **Pérdida de historial:** ninguna.
- **Migración de datos:** solo la de esquema→Alembic, con prueba de equivalencia
  antes de retirar `create_all()`.
- **Pruebas de equivalencia:** disponibles — la suite de 2360 tests es
  precisamente ese instrumento.
- **Posibilidad de mantener servicio:** sí; el strangler permite operar y migrar
  a la vez, y la producción está suspendida (ventana ideal).

### Opción C — Repositorio nuevo con transferencia controlada

- **Coste:** alto (reescritura del backend, re-plataforma del frontend,
  reconstrucción de la suite).
- **Riesgo:** alto. Se pierde la cobertura que hoy detecta los riesgos legales y
  de dinero; esos riesgos **no desaparecen** al reescribir, vuelven sin red.
- **Tiempo hasta demo:** medio.
- **Tiempo hasta primera venta:** **más largo** que A o B — habría que rehacer
  antes de reanudar lo que ya funciona.
- **Pérdida de historial:** total (483 commits, decisiones, `docs/ops/agent-runs/`
  con ledgers de coste y riesgo).
- **Migración de datos:** mayor (hay datos de usuarios reales en Supabase).
- **Disparador legítimo para C:** que existiera un requisito nuevo que el diseño
  actual no pueda cumplir (p. ej. multi-tenant estricto con RLS desde el día 1, o
  una migración de runtime). **Ese disparador no está en la evidencia recogida.**
- **Veredicto:** no recomendado hoy.

---

## 4. Recomendación

**Opción B — migración gradual tipo strangler, con el hardening de Fase 0/1 como
primer incremento y criterio de parada explícito.**

Razón central: la evidencia muestra un repositorio **grande y vivo con deuda
localizada**, no un repositorio inviable. Las intervenciones que hacen falta
(rotación de secretos, TCPA/STOP, auth web, techo de `cryptography`, Alembic como
fuente única, cola persistente) son **puntuales, reversibles y ya están
cubiertas por 2360 tests verdes**. Reconstruir (C) pagaría un coste total para
resolver problemas que son puntuales, y perdería el único activo de mercado del
portafolio: usuarios reales.

B se distingue de A en lo que importa: **B fija criterio de parada y orden**, que
es justo lo que evita la construcción indefinida.

### 4.1 Secuencia de la migración strangler

| Incremento | Contenido | Criterio de aceptación | Reversible |
|---|---|---|---|
| **B0 — Seguridad primero** (bloquea cobrar) | Rotar secretos (Anthropic, OpenAI, Stripe, Whapi, Supabase, R2, admin token); borrar transcripts con secretos; subir el techo de `cryptography` a `<51` y verificar `pip-audit` verde; allowlist de fixtures de test en `.gitleaks.toml` y verificar `gitleaks` verde | `Security` workflow verde en `main`; secretos rotados con evidencia de fecha | N/A (no es código) |
| **B1 — Cumplimiento TCPA** | Quiet hours correctas; detección STOP más allá del set cerrado; pruebas de regresión | Suite verde + casos nuevos de STOP/quiet hours | Sí |
| **B2 — Esquema con fuente única** | `create_all()` fuera del lifespan; Alembic como fuente única; `migration.py` deprecado | Prueba de equivalencia Alembic↔esquema en base limpia | Sí |
| **B3 — Cola persistente** | `arq`/Redis como camino por defecto; `inproc` solo explícito | Job sobrevive a un restart con Redis; test que lo prueba | Sí |
| **B4 — Auth web endurecido** | Sustituir el auth provisional manteniendo el contrato de sesión | Suite de auth web verde + revisión de seguridad | Sí |
| **B5 — Frontend demostrable** | Cerrar landing + flujo principal del dashboard con tokens compartidos | Demo grabable del flujo completo | Sí |
| **B6 — Higiene** | Podar ramas remotas, cerrar/actualizar los 24 PRs, decidir los restos huérfanos | `gh pr list` acotado; ramas < 10 | Sí |

Orden no negociable: **B0 antes que cualquier despliegue**; B2 y B3 antes de
reanudar producción a escala; B5 puede correr en paralelo desde el principio
porque es aditivo.

### 4.2 Lo que NO se hace en esta ruta

- No se reescribe el core del agente (`brain.py`, `billing.py`, `automation/`).
- No se cambia de framework, ni de lenguaje, ni de proveedor de base de datos.
- No se construyen features nuevas (marketplace, multi-tenant, builder de
  agentes): el propio repo ya lo prohíbe en su fase actual
  (`docs/CURRENT_STATE.md` §"Qué NO construir todavía").
- No se migra a un repositorio nuevo.

---

## 5. Preguntas que requieren decisión humana

1. **Reactivar producción**: ¿se reanuda Render + Vercel tras B0 y B1, o se
   mantiene suspendida hasta terminar la migración? (Recomendación: tras B0+B1.)
2. **Orden de rotación de secretos**: ¿se rotan todos a la vez o por proveedor,
   con ventana de mantenimiento? (Recomendación: por proveedor, empezando por los
   que tocan dinero y mensajería.)
3. **Alcance de B5** en la primera iteración: ¿landing, dashboard, o ambos a la
   vez? (Recomendación: flujo demostrable del dashboard primero; el hero de
   landing ya existe sin mergear en `design/landing-hero-v2`.)
4. **Restos huérfanos** (`enhanced/`, `knowledge/`, `start.sh`,
   `config/business.yaml`, `migration.py`): ¿se eliminan en B6 o se conservan como
   referencia? `enhanced/` está marcado como VIVO en `docs/CURRENT_STATE.md` y no
   debe tocarse.
