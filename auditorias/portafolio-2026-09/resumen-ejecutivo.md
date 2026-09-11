# Resumen ejecutivo — Auditoría de portafolio 2026-09

**Fecha:** 2026-09-11 · **Alcance:** Dona-agent, nova-context, Fluvia, EvolveOS,
Donalabs · **Centro de coordinación:** entrenamiento-hermes · **Tarea:** H-014

Toda cifra técnica de este documento proviene de ejecución real sobre clones
limpios; el detalle y los comandos están en
[`evidencia/comandos-y-resultados.md`](evidencia/comandos-y-resultados.md).

---

## 1. La conclusión en una línea

**El portafolio no tiene un problema de construcción: tiene un problema de foco y
de cierre.** Los cinco repos compilan, instalan y pasan sus suites (o pasarían,
si el entorno tuviera los servicios que piden); lo que falta es decidir el orden,
cerrar la deuda que impide cobrar en el único producto que ya tiene usuarios, y
dar coherencia visual a cinco frontends que existen por separado.

---

## 2. Qué encontró la auditoría (hallazgos verificados)

### 2.1 El único producto con usuarios ya está listo para cobrar, salvo deuda enumerada

**Dona** es el proyecto más antiguo y el único con usuarios reales. Su backend es
maduro (2360 tests verdes, CI `Tests` verde en `main`) y su deuda es **puntual,
conocida y reversible**:

- El workflow **`Security` está rojo de forma permanente** en `main` (3 runs
  fallidos consecutivos), por dos causas concretas y arreglables en horas:
  1. `cryptography 49.0.0` tiene **PYSEC-2026-3552** y el rango
     `>=49.0.0,<50.0.0` de `requirements.txt` **impide aplicar el fix**.
  2. `gitleaks` reporta 6 hallazgos que son **falsos positivos en archivos de
     test** con valores sintéticos.
- Producción **suspendida**, secretos **sin rotar**, quiet hours TCPA y detección
  STOP incompletas, auth web **provisional**.
- La suite **no está verificada en Python 3.14**: los 62 ítems no verdes del
  entorno local son incompatibilidad de `asyncio`, no defectos de producto. El
  repo declara 3.11+ y su CI no cubre 3.14.

**Lectura:** nada de esto exige reescribir. Todo esto exige ejecutar.

### 2.2 Cuando el entorno tiene los servicios, cuatro de cinco repos son verdes

Era crítico no confundir fallo de infraestructura con fallo de código:

| Repo | Sin servicios | Con servicios reales |
|---|---|---|
| Fluvia | 9 passed / 80 skipped (`ECONNREFUSED 5432`) | **verde completo** con PostgreSQL 16 + Redis |
| EvolveOS | `Connection terminated unexpectedly` | **432 passed / 0 failed** + checks de spec **PASS** |
| nova-context | unit verde; integración no ejecutable | **245 passed / 0 failed** con PostgreSQL 18 + pgvector + Redis |
| Donalabs | verde | verde |

**Lectura:** Fluvia y EvolveOS no tienen suites rotas; tienen suites que nadie
estaba ejecutando con sus dependencias reales. Ese es un hallazgo de proceso, no
de código.

### 2.3 Los frontends existen; lo que falta es coherencia y cierre de flujo

- **Donalabs** tiene el **único sistema de tokens real** del portafolio
  (`design-system/packages/ui/src/styles/globals.css`, OKLCH + Tailwind v4,
  documentado en `docs/design-tokens.md`).
- **Fluvia** es el frontend más maduro en accesibilidad (checkout con i18n es/en
  y WCAG AA).
- **Dona**, **nova-context** y **EvolveOS** tienen frontends funcionales sin
  relación formal con esa base.

**Lectura:** "empezar a ver frontends de alta calidad" no requiere cinco
proyectos de diseño. Requiere **una** capa de fundamentos compartidos y cerrar el
flujo demostrable de cada producto. Propuesta completa en
[`sistema-diseno-compartido.md`](sistema-diseno-compartido.md).

### 2.4 Higiene de repositorio despareja

- Dos repos tienen rama por defecto `claude/…` (Fluvia, Donalabs), no `main`.
- **36 PRs abiertos acumulados** (24 en Dona, 12 en Fluvia), mayoría Dependabot.
- En Fluvia **todos los runs de CI de Dependabot fallan**: hoy ninguna
  actualización de dependencias puede entrar sin trabajo de arreglo.
- EvolveOS tiene 11 issues abiertos y 0 PRs: su backlog está sano y esperando una
  decisión humana, no código.

---

## 3. Las cinco decisiones que el propietario debe tomar

1. **Secuencia de lanzamiento: Dona → Nova Context → Fluvia.**
   EvolveOS y Donalabs no se lanzan; se usan.
2. **DONA: opción B (strangler), no reconstruir.** La evidencia no sostiene que el
   repo sea inviable; sostiene que su deuda es localizada. Reconstruir (C)
   sacrificaría 483 commits, 2360 tests verdes y el único producto con usuarios
   para resolver problemas puntuales. Detalle y secuencia B0–B6 en
   [`decision-dona.md`](decision-dona.md).
3. **Frontend primero: el flujo demostrable del dashboard de Dona**, porque es lo
   que se enseña a un comprador en las próximas semanas y ya existe la base.
4. **Nova Context: desplegar de verdad.** Su bloqueo no es técnico — es
   `LICENSE`, cadena de título y ejecutar los gates de operador contra
   infraestructura real. Es el test falsable más barato del portafolio (25
   usuarios, 6 semanas, criterios de kill numéricos ya escritos).
5. **Fluvia: decisión humana sobre Fase 5.** La infraestructura más valiosa a
   largo plazo no debe meterse antes que Dona: su tiempo hasta la primera venta
   se mide en meses y depende de proveedor real y verificación legal.

---

## 4. Qué falta exactamente para vender y lanzar (por producto)

| Producto | Falta para demo | Falta para cobrar | Tiempo hasta 1ª venta (estimación) |
|---|---|---|---|
| **Dona** | Infraestructura con secretos rotados | Secretos, TCPA/STOP, auth web, techo de `cryptography`, reactivar producción | **4–8 semanas** |
| **Nova Context** | Despliegue real (hoy solo hay reuniones de despliegue, nunca ejecutadas) | LICENSE + cadena de título + infraestructura | 8–16 semanas |
| **Fluvia** | Nada relevante: se levanta y se demuestra | Proveedor real (Fase 5) + verificación legal Colombia | 4–8 meses |
| **EvolveOS** | Nada: la consola corre | No aplica: es interno y su spec prohíbe mover dinero sin ratificación | n/a |
| **Donalabs** | Nada | No aplica: plataforma interna | n/a |

---

## 5. Lo que NO recomienda esta auditoría

- **No** recomienda un repositorio nuevo para Dona. La evidencia recogida no
  contiene el disparador que lo justificaría.
- **No** recomienda modernizar de forma indiscriminada. Cada intervención
  propuesta mapea a seguridad, cumplimiento, mantenibilidad o viabilidad
  comercial; ninguna es estética por sí sola.
- **No** recomienda lanzar los cinco productos. El plan de 90 días asigna **un
  producto protagonista por mes** porque la restricción real es la atención, no el
  código.
- **No** recomienda construir features nuevas en ningún producto durante el
  trimestre.

---

## 6. Riesgos que la auditoría deja explícitos

1. **Bus factor 1** en los cinco repos: un solo humano sostiene cuentas, claves y
   decisiones.
2. **Documentación que supera al código** en nova-context y EvolveOS: excelente
   para diseño, peligrosa si se lee como estado. La línea base de este documento
   existe justamente para separar una cosa de la otra.
3. **Riesgo legal en Dona**: mensajería en EEUU con quiet hours TCPA incompletas
   es el bloqueo de cobro más serio, no el técnico.
4. **Riesgo de dispersión**: cinco frentes con una sola capacidad de atención es
   el modo de fallo más probable del trimestre.

---

## 7. Entregables de esta auditoría

| Documento | Contenido |
|---|---|
| [`matriz-comparativa.md`](matriz-comparativa.md) | Comparación medida de los cinco productos y secuencia recomendada |
| [`informes/`](informes/) | Un informe por repositorio |
| [`decision-dona.md`](decision-dona.md) | Decisión argumentada A/B/C con secuencia strangler B0–B6 |
| [`plan-90-dias.md`](plan-90-dias.md) | Plan trimestral con gates go/no-go |
| [`sistema-diseno-compartido.md`](sistema-diseno-compartido.md) | Tokens, tipografía, movimiento, imágenes y componentes base |
| [`backlog-priorizado.md`](backlog-priorizado.md) | Backlog P0/P1/P2 con esfuerzo, dependencias y criterio de aceptación |
| [`evidencia/comandos-y-resultados.md`](evidencia/comandos-y-resultados.md) | Registro reproducible de comandos y resultados |
