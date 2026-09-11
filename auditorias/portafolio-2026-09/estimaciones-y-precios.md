# Estimaciones, supuestos y precios — portafolio 2026-09

Responde al bloqueador nº7 de la revisión: *"'Ningún dato es estimado' es falso.
Hay plazos de 4–8 semanas… Marcar cada estimación, supuestos, confianza y
condición que la invalida. H-014 también pidió pricing inicial: proponer
hipótesis de precio comprobables; no basta con 'decisión del propietario'."*

**Corrección aceptada.** La afirmación "ningún dato de este PR es estimado" era
falsa: se refería a las **mediciones técnicas** (que sí son reales y
reproducibles), pero el documento también contiene **plazos y precios**, que son
estimaciones. Quedan separados a partir de ahora:

- **Medido** = resultado de un comando, con log. No es estimación.
- **Estimado** = juicio con supuestos. Se marca con supuestos, confianza y la
  condición que lo invalida.

---

## 1. Plazos estimados (con supuestos explícitos)

Supuestos comunes a todos: **una persona con atención repartida**, agentes
disponibles para implementación y revisión, y ningún frente nuevo abierto. Si
alguno de esos tres falla, el plazo correspondiente deja de ser válido.

| Estimación | Valor | Supuestos | Confianza | Se invalida si… |
|---|---|---|---|---|
| Dona → primera venta | **4–8 semanas** | Producción suspendida se reactiva tras I1–I6; no aparece un bloqueo legal nuevo en TCPA; la rotación de secretos no descubre cuentas perdidas | **Media** | Aparece un hallazgo legal en TCPA/WhatsApp, o el proveedor de WhatsApp exige revisión de plantillas/verificación de negocio |
| Nova → primera venta | **8–16 semanas** | Se resuelve infraestructura propia o de un proveedor concreto; el alpha de 6 semanas se ejecuta sin recortes; se decide postura de licencia | **Baja** | No hay infraestructura disponible, o se decide no abrir alpha con 25 usuarios |
| Fluvia → primera venta | **4–8 meses** | Fase 5 autorizada, proveedor real elegido, verificación legal colombiana cerrada, y adaptador implementado | **Baja** | La verificación legal de la matriz de jurisdicción revela un requisito no contemplado (p. ej. licencia o capital mínimo) |
| Cerrar el flujo del dashboard de Dona (I1) | **1–2 semanas** | El gate de auth web provisional no bloquea el recorrido con datos de demo | **Media** | El auth provisional impide completar el flujo sin tocarlo antes |
| Corregir los defectos visuales de la landing (I2) | **1–2 días** | Son 4 arreglos acotados y localizados | **Alta** | — |
| Diseñar el dashboard de Fluvia (P1.6) | **3–5 semanas** | Se diseña y aplica a 13 rutas sin tocar el núcleo financiero; axe sigue en 0 | **Media** | El rediseño obliga a tocar los route handlers BFF |

**Ninguna de estas cifras es un compromiso de fecha.** Son rangos para ordenar
decisiones, y su confianza se declara arriba.

---

## 2. Hipótesis de precio comprobables

Regla de esta sección: **una hipótesis de precio solo sirve si dice cómo se
falsifica.** Cada una lleva su métrica y el umbral que obliga a cambiarla.

### 2.1 Dona — el precio ya está publicado, la hipótesis es la conversión

Dato de partida medido: la landing publica **Premium 20 US$/mes** y
**Pro 40 US$/mes** ("Recomendado"), más paquetes de créditos
(captura `dona__checkout__desktop.png`, ruta `/checkout`).

| Hipótesis | Enunciado | Métrica | Se falsifica si… |
|---|---|---|---|
| H-D1 | El plan de **40 US$/mes** convierte ≥ 25 % de las compras frente al de 20 US$ | % de altas por plan | < 15 % elige Pro en 60 días y 30 compras → el plan Pro no tiene propuesta diferencial percibida: renombrar o reprecificar |
| H-D2 | El **paquete de créditos** genera ≥ 30 % de los ingresos recurrentes | ARPU por créditos / ARPU total | < 15 % → los créditos no son el mecanismo de monetización: pasar a límite de uso mensual |
| H-D3 | Un usuario nuevo ejecuta **≥ 3 acciones pagadas** en los primeros 7 días | acciones pagadas/usuario/semana 1 | mediana < 1 → el producto no llega a "hábito" y el churn será alto antes de optimizar precio |

**No se propone cambiar los precios actuales.** Se propone **medirlos**: hoy no
existe panel de métricas de negocio (ver `informes/dona-agent.md` §6), así que
estas tres hipótesis no se pueden falsificar todavía. Eso es parte del trabajo
P1.2, y es el motivo por el que "decisión del propietario" no bastaba.

### 2.2 Nova Context — hipótesis a testear durante el alpha

`docs/BUSINESS_MODEL.md` ya define Free → Pro → Teams → Enterprise, pero sin
cifras. Hipótesis propuesta para el alpha (a testear con los 25 usuarios, **no**
a publicar todavía):

| Hipótesis | Enunciado | Métrica | Se falsifica si… |
|---|---|---|---|
| H-N1 | Pro a **12 US$/mes** (individual) es aceptable para el cohorte de alta carga de contexto | intención de pago declarada en entrevista semanal + conversión si se ofrece al final del alpha | < 25 % dice "lo pagaría" → el valor percibido es de herramienta gratuita, no de infraestructura |
| H-N2 | El **límite gratuito** (p. ej. 50 capturas/mes) es el que empuja a Pro sin ahuyentar | capturas/mes por usuario antes de churn | > 60 % de usuarios se queda justo por debajo del límite sin convertir, o se va antes de tocarlo → el límite no discrimina |
| H-N3 | La **retención a 6 semanas** (mediana ≥ 3 días activos/semana) es condición previa a cualquier precio | el propio umbral del `MVP_SCOPE.md` §9 | < 1,5 días activos/semana → **no cobrar**: es el criterio de kill ya definido por el propio repo |

H-N3 no es una hipótesis nueva: es el criterio de kill del repositorio, y se
incluye aquí para dejar claro que **la secuencia es validar y después cobrar**.

### 2.3 Fluvia — hipótesis a validar antes de Fase 5

| Hipótesis | Enunciado | Métrica | Se falsifica si… |
|---|---|---|---|
| H-F1 | **Fee por transacción** (orden de 1,5–2,5 % sobre el volumen del comercio) es aceptable para el mercado objetivo colombiano frente a las alternativas locales | comparación con tarifas públicas de Wompi/PayU/Mercado Pago en 3 conversaciones con comercios | si el fee propuesto queda por encima de la alternativa local sin diferencial claro → el modelo debe apoyarse en suscripción, no en fee |
| H-F2 | Una **suscripción base** (orden de 30–80 US$/mes) más fee bajo es preferible a fee alto sin suscripción | preferencia declarada en las mismas 3 conversaciones | si ningún comercio acepta suscripción fija → fee puro con mínimo mensual |

**Estas cifras son hipótesis de conversación, no una recomendación de precio.**
El `docs/product/mvp-scope.md` de Fluvia deja el pricing explícitamente para
Fase 5, y esta auditoría no lo cambia.

### 2.4 EvolveOS y Donalabs

No aplica: no se venden. Cualquier hipótesis de precio sería inventada.

---

## 3. Qué sigue siendo medido y no estimado

Para que la corrección no se lea como un descargo general: **siguen siendo
mediciones reales, con log reproducible**, todo lo siguiente:

- Commits, ramas, LOC, número de tests, archivos de test, versiones de SDK y de
  runtimes declarados.
- Resultados de `install`, `typecheck`, `lint`, `test`, `build` con exit code y
  duración.
- El control positivo de Python 3.12 (**2422 passed / 0 failed**).
- Resultados de `pip-audit` y `npm audit` (paquete, CVE, versión con fix).
- Resultados de axe-core por ruta y viewport, capturas, overflow horizontal,
  errores de consola.
- Las cuatro mediciones de gitleaks (defecto / actual / propuesta / sembrado).
- CI real consultado con `gh run list` y `gh run view`.
- Datos de fin de soporte de `endoflife.date` y `nodejs.org/dist`.

## 4. Inventario de todas las estimaciones de este PR

Para que ninguna quede sin marcar, la lista completa:

| Dónde | Estimación | Estado |
|---|---|---|
| `matriz-comparativa.md` §5 | Tiempos hasta primera venta (4–8 sem / 8–16 sem / 4–8 meses) | Marcada como estimación con supuestos; detalle en §1 de este documento |
| `plan-90-dias.md` | Duraciones de tareas (S/M/L/XS) y asignación por mes | Esfuerzo relativo, no plazo |
| `backlog-priorizado.md` | Columna de esfuerzo | Relativo |
| `decision-dona.md` §3 | "Tiempo hasta demo" y "hasta primera venta" por opción | Marcadas; alineadas con §1 |
| Precios de Dona (20/40 US$) | **Medido**: están publicados en la landing | No es estimación |
| Precios de Nova y Fluvia | **Hipótesis** de §2.2 y §2.3 | Marcadas como hipótesis con umbral de falsificación |
