# Auditoría visual de producto — portafolio 2026-09

Responde al bloqueador nº1 de la revisión de Codex sobre el PR #2: *"la
prioridad de frontend no fue auditada visualmente"*. Esta vez sí: **las
aplicaciones se arrancaron, se recorrieron con navegador real, se capturaron
pantallas en escritorio y móvil, se midió accesibilidad con axe-core y se
registraron los errores de consola**.

Todo lo de este documento proviene de ejecución real. Las capturas están en
[`evidencia-visual/capturas/`](evidencia-visual/capturas/) y los datos crudos
(JSON con métricas por ruta y viewport) en
[`evidencia-visual/informe-donalabs-dona-nova.json`](evidencia-visual/informe-donalabs-dona-nova.json)
y [`evidencia-visual/fluvia-e2e.json`](evidencia-visual/fluvia-e2e.json).

---

## 1. Método

| Elemento | Detalle |
|---|---|
| Herramienta | Playwright (Chromium headless-shell 153.0.8010.12) + `@axe-core/playwright` |
| Viewports | escritorio 1440×900 · móvil 390×844 |
| Por ruta y viewport | captura full-page, errores de consola, `pageerror`, peticiones fallidas, `title`, `lang`, `h1`, nº de imágenes sin `alt`, nº de botones sin nombre accesible, overflow horizontal (`scrollWidth > clientWidth`) |
| Accesibilidad | axe-core con etiquetas `wcag2a, wcag2aa, wcag21a, wcag21aa` sobre la captura de escritorio |
| Contexto de navegador | `reducedMotion: reduce`, `locale es-ES` |
| Modo | `next dev` (servidor de desarrollo) en todas las apps |

**Advertencia de interpretación:** al correr en modo desarrollo, Next.js abre un
WebSocket de HMR que falla en este entorno (`ws://…/_next/webpack-hmr`). Esos
errores de consola **son artefacto del servidor de desarrollo, no defectos de
producto**, y así se clasifican abajo. Cualquier error de consola distinto de ese
se reporta como hallazgo.

Aplicaciones arrancadas y puertos reales:

| Producto | Comando | Puerto |
|---|---|---|
| Donalabs showcase | `pnpm --dir design-system/apps/showcase dev` | 3400 |
| Dona landing | `npx next dev --port 3500` (con `NEXTAUTH_SECRET`/`NEXTAUTH_URL` de auditoría) | 3500 |
| Nova web | `pnpm --filter @nova/web dev` | 3000 |
| Fluvia API | `pnpm --filter @fluvia/api start` (`PORT=3700`) | 3700 |
| Fluvia dashboard | `pnpm --filter @fluvia/dashboard dev` | 3200 |

---

## 2. Donalabs — showcase del design system (7 rutas)

Capturado en escritorio y móvil: `/`, `/foundations`, `/components`,
`/animations`, `/marketing`, `/dashboard`, `/evaluated`.

### Lo que está bien

- Es un **sistema real y utilizable**: tokens OKLCH con pareja claro/oscuro,
  escala tipográfica con tamaños en px/rem, espaciado, radios, sombras y set de
  iconos. La página `/foundations` funciona como documentación viva.
- Sin desbordes horizontales en móvil en 6 de 7 rutas, y todas las rutas con un
  `h1` único. Ninguna imagen sin `alt`. Ningún error de consola más allá del HMR.

### Hallazgos medidos (todos verificables en el JSON)

| # | Hallazgo | Evidencia |
|---|---|---|
| V1 | **`/marketing` desborda horizontalmente en escritorio**: `scrollWidth` 1696 px sobre `clientWidth` 1440 px (256 px de desborde) | métrica en JSON + captura |
| V2 | **Contraste insuficiente en la etiqueta del token `--muted`** en `/foundations` (violación axe `color-contrast`, impacto *serious*) | `<span class="font-mono text-xs">--muted</span>` |
| V3 | **Contraste insuficiente en 12 nodos de la variante `destructive`** del botón, en `/components` (axe `color-contrast`, *serious*) | `<button data-variant="destructive" …>` |
| V4 | **Contraste insuficiente en el badge `destructive`** en `/dashboard` (axe `color-contrast`, *serious*) | `<span data-slot="badge" data-variant="destructive">` |
| V5 | **ARIA inválido** en `/evaluated`: `aria-label` sobre un `div` sin `role` (axe `aria-prohibited-attr`, *serious*) | `<div aria-label="Default user avatar" …>` |
| V6 | **4 botones sin nombre accesible y 3 campos sin etiqueta detectable** en `/components` | heurística de DOM en el JSON |
| V7 | **Etiquetas de la escala de espaciado envueltas de forma ilegible**: "spacing-12" se parte en "spacing-" / "12" | visible en la captura de `/foundations` |

**Lectura crítica:** V2, V3 y V4 son contraste insuficiente **en el propio
sistema de diseño**. Como este sistema es la base propuesta para los otros
productos, son la clase de defecto que se propaga a los cuatro. Deben corregirse
en el origen, no ruta por ruta.

---

## 3. Dona — landing y superficie pública (9 rutas)

Capturado: `/`, `/login`, `/checkout`, `/soporte`, `/prototipo`,
`/politica-de-privacidad`, `/terminos-y-condiciones`, `/dashboard`, `/success`.

### Lo que está bien

- La landing tiene **dirección de arte real**: jerarquía editorial fuerte,
  titular de gran tamaño con acento en itálica degradada, rejillas de tarjetas
  consistentes, tabla de precios de tres columnas, FAQ y footer completo. No
  parece un "chatbot de WhatsApp" — cumple el mandato de `landing/AGENTS.md`.
- Todas las rutas responden 200, con `lang="es"`, un solo `h1` y ninguna imagen
  sin `alt`.
- **El gate de autenticación funciona**: `/dashboard` sin sesión renderiza la
  pantalla de login ("Inicia sesion"), no una vista protegida.
- `/checkout` (Stripe embebido) y las páginas legales están completas y
  publicadas.

### Hallazgos medidos

| # | Hallazgo | Evidencia |
|---|---|---|
| V8 | **Contraste insuficiente en texto secundario de secciones oscuras**: `text-white/35` y `text-white/40` fallan AA. Rutas `/` (chip "Respuestas −9%"), `/soporte` (7 nodos), `/success` (2 nodos) | 4 violaciones axe `color-contrast` *serious* |
| V9 | **`link-in-text-block`**: los enlaces dentro de bloques de texto no se distinguen del texto por algo más que el color. Rutas `/soporte` (1 nodo), `/politica-de-privacidad` (2), `/terminos-y-condiciones` (2) | axe *serious* |
| V10 | **Elemento decorativo del hero que no renderiza bien**: bajo la maqueta del dashboard aparece un triángulo negro de gran tamaño en lugar del elemento gráfico previsto | visible en la captura de `/` |
| V11 | **Tarjeta incompleta en la rejilla "Seis módulos"**: la sexta tarjeta (Medición) aparece sin icono ni contenido visible | visible en la captura de `/` |
| V12 | **La imagen del hero no es una captura real** del producto: es una maqueta dibujada | visible en la captura de `/` |
| V13 | **CSP sin `unsafe-eval` en desarrollo** impide a React hacer validación en modo dev (un error de consola por ruta) | `eval() is not supported in this environment… React requires eval() in development mode` |

### Lo que NO se pudo capturar y por qué

- **Dashboard autenticado.** Requiere una sesión NextAuth derivada de Stripe y
  el backend FastAPI con sus secretos. `docs/CURRENT_STATE.md` declara la
  producción **suspendida** y las env de Vercel vacías. **Estado registrado: no
  verificado visualmente.** Es exactamente el flujo que el `plan-90-dias.md`
  pone como primera tarea de frontend.

---

## 4. Nova Context — web app (4 rutas)

Capturado: `/login`, `/reset`, `/`, `/approvals`.

### Hallazgo estructural importante

**Las cuatro rutas renderizan la misma pantalla de login.** La app está
enteramente detrás del gate: no existe superficie pública. Es correcto por
diseño (alpha privada) y significa que **visualmente Nova Context, hoy, es una
pantalla de login**: la timeline, proyectos, aprobaciones, tareas, auditoría y
settings **no son auditables visualmente sin sesión** y no había credenciales
— el propio repo exige aprobación explícita del operador
(`README.md`: *"no real user data until the operator explicitly approves"*).

### Lo que está bien

- **0 violaciones axe** en las 4 rutas. 0 errores de consola. Ningún desborde
  horizontal en escritorio ni móvil. Los campos **sí tienen nombre accesible**.
- El mensaje de privacidad en el login es honesto y específico ("your captured
  context is private to your account: sessions expire, and you can revoke any
  device from Settings").

### Hallazgos medidos

| # | Hallazgo | Evidencia |
|---|---|---|
| V14 | **No hay `h1` en ninguna página**: el encabezado principal "Sign in to Nova" es un **`H2`** (`<h2>Sign in to Nova</h2>`), así que el documento no tiene H1 | volcado de DOM |
| V15 | **La pantalla es visualmente genérica**: formulario centrado con bordes por defecto, sin sistema de diseño, sin marca más allá del texto "Nova Context", enlace azul subrayado por defecto del navegador | captura `nova__login__desktop.png` |
| V16 | **Idioma del producto en inglés** (`lang="en"`) mientras Dona, Fluvia y Donalabs están en español | métrica `lang` |

### Corrección de un falso positivo propio (importante)

En la primera pasada medí "3 inputs sin etiqueta" en `/login` y `/reset`. **Era
un falso positivo de mi heurística**: solo comprobaba `label[for]`, `aria-label`
y `placeholder`, pero los campos usan **`<label>` envolvente**, que sí produce
nombre accesible ("Email", "Password", "Account email"). axe-core, que calcula
el nombre accesible real, **no reportó ninguna violación**, y tenía razón.
Se deja constancia porque la primera medición estaba mal.

---

## 5. Fluvia — dashboard y checkout (recorrido autenticado real)

**Este es el logro más fuerte de esta ronda:** no se auditó una pantalla de
login, se hizo el **recorrido completo de producto** por navegador:

```
POST /api/signup             -> 201
POST /api/session            -> 200
POST /api/onboarding/organization -> 201
POST /api/orgs/<id>/onboarding/merchant -> 201
```

Y con la sesión resultante se capturaron **las 13 rutas autenticadas** en
escritorio y 2 en móvil: overview, payments, refunds, checkout-sessions,
payment-links, payouts, disputes, reconciliation, cases, webhook-events,
webhook-endpoints, api-keys, events.

### Lo que está bien (y ahora está demostrado, no afirmado)

- **0 violaciones axe en las 13 rutas.** Seniors limpios.
- H1 correcto y único en cada ruta ("Panel de operación", "Pagos (payment
  intents)", "Reembolsos", "Sesiones de checkout", "Payment links", "Payouts
  (salidas de dinero)", "Disputas (contracargos)", "Reportes de liquidación",
  "Casos operativos", "Eventos de webhook", "Endpoints de webhook", "API keys",
  "Eventos de auditoría").
- **Sin desbordes horizontales** ni en escritorio (1440/1440) ni en móvil
  (390/390).
- **La banda "SANDBOX — dinero simulado"** es honesta, persistente y visible: el
  usuario nunca puede confundir el entorno con producción. Es el mejor detalle
  de producto de todo el portafolio.
- El checkout (`apps/checkout`) no se capturó en esta ronda (requiere una
  checkout session con `client_secret`); su WCAG AA ya está verificado por axe en
  su propio CI.

### Hallazgos medidos

| # | Hallazgo | Evidencia |
|---|---|---|
| V17 | **El dashboard no tiene sistema de diseño.** La navegación es una pared de enlaces azules subrayados (estilo por defecto del navegador) repartidos en dos líneas; las tarjetas son rectángulos blancos planos; no hay sidebar, ni jerarquía tipográfica, ni badges de estado, ni formato monetario, ni estados vacíos diseñados (solo el texto "Sin registros.") | captura `fluvia__org-overview.png` |
| V18 | **La única ruta con `title` de marca es el propio dashboard**; el `h1` "Panel de operación" compite con el nombre de la organización partido en dos líneas ("Org Auditoria H- / 014") | captura |
| V19 | **El selector de país del onboarding no tiene ninguna opción** (`<select id="merchant-country">` con 0 `<option>`), y aun así el paso se completa con `201` | volcado de DOM + `paisesEnSelectMerchant: 0` |
| V20 | **`pattern` inválido en el campo slug del onboarding**: `pattern="[a-z0-9][a-z0-9-]{1,48}"` → `SyntaxError: Invalid regular expression … /v: Invalid character class`. El navegador ignora el patrón, así que **la validación del slug no está ocurriendo** | error de consola capturado |
| V21 | **El guard CSRF rompe todas las mutaciones si se accede por `127.0.0.1`.** Deriva el origen permitido de `request.url` (que normaliza a `localhost`), así que `Origin: http://127.0.0.1:3200` → `403 origin_not_allowed`. Reproducido con `curl`: `127.0.0.1` → 403 · `localhost` → 201 | ver §6 |
| V22 | **El error de CSRF es indistinguible de un fallo real** para el usuario: la UI muestra "No se pudo crear la cuenta. Inténtalo de nuevo." sin pista alguna | captura + respuesta de la API |

**Lectura crítica:** mi evaluación anterior decía que el frontend de Fluvia
estaba a distancia "**Baja**" del objetivo y que "lo que falta es contenido de
demo, no interfaz". **Era incorrecto.** La accesibilidad es de primera (0 violaciones
axe en 13 rutas) pero **la identidad visual del dashboard es la del navegador sin
estilizar**. Son dos ejes distintos y los había promediado en uno. Corregido en
`matriz-comparativa.md` §4 y en `informes/fluvia.md` §5.

---

## 6. Evidencia del hallazgo CSRF (reproducible)

```bash
# A) acceso por 127.0.0.1 -> 403
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:3200/api/signup \
  -H 'Origin: http://127.0.0.1:3200' -H 'X-Fluvia-CSRF: 1' \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.local","password":"xxxxxxxxxxxx"}'
# 403  {"ok":false,"error":{"code":"origin_not_allowed"}}

# B) mismo request por localhost -> 201
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:3200/api/signup \
  -H 'Origin: http://localhost:3200' -H 'X-Fluvia-CSRF: 1' \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.local","password":"xxxxxxxxxxxx"}'
# 201  {"registered":true,"email_verified":true}
```

El guard **falla cerrado**, que es lo correcto. El defecto es de
**diagnosticabilidad y de experiencia de desarrollo**, no de seguridad: acceder
al dashboard por IP en vez de por nombre rompe todas las mutaciones con un
mensaje que no dice nada.

---

## 7. EvolveOS — sin interfaz, con wireframe

`app/src/index.ts` solo expone `GET /health`; `docs/DEVELOPMENT.md` dice
literalmente *"No UI (Next.js enters in Phase 1)"*. **No hay nada que capturar.**
Se verificó con `find EvolveOS/app/src -name "*.tsx"` → 0 resultados.

Tal como pidió la revisión, se produce **únicamente el wireframe de la pantalla
prioritaria**, sin presentarlo como implementación:
[`informes/evolveos-wireframe-console.svg`](informes/evolveos-wireframe-console.svg).

Representa la pantalla que el propio `docs/MVP_SCOPE.md` §6 identifica como
métrica de éxito: la **cola de gates de la revisión semanal**, con el registro
del venture, el checklist de análisis, las kill criteria preregistradas, la base
de conocimiento pendiente de validación humana y el event log verificable. El
wireframe lleva rotulado en su cabecera que no está implementado.

---

## 8. Síntesis visual del portafolio

| Producto | ¿Se pudo recorrer? | Accesibilidad (axe) | Identidad visual | Veredicto visual |
|---|---|---|---|---|
| Dona (landing) | Sí, 9 rutas | 6 violaciones *serious* (contraste + enlaces) | Propia y con dirección de arte | **Buena base, defectos acotados** |
| Dona (dashboard) | **No** — requiere sesión + backend | no medido | no medido | **No verificado** |
| Nova Context | Solo el gate de login | **0 violaciones** | Genérica, la del navegador | **Sin identidad; el resto no es auditable aún** |
| Fluvia (dashboard) | Sí, 13 rutas autenticadas | **0 violaciones** | Genérica, la del navegador | **Accesible pero no presentable** |
| Fluvia (checkout) | No en esta ronda (requiere sesión de checkout) | WCAG AA en su CI | Propia | No re-medido |
| EvolveOS | **No existe UI** | n/a | n/a | **Wireframe entregado** |
| Donalabs showcase | Sí, 7 rutas | 4 violaciones *serious* | Sistema real y documentado | **El mejor activo visual; 4 defectos que se propagan** |

### La conclusión que cambia respecto a la ronda anterior

El problema de frontend del portafolio **no es uniforme** y no se arregla con un
promedio:

1. **Donalabs** tiene un sistema real con 4 defectos concretos (V2–V5). Es el
   punto de partida correcto, pero **no está listo para propagarse** hasta
   corregir el contraste de `destructive` y `muted`.
2. **Dona** tiene dirección de arte propia; le faltan 4 arreglos puntuales (V8–V11)
   y cerrar el flujo del dashboard.
3. **Nova Context y Fluvia** tienen accesibilidad correcta y **cero identidad
   visual**. Aquí no hace falta "pulir": hace falta **diseñar**. Y son dos
   proyectos, no uno.
4. **EvolveOS** no tiene interfaz: hay que construirla, y debe nacer sobre el
   sistema compartido ya corregido.

Orden de trabajo que se deriva (y que actualiza el `plan-90-dias.md`):
**corregir los 4 defectos del sistema de diseño → cerrar el flujo del dashboard
de Dona → diseñar el dashboard de Fluvia → dar identidad a Nova Context →
construir la consola de EvolveOS.**

### Lo que esta auditoría visual NO cubre

- Interacción (hover, foco, transiciones, teclado): no se ejercitaron estados
  interactivos. **No verificado.**
- Lectores de pantalla reales (NVDA/VoiceOver): la medición es axe-core +
  inspección de DOM, no una prueba con usuario de tecnología asistiva.
- Rendimiento (LCP/CLS/peso): no medido.
- Contraste en el tema oscuro de Donalabs: el toggle existe; se midió el tema por
  defecto.
- Flujo de demo grabable de cada producto: pendiente, y es la tarea P1 de Dona.
