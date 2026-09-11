# Sistema de diseño compartido — propuesta para el portafolio 2026-09

Estado: propuesta de auditoría (no implementada). Autor: Hermes, con base en la
evidencia de `evidencia/comandos-y-resultados.md` y en los informes por
repositorio de `informes/`.

---

## 1. El problema que resuelve

Los cinco productos se diseñaron en momentos distintos, con agentes distintos y
sin una capa visual común:

- **Donalabs/design-system** ya tiene un sistema de tokens real (shadcn + Tailwind
  v4 + OKLCH, `Donalabs/design-system/packages/ui/src/styles/globals.css`,
  documentado en `Donalabs/design-system/docs/design-tokens.md`). Es la única base
  de tokens existente en el portafolio.
- **Dona-agent** tiene su propio Next.js con shadcn/Radix y modo oscuro
  (`Dona-agent/landing/`), sin relación formal con el de Donalabs.
- **Fluvia** tiene checkout y dashboard propios (Next.js 15, i18n es/en, WCAG AA).
- **nova-context** tiene web app + extensión MV3 + browser-shell Electron.
- **EvolveOS** tiene el console (Next.js) con foco en tablas de gobernanza.

El objetivo no es unificar la *identidad* — cada producto debe seguir siendo
reconociblemente suyo — sino unificar **fundamentos**: tokens, escala tipográfica,
espaciado, radios, sombras, estados, accesibilidad y componentes base. Eso es lo
que hace que "ver frontends de alta calidad en todos los productos" deje de ser
cinco proyectos de diseño y pase a ser un proyecto con cuatro variaciones.

## 2. Principios rectores

1. **Claridad primero.** Cada elemento responde a una pregunta del usuario. Si no
   responde a ninguna, se elimina. Sin efectos decorativos sin función.
2. **Premium por contención, no por ornamentación.** La sensación premium del
   portafolio viene de espacio en blanco generoso, jerarquía tipográfica fuerte,
   contraste disciplinado y movimiento sutil con propósito — no de gradientes,
   glassmorphism ni animaciones de adorno.
3. **Product shot como material principal.** En productos de infraestructura y
   agentes con interfaz real (Fluvia, nova-context, Dona) la UI es el mejor
   activo visual: capturas de la pantalla en uso, con datos de demo reales,
   superan a cualquier ilustración genérica. Donde no hay UI todavía — EvolveOS,
   cuyo `app/` solo expone `GET /health` — el sustituto honesto es un diagrama,
   nunca una maqueta presentada como producto existente.
4. **Verde operativo ≠ verde visual.** Un "estado correcto" visual nunca debe
   ocultar un estado de datos degradado o vacío (ver `OMITIDO` en la política de
   reportes de entrenamiento-hermes: `SKILL.md`).
5. **Accesibilidad como requisito, no como fase.** WCAG AA (contraste, foco
   visible, navegación por teclado, `prefers-reduced-motion`) desde el primer
   componente. Fluvia ya lo declara en `Fluvia/apps/checkout`; debe ser el
   estándar del portafolio, no la excepción.

### Referencias autorizadas (forma, no identidad)

El propietario autorizó inspirarse en la sobriedad de UsaDona.com, Luma,
ChatGPT/Codex y la app desktop de Hermes, con preferencia declarada por el
registro premium oscuro de LTX Studio: tipografía editorial en mayúsculas,
tarjetas cinematográficas/de vídeo, workflows modulares, "starting points" y
sensación de control.

Regla de uso: se toma el **registro** (densidad, ritmo, jerarquía, tratamiento de
tarjetas y de movimiento), nunca la **identidad** (logo, paleta exacta, copy,
layout reconocible). Ningún producto debe parecer una copia de otro.

## 3. Fundamentos propuestos

### 3.1 Tokens

Base: adoptar el sistema ya existente en
`Donalabs/design-system/packages/ui/src/styles/globals.css` (OKLCH + `@theme`
inline de Tailwind v4) como capa de tokens canónica del portafolio, y publicarla
como paquete consumible en lugar de reimplementarla cuatro veces.

Conjunto mínimo obligatorio por producto:

| Grupo | Tokens | Nota |
|---|---|---|
| Superficie | `background`, `foreground`, `card`, `popover`, `muted`, `border`, `input`, `ring` | ya existen en Donalabs |
| Acción | `primary`, `primary-foreground`, `secondary`, `accent`, `destructive` | ya existen |
| Estado | `success`, `warning`, `danger`, `info` (+ `-foreground`) | **faltan hoy**: los productos usan verdes/rojos crudos |
| Datos | `chart-1`…`chart-5` | ya existen; falta criterio de uso por producto |
| Espaciado | `--spacing` (0.25rem) | default, correcto |
| Radios | `--radius` + derivados sm/md/lg/xl | definir explícitamente |
| Elevación | `shadow-*` semánticos (no por valor) | hoy disperso |
| Movimiento | `--duration-fast/base/slow`, `--ease-out/in-out` | **no existe hoy**: definir |

Motivo de la elección OKLCH (`Donalabs/design-system/docs/design-tokens.md`):
interpolación perceptualmente uniforme; los estados hover/activo no producen
puntos medios "sucios". No hay razón para introducir otro modelo de color.

### 3.2 Tipografía

- **Sans de producto:** una sola familia en todo el portafolio para UI y texto
  (Donalabs ya usa Geist vía `next/font`). Alternativa de marca para landings:
  una familia editorial (grotesk de alto contraste) **solo** para titulares.
- **Mono:** obligatoria en Fluvia, EvolveOS y nova-context (ids, hashes, códigos
  de evento, campos técnicos). No decorativa.
- **Escala:** mantener la escala por defecto de Tailwind como base y añadir
  únicamente los pasos que falten para display editorial (`text-5xl`…`text-7xl`).
- **Mayúsculas editoriales:** usarlas para *etiquetas de sección y kickers*, con
  `tracking-wide` — no en párrafos ni en cuerpos de texto.
- **Regla de densidad:** landings respiran (interlineado amplio, bloques grandes);
  consolas y dashboards densifican (filas compactas, tipografía pequeña pero con
  contraste suficiente para AA).

### 3.3 Movimiento

- Duración base 150–250 ms; transiciones de vista 250–400 ms.
- Propósito único: dar continuidad espacial (de dónde viene y a dónde va un
  elemento) y confirmar acciones. Prohibido animar para "llenar".
- Respetar `prefers-reduced-motion` de forma global (hoy no verificado en ningún
  producto — ver informes).
- Movimiento cinematográfico (video, reveals) reservado a **landings y páginas de
  producto**, nunca dentro de flujos transaccionales (checkout de Fluvia,
  aprobaciones de acciones en Dona/nova-context).

### 3.4 Imágenes

Recomendación por tipo de producto, no por gusto:

| Producto | Material recomendado | Por qué |
|---|---|---|
| Dona | UI product shots + fotografía real de negocio pequeño + iconografía propia de acciones/riesgo | El producto se vende a un dueño de negocio, no a un ingeniero: necesita reconocerse en la escena |
| Nova Context | UI product shots de captura + diagramas de flujo del "Context Moment" + motion corto (captura → acción) | El valor es un flujo invisible (contexto→acción); el motion lo hace visible |
| Fluvia | UI product shots del dashboard/checkout con datos de demo + diagramas técnicos (ledger, outbox/inbox, RLS) | Compra un decisor técnico/financiero; la duda es "¿es serio?", se responde con la interfaz y con arquitectura |
| EvolveOS | Diagramas de gobernanza (gates, DR, event log); **sin capturas de UI porque todavía no existe** (`app/` solo expone `GET /health`, `docs/DEVELOPMENT.md` §"Out of scope"). Sin fotografía | Es un sistema de decisión; la fotografía genérica de "startup" restaría seriedad |
| Donalabs | Diagramas de arquitectura de plataforma + capturas del showcase del design system | Es infraestructura interna; su audiencia son otros proyectos y operadores |

Regla transversal: **nada de stock genérico** (manos estrechándose, personas
señalando pantallas). Si no hay material propio, mejor un diagrama honesto.

### 3.5 Iconografía

Una sola librería de iconos para todo el portafolio (línea, grosor 1.5–2 px,
óptica consistente). Candidata natural: la que ya entra por shadcn/Lucide en
Donalabs y Dona. Los iconos de **riesgo** (LOW/MEDIUM/HIGH/CRITICAL de Dona) y de
**estado operativo** deben ser propios y consistentes: son semánticos, no
decorativos.

## 4. Variaciones de marca por producto

Misma base de tokens; varía solo un eje cromático de acento, un registro
tipográfico de titulares y el tono de movimiento.

| Producto | Registro | Acento propuesto | Titulares | Movimiento |
|---|---|---|---|---|
| Dona | Cálido, humano, "negocio que funciona" | Ámbar/cálido | Sans editorial, caja normal | Suave, confirmatorio |
| Nova Context | Preciso, etéreo, infraestructura | Frío alto (azul-violeta) | Sans editorial, mayúsculas en kickers | Motion de flujo (captura→acción) |
| Fluvia | Sobrio, bancario, confiable | Verde/teal profundo con neutros fríos | Sans neutra, sin display | Mínimo: solo confirmación |
| EvolveOS | Institucional, serio, gobernanza | Monocromo + un acento de aprobación | Sans neutra densa | Casi nulo |
| Donalabs | Técnico, interno, ordenado | Neutro + acento del design system | Sans técnica | Nulo |

## 5. Componentes base compartidos (mínimo viable)

No se propone un "design system completo" (sería otro proyecto de meses). Se
propone extraer **siete** piezas que hoy se repiten mal en todos los productos:

1. `AppShell` (nav + layout responsive, colapsable, foco visible).
2. `DataTable` (densidad, orden, paginación, estados vacío/carga/error, fila técnica mono).
3. `StatusBadge` (estados semánticos + estados operativos, accesible sin depender solo del color).
4. `ApprovalCard` (preview → confirmar → resultado; patrón común a Dona, nova-context y los gates de Fluvia/EvolveOS).
5. `Money`/`IdCell` (mono, tabular, sin `float` en presentación; relevante para Fluvia y Dona billing).
6. `EmptyState` / `ErrorState` / `Skeleton` (hoy inexistentes o inconsistentes).
7. `Toast`/`InlineAlert` (éxito, advertencia, error, con `role` correcto).

## 6. Plan de adopción

1. **Fase A — Tokens canónicos (1 semana).** Promover el paquete de tokens de
   `Donalabs/design-system/packages/ui` a fuente única; añadir los grupos que hoy
   faltan (estado, radios, elevación, movimiento). Publicar como paquete del
   workspace consumible vía pnpm.
2. **Fase B — Auditoría visual por producto (1 semana).** Levantar cada frontend
   con datos de demo y producir el mapa de pantallas + la lista de faltantes
   (está en cada informe). Sin cambios de código.
3. **Fase C — Rediseño del flujo demostrable (2–4 semanas por producto).** En el
   producto elegido primero (§6 de `plan-90-dias.md`), reconstruir solo las
   pantallas del flujo principal con los componentes base.
4. **Fase D — Propagación.** Aplicar tokens + componentes al resto, en orden de
   secuencia de lanzamiento.

Regla de no-regresión: ninguna fase introduce un componente compartido nuevo sin
un caso de uso real en al menos dos productos.

## 7. Lo que este documento NO propone

- No propone reescribir los frontends existentes ni migrar de Next.js.
- No propone una librería de componentes publicada fuera del workspace: no hay
  consumidores externos y sería coste sin usuario.
- No propone copiar la interfaz de Luma, ChatGPT o Hermes. Se adopta registro,
  no identidad.
- No propone un modo oscuro obligatorio: se mantiene la preferencia por el
  registro oscuro premium en landings y consolas, y claro/oscuro en dashboards
  transaccionales donde el usuario trabaja horas.
