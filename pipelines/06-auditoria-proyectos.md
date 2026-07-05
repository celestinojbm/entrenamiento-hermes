# Pipeline 06 — Auditoría de Proyectos

**Objetivo:** que Hermes (o Claude) pueda auditar cualquier proyecto del usuario con una sola instrucción, produciendo un informe accionable y tarjetas de hallazgos — siempre con el mismo formato.

## Cómo se invoca

El usuario dice: *"Audita el proyecto X"* (o crea una tarjeta `Auditoría de X` en el tablero). El agente:
1. Localiza el proyecto: repo en GitHub del usuario, carpeta local, o VPS (según inventario).
2. Ejecuta las fases de abajo.
3. Entrega informe + tarjetas. Nada más que preguntar salvo que falte acceso.

## Fases de la auditoría

1. **Reconocimiento** — clonar/abrir el repo; mapear estructura, stack, dependencias, scripts de build/deploy, y si tiene despliegue en la nube, verificar que responde.
2. **Salud del código** — deudas evidentes: dependencias desactualizadas o vulnerables, secretos hardcodeados (¡crítico!), archivos muertos, TODOs acumulados, ausencia de tests o CI.
3. **Seguridad básica** — credenciales expuestas en el historial de git, endpoints sin autenticación, CORS/headers en despliegues web, permisos excesivos.
4. **Funcionalidad** — ¿compila/arranca? ¿los flujos principales funcionan? (en local o contra el deploy).
5. **Informe** — `reportes/auditoria-<proyecto>-<fecha>.md` con: resumen ejecutivo (3 líneas), hallazgos por severidad (crítico/alto/medio/bajo) **con evidencia** (archivo:línea, salida de comando), y recomendaciones priorizadas.
6. **Tarjetas** — cada hallazgo crítico o alto se convierte en tarjeta en Triage del tablero, autocontenida (qué, dónde, cómo reproducir).

## Reglas

- **Evidencia siempre**: ningún hallazgo sin archivo:línea o salida literal. Prohibido el "parece que".
- **Solo lectura por defecto**: una auditoría NUNCA modifica el proyecto auditado. Los arreglos son tarjetas, no cambios directos.
- **Secretos**: si se encuentra un secreto expuesto, se reporta el hecho y su ubicación en el informe, pero NUNCA se copia el valor del secreto al informe ni a la tarjeta.
- **Repos privados**: si el agente no tiene acceso, lo dice y pide el mecanismo (el PC local ya tiene `gh` autenticado; el sandbox del panel necesitaría token).

## Criterio de éxito
El usuario lee el resumen ejecutivo en < 1 minuto y sabe exactamente qué arreglar primero. Las tarjetas generadas se pueden trabajar sin releer el informe.
