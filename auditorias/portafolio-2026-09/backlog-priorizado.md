# Backlog priorizado P0/P1/P2 — portafolio 2026-09

Origen: hallazgos verificados de esta auditoría (H-014). Cada ítem lleva ID,
producto, esfuerzo (XS/S/M/L/XL), dependencias, criterio de aceptación (CA) y
responsable sugerido.

Convención de responsable:
- **Propietario** — decisión humana, no delegable.
- **Claude Code** — implementador primario (incluye zona roja).
- **Codex** — segunda opinión / revisión no roja.
- **Hermes** — orquestación, evidencia, verificación y publicación.
- **OpenClaw/Gemini** — auditoría/contradicción de decisiones mayores.

---

## P0 — Bloquea cobrar o bloquea desplegar (ejecutar en días 1–60)

### Dona

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| D-P0-01 | Subir el techo de `cryptography` a `<51` en `requirements.txt` y verificar que `pip-audit` queda verde (cierra PYSEC-2026-3552) | XS | — | Job `pip-audit` del workflow `Security` en verde | Claude Code + Hermes (verif.) |
| D-P0-02 | Allowlist de fixtures sintéticos de test en `.gitleaks.toml` y verificar `leaks found: 0` | XS | — | Job `gitleaks` verde con 0 hallazgos | Claude Code + Hermes (verif.) |
| D-P0-03 | Rotar secretos por proveedor (Anthropic, OpenAI, Stripe, Whapi, Supabase, R2, admin token) con registro de fecha | M | decisión del propietario | Ningún secreto previo sigue activo; registro fechado en `bitacora/` | Propietario + Hermes |
| D-P0-04 | Corregir quiet hours TCPA y robustecer la detección de STOP más allá del set cerrado | M | — | Suite verde + casos nuevos de STOP y quiet hours | Claude Code + Codex (revisión) |
| D-P0-05 | Retirar `metadata.create_all()` del lifespan; Alembic como fuente única del esquema | M | D-P0-03 | Prueba de equivalencia Alembic↔esquema en base limpia | Claude Code |
| D-P0-06 | `arq`/Redis como camino por defecto; `inproc` solo explícito, nunca silencioso | S | D-P0-03 | Job sobrevive a un restart con Redis (test que lo prueba) | Claude Code |
| D-P0-07 | Endurecer el auth web sustituyendo el provisional sin cambiar el contrato de sesión | L | D-P0-03 | Suite de auth web verde + revisión de seguridad sin P1 | Claude Code + Codex (revisión) |
| D-P0-08 | Reactivar producción (Render + Vercel) con env vars, webhook Stripe y provider WhatsApp verificados | M | D-P0-01…07 | Smoke test end-to-end contra producción real | Propietario (autoriza) + Hermes |
| D-P0-09 | Verificar el cobro end-to-end en producción | S | D-P0-08 | Un pago real registrado con su fila en `transacciones_credito` | Hermes (evidencia) |

### Nova Context

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| N-P0-01 | Añadir `LICENSE` y registrar la postura de licencia (hoy ausente: `Donalabs`/`nova-context` sin LICENSE) + NOTICE de atribución | S | decisión del propietario | LICENSE presente; postura registrada por escrito | Propietario + Hermes |
| N-P0-02 | Ejecutar los gates de operador contra infraestructura real (`validate:predeploy`) y un deploy con smoke verde | L | N-P0-01 | `validate:predeploy` PASS en infra real; smoke sin fallos | Claude Code + Hermes |
| N-P0-03 | Iniciar la verificación documental de la cadena de título (R-01) | M | decisión del propietario | Paquete documental iniciado; estado registrado | Propietario |

### Fluvia

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| F-P0-01 | Arreglar el CI para que los bumps de Dependabot puedan entrar (bumps agrupados y `node:22→25`) | M | — | Al menos un PR de Dependabot verde y fusionable | Claude Code |
| F-P0-02 | Llevar el checklist legal (`docs/compliance/legal-questions-checklist.md`) a revisión legal en Colombia | M | decisión del propietario | Checklist entregado; estado por fila registrado (sin conclusiones legales) | Propietario |
| F-P0-03 | Decisión humana registrada sobre Fase 5.1 (proveedor real) | XS | F-P0-02 | Decisión escrita: avanzar o mantener freeze | Propietario |

### Transversal

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| X-P0-01 | Promover los tokens de `Donalabs/design-system` a paquete consumible del workspace y añadir los grupos que faltan (estado, radios, elevación, movimiento) | M | — | Paquete instalable desde los otros repos; showcase actualizado | Claude Code |
| X-P0-02 | Levantar los cinco frontends con datos de demo y producir el mapa de pantallas + faltantes por producto | M | — | Un documento de auditoría visual por producto | Hermes |
| X-P0-03 | Cerrar/actualizar los PRs abiertos (24 Dona, 12 Fluvia) y podar ramas remotas | S | — | PRs abiertos < 5 en Dona y Fluvia; ramas remotas < 15 en Dona | Hermes |
| X-P0-04 | Corregir el test roto en Python 3.14 (`test_contextvar_independiente_entre_tareas_async`) y fijar la matriz de CI | S | — | Suite verde en la matriz declarada (3.11/3.12/3.13) | Claude Code |
| X-P0-05 | `ruff check .` limpio en Dona (446 correcciones automáticas + 12 manuales) | S | — | `ruff check .` sin hallazgos | Claude Code |

---

## P1 — Necesario antes de escalar (días 61–90)

### Dona

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| D-P1-01 | Cerrar el flujo demostrable del dashboard con los componentes base compartidos | L | X-P0-01, X-P0-02 | Demo grabable del flujo principal en < 5 min | Claude Code |
| D-P1-02 | Decidir el destino de `design/landing-hero-v2` (fusionar o descartar) | XS | X-P0-01 | Decisión registrada | Propietario |
| D-P1-03 | Instrumentar y **leer** métricas de activación, uso y conversión post-reactivación | M | D-P0-09 | Métricas leídas y con acción asociada | Hermes |
| D-P1-04 | Higiene: decidir `knowledge/`, `start.sh`, `config/business.yaml`, `migration.py` (NO tocar `enhanced/`) | S | D-P0-05 | Decisión registrada por archivo | Propietario |
| D-P1-05 | Propagar tokens y componentes base al frontend de Dona | M | X-P0-01 | Tokens compartidos en uso, sin regresión visual | Claude Code |

### Nova Context

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| N-P1-01 | Onboarding e inicio del alpha (~25 usuarios) con instrumentación del funnel `invoke → capture → link → action → return` | M | N-P0-02 | Funnel medido por usuario | Propietario + Hermes |
| N-P1-02 | Operar el loop de feedback de alpha (`alpha_feedback`) con revisión semanal | S | N-P1-01 | Categorías revisadas semanalmente con registro | Hermes |
| N-P1-03 | Completar el inventario transitivo de dependencias/licencias | M | N-P0-01 | Inventario completo con licencias verificadas | Codex |
| N-P1-04 | Propagar tokens y componentes base a `apps/web` | M | X-P0-01 | Tokens compartidos en uso | Claude Code |

### Fluvia

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| F-P1-01 | Fase 5.0: cerrar la verificación legal de la matriz de jurisdicción | M | F-P0-02 | Matriz con estado de verificación por fila | Propietario |
| F-P1-02 | Propagar tokens y componentes base a dashboard y checkout, sin romper WCAG AA | M | X-P0-01 | Tokens en uso; axe sigue verde | Claude Code |

### EvolveOS

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| E-P1-01 | Ratificación fundacional: lectura de Part 0 + Apéndice C + `docs/BUILDABILITY_AUDIT.md` (~30–40 min) y decisión sobre el PR #1 | S | decisión del propietario | PR #1 sale de draft o se registran los cambios pedidos | Propietario |
| E-P1-02 | Extraer esquemas machine-readable (`schemas/*.schema.json`, `schemas/gates.yaml`) con validación de drift en CI | M | — | CI valida spec↔schema sin drift | Claude Code |

### Donalabs

| ID | Ítem | Esf. | Deps | CA | Resp. |
|---|---|---|---|---|---|
| L-P1-01 | Hardening operativo: cerrar signups, rotar credenciales de servicios, verificar restauración de backup | M | — | `./scripts/health.sh` verde + una restauración probada | Hermes |
| L-P1-02 | `src/` y documentación del showroom: cubrir los componentes base nuevos | S | X-P0-01 | Showcase cubre los componentes compartidos | Claude Code |

---

## P2 — Posponible sin bloquear nada

| ID | Ítem | Producto | Esf. | Nota |
|---|---|---|---|---|
| D-P2-01 | Desactivar/actualizar los workflows de dependabot que generan ruido | Dona | XS | Menor |
| D-P2-02 | Consolidar `docs/ops/agent-runs/` histórico | Dona | S | Documental |
| D-P2-03 | Estrategia de secret manager gestionado en lugar de `.env` | Dona | M | Mejora, no bloqueo |
| N-P2-01 | API pública, SDK, marketplace, plugins | Nova Context | XL | Explícitamente fuera de MVP (`docs/MVP_SCOPE.md` §5) |
| N-P2-02 | Apps móviles, wake word, E2EE completo | Nova Context | XL | Fuera de MVP por decisión documentada |
| N-P2-03 | Ampliar la cobertura de integración a más rutas | Nova Context | M | Mejora continua |
| F-P2-01 | Multi-país, proveedores múltiples, routing, disputas completas | Fluvia | XL | Fuera de MVP; requiere Fase 5 resuelta |
| F-P2-02 | OTel con collector real y tablero (hoy `request_id` en logs) | Fluvia | M | Desviación ya registrada en el repo |
| E-P2-01 | 60 de los 68 agentes del registro | EvolveOS | XL | Per capability wave |
| E-P2-02 | Kernel completo (SPIFFE/OPA/capability tokens), treasury, células por venture | EvolveOS | XL | Después de Fase 3 |
| L-P2-01 | Postgres gestionado para Vaultwarden y Open WebUI | Donalabs | M | Upgrade path ya documentado |
| L-P2-02 | Exposición pública vía Caddy con dominios reales | Donalabs | S | Solo si hace falta |
| X-P2-01 | Librería de componentes publicada fuera del workspace | Todos | L | No hay consumidores externos: coste sin usuario |
| X-P2-02 | Modo oscuro obligatorio en todos los productos | Todos | M | Contra la decisión de tokens: es preferencia por superficie, no por sistema |

---

## Criterio de uso de este backlog

1. **Nada de P1 antes de P0 completado** en el mismo producto.
2. Los ítems `P0` transversales (X-P0-0x) son los únicos que pueden correr en
   paralelo con el producto protagonista del mes.
3. Todo ítem que toque infraestructura real, dinero o legal está marcado como
   **Propietario** en responsable: no se ejecuta sin decisión humana explícita.
4. Ningún ítem de este backlog introduce features nuevas. Si aparece una, va a
   `P2` con nota y espera al siguiente trimestre.
