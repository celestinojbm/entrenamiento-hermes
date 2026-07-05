# entrenamiento-hermes

> **Skill propuesta para la app Hermes (Nous Research).** No está activa: para
> instalarla, copia esta carpeta a `~\.hermes\skills\` (ver `integracion\README.md`).

El operador mantiene un **centro de orquestación de su ecosistema** en
`C:\Users\celes\entrenamiento hermes\`. Cuando el operador pida trabajar en su
infraestructura (VPS, Tailscale, Market Castilla, scrapers, dashboards, monitoreo,
reportes) o diga "lee el tablero", "ejecuta las tarjetas" o "entrenamiento":
opera desde ese directorio siguiendo este protocolo.

## Protocolo de sesión

1. **Abrir**: lee `kanban\tablero.md` y el archivo más reciente de `estado\`.
   Toma las tarjetas de mayor prioridad (Triage primero, luego Todo).
2. **Ejecutar**: por cada tarjeta sigue el ciclo completo
   análisis → ejecución → depuración → documentación → verificación.
   La spec de cada pipeline está en `pipelines\`.
3. **Verificar**: ninguna tarjeta pasa a "Hecho" sin evidencia real
   (salida de comando, archivo generado, respuesta HTTP, extracto de log).
4. **Cerrar**: actualiza `kanban\tablero.md`, escribe entrada en
   `bitacora\sesion-YYYY-MM-DD.md` y, si hubo monitoreo, ejecuta
   `scripts\generar-reporte.ps1`.

## Reglas duras

- **Nada de datos inventados.** Si un chequeo falla o falta acceso, se registra
  como bloqueado con el error literal.
- **El inventario vive en `config\ecosistema.json`** (IPs Tailscale, servicios,
  URLs). Si no existe, la única tarjeta ejecutable es H-001 (pedir los datos al
  operador). Secretos NUNCA en ese archivo: solo nombres de variables de entorno.
- **Scripts `.ps1`: siempre UTF-8 con BOM** y sin guiones largos en código
  (PowerShell 5.1 sin BOM lee ANSI y el em-dash inyecta una comilla que rompe el
  parseo). `\"` y `\$` NO escapan en PowerShell — eso es sintaxis bash.
- **Acciones destructivas** (borrar datos, reiniciar servicios en producción):
  detente y pide confirmación explícita al operador.

## Coordinación con Claude Code

Existe un puente diario `apply-hermes-scout` (10:00) que lleva hallazgos de
Hermes hacia Claude Code (auto-merge de bajo riesgo; dinero/legal vía PR).
Para delegar trabajo a ese puente: deja el hallazgo como tarjeta nueva en la
columna **Triage** de `kanban\tablero.md` con contexto suficiente para actuar
sin esta conversación.

## Qué NO hacer

- ❌ Ejecutar pipelines contra hosts no inventariados en `config\ecosistema.json`.
- ❌ Marcar tarjetas como hechas sin evidencia.
- ❌ Cerrar sesión sin entrada de bitácora (incluso si la sesión falló).
- ❌ Confundir este trabajo con el proyecto `Dona-agent\hermes-poc` (el "segundo
  cerebro" de captura de pantalla): son proyectos distintos que comparten nombre.
