# Revisión de calidad de las vistas previas — H-014, ronda 3

Responde a la indicación: *"para los frontends, exigir vistas previas, capturas
móvil/escritorio y revisión de calidad visual y funcional"*.

**Qué es esto:** maquetas estáticas de las pantallas que la auditoría identificó
como prioritarias y que **hoy no existen o no tienen identidad**. Son vistas
previas, **no implementación**: no están conectadas a ningún backend, no sustituyen
código de los repos auditados y llevan rotulado en su propia cabecera que no están
implementadas.

| Fichero | Qué ilustra | Por qué esa pantalla |
|---|---|---|
| [`fluvia-dashboard.html`](fluvia-dashboard.html) | Panel de operación de Fluvia con sistema de diseño | Hallazgo **V17**: el dashboard real tiene 0 violaciones axe pero **cero identidad visual** — navegación de enlaces azules por defecto y tarjetas planas |
| [`nova-shell.html`](nova-shell.html) | Identidad de acceso de Nova Context | Hallazgos **V14/V15/V16**: sin `h1`, pantalla genérica estilizada por el navegador y producto en inglés |
| [`tokens-corregidos.css`](tokens-corregidos.css) | Contrato de tokens con las correcciones de accesibilidad | Hallazgos **V2–V5**: contraste insuficiente en `--muted` y en `destructive` **dentro del propio sistema de diseño**, que se propagaría a cuatro productos |

---

## 1. Método

`capturar-previa.mjs` (Playwright + axe-core, disponible en este directorio y
reproducible) recorre cada vista en **escritorio 1440×900** y **móvil 390×844** y
para cada combinación mide:

- captura full-page;
- violaciones **axe-core** con las etiquetas `wcag2a, wcag2aa, wcag21a, wcag21aa`;
- `h1` presente y único, `lang`, `title`;
- **desborde horizontal** (`scrollWidth > clientWidth`);
- imágenes sin `alt`, botones sin nombre accesible, campos sin etiqueta detectable
  y enlaces sin texto;
- errores de consola y excepciones de página.

```bash
cd auditorias/portafolio-2026-09/vistas-previas
node capturar-previa.mjs      # escribe capturas/ e informe-vistas-previas.json
```

---

## 2. Resultado final medido

| Vista | Viewport | `h1` | Desborde horizontal | Violaciones axe |
|---|---|---|---|---|
| `fluvia-dashboard.html` | escritorio 1440 | 1 | No | **0** |
| `fluvia-dashboard.html` | móvil 390 | 1 | No | **0** |
| `nova-shell.html` | escritorio 1440 | 1 | No | **0** |
| `nova-shell.html` | móvil 390 | 1 | No | **0** |

**Totales: 0 violaciones axe, 0 desbordes, 1 `h1` por página, 0 errores de consola.**
Capturas en [`capturas/`](capturas/) · datos crudos en
[`capturas/informe-vistas-previas.json`](capturas/informe-vistas-previas.json).

---

## 3. Los cinco defectos que destapó el bucle de revisión

Esta sección importa más que la tabla anterior: **las vistas previas salieron mal
en la primera pasada y lo detectó la propia medición, no una lectura del código.**
Se listan los cinco defectos con su corrección.

| # | Defecto | Cómo se detectó | Corrección |
|---|---|---|---|
| 1 | **Desborde horizontal en móvil** del panel de Fluvia: `scrollWidth` 654 sobre `clientWidth` 390 | Métrica de la captura | `min-width: 0` en los ítems de grid: sin eso, el hijo con `min-width` propio (la tabla) empuja el documento |
| 2 | **Dos `h1` en la pantalla de Nova** (el titular editorial y el del formulario) | Conteo de `h1` por página | El `h1` único es el titular editorial; el del formulario pasa a `h2`. Es exactamente el hallazgo V14 aplicado a mi propia maqueta: yo había cometido el mismo error que critico |
| 3 | **Región desplazable no accesible por teclado** (`scrollable-region-focusable`, impacto *serious*) | axe-core en móvil | `tabindex="0"`, `role="region"` y `aria-label` en el contenedor de la tabla |
| 4 | **Vacío interno desproporcionado en las tarjetas de KPI** (~215 px de alto para tres líneas, con ~90 px muertos entre etiqueta y pie) | Revisión visual de la captura | Ritmo ajustado: `gap` reducido, `line-height` 1.1 en el valor, `align-items: start` en la rejilla. Las tarjetas bajaron a ~130 px |
| 5 | **Vacío de ~440 px en la columna editorial de Nova**, con el pie descolgado al fondo | Revisión visual de la captura | Distribución agrupada arriba y **franja de superficies real** (Timeline, Proyectos, Aprobaciones, Auditoría) que equilibra la columna con contenido, no con relleno |

Los defectos 1, 2 y 3 son **de accesibilidad y de estructura** (los mide la
herramienta). Los 4 y 5 son **de composición** (los ve el ojo). Hacían falta las
dos cosas: axe daba 0 violaciones en la versión con el vacío de 440 px.

---

## 4. Revisión funcional

| Comprobación | Fluvia | Nova |
|---|---|---|
| Un solo `h1` y jerarquía coherente (`h1` → `h2` → etiquetas) | Sí | Sí |
| `lang="es"` declarado y coherente con Dona, Fluvia y Donalabs | Sí | Sí |
| Campos con etiqueta asociada real (`label[for]`) | n/a | Sí |
| Botones y enlaces con nombre accesible | Sí | Sí |
| Tabla con `<caption>`, `th` con `scope` y cifras con `tabular-nums` | Sí | n/a |
| Estados de la máquina de estados visibles como badge, no como texto | Sí (aprobado / en revisión / fallido) | n/a |
| Importes con formato monetario y alineación a la derecha | Sí | n/a |
| Objetivo táctil mínimo en móvil | Sí | Sí |
| Sin desborde horizontal en móvil | Sí | Sí |
| Estados vacíos diseñados | **Pendiente**: la vista previa no incluye el estado vacío de la tabla; queda declarado | n/a |
| Tema claro | **No incluido**: solo tema oscuro | Solo oscuro |
| Foco visible en todos los controles | Sí (`:focus-visible` en los campos y el botón) | Sí |
| Interacción real (hover, transiciones, teclado completo) | Parcial: hay transiciones declaradas, no se probó con teclado | Parcial |

---

## 5. Lo que esta entrega NO es

- **No es implementación.** Ninguna vista previa toca los repositorios auditados
  (Dona, Fluvia, Nova, EvolveOS, Donalabs). Los artefactos viven en el centro de
  coordinación, como el resto de la auditoría.
- **No es un rediseño cerrado.** Son dos pantallas de las muchas que hacen falta
  (Fluvia tiene 13 rutas y Nova seis superficies). El objetivo era dar una
  referencia visual concreta y medible, no la hoja de ruta completa.
- **No sustituye la decisión de producto.** Cuál de estas direcciones se adopta
  sigue siendo una decisión del propietario.
- **No está probado con lector de pantalla real** (NVDA/VoiceOver): la medición es
  axe-core más inspección de DOM.

---

## 6. Qué se deriva para el backlog

| Ítem | Cambio |
|---|---|
| `M7` (corregir los 4 defectos del design system) | **Se refuerza**: los tokens corregidos de `tokens-corregidos.css` son el punto de partida listo para aplicar. Corregir en el origen, antes de propagar |
| `P1.6` (diseñar el dashboard de Fluvia) | **Con referencia**: existe una vista previa medible que marca el objetivo |
| `P1.7` (dar identidad a Nova) | **Con referencia**: idem, con el `h1` y el idioma ya resueltos en la maqueta |
| Nuevo | Añadir el estado vacío de la tabla y el tema claro a las vistas previas cuando se aborde la implementación |
