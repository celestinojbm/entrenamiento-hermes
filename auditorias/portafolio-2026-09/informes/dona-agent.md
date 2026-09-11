# Informe de auditoría — Dona-agent

Parte de la auditoría de portafolio 2026-09 (H-014). Línea base y comandos:
`../evidencia/comandos-y-resultados.md`.

---

## 1. Ficha del repositorio

| Campo | Valor |
|---|---|
| Repositorio | `celestinojbm/Dona-agent` |
| Rama por defecto | `main` |
| HEAD auditado | `958b525` — merge PR #240, 2026-07-19 |
| Primer commit | 2026-03-17 · **483 commits** |
| Ramas remotas | **75** · tags: 3 |
| Autores principales | Celestino (239+181 commits), dependabot (26), Enrique Henry (8) |
| Lenguaje / runtime | Python ≥ 3.11 (`pyproject.toml` → `target-version = "py311"`; `start.sh` aborta si <3.11) |
| Framework | FastAPI + Uvicorn/Gunicorn |
| Package manager | pip + `requirements.txt` / `requirements-dev.txt` |
| Base de datos | PostgreSQL en producción (Supabase) / SQLite en dev · SQLAlchemy 2 async · Alembic |
| Cola | Redis + `arq` (opcional) con fallback `inproc` |
| Storage | Cloudflare R2 (S3-compatible), fallback local |
| Pagos | Stripe Checkout + webhook + Customer Portal |
| Deploy | Render (web service + background worker); dashboard en Vercel |
| Licencia | MIT (`README.md` §Licencia) |
| Tamaño | 411 archivos de código, **~117.875 LOC**, 132 archivos de test (125 en `tests/` + `landing/`) |
| Documentación | `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/` (vision, ops, auditorias, planes, tools) |
| CI | 6 workflows: `Tests`, `Lint (ruff)`, `Security`, `Landing CI`, `Agent Runs Validation`, `Claude Review` |
| PRs / issues abiertos | **24 PRs** / 0 issues |

## 2. Línea base reproducible

| Comando | Resultado | Duración |
|---|---|---|
| `python -m venv` + `pip install -r requirements.txt` | exit 0 | 28 s |
| `pip install -r requirements-dev.txt` | exit 0 | 3 s |
| `ruff check .` | **exit 1 — 458 hallazgos** (446 auto-fixables) | <1 s |
| `python -m pytest -q` | **exit 1 — 1 failed, 2360 passed, 61 errors** | 283,6 s |

Lectura correcta de ese resultado:

- Los **61 errors** están todos en `tests/test_internal_assets.py`,
  `tests/test_internal_stripe_topup_dispatch.py`, `tests/test_main_internal_stripe.py`
  y `tests/test_main_internal_usuario_resumen.py`, con error uniforme
  `RuntimeError: Event loop is closed` (worker thread de `aiosqlite`).
- El **1 failed** es `tests/test_observability_y_catalog.py::TestRequestId::test_contextvar_independiente_entre_tareas_async`,
  que falla en `asyncio.get_event_loop()` con
  `RuntimeError: There is no current event loop in thread 'MainThread'`.

Ambas son incompatibilidades con **Python 3.14** (API eliminada), no defectos de
producto. En la matriz declarada por el repo (3.11+) y según el CI, la suite está
verde: workflow `Tests` en `main`, últimos 3 runs → **success**.

Comando de reproducción del fallo aislado:

```bash
python -m pytest "tests/test_observability_y_catalog.py::TestRequestId::test_contextvar_independiente_entre_tareas_async" -q --tb=short
```

## 3. Arquitectura y límites de módulos

Estructura real (`README.md` §Estructura del repo, verificado en el árbol):

- `agent/main.py` — app FastAPI, webhooks WhatsApp, comandos determinísticos por
  regex **antes** del LLM, endpoints `/internal` y `/admin`.
- `agent/brain.py` — LLM principal + fallbacks + tool use; sanitización de
  contenido externo contra prompt injection (`_PATRONES_INYECCION`).
- `agent/entorno.py` — helper único de entorno, **fail-closed por defecto**.
- `agent/memory.py` — historial, dedupe persistente, DB.
- `agent/automation/` — Action Center: oportunidades → acciones → permisos →
  créditos/reservas → ejecutores LOW/MEDIUM/HIGH → audit; scheduler de
  reconciliación opt-in.
- `agent/business/` — CRM, finanzas, pedidos, cotizaciones, contenido, reportes.
- `agent/creativos/` — imagen (Gemini) bajo patrón `preparar_X`/`confirmar_X`.
- `agent/jobs/` — cola `arq` + handlers.
- `agent/providers/` — adaptadores Whapi y Meta; Twilio declarado **sin módulo**.
- `agent/billing.py` — créditos enteros, `cobrar_o_rechazar`, audit trail.
- `landing/` — dashboard Next.js 16 + NextAuth, bridge HMAC hacia `/internal/*`.
- `enhanced/` — **código vivo** (imports activos), no tocar.
- `alembic/` — solo **3 versiones** de migración.
- `migration.py` — bootstrap manual a Supabase (psycopg2 sync), redundante con Alembic.

**Límites sanos:** el core (brain, billing, automation) está separado y cubierto
por tests; el frontend habla con el backend por un contrato firmado, no por acceso
directo a la base.

**Puntos frágiles reales:** (a) doble fuente de esquema — `create_all()` en el
lifespan convive con 3 migraciones Alembic; (b) `inproc` como default de la cola,
que pierde jobs sin `REDIS_URL`; (c) provider Twilio declarado en env vars pero
sin módulo, con aborto de arranque si se selecciona.

## 4. Riesgos técnicos

### (a) Funciona hoy — verificado

Suite de 2360 tests verdes; CI `Tests` verde en `main`; billing con créditos y
webhook idempotente por `stripe_session_id`; Action Center con niveles de riesgo
operable; audit trail de automatización; CCPA/TCPA con `STOP`/`START` evaluados
antes de dedupe y rate-limit; fail-closed por defecto (`agent/entorno.py`); firma
de webhooks verificada; tokens OAuth cifrados con Fernet; redacción de PII en logs.

### (b) Bloquea una demostración

1. **Producción suspendida** (Render suspendido desde ~2026-06-24; env de Vercel
   vacías) — `docs/CURRENT_STATE.md` §Producción.
2. **Arranque fail-closed**: sin los secretos críticos el deploy **aborta en vez
   de arrancar degradado** (`README.md` §Deploy). Es una virtud de seguridad que
   hoy funciona como bloqueo de demo.

### (c) Bloquea cobrar — el riesgo más serio del producto

1. **Techo de versión que impide un parche de seguridad.** Workflow `Security`
   (job `pip-audit`) → exit 1:

   ```
   Name         Version ID              Fix Versions
   cryptography 49.0.0  PYSEC-2026-3552 50.0.0
   ```

   `requirements.txt` declara `cryptography>=49.0.0,<50.0.0`: el techo **impide
   aplicar el fix**. Riesgo directo sobre el cifrado de tokens OAuth.
2. **`gitleaks` rojo permanente**: 6 hallazgos, todos regla `generic-api-key`,
   todos en **archivos de test** con valores sintéticos (fixtures de redacción de
   PII y `sub_SECRET…`). Falsos positivos que enmascaran hallazgos reales.
3. **Rotación de secretos pendiente** — `docs/CURRENT_STATE.md` §Seguridad.
4. **Quiet hours TCPA incompletas y detección STOP por set cerrado** —
   `docs/CURRENT_STATE.md` §Riesgos. Es el riesgo **legal** del canal WhatsApp.

### (d) Deuda antes de producción

- **Doble fuente de esquema**: Alembic (3 migraciones) vs `metadata.create_all()`.
- **`inproc` pierde jobs** si no hay `REDIS_URL`.
- **Auth web provisional** (`landing/app/login` + `api/auth`), no apto para
  producción sin endurecimiento.
- **`ruff`: 458 hallazgos** (446 auto-fixables) — el propio `pyproject.toml`
  documenta que la adopción es por ratchet.
- **No verificado en Python 3.14** (matriz de CI no lo cubre).
- **75 ramas remotas** y **24 PRs abiertos** (mayoría Dependabot).

### (e) Deuda posponible

`enhanced/` (vivo, no tocar), `knowledge/`, `start.sh`, `config/business.yaml`
(huérfano tras eliminarse `agent/tools.py`), `migration.py`, docs históricos en
`docs/ops/zonificacion-autonomia.md` con referencias a `agent/tools.py` ya
eliminado.

### Observabilidad, costos de IA y control de consumo

Existe `agent/logging_config.py` (JSON + redacción de PII en entorno estricto) y
audit trail de créditos. El control de consumo es **económico y explícito**:
créditos enteros prepago, `cobrar_o_rechazar` antes del trabajo caro, reserva
write-ahead y reconciliación post-crash con scheduler opt-in. Es el aparato de
control de coste más completo del portafolio.

## 5. Frontend y producto (`landing/`)

**Mapa de experiencia actual** (rutas reales verificadas en el árbol):

| Ruta | Función |
|---|---|
| `/` | Landing pública |
| `/login` | Login (auth provisional) |
| `/dashboard` | Dashboard: chat web contra `/internal/chat`, adjuntos de imagen y nota de voz |
| `/checkout` | Checkout Stripe Embedded (flujo hospedado como fallback) |
| `/success`, `/cancel` | Retornos de pago |
| `/soporte`, `/prototipo`, `/engineering` | Soporte, prototipo y vista interna |
| `/politica-de-privacidad`, `/terminos-y-condiciones` | Legales |
| `/api/automation/acciones/*` | aprobar, rechazar, ejecutar, high-preview, high-confirmar, generar |

**Stack de UI:** Next.js 16.2.10, React 19.2.7, Tailwind v4, Radix UI (accordion,
dialog), `framer-motion` 12, `lucide-react`, `next-themes` (modo oscuro).
Es una base moderna y suficiente: no requiere reescritura.

**Flujo principal que debe poder demostrarse:**
`login → dashboard → detección de oportunidad → acción con nivel de riesgo →
aprobación (HIGH con confirmación dedicada) → ejecución → audit trail visible`.

**Inventario de pantallas faltantes** (para el flujo demostrable):

1. Estado de onboarding de primera sesión (hoy no hay: se entra directo al dashboard).
2. Lista de acciones del Action Center con filtros y detalle de riesgo.
3. Detalle de acción con diff de preview y confirmación dedicada de HIGH.
4. Saldo de créditos y movimientos con explicación del consumo por acción.
5. Estados vacío / carga / error / degradado explícitos en dashboard y checkout.
6. Estado de "servicio suspendido / degradado" honesto (hoy el bloqueo es fail-closed
   y no comunica al usuario).
7. Panel de configuración (canal WhatsApp, plan, datos del negocio).

**Dirección visual recomendada:** registro cálido y humano (el comprador es un
dueño de negocio, no un ingeniero), con acento ámbar, tipografía sans con
titulares en caja normal (reservar mayúsculas editoriales para kickers), UI
product shots y fotografía real de negocio pequeño. Detalle en
`../sistema-diseno-compartido.md` §3.4 y §4.

**Recomendación de imágenes:** capturas reales del dashboard con datos de demo +
fotografía de negocio pequeño; **no** ilustraciones genéricas de IA, que empujan
el producto hacia "chatbot" — precisamente lo que `AGENTS.md` §Anti-regresión
prohíbe.

## 6. Viabilidad de lanzamiento

| Dimensión | Definición |
|---|---|
| Usuario comprador | Dueño de pequeño negocio hispanohablante que ya opera por WhatsApp (LatAm / EEUU hispano) |
| Problema vendible | "Tengo el negocio en el teléfono y no me alcanza el tiempo para perseguir oportunidades, cobrar y dar seguimiento" |
| Propuesta de valor | Convierte la conversación en diagnósticos, activos y **acciones ejecutadas con permiso humano**, con coste visible por acción |
| Alcance mínimo cobrable | Créditos prepago + plan de suscripción con: Action Center, CRM/finanzas básicas, recordatorios, generación de imagen y reportes al teléfono |
| Demo mínima | Flujo `oportunidad → propuesta → aprobación HIGH → ejecución → audit trail`, ejecutado en vivo sobre WhatsApp + dashboard |
| Pricing inicial sugerido | Suscripción base + paquetes de créditos (la infraestructura ya existe y es entera, sin decimales). Cifras concretas: **decisión del propietario** — no se proponen aquí |
| Landing y materiales | Landing existente (`/`) + video corto del flujo real + página de precios + legales ya presentes |
| Pagos / onboarding / soporte | Stripe Checkout + Customer Portal ya construidos; onboarding y soporte son los huecos reales (§5) |
| Métricas de activación / uso / conversión / retención / costo | **No instrumentadas de forma legible hoy**. Existen eventos y audit trail, pero no un panel de métricas de negocio |
| Condiciones go/no-go | Ver `../plan-90-dias.md` §Gates (G-1 y G-2) |

**Secuencia recomendada:** Dona es el **producto nº1 del portafolio** — el único
con usuarios reales y con camino de ingresos ya construido. Ver
`../matriz-comparativa.md` §6 y `../decision-dona.md` §4.

## 7. Backlog P0/P1/P2

Referencia completa en `../backlog-priorizado.md`. Resumen:

- **P0 (bloquea cobrar):** techo de `cryptography`; allowlist de gitleaks;
  rotación de secretos; TCPA/STOP; Alembic como fuente única; `arq` por defecto;
  auth web endurecido; reactivación de producción; verificación del cobro E2E.
- **P1:** cerrar el flujo demostrable del dashboard con tokens compartidos;
  decidir el hero pendiente (`design/landing-hero-v2`); instrumentar y **leer**
  métricas; higiene de restos huérfanos; propagar tokens al frontend.
- **P2:** limpiar workflows de dependabot ruidosos; consolidar
  `docs/ops/agent-runs/`; secret manager gestionado en lugar de `.env`.

**Decisión de arquitectura recomendada:** opción **B, migración gradual tipo
strangler**, con el hardening como primer incremento. Justificación completa en
`../decision-dona.md`. En resumen: el repositorio es grande y vivo con deuda
**localizada**; reconstruir sacrificaría 483 commits, 2360 tests verdes y el único
producto con usuarios para resolver problemas puntuales, y la evidencia recogida
no contiene el disparador que justificaría un repositorio nuevo.
