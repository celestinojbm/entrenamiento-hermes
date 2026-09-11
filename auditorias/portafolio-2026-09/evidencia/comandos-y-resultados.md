# Registro de comandos y evidencia reproducible — H-014

Fecha de ejecución: 2026-09-11. Ejecutor: Hermes Agent (sesión local WSL2).

Todo lo de este documento proviene de **ejecución real**. Donde algo no se pudo
verificar, se indica explícitamente en lugar de estimarse.

---

## 1. Condiciones de ejecución

| Elemento | Valor |
|---|---|
| Host | WSL2 local, usuario `celestinojbm` |
| Node | v22.23.0 |
| pnpm | 10.4.1 |
| Python | 3.14.4 (venv aislado por repo) |
| Docker | **no disponible** en la distro WSL |
| root/sudo | **no disponible** (autenticación interactiva requerida) |
| Directorio de trabajo | `/home/celestinojbm/h014-work/` (fuera de los árboles locales del usuario) |

Los repositorios se auditaron en **clones limpios** desde GitHub con token del
GitHub CLI autenticado en Windows, sin tocar ningún árbol de trabajo local
existente.

### 1.1 Servicios reales levantados sin privilegios

Como no había Docker ni root, se instalaron binarios de usuario con `micromamba`
(conda-forge) para poder ejecutar las suites que exigen servicios reales:

```bash
# PostgreSQL 16.15 (Fluvia, EvolveOS)
micromamba create -y -p ./env -c conda-forge "postgresql=16" redis-server
initdb -D ./data -U postgres --auth=trust
pg_ctl -D ./data -o "-p 5432 -c listen_addresses=127.0.0.1" start

# PostgreSQL 18.6 + pgvector 0.8.6 (nova-context, que requiere pgvector)
micromamba create -y -p ./env18 -c conda-forge "postgresql=18" pgvector
initdb -D ./data18 -U postgres --auth=trust
pg_ctl -D ./data18 -o "-p 5433 -c listen_addresses=127.0.0.1" start
psql -p 5433 -U postgres -d nova -c "CREATE EXTENSION vector;"

# Redis 8.10.1
redis-server --port 6379 --daemonize yes --save '' --appendonly no
```

Nota de método: instalar `pgvector` en el mismo entorno que PostgreSQL 16
arrastró PostgreSQL 18 y rompió el servidor 16 en marcha (`version mismatch` de
`plpgsql.so`). Se corrigió reinstalando 16 en su entorno y creando un segundo
entorno aislado para PostgreSQL 18. Este incidente y su resolución quedan
registrados aquí porque es exactamente el tipo de fallo que la auditoría exige no
ocultar.

---

## 2. Línea base por repositorio

### 2.1 Dona-agent

Rama auditada: `main`. HEAD `958b525` (2026-07-19, merge PR #240).

| Comando | Resultado | Duración |
|---|---|---|
| `python -m venv` + `pip install -r requirements.txt` | exit 0 | 28 s |
| `pip install -r requirements-dev.txt` | exit 0 | 3 s |
| `ruff check .` (config ratchet en `pyproject.toml`: `select = ["F","I","UP","B"]`) | **exit 1 — 458 hallazgos** (446 auto-fixables) | <1 s |
| `python -m pytest -q` | **exit 1 — 1 failed, 2360 passed, 61 errors** | 283,6 s |

Análisis de los 62 ítems no verdes (verificado uno a uno con `--tb`):

- **61 errors**: todos en `tests/test_internal_assets.py`,
  `tests/test_internal_stripe_topup_dispatch.py`, `tests/test_main_internal_stripe.py`,
  `tests/test_main_internal_usuario_resumen.py`. Error uniforme:
  `RuntimeError: Event loop is closed` durante el `aiosqlite` worker thread.
- **1 failed**: `tests/test_observability_y_catalog.py::TestRequestId::test_contextvar_independiente_entre_tareas_async`,
  falla en `asyncio.get_event_loop()` con
  `RuntimeError: There is no current event loop in thread 'MainThread'`.

Ambas causas son **incompatibilidad con Python 3.14**: `asyncio.get_event_loop()`
dejó de crear un loop implícito. El repo declara Python ≥3.11
(`pyproject.toml` → `target-version = "py311"`, `start.sh` exige ≥3.11) y su CI
no cubre 3.14.

Comando de reproducción del fallo aislado:

```bash
python -m pytest "tests/test_observability_y_catalog.py::TestRequestId::test_contextvar_independiente_entre_tareas_async" -q --tb=short
```

#### Estructura de migraciones verificada

`alembic/versions/` contiene **3 archivos**, pero solo 2 ejecutan DDL:

- `001_estado_inicial.py` — `upgrade()` y `downgrade()` con cuerpo **`pass`**
  (stamp vacío, sin DDL).
- `002_suscripcion_stripe.py` — crea `evento_stripe_procesado` y
  `suscripcion_stripe` con sus índices.
- `003_bienvenida_enviada.py` — añade la columna `bienvenida_enviada`.

El resto del esquema se crea con `Base.metadata.create_all()` en el lifespan de
`agent/main.py`. Los propios docstrings de las migraciones declaran la redundancia
y la marcan como pendiente (T4.3); `grep -rn "create_all"` lo confirma en
`agent/main.py` y en los docstrings de `002` y `003`.

#### CI real del repositorio (consultado con `gh run list`, no inferido)

| Workflow | Rama | Último resultado |
|---|---|---|
| Tests | `main` (push, merge PR #240) | **success** (16m30s) |
| Tests | `main` (push, merge PR #239) | success (13m01s) |
| Tests | `main` (push, merge PR #238) | success (13m34s) |
| Security | `main` (schedule 2026-09-07) | **failure** |
| Security | `main` (schedule 2026-08-31) | failure |
| Security | `main` (schedule 2026-08-24) | failure |

Contenido de los dos jobs que fallan en **Security** (`gh run view 34119971450 --log`):

- `pip-audit (deps Python)` → exit 1:

  ```
  Name         Version ID              Fix Versions
  cryptography 49.0.0  PYSEC-2026-3552 50.0.0
  ```

  El rango declarado en `requirements.txt` es `cryptography>=49.0.0,<50.0.0`:
  el techo de versión **impide aplicar el fix**.

- `gitleaks (secret scan)` → exit 1, `leaks found: 6`. Las seis entradas son de
  regla `generic-api-key` y apuntan a **archivos de test** con valores sintéticos
  (fixtures de redacción de PII y de identificadores `sub_SECRET…`). Los valores
  no se reproducen aquí por tratarse de un repositorio público. Conclusión: falsos
  positivos de configuración que mantienen el gate rojo de forma indefinida.

### 2.2 nova-context

Rama auditada: `main`. HEAD `c49ef4d` (2026-07-22, merge PR #17).

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | — |
| `pnpm run typecheck` (`turbo run typecheck`) | exit 0 | — |
| `pnpm run build` (`turbo run build`) | exit 0 | ~15 s |
| `pnpm run test` (unit, 12 workspaces) | **exit 0** (p. ej. `@nova/api` 109 tests, `@nova/validation-gate` 106 tests) | 16 s |
| `pnpm db:migrate` (PG18 + pgvector, `127.0.0.1:5433`) | exit 0 — 13 migraciones aplicadas | 2 s |
| `pnpm test:integration` (PG18 + pgvector + Redis reales) | **exit 0 — 245 passed, 17 skipped, 0 failed** (35 archivos verdes, 4 skipped) | 78 s |

Nota: la primera pasada de integración dio 6 fallos, todos en
`test/integration/m18a-backup-sh.test.ts`, causados por `pg_dump: command not
found` — un problema de `PATH` del entorno de prueba, no del código. Con
`pg_dump` en `PATH` la suite quedó completamente verde. Queda registrado porque
demuestra que el fallo era del arnés de ejecución.

#### CI real

Workflow `ci` en `main`: success (push 2026-07-22, 9m37s). Sin runs fallidos
recientes.

### 2.3 Fluvia

Rama auditada: **la rama por defecto real del repositorio**,
`claude/new-session-haeo7h`. HEAD `ed2f368` (2026-07-17, merge PR #46).

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | 7 s |
| `pnpm run build` (`turbo run build`) | exit 0 | 16 s |
| `pnpm run lint` (`eslint .`) | exit 0 | 4 s |
| `pnpm test` **sin servicios** | exit 1 — 9 passed / 80 skipped, `ECONNREFUSED 127.0.0.1:5432` | 8 s |
| `pnpm migrate` (PG16 real) | exit 0 — 45 migraciones aplicadas | 4 s |
| `pnpm test` (PG16 real, sin Redis) | exit 1 — 257 passed / 3 skipped; único fallo: `test/rate-limit-redis.test.ts` (hook timeout por falta de Redis) | 76 s |
| `pnpm test` (PG16 + Redis reales) | **exit 0 — todas las suites verdes** (p. ej. `@fluvia/api` 257+ tests, `@fluvia/worker` 46, `@fluvia/sdk` 10) | 40 s |

Los dos únicos rojos de Fluvia en este entorno fueron, en orden: falta de
PostgreSQL y falta de Redis. Con ambos servicios reales, la suite es verde.

#### CI real

- Sobre la rama por defecto `claude/new-session-haeo7h`: últimos 5 pushes →
  **success** (2m37s–2m54s).
- Sobre ramas de Dependabot: **todos los runs fallan** — bumps agrupados
  `minor-y-patch` (15 y 14 updates) y `node:22-slim → 25-slim`.
- 12 PRs abiertos, en su mayoría Dependabot.

### 2.4 EvolveOS

Rama auditada: `main`. HEAD `88103ee` (2026-07-19, merge PR #34).

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm install --frozen-lockfile` | exit 0 | 2 s |
| `pnpm run build` | exit 0 | 2 s |
| `pnpm test` **sin servicios** | exit 1 — `Connection terminated unexpectedly` (sin PostgreSQL) | 5 s |
| `pnpm migrate` (PG16 real) | exit 0 — 7 migraciones aplicadas | — |
| `pnpm test` (PG16 real) | **exit 0 — 9 archivos, 432 tests passed, 0 failed** | 22 s |
| `python scripts/run_all_checks.py` (consistencia de spec) | **RESULT: PASS** — expected files, fenced blocks, gate range, agent references, taxonomies, table integrity, markdown links, placeholders | <1 s |

#### CI real

Push a `main` (2026-07-19): `app-ci` success (1m01s), `spec-consistency`
success (14s). 11 issues abiertos de los backlogs de Fase 0/1, 0 PRs abiertos.

### 2.5 Donalabs

Rama auditada: **la rama por defecto real**, `claude/donalabs-infrastructure-setup-j2hs6v`.
HEAD `dd6e08b` (2026-07-08).

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm --dir design-system install --frozen-lockfile` | exit 0 | 7 s |
| `pnpm --dir design-system run typecheck` | exit 0 | 6 s |
| `pnpm --dir design-system run lint` | exit 0 | 7 s |
| `pnpm --dir design-system run build` | exit 0 | 8 s |

No existe suite de tests para el design system (`design-system/package.json` no
declara script `test`). La validación de CI es `Design System CI` +
`Infrastructure Validation`, ambas verdes en el push a `main` de 2026-07-09.

---

## 3. Resumen consolidado

| Repositorio | Rama por defecto | install | typecheck | lint | test | build | CI |
|---|---|---|---|---|---|---|---|
| Dona-agent | `main` | OK | n/a | 458 hallazgos | 1F/2360P/61E (Py3.14) | n/a | Tests verde; **Security rojo** |
| nova-context | `main` | OK | OK | n/a | unit OK + integración 245P/0F | OK | verde |
| Fluvia | `claude/new-session-haeo7h` | OK | OK | OK | **verde con PG+Redis** | OK | verde en rama por defecto; Dependabot rojo |
| EvolveOS | `main` | OK | OK | n/a | **432P/0F con PG** | OK | verde |
| Donalabs | `claude/donalabs-infrastructure-setup-j2hs6v` | OK | OK | OK | sin suite | OK | verde |

## 4. Archivos de evidencia crudos

En `evidencia/` se conservan los logs crudos de las ejecuciones descritas:

- `00-runner.log` — secuencia de comandos y exit codes del ciclo por repo.
- `01-recon.txt` — reconocimiento: git, tamaño, ramas, tests, workflows, TODOs.
- `Dona-agent.log` — install, ruff y pytest de Dona-agent.
- `Dona-agent-pytest-final.log` — resumen limpio de pytest (short test summary).
- `nova-context.log` — install, typecheck, build y unit tests.
- `nova-context-integration-2.log` — suite de integración con PG18+pgvector+Redis.
- `Fluvia.log` — install, build, lint y test sin servicios.
- `Fluvia-postgres-redis.log` — suite completa con PG16 + Redis reales.
- `EvolveOS.log` — install, build y test sin servicios.
- `EvolveOS-postgres.log` — suite completa con PG16 real + checks de spec.
- `Donalabs.log` — install, typecheck, lint y build del design system.
- `ci-runs.txt` — salida de `gh run list` usada para la sección de CI.
