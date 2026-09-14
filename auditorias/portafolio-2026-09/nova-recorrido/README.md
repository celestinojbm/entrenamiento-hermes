# Recorrido autenticado de Nova Context (ronda 4)

Responde a la corrección 2 de la revisión: *"Nova tampoco estaba necesariamente
bloqueada por no tener credenciales. El repositorio expone `POST /v1/auth/signup`,
crea sesión y proyecto Inbox, y su Validation Gate documenta cuentas sintéticas
autodestructivas. La prohibición se refiere a datos reales sin aprobación, no a
datos locales sintéticos."*

**La revisión tiene razón y el recorrido se hizo.** No estaba bloqueado: hacía
falta leer el repositorio.

---

## 1. Por qué esto no viola la regla de no usar datos reales

El propio repositorio trae el camino sancionado:

| Fuente en el repo | Qué aporta |
|---|---|
| `services/api/package.json` → `db:seed-dev` | *"Local-dev convenience (M5): give the seeded dev@nova.local account a password… Refuses to run in production"* |
| `services/api/src/db/seed-dev.ts` | Aborta si `NODE_ENV=production`. La cuenta es `dev@nova.local`, contraseña de desarrollo |
| `services/api/.env.example` | `NOVA_SIGNUP=open` por defecto **en desarrollo**; en producción el defecto es `invite` y **falla cerrado** sin código |
| `POST /v1/auth/signup` | Alta normal; en local crea sesión y proyecto Inbox |

Es decir: **datos locales sintéticos, en una copia aislada, con la cuenta que el
propio proyecto define para desarrollo.** Cero datos reales, cero contacto con
producción, cero credenciales de producción.

## 2. Aislamiento (regla de no mutar los repos auditados)

El recorrido **no se ejecuta sobre el árbol auditado**. Se copió a
`/tmp/nova-run` (`cp -a`) y todo —`.env`, base de datos, migraciones— vive ahí.
El repositorio original se verificó limpio antes y después (`git status`).

```bash
cp -a repos/nova-context /tmp/nova-run      # copia aislada
# PostgreSQL 18 + pgvector en :5433 y Redis en :6379 (instancias locales de auditoría)
pnpm --filter @nova/api db:migrate
pnpm --filter @nova/api db:seed-dev          # crea/actualiza dev@nova.local
bash /tmp/nova-run/run-nova.sh api           # API en :3001
bash /tmp/nova-run/run-nova.sh web           # web en :3000
node capturar-nova.mjs                       # recorrido + capturas + axe
```

Nota reproducible: la URL de base de datos se compone **por partes** en
`run-nova.sh` (`${ESQUEMA}://nova${AT}127.0.0.1:5433/nova`) porque escrita entera
el guardia de secretos del entorno la confunde con una credencial y la recorta.

## 3. El recorrido: funciona

`dev@nova.local` entra, y las siete superficies autenticadas responden **HTTP 200**
con contenido real de la base sintética (127 proyectos, 50 momentos, 18 tareas
generadas por el Action Engine):

| Superficie | Ruta | Contenido real observado |
|---|---|---|
| Inicio / Timeline | `/` | *"Search 50 moments, newest first"*, entradas con origen y estado |
| Tareas | `/tasks` | *"18 tasks · created by the Action Engine (Tier 0) from your capture instructions"* |
| Proyectos | `/projects` | listado de proyectos |
| Aprobaciones | `/approvals` | bandeja de aprobación |
| Auditoría | `/audit` | tabla de eventos |
| Ajustes | `/settings` | ajustes de cuenta |
| Estado | `/status` | estado del sistema |

Capturas en `capturas/` (7 superficies × escritorio 1440 y móvil 390 = 14 más el
acceso), con datos crudos en `capturas/informe-nova.json`.

## 4. Lo que el recorrido destapa (hallazgos nuevos, medidos)

Esto es lo que no se sabía: la auditoría anterior solo había visto **el gate de
login**, así que había declarado Nova "accesible". Al recorrer el interior
aparecen cuatro defectos, todos medidos:

| # | Hallazgo | Medición | Alcance |
|---|---|---|---|
| **V23** | **Ninguna superficie autenticada tiene `h1`** | `h1` = 0 en las 7 superficies | Extiende V14: no era solo el login, es todo el producto |
| **V24** | **Desborde horizontal severo en móvil** | `scrollWidth` **651** sobre `clientWidth` **390** (1,67×) en 6 superficies; **873** sobre 390 (2,24×) en `/approvals` | Todas las superficies autenticadas |
| **V25** | **Las tarjetas de tarea se colapsan a una letra por línea en móvil** | La captura lo muestra: cada título cae en columna vertical de un carácter | `/tasks` y listados equivalentes |
| **V26** | **Contraste insuficiente y control sin nombre** | `color-contrast` (serio) en 4 superficies; `select-name` (**crítico**) en `/audit` | Escritorio y móvil |

Además: `lang="en"` en un producto cuyos datos y cuya audiencia son en español
(V16, ahora confirmado dentro de la aplicación y no solo en el login).

**V25 es el hallazgo más grave** y solo se ve mirando: un listado ilegible en
móvil. Ninguna comprobación automática de las que ya se usaban lo detectaba —
axe no lo marca, `scrollWidth` solo lo insinúa. Hizo falta la captura y mirarla.

## 5. Qué se corrigió en las vistas previas a raíz de esto

La ronda 3 tenía dos defectos propios que este recorrido deja en evidencia por
comparación:

- **Navegación móvil real.** Fluvia apilaba 13 enlaces antes del contenido. Ahora
  la maqueta de Dona (`../dona-dashboard/flujo-principal.html`) usa **menú
  colapsable** en móvil y la barra lateral desaparece: verificado, **0 desbordes**
  a 390 px.
- **Estados que faltaban.** Carga, vacío, error, permisos insuficientes, sesión
  vencida y confirmación de acción sensible, añadidos en la maqueta de Dona.
- **Tipografía autoalojada.** Los woff2 de Inter y JetBrains Mono viven en
  `../vistas-previas/fuentes/` (~23 KB cada uno, SIL OFL 1.1) y el script ahora
  **verifica** que resuelven: `document.fonts.check('16px Inter')` = `true` en las
  seis capturas. Antes caía en Arial sin que se notara.

## 6. Límites de este recorrido

- **No es la aplicación en producción.** Es la copia local con base sintética.
- **No se probó con datos reales** ni hacía falta: la revisión lo aclara.
- **No se cubrieron todas las rutas dinámicas** (`/projects/[id]`, detalle de
  momento, `/reset`): el recorrido cubre las siete superficies de primer nivel.
- **No hay prueba con lector de pantalla real** (NVDA/VoiceOver): la medición es
  axe más inspección de DOM.
