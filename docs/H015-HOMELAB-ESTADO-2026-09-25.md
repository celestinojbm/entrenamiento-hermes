# H-015 — HomeLab: estado y decisiones (25-09-2026)

Fuente de verdad operativa en revisión. Evidencia local aportada por el propietario; lo que solo se observa en GitHub se indica aparte. Esta rama documental no despliega servicios ni modifica el puente.

## Estado confirmado por el propietario

- OptiPlex: Windows con Ubuntu 24.04 WSL2 (usuario `homelab`); perfil histórico activo de Hermes en `/home/homelab/.hermes/`; Docker y n8n funcionan. Hermes Desktop en MSI accede al backend remoto y a las conversaciones históricas.
- Tailscale corre en Windows del OptiPlex; HTTPS privado de Hermes en puerto 10000 lleva a `127.0.0.1:9119` de WSL. n8n usa `127.0.0.1:5678` y Tailscale Serve privado :8443. No habilitar Funnel ni publicar servicios.
- `hermes serve --host 127.0.0.1 --port 9119 --skip-build --isolated` funciona con `HERMES_DASHBOARD_PUBLIC_URL` apuntando al HTTPS privado. Telegram responde a través de un único gateway existente en tmux `hermes-gateway`.
- No está demostrada la recuperación automática de serve y gateway después de reiniciar Windows/WSL.
- `~/.hermes/config.yaml` guarda `model.default=openrouter/free`, `auxiliary.free_only=true`, `auxiliary.openrouter_model=nvidia/nemotron-3-ultra-550b-a55b:free`, compression/title generation fijados a ese SKU gratuito y `x_search` desactivado en cli, telegram, api_server, cron y webhook. Respaldo `config.yaml.bak-h015`. Logs previos aún muestran intentos de auxiliar `openrouter/free` rechazados por `free_only`: configuración efectiva por proceso y sesión pendiente de verificar. Hermes debe funcionar con inferencia US$0; nunca activar fallback de pago. n8n consume OpenRouter por separado.
- n8n Compose: `/home/homelab/homelab/stacks/n8n/compose.yaml`; versión registrada 2.40.5, aproximadamente 8 workflows y 6 tablas: confirmar inventario actual. Su proceso Node pertenece al contenedor Docker (padre tini); no eliminarlo.
- El puente firmado permanece en staging, sin producción, cron ni merge. Clave privada del supervisor solo en MSI; la pública llegó al entorno de prueba del OptiPlex. No publicar claves, tokens ni datos sensibles.

## Evidencia remota GitHub verificada

- [PR #4](https://github.com/celestinojbm/entrenamiento-hermes/pull/4) abierto, sin fusionar; head `puente/codex-hermes-local` @ `42390b81563647840588e3bc87cfb65ffb8c1c3d`. Incluye archivos de autenticación SSH, pero esto no prueba ejecución local.
- La rama `fix/puente-s8-autocontaminacion` no apareció en búsqueda remota y GitHub no encontró el commit abreviado `1c82e3b` en el repositorio. S8 debe tratarse como local/no publicado hasta cotejar SHAs y ancestría; no rebasar ni fusionar a ciegas.
- [Issue #5](https://github.com/celestinojbm/entrenamiento-hermes/issues/5) conserva la historia de H-015. Algunas notas antiguas describen estados anteriores (Hermes no instalado, Telegram pendiente, Funnel temporal); las observaciones actuales del propietario arriba las reemplazan.
- La issue advierte que `hermes serve` en loopback podría no aplicar el control de autenticación del dashboard. Acceso funcional desde MSI no demuestra por sí solo que el control HTTP/WebSocket sea correcto. Verificar `auth_required`, sesión y rechazo anónimo antes de dar por seguro el arranque persistente. Hubo una contraseña expuesta en una conversación previa: su rotación efectiva debe comprobarse localmente sin revelar valores.

## Decisiones y límites

1. Un solo perfil y un solo propietario de cada proceso. Inventariar tareas Windows, systemd, cron, tmux, listeners y PIDs antes de preparar persistencia. Existe antecedente de tarea Windows `HomeLab WSL Startup` para levantar WSL; inspeccionarla, no duplicarla.
2. Preparar unidades o scripts reproducibles de arranque con bloqueo/idempotencia y dependencias explícitas. No habilitarlos ni reiniciar procesos activos hasta revisión concreta del plan de corte. El gateway tmux actual debe seguir funcionando durante la preparación.
3. No repetir la integración OAuth/MCP pública de ChatGPT con n8n. Conservar workflows y datos. No instalar agentes adicionales ni activar el puente hasta sus pruebas.
4. Ningún merge, Funnel, despliegue, nuevo cron, modelo de pago, gasto ni ejecución privilegiada sin autorización específica.

## Bloque A — encargo para Hermes Desktop (OptiPlex; inventario y preparación)

**Tiempo máximo de trabajo:** 25 minutos. Si una etapa tarda más de 7 minutos sin evidencia nueva, parar y reportar. Un solo informe; no abrir auditorías paralelas.

1. Inventariar en solo lectura cómo se inicia WSL desde Windows, cómo se inicia Hermes serve y gateway, sesiones tmux, unidades systemd, tareas programadas, sockets :9119 y rutas de logs. Identificar los PID y dueños de los dos procesos; no matar ni lanzar instancias.
2. Inspeccionar configuración **efectiva**, versión y logs recientes (redactados) de CLI, serve y gateway. Verificar modelo principal, proveedor, auxiliar de compresión/títulos, `free_only`, subagentes/fallbacks, y estado real de sesión Telegram. Aislar el motivo del intento auxiliar `openrouter/free`; proponer corrección de precedencia/caché/sesión sin habilitar modelos de pago.
3. Verificar desde MSI el control de autenticación HTTPS de serve: estado de auth y rechazo de acceso protegido anónimo; confirmar que la contraseña expuesta anteriormente ya no sirve. No imprimir secretos ni trasladarlos a GitHub. Si el control no opera, detener la preparación de persistencia de serve y presentar corrección acotada.
4. Preparar (sin activar) una sola vía de arranque Windows→WSL y una unidad independiente por proceso Hermes, con `HERMES_DASHBOARD_PUBLIC_URL` en el entorno de serve, arranque único, registro, reintentos acotados y rollback. Indicar cómo retirar tmux gateway en un corte controlado solo después de autorización. Conservar Tailscale Serve existente.
5. Entregar: tabla `proceso / PID / responsable / mecanismo de arranque / duplicación / modelo efectivo`; diffs de archivos nuevos; evidencia redactada de auth y auxiliar; pasos exactos de corte y rollback; prueba de reinicio Windows/WSL **pendiente** hasta autorización de ese corte.

## Siguientes bloques (no ejecutar ahora)

- **B.** Resolver ubicación real de S8, comparar con PR #4; probar orden Ed25519 firmada MSI→staging OptiPlex→GitHub→Telegram, con allowlist inocua, deduplicación y rechazo de firma inválida. Sin cron/producción/merge hasta éxito.
- **C.** Inventario n8n y costes OpenRouter independientes; respaldo verificable y workflow aislado para bidireccionalidad local bajo aprobación.
- **D.** Inventario Jev/Jeff, OpenClaw, Claude Code y Codex; integrar gradualmente según permisos, aislamiento y registros, sin instalar duplicados.

## Incidencias abiertas

| ID | Incidencia | Condición de cierre |
| --- | --- | --- |
| A1 | Serve y gateway no demostrados tras reinicio | Arranque único de ambos y acceso privado verificado después de reinicio autorizado |
| A2 | `openrouter/free` se intenta como auxiliar y `free_only` lo rechaza | Configuración efectiva y llamada auxiliar gratuita verificadas; sin fallback de pago |
| A3 | Auth gate del dashboard y rotación previa no verificadas aquí | Acceso anónimo denegado y credencial anterior inválida desde MSI |
| B1 | S8 no se ve en GitHub PR #4 | Commit/ancestría remota y diff S8 comprobados |
| B2 | Circuito firmado no demostrado completo | Una orden inocua una vez, resultado GitHub, aviso Telegram y rechazo de suplantación |
| C1 | Inventario y gasto n8n no actualizados | Conteo actual, proveedor/modelo/costo por workflow y respaldo documentados |
