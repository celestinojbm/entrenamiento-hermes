# Auditoría de portafolio 2026-09

Resultado de la tarea **H-014** — *Auditoría ejecutable de portafolio, frontend y
ruta de lanzamiento* (`celestinojbm/entrenamiento-hermes#1`).

Productos auditados: **Dona-agent, nova-context, Fluvia, EvolveOS, Donalabs**.

---

## Cómo leer esta auditoría

1. **[resumen-ejecutivo.md](resumen-ejecutivo.md)** — qué se encontró, qué
   decisión hay que tomar y qué falta para vender y lanzar. **Empezar aquí.**
2. **[matriz-comparativa.md](matriz-comparativa.md)** — comparación medida de los
   cinco productos y la secuencia de lanzamiento recomendada.
3. **[decision-dona.md](decision-dona.md)** — decisión argumentada A/B/C para
   DONA, con la secuencia strangler B0–B6.
4. **[plan-90-dias.md](plan-90-dias.md)** — plan trimestral con gates go/no-go.
5. **[backlog-priorizado.md](backlog-priorizado.md)** — backlog P0/P1/P2 con
   esfuerzo, dependencias, criterio de aceptación y responsable sugerido.
6. **[sistema-diseno-compartido.md](sistema-diseno-compartido.md)** — fundamentos
   visuales compartidos y variaciones de marca.
7. **[informes/](informes/)** — un informe por repositorio con las 7 secciones
   exigidas: ficha, línea base reproducible, arquitectura, riesgos técnicos,
   frontend y producto, viabilidad de lanzamiento y backlog.
8. **[evidencia/comandos-y-resultados.md](evidencia/comandos-y-resultados.md)** —
   registro reproducible de comandos, resultados y duración, más los logs crudos.

### Documentos añadidos en la ronda 2 (respuesta a la revisión del PR)

| Documento | Qué responde |
|---|---|
| [auditoria-visual.md](auditoria-visual.md) | La prioridad de frontend **medida con navegador**: 65 capturas, axe-core, escritorio y móvil, 22 hallazgos numerados |
| [matriz-actualizacion.md](matriz-actualizacion.md) | Versión actual vs. estable, breaking changes, CVE/EOL, coste y decisión de actualización por repo |
| [estimaciones-y-precios.md](estimaciones-y-precios.md) | Qué es medido y qué es estimado, con supuestos, confianza e hipótesis de precio falsificables |
| [evidencia-gitleaks.md](evidencia-gitleaks.md) | Cómo dejar el gate de secretos en verde **sin cegarlo**, con prueba de secreto sembrado |
| [propuestas/gitleaks-dona.toml](propuestas/gitleaks-dona.toml) | La configuración propuesta, aplicable tal cual |
| [evidencia-visual/](evidencia-visual/) | Capturas, JSON con métricas por ruta y los scripts de captura |
| [informes/evolveos-wireframe-console.svg](informes/evolveos-wireframe-console.svg) | El wireframe de la pantalla prioritaria de EvolveOS (no implementada) |

## Principio de esta auditoría

**Cero datos inventados.** Toda cifra técnica proviene de ejecución real sobre
clones limpios. Donde algo no se pudo verificar, se dice explícitamente y se
explica por qué, en lugar de estimarse.

**Lo medido y lo estimado están separados y etiquetados.** Plazos, esfuerzos y
precios son estimaciones: llevan supuestos, confianza declarada y la condición
que las invalida, en [estimaciones-y-precios.md](estimaciones-y-precios.md). El
resto son resultados de comandos con su log.

## Condiciones de la ejecución

WSL2 local sin Docker y sin root. Para poder ejecutar las suites que exigen
servicios reales se levantaron, sin privilegios: PostgreSQL 16.15, PostgreSQL
18.6 + pgvector 0.8.6 y Redis 8.10.1. El detalle está en
[evidencia/comandos-y-resultados.md](evidencia/comandos-y-resultados.md) §1.

## Alcance y límites

- **No** se modificó ningún repositorio auditado **durante la auditoría**: solo se
  leyó y se ejecutaron sus comandos declarados, y las pruebas que exigían escribir
  se hicieron sobre **copias aisladas** (`/tmp/nova-run`).
  **Excepción, por instrucción explícita del propietario:** la corrección de V25
  (tarjetas de tarea ilegibles en móvil) se entregó en una **rama del repositorio
  de Nova** — `celestinojbm/nova-context#19` — sin fusionar ni desplegar.
- **No** se realizaron migraciones, compras, despliegues ni cambios de producción.
- **No** se expusieron secretos, tokens, IPs ni valores de `.env`.
- Las decisiones que requieren un humano (rotar secretos, reactivar producción,
  adoptar licencia, aprobar la ratificación fundacional de EvolveOS) están
  marcadas como tales y **no** se ejecutaron.
### Documentos añadidos en las rondas 3 y 4 (respuesta a las revisiones)

| Documento | Qué responde |
|---|---|
| [matriz-canonica.md](matriz-canonica.md) | **Fuente única de verdad por producto**: prueba técnica, cobertura visual, demo, cobro, limitaciones y evidencia (corrección 1) |
| [nova-recorrido/](nova-recorrido/) | **Recorrido autenticado de Nova con cuenta sintética**: 15 capturas, axe y los hallazgos V23–V26 (corrección 2a) |
| [dona-dashboard/](dona-dashboard/) | Gate de Dona documentado, intento reproducible y **maqueta del flujo prioritario** con seis estados (corrección 2b) |
| [vistas-previas/revision-calidad.md](vistas-previas/revision-calidad.md) | Ronda 3: vistas previas con capturas móvil/escritorio, tipografía autoalojada y **reetiquetado a validación de maquetas estáticas** (corrección 3) |
| [node-lts.md](node-lts.md) | **Node 24 LTS, no 25 (EOL)**, rango acotado y los cuatro sitios donde vive el runtime (corrección 5) |
| [evidencia-gitleaks-estado.md](evidencia-gitleaks-estado.md) | Cifras corregidas (5 literales → **3 supresiones**, no 4) y criterio de cierre del gate (corrección 7) |
| [precio-experimentos.md](precio-experimentos.md) · [precio-unit-economics.md](precio-unit-economics.md) | Hipótesis convertidas en **experimentos falsables** y el **piso económico** por cuenta y por acción (corrección 8) |
