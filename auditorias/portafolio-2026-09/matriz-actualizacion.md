# Matriz de actualización por repositorio — portafolio 2026-09

Responde al bloqueador nº8 de la revisión: faltaba la matriz de actualización
(versión actual, versión estable objetivo, breaking changes, vulnerabilidad o fin
de soporte, coste de migración y decisión `actualizar ahora / después / no
actualizar`).

**Regla de decisión aplicada en todo el documento:** la versión más reciente
**no** es el objetivo automático. Solo se recomienda actualizar cuando la
actualización compra **seguridad, cumplimiento o viabilidad comercial**; cuando
no, se recomienda explícitamente **no actualizar ahora** y se dice por qué.

Fuentes: versiones declaradas leídas de cada `package.json` / `requirements.txt`
(`evidencia/versiones-declaradas.txt`), versiones estables consultadas en el
registro público de npm, CVEs de `pip-audit` y de `npm audit`, y datos de fin de
soporte de `endoflife.date` y `nodejs.org/dist`.

---

## 1. Runtimes — el hallazgo con más urgencia real

| Runtime | Declarado en | Versión estable | Fin de soporte | Decisión |
|---|---|---|---|---|
| **Node 20** | Fluvia (`engines: >=20`), EvolveOS (`>=20`), Donalabs (`>=20`) | 20.19.x | **2026-04-30 — YA VENCIDO** | **Actualizar ahora** el `engines` a `>=22` y las imágenes base de Docker/CI. Es el único ítem con fecha ya incumplida |
| Node 22 (Jod LTS) | nova-context (`engines: >=22`) | 22.23.2 | 2027-04-30 | **No actualizar ahora.** Correcto |
| Node 24 (Krypton LTS) | — | 24.21.0 | 2028-04-30 | **Actualizar después** (mes 2–3), como destino de Node 20 |
| Node 25 | — | 25.9.0 | 2026-06-01 (ya vencido) | **No adoptar.** No es LTS |
| Python 3.11 | Dona (`target-version = "py311"`, `start.sh` exige ≥3.11) | 3.11.16 | 2027-10-31 | **Mantener**, y **añadir 3.11 y 3.13 a la matriz de CI** (ver §3) |
| Python 3.14 | (única versión del entorno de auditoría) | 3.14.7 | 2030-10-31 | **No adoptar todavía** en Dona: el control positivo demuestra que la suite pasa en 3.12 y **no** está verificada en 3.14 |
| PostgreSQL 16 | Fluvia, EvolveOS | 16.15 | 2028-11-09 | **No actualizar ahora.** Suficiente y estable |
| PostgreSQL 18 | patch de auditoría para nova-context (pgvector) | 18.6 | 2030-11-14 | No aplica al producto |
| Redis 8.10.1 | patch de auditoría | — | — | No aplica |

**Acción concreta y mínima:** cambiar el `engines.node` de Fluvia, EvolveOS y
Donalabs de `>=20` a `>=22` (o `>=24`) y fijar la imagen base de Docker en Node
24 LTS. Coste: XS. Riesgo: bajo. Es el único ítem de esta matriz con una fecha
de soporte **ya vencida**.

---

## 2. Dependencias por repositorio

### 2.1 Dona-agent — `landing/`

| Paquete | Declarado | Estable | Salto | Decisión y motivo |
|---|---|---|---|---|
| `next` | 16.2.10 | 16.3.5 | menor | **Actualizar ahora.** Además es el fix que `npm audit` ofrece para 3 vulnerabilidades |
| `postcss` (transitiva de next) | ≤8.5.22 | 8.5.x | parche | **Actualizar ahora** (vía next): **3 HIGH** — XSS en la salida CSS, lectura arbitraria de ficheros y path traversal por `sourceMappingURL`. CVEs GHSA-qx2v-qp2m-jg93, GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-r28c-9q8g-f849 |
| `sharp` (transitiva de next) | ≤0.35.4-rc.0 | 0.35.x | parche | **Actualizar ahora** (vía next): **3 CRITICAL** heredadas de libvips/libheif (CVE-2026-33327, -33328, -35590, -35591, GHSA-g89c-p67h-r497, GHSA-2jg2-4ch7-h545) |
| `react` / `react-dom` | 19.2.7 | 19.3.0 | parche | **Actualizar después**, junto con next |
| `typescript` | ^6 | 7.0.2 | **mayor** | **No actualizar ahora.** Un salto mayor en el compilador no compra lanzamiento |
| `vitest` | ^4.1.9 | 5.0.0 | **mayor** | **No actualizar ahora.** Cambio de infraestructura de test sin beneficio de producto |
| `next-auth` | ^5.0.0-beta.31 | 5.0.0-beta.x | beta | **Vigilar.** Es beta en el camino crítico del auth web (que además es "provisional", ver el informe de Dona) |
| `tailwindcss` | ^4 | 4.3.3 | menor | **Actualizar después** |
| `eslint` | ^9 | 10.10.0 | **mayor** | **No actualizar ahora** |

`npm audit --omit=dev` sobre `landing/`: **7 vulnerabilidades (1 moderate, 3 high, 3 critical)**, todas resolubles subiendo `next` a 16.3.5. Nota: el fix está **fuera del rango declarado**, así que requiere un PR explícito.

### 2.2 Dona-agent — Python

`pip-audit -r requirements.txt` (en Python 3.12): **4 vulnerabilidades en 2 paquetes**.

| Paquete | Actual | Fix | Severidad | Decisión |
|---|---|---|---|---|
| `cryptography` | 49.0.0 | **50.0.0** | PYSEC-2026-3552 — oráculo de Bleichenbacher en `pkcs7_decrypt_*` (fuga de longitud de la clave por distinción de errores y por tiempo) | **Actualizar ahora.** El techo `>=49.0.0,<50.0.0` de `requirements.txt` **impide el fix**. Además el comentario del workflow `security.yml` dice *"cryptography ya esta parchada (>=46.0.7)"*, que es **falso a día de hoy**: es el origen del gate rojo |
| `pytest` | 8.4.2 | **9.0.3** | PYSEC-2026-1845 — `/tmp/pytest-of-{user}` permite DoS o escalada local | **Actualizar ahora** en `requirements-dev.txt` (dependencia de test, no de runtime). El comentario del workflow ya reconoce un CVE previo de pytest y anota que "se remediará sacando pytest a requirements-dev.txt en un PR aparte": sigue pendiente |

`ruff check .` → **458 hallazgos tanto en 3.12 como en 3.14**: no es un problema
de versión de Python, es deuda de lint acumulada (ratchet declarado en
`pyproject.toml`).

### 2.3 nova-context

| Paquete | Declarado | Estable | Salto | Decisión y motivo |
|---|---|---|---|---|
| `next` (apps/web) | ^15.1.0 | 16.3.5 | **mayor** | **No actualizar ahora.** No compra lanzamiento y el repo está a un despliegue de su alpha |
| `typescript` | ^5.6.0 | 7.0.2 | **mayor** | **No actualizar ahora** |
| `fastify` | ^5.1.0 | 5.12.4 | menor | **Actualizar después**, en un PR aislado |
| `vitest` | ^2.1.0 | 5.0.0 | **dos mayores** | **No actualizar ahora** |
| `zod` | ^3.24.0 | 4.6.2 | **mayor** | **No actualizar ahora.** El repo usa schemas Zod como contrato |
| `pnpm` (packageManager) | 10.33.0 | 12.4.1 | **dos mayores** | **No actualizar ahora** |
| `pg`, `ioredis`, `turbo`, `tsx` | varios | — | menor | **Actualizar después**, agrupado |

`pnpm audit` no reportó advisories explotables en este entorno (ver
`evidencia/pnpm-audit.log`); la única cautela es el volumen de saltos mayores
pendientes, que **no** son bloqueo de lanzamiento.

### 2.4 Fluvia

| Paquete | Declarado | Estable | Salto | Decisión y motivo |
|---|---|---|---|---|
| `next` (dashboard, checkout) | ^15.5.16 | 16.3.5 | **mayor** | **No actualizar ahora.** Es el proyecto con núcleo financiero auditado; el coste de un salto mayor de framework no compra nada hasta Fase 5 |
| `typescript` | ^5.7.0 | 7.0.2 | **mayor** | **No actualizar ahora** |
| `zod` | ^3.25.0 | 4.6.2 | **mayor** | **No actualizar ahora.** Los contratos de la API financiera se validan con Zod; un salto mayor toca el camino de dinero |
| `redis` | 6.1.0 (fijado) | — | — | **No actualizar** |
| `vitest` | ^3.0.0 | 5.0.0 | **dos mayores** | **No actualizar ahora** |
| `fastify` | ^5.2.0 | 5.12.4 | menor | **Actualizar después**, con la suite de integración como red |
| `turbo`, `eslint`, `prettier` | varios | — | menor/mayor | **No actualizar ahora** |

**El bloqueo real de Fluvia no es una versión: es que su CI de Dependabot está en
rojo sistemático.** Todos los bumps agrupados (`minor-y-patch` con 15 y 14
updates) y `node:22-slim → 25-slim` fallan. Hasta arreglar eso, esta matriz es
teórica: **ninguna** actualización puede entrar. Ese es el P0 real de Fluvia.

> **Corrección (ronda 4):** ese bump apuntaba a **Node 25, que está EOL**. El
> objetivo correcto es **Node 24 LTS** con rango acotado (`">=24 <25"`), y el
> cambio abarca también Dockerfile y workflows, no solo `package.json`. Ver
> [`node-lts.md`](node-lts.md) para el inventario y la decisión.

### 2.5 EvolveOS

| Paquete | Declarado | Estable | Salto | Decisión y motivo |
|---|---|---|---|---|
| `typescript` | ^5.7.2 | 7.0.2 | **mayor** | **No actualizar ahora** |
| `vitest` | ^2.1.8 | 5.0.0 | **dos mayores** | **No actualizar ahora** |
| `pg` | ^8.13.1 | 8.x | parche | **No actualizar ahora.** Funciona y está probado (432 tests) |
| `tsx` | ^4.19.2 | 4.x | parche | **No actualizar ahora** |
| `engines.node` | `>=20` | — | — | **Actualizar ahora** a `>=22` (§1) |

### 2.6 Donalabs

| Paquete | Declarado | Estable | Salto | Decisión y motivo |
|---|---|---|---|---|
| `next` (showcase) | (ver paquete) | 16.3.5 | — | **Actualizar después.** No hay prisa: es herramienta interna |
| `tailwindcss` | ^4 | 4.3.3 | menor | **Actualizar después**, y **añadir el grupo `motion`** de tokens que hoy no existe |
| `typescript` | ^5 | 7.0.2 | **mayor** | **No actualizar ahora** |
| `engines.node` | `>=20` | — | — | **Actualizar ahora** a `>=22` (§1). Además la plataforma de servicios requiere Docker Engine 24+ |
| Imágenes de los 7 servicios | fijadas por tag | — | — | **Actualizar deliberadamente**, revisando release notes upstream. `yt-dlp` exige `>=2026.07.04` por CVE-2026-55404 |

---

## 3. Huecos de verificación en la matriz de CI (no de versión)

| Repo | Matriz de CI declarada | Hueco | Decisión |
|---|---|---|---|
| Dona-agent | Python 3.11 (`security.yml` fija `3.11`); `pyproject` apunta a 3.11 | **La suite no se ejecuta en 3.12 ni 3.13.** El entorno de auditoría solo tenía 3.14, donde falla | **Añadir 3.12 y 3.13 a `tests.yml`.** Coste S. Evita que la próxima incompatibilidad se descubra en producción |
| Fluvia, EvolveOS, Donalabs | Node `>=20` | El rango incluye una versión **EOL** | **Subir a `>=22`** |
| nova-context | Node `>=22` | Sin hueco | — |

### El control positivo que cierra la duda de Python 3.14

La versión anterior de esta auditoría afirmaba como hecho que los 62 ítems no
verdes de Dona "son incompatibilidades con 3.14, no defectos". **Era una
hipótesis presentada como hecho.** Ya está medida:

| Runtime | Comando | Resultado |
|---|---|---|
| Python 3.14.4 (única disponible al inicio) | `pytest -q` | **1 failed, 2360 passed, 61 errors** — ejecución globalmente fallida |
| **Python 3.12.14** (runtime soportado) | `pytest -q` | **2422 passed, 0 failed, 0 errors, EXIT 0** (309 s) |

Mismo HEAD (`958b525`). Evidencia:
`evidencia/Dona-agent-python312.log`.

**Conclusión corregida:** en el runtime declarado la suite está **completamente
verde**; en 3.14 falla por APIs de `asyncio` eliminadas. La atribución deja de
ser hipótesis y pasa a ser medida — pero el enunciado correcto del resultado en
3.14 es *"2360 tests pasaron dentro de una ejecución globalmente fallida"*, no
"2360 tests verdes".

---

## 4. Resumen ejecutivo de la matriz

| Prioridad | Ítem | Repos | Esfuerzo | Por qué ahora |
|---|---|---|---|---|
| 1 | `cryptography` a `>=50` (quitar el techo) | Dona | XS | CVE con fix disponible y bloqueado por el propio rango |
| 2 | `next` a 16.3.5 | Dona landing | S | Resuelve 3 high + 3 critical |
| 3 | `pytest` a `>=9.0.3` en `requirements-dev.txt` | Dona | XS | CVE en herramienta de test |
| 4 | `engines.node` a `>=22` + imagen base | Fluvia, EvolveOS, Donalabs | XS | **Node 20 está EOL desde 2026-04-30** |
| 5 | Arreglar el CI de Dependabot | Fluvia | M | Sin esto, ninguna actualización entra |
| 6 | Añadir 3.12/3.13 a la matriz de CI | Dona | S | Convierte una incompatibilidad futura en un fallo de CI |
| — | Saltos mayores (`typescript` 7, `vitest` 5, `zod` 4, `next` 16 en Fluvia/nova, `pnpm` 12) | todos | XL | **No actualizar ahora.** No compran seguridad, cumplimiento ni lanzamiento |

**Regla que se mantiene:** ninguna actualización de esta matriz se aplicó. Esta
auditoría no modifica repos.
