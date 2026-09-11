# Informe de auditoría — Donalabs

Parte de la auditoría de portafolio 2026-09 (H-014). Línea base y comandos:
`../evidencia/comandos-y-resultados.md`.

---

## 1. Ficha del repositorio

| Campo | Valor |
|---|---|
| Repositorio | `celestinojbm/Donalabs` |
| Rama por defecto | **`claude/donalabs-infrastructure-setup-j2hs6v`** (no `main`) |
| HEAD auditado | `dd6e08b` — 2026-07-08 |
| Primer commit | 2026-07-08 · **6 commits** |
| Ramas remotas | 5 · tags: 0 |
| Autores | Claude (6 de 6 commits) |
| Naturaleza | **Plataforma de servicios compartidos self-hosted**, no un producto |
| Lenguaje | Bash + Docker Compose; design system en TypeScript/Next.js |
| Runtime | Docker Engine 24+ y Compose v2; ~8 GB RAM, ~30 GB disco |
| Servicios | Vaultwarden, Cal.com, Plausible, Penpot, n8n, Open WebUI, yt-dlp |
| Base de datos | Postgres/ClickHouse/Valkey por servicio (aisladas por red por servicio) |
| Licencia | **no hay archivo LICENSE** |
| Tamaño | infraestructura (`services/`, `proxy/`, `scripts/`) + `design-system/` (monorepo pnpm) |
| Documentación | `README.md`, `docs/architecture.md`, `docs/security.md`, `docs/consuming.md`, `services/*/README.md`, `design-system/docs/*` |
| CI | `Design System CI` e `Infrastructure Validation` |
| PRs / issues abiertos | 1 PR / 0 issues |

## 2. Línea base reproducible

| Comando | Resultado | Duración |
|---|---|---|
| `pnpm --dir design-system install --frozen-lockfile` | exit 0 | 7 s |
| `pnpm --dir design-system run typecheck` | exit 0 | 6 s |
| `pnpm --dir design-system run lint` | exit 0 | 7 s |
| `pnpm --dir design-system run build` | exit 0 | 8 s |

**No existe suite de tests**: `design-system/package.json` declara
`dev`, `build`, `lint`, `format` y `typecheck`, pero **no `test`**. Es el único
repo del portafolio sin cobertura automática de comportamiento.

La parte de infraestructura (Docker Compose + scripts) **no se pudo ejecutar** en
este entorno: no hay Docker disponible en la distro WSL y no hay root. Queda
**No verificado**: el arranque real del stack, `start.sh`, `stop.sh`, `update.sh`,
`backup.sh`, `scripts/restore.sh`, `scripts/health.sh` y `scripts/proxy.sh`.
Lo que sí se verificó es su contenido (`scripts/health.sh`, `generate-secrets.sh`,
`restore.sh`, `init-network.sh`, `proxy.sh`, `lib.sh`) y la documentación asociada.

CI real: push a `main` (2026-07-09) → `Design System CI` success (57s),
`Infrastructure Validation` success (19s).

## 3. Arquitectura y límites de módulos

**Dos mitades con propósitos distintos:**

### 3.1 Plataforma de servicios (`services/`, `proxy/`, `scripts/`)

- **Stacks modulares, un orquestador**: cada servicio es un stack autocontenido en
  `services/<name>/docker-compose.yml`; el `docker-compose.yml` raíz los une con
  `include:`. Se puede correr uno o todos.
- **Red compartida para consumo**: los contenedores de aplicación se unen a la red
  externa `donalabs_edge`, que otros proyectos usan para alcanzarlos por nombre.
  **Las bases de datos quedan en redes privadas por servicio y nunca tocan el edge.**
- **Bases aisladas y con versión alineada al upstream**; Vaultwarden y Open WebUI
  usan su SQLite con ruta documentada a Postgres.
- **Fuente única de configuración**: todo el `.env` raíz, documentado por
  `.env.example`; secretos generados localmente y nunca commiteados.
- **Defaults seguros**: puertos publicados en `127.0.0.1`; exposición pública solo
  vía Caddy opcional con TLS.

Es un diseño **correcto y deliberadamente sobrio**: la separación de redes entre
aplicación y base de datos es el acierto principal.

### 3.2 Design system (`design-system/`)

Monorepo pnpm + Turborepo con `packages/ui`, `packages/eslint-config`,
`packages/typescript-config` y `apps/showcase`.

Contenido real y documentado (`design-system/docs/`):
- `design-tokens.md` — tokens semánticos en **OKLCH** con bloque `.dark` para cada
  token, expuestos como utilidades Tailwind v4 vía `@theme inline`; única fuente de
  verdad en `packages/ui/src/styles/globals.css`. Justificación explícita del uso
  de OKLCH (interpolación perceptualmente uniforme).
- `components.md`, `animations.md`, `stack-decisions.md`,
  `evaluated-libraries.md`, `maintenance.md`.
- Showcase con 7 rutas: `/`, `/foundations`, `/components`, `/animations`,
  `/marketing`, `/dashboard`, `/evaluated`.

**Este es el activo más reutilizable del portafolio entero** y la base natural del
`sistema-diseno-compartido.md`.

## 4. Riesgos técnicos

### (a) Funciona hoy — verificado

El design system instala, tipa, lintea y compila; el CI está verde. Los scripts de
infraestructura existen y están documentados; la documentación de consumo
(`docs/consuming.md`) y de seguridad (`docs/security.md`) es concreta y
accionable (y la verificación documental se hizo: ver §2).

### (b) Bloquea una demostración

**Docker.** El stack completo requiere Docker Desktop con integración WSL o un
host con Docker y ~8 GB RAM. Sin eso no hay demo de la plataforma de servicios.
El design system, en cambio, **sí se demuestra hoy** con `pnpm dev`.

### (c) Bloquea cobrar

No aplica: es infraestructura interna, no se vende. Su "lanzamiento" es operativo.

### (d) Deuda antes de producción

1. **Sin suite de tests** en el design system: `typecheck` y `lint` no verifican
   comportamiento; un cambio de tokens o de componente puede romper el showcase
   sin que CI lo detecte.
2. **Hardening operativo pendiente** por naturaleza (el propio README lo lista como
   "Next steps"): cerrar signups tras el primer run en cada servicio
   (`VW_SIGNUPS_ALLOWED=false`, `PLAUSIBLE_DISABLE_REGISTRATION=true`,
   `OPENWEBUI_ENABLE_SIGNUP=false`), guardar credenciales en Vaultwarden, programar
   `backup.sh` por cron.
3. **Backups incluyen `.env`** con todas las claves de cifrado: el README advierte
   "keep backups private". Es correcto y exige disciplina operativa real.
4. **`yt-dlp` con CVE**: el README fija `YTDLP_VERSION` ≥ `2026.07.04` por
   CVE-2026-55404. **No verificado** cuál es el valor actual en `.env` (el `.env`
   real no está en el repo).
5. **Rama por defecto no convencional** y 1 PR abierto.

### (e) Deuda posponible

Postgres gestionado para Vaultwarden y Open WebUI (ruta ya documentada);
exposición pública con dominios reales vía Caddy; CORS para despliegues públicos.

### Postura de seguridad (revisada, no asumida)

`docs/security.md` documenta decisiones concretas y correctas: secretos generados
localmente con `chmod 600`; puertos en `127.0.0.1`; bases en redes privadas;
exposición solo por Caddy; lock-down de signups; `/admin` de Vaultwarden con token
y opción Argon2; y un wrapper `yt-dlp` **sin ejecución insegura** (no reenvía flags
arbitrarios que habilitarían `--exec`, usa `--ignore-config`, solo acepta URLs
`http(s)`, pasa las URLs como `argv` tras `--`, y corre como usuario no-root en
contenedor desechable). Es una de las mejores piezas de razonamiento de seguridad
del portafolio.

## 5. Frontend y producto

**`design-system/apps/showcase`** — Next.js con Tailwind v4 y shadcn.

| Ruta | Función |
|---|---|
| `/` | Portada del showcase |
| `/foundations` | Referencia viva de tokens (color, tipo, espaciado) |
| `/components` | Galería de componentes del paquete `ui` |
| `/animations` | Catálogo de animaciones |
| `/marketing` | Patrones de página de marketing |
| `/dashboard` | Patrón de dashboard |
| `/evaluated` | Librerías evaluadas y descartadas |

**Mapa de experiencia actual:** es una **referencia interna**, no un producto. Su
usuario es otro desarrollador del portafolio.

**Lo que le falta para sostener el portafolio:**

1. **Suite de tests** de tokens y componentes (visual + de comportamiento).
2. Documentar los grupos de tokens que hoy **no existen**: estado
   (success/warning/danger/info), radios explícitos, elevación semántica y
   duración/curvas de movimiento. Hoy el sistema cubre superficie, acción, datos y
   sidebar, pero no estados ni movimiento.
3. Publicar el paquete de tokens/componentes como consumible desde los otros
   repos del workspace (hoy cada producto reimplementa su capa).
4. Página de "cómo adoptar" para los cuatro productos consumidores.

**Dirección visual recomendada:** técnico, interno y ordenado — neutro con el
acento del propio design system; tipografía sans técnica; movimiento nulo. El
showcase debe leerse como **documentación viva**, no como producto de marketing.

**Recomendación de imágenes:** diagramas de arquitectura de la plataforma
(red `donalabs_edge`, aislamiento de bases, flujo de backup/restore) y capturas
del showcase. Sin fotografía ni ilustración.

## 6. Viabilidad de lanzamiento

| Dimensión | Definición |
|---|---|
| Usuario comprador | **No aplica.** El "usuario" son los otros proyectos del portafolio y el operador |
| Problema vendible | No aplica |
| Propuesta de valor | Servicios compartidos definidos como código, versionados, persistidos, con health checks y backups: no reinventar gestión de secretos, agenda, analítica, diseño, automatización ni interfaz de IA en cada proyecto |
| Alcance mínimo cobrable | No aplica |
| Demo mínima | `pnpm dev` en el showcase (design system). El stack completo requiere Docker |
| Pricing inicial sugerido | No aplica |
| Landing y materiales | No aplica |
| Pagos / onboarding / soporte | No aplica |
| Métricas | No aplica como negocio. Operativas: `scripts/health.sh` verde, una restauración probada, backups corriendo por cron |
| Condiciones go/no-go | No aplica lanzamiento. Condición operativa: el hardening de `../plan-90-dias.md` §2.11 (signups cerrados, credenciales rotadas, restauración verificada) |

**Rol estratégico:** Donalabs es el **habilitador transversal** del portafolio y la
base del sistema de diseño compartido. No compite por atención de producto; su
prioridad en el trimestre es **dejar de ser una capa visual huérfana** y pasar a ser
la fuente única de tokens para los cuatro frontends.

## 7. Backlog P0/P1/P2

Referencia completa en `../backlog-priorizado.md`. Resumen:

- **P0:** promover los tokens del design system a paquete consumible y añadir los
  grupos que faltan (estado, radios, elevación, movimiento) — es el ítem X-P0-01
  transversal del backlog.
- **P1:** hardening operativo (cerrar signups, rotar credenciales, verificar una
  restauración de backup); cubrir los componentes base nuevos en el showcase.
- **P2:** Postgres gestionado para Vaultwarden y Open WebUI; exposición pública vía
  Caddy con dominios reales.

**Lo que no se propone:** añadir servicios nuevos a la plataforma, ni publicar el
design system fuera del workspace. No hay consumidores externos y sería coste sin
usuario.
