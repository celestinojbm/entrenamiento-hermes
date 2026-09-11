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

## Principio de esta auditoría

**Cero datos inventados.** Toda cifra técnica proviene de ejecución real sobre
clones limpios. Donde algo no se pudo verificar, se dice explícitamente y se
explica por qué, en lugar de estimarse.

## Condiciones de la ejecución

WSL2 local sin Docker y sin root. Para poder ejecutar las suites que exigen
servicios reales se levantaron, sin privilegios: PostgreSQL 16.15, PostgreSQL
18.6 + pgvector 0.8.6 y Redis 8.10.1. El detalle está en
[evidencia/comandos-y-resultados.md](evidencia/comandos-y-resultados.md) §1.

## Alcance y límites

- **No** se modificó ningún repositorio auditado: solo se leyó y se ejecutaron
  sus comandos declarados.
- **No** se realizaron migraciones, compras, despliegues ni cambios de producción.
- **No** se expusieron secretos, tokens, IPs ni valores de `.env`.
- Las decisiones que requieren un humano (rotar secretos, reactivar producción,
  adoptar licencia, aprobar la ratificación fundacional de EvolveOS) están
  marcadas como tales y **no** se ejecutaron.
