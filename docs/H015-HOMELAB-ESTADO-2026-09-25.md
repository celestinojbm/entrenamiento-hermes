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
- Corrección del propietario (25-09-2026): el PR #4 remoto ya contiene `fix(S8)` en el head `42390b8`. Se considera resuelta la publicación de S8; no repetir esa corrección ni volver a auditar GitHub en el Bloque A.
- [Issue #5](https://github.com/celestinojbm/entrenamiento-hermes/issues/5) conserva la historia de H-015. Algunas notas antiguas describen estados anteriores (Hermes no instalado, Telegram pendiente, Funnel temporal); las observaciones actuales del propietario arriba las reemplazan.
- La issue advierte que `hermes serve` en loopback podría no aplicar el control de autenticación del dashboard. Acceso funcional desde MSI no demuestra por sí solo que el control HTTP/WebSocket sea correcto. Verificar `auth_required`, sesión y rechazo anónimo antes de dar por seguro el arranque persistente. Hubo una contraseña expuesta en una conversación previa: su rotación efectiva debe comprobarse localmente sin revelar valores.

## Forma de ejecución y límites

1. Trabajar de forma continua y secuencial hasta completar H-015; no usar timeboxes artificiales ni detenerse tras el primer informe. Entregar checkpoints sustantivos con evidencia, cambios, estado y siguiente acción, y continuar mientras exista trabajo desbloqueado.
2. Un solo perfil y un solo propietario de cada proceso. Inspeccionar la tarea Windows existente `HomeLab WSL Startup`; no duplicarla. Evitar instancias paralelas de serve o gateway.
3. Mantener el objetivo de activar la configuración acordada y los workflows existentes, avanzando por etapas con rollback preparado. Antes de cualquier acción que pueda interrumpir acceso, enviar mensajes externos, generar cargos, publicar servicios o alterar datos de producción, exponer el paso concreto y sus consecuencias para aprobación. La inferencia de Hermes debe permanecer en modelos gratuitos; no activar fallbacks de pago.
4. No repetir la integración OAuth/MCP pública de ChatGPT con n8n. Conservar workflows y datos. No instalar agentes duplicados. No habilitar Funnel ni exponer servicios.
5. No reiniciar Windows, WSL, Hermes o Telegram durante el Bloque A. Preparar y documentar el corte; solicitar autorización cuando la única verificación pendiente requiera reinicio o interrupción. Continuar mientras tanto con tareas independientes ya autorizadas.
6. El PR #4 ya incluye S8 según confirmación del propietario; no volver a corregirlo ni auditarlo en el Bloque A. El estado del puente firmado permanece sujeto a su prueba end-to-end posterior.

## Modo permanente: automatización del desarrollo

El objetivo de H-015 es dejar el HomeLab operando como sistema continuo de trabajo para automatizar la construcción y mantenimiento de los desarrollos del propietario, incluidos DONA, Donalabs, Fluvia, Nova Context y los repositorios priorizados en sus backlogs.

- No imponer límites artificiales de minutos ni parar al entregar un informe intermedio. Al cerrar una unidad, el coordinador toma el siguiente elemento priorizado de la cola y continúa; mantiene checkpoints con evidencia y registra bloqueos.
- El trabajo es continuo y dirigido por cola/eventos: GitHub Issues y backlogs proveen tareas; n8n gestiona disparadores, cola, reintentos, aprobación y notificaciones; Hermes coordina contexto, asignación, ejecución y memoria; agentes de desarrollo disponibles trabajan en entornos aislados; GitHub conserva ramas, commits, PR, pruebas y trazas.
- Automatizar desde análisis y plan hasta implementación, pruebas, revisión, documentación y creación/actualización de PR. Dejar cada tarea lista para revisión y tomar el siguiente trabajo sin esperar una nueva orden cuando la cola autorizada tenga tareas.
- **Puerta de calidad por tarea:** confirmar alcance y criterios de aceptación antes de editar; trabajar en rama/entorno aislado; ejecutar las pruebas pertinentes y revisar el diff, regresiones, secretos y permisos; registrar comandos, resultados y limitaciones. Pasar a la siguiente tarea solo cuando los criterios se cumplan. Si una prueba falla, corregir y repetir la verificación afectada; si está bloqueada, dejar evidencia y seguir solo con trabajo independiente. No sustituir calidad por velocidad o volumen.
- La autonomía cubre tareas existentes y priorizadas en la cola autorizada. No inventar alcance ni interpretar la continuidad como permiso para cambios irreversibles. Cada informe debe separar evidencia comprobada, inferencias, cambios hechos y decisiones pendientes.
- Si no hay trabajo pendiente y autorizado, esperar nuevos eventos sin ejecutar inferencias en bucle ni gastar tokens. Mantener Hermes en modelos gratuitos exclusivamente; cualquier workflow externo que implique coste debe respetar el presupuesto autorizado y mostrar su coste esperado.
- Respetar límites de permisos por repositorio/agente. No hacer merge, despliegue, cambios destructivos, publicaciones, gastos adicionales ni acciones externas irreversibles sin aprobación específica. El sistema debe producir código y PR revisables de forma autónoma, con aprobaciones humanas en esos puntos de control.
- n8n es infraestructura activa y no se pausa mientras avanza Hermes. No matar procesos Node que formen parte del contenedor. No crear workflows duplicados. Activar los workflows existentes previstos para operar, verificando primero su trigger, efectos, credenciales (nombres solamente) y costes conocidos; conservar configuración y datos. Un riesgo concreto puede bloquear ese workflow particular, pero no debe detener los demás ni el avance independiente.

## Bloque A — trabajo continuo para Hermes Desktop (OptiPlex)

No hay límite de tiempo global. Trabajar en pasos consecutivos, producir evidencia y continuar; si un paso está bloqueado, reportar el bloqueo concreto y avanzar en lo que no dependa de él.

1. Inventariar en solo lectura cómo se inicia WSL desde Windows, cómo se inicia Hermes serve y gateway, sesiones tmux, unidades systemd, tareas programadas, sockets :9119 y rutas de logs. Identificar los PID y dueños de los dos procesos; no matar ni lanzar instancias.
2. Inspeccionar configuración **efectiva**, versión y logs recientes (redactados) de CLI, serve y gateway. Verificar modelo principal, proveedor, auxiliar de compresión/títulos, `free_only`, subagentes/fallbacks, y estado real de sesión Telegram. Aislar el motivo del intento auxiliar `openrouter/free`; proponer corrección de precedencia/caché/sesión sin habilitar modelos de pago.
3. Verificar desde MSI el control de autenticación HTTPS de serve: estado de auth y rechazo de acceso protegido anónimo; confirmar que la contraseña expuesta anteriormente ya no sirve. No imprimir secretos ni trasladarlos a GitHub. Si el control no opera, detener la preparación de persistencia de serve y presentar corrección acotada.
4. Preparar (sin activar) una sola vía de arranque Windows→WSL y una unidad independiente por proceso Hermes, con `HERMES_DASHBOARD_PUBLIC_URL` en el entorno de serve, arranque único, registro, reintentos acotados y rollback. Indicar cómo retirar tmux gateway en un corte controlado solo después de autorización. Conservar Tailscale Serve existente.
5. Entregar: tabla `proceso / PID / responsable / mecanismo de arranque / duplicación / modelo efectivo`; diffs de archivos nuevos; evidencia redactada de auth y auxiliar; pasos exactos de corte y rollback; prueba de reinicio Windows/WSL **pendiente** hasta autorización de ese corte.

## Último checkpoint recibido — Bloque A (25-09-2026)

Informe de Hermes Desktop recibido por el propietario; la sesión reportada no hizo cambios ni detuvo servicios.

- Telegram gateway en tmux `hermes-gateway`, Hermes serve en tmux `hermes-serve`, Tailscale Serve privado, Docker/n8n y otros contenedores se reportan activos. La tarea Windows `HomeLab WSL Startup` no fue visible desde WSL; esto no determina si existe en Windows y debe inspeccionarse allí con PowerShell.
- Configuración guardada de auxiliares coincide con los SKU gratuitos indicados arriba. Hermes reporta que el gateway intentó `openrouter/free` al arrancar y propone reiniciarlo; atribuye el intento a configuración previa/caché, pero esa causa sigue siendo hipótesis hasta cotejar hora de inicio, hora de modificación de config y valor efectivo cargado por cada auxiliar. No reiniciar el gateway sin autorización expresa; no seleccionar modelos de pago.
- Hermes también etiquetó un Node de n8n como duplicado al observar que su PPID coincide con el PID informado para el proceso principal del contenedor. Esa conclusión **no está probada**: una relación padre-hijo apunta a pertenencia al árbol del contenedor, no a un servicio duplicado. No matar ni detener ese proceso. Validar en solo lectura con cgroup/namespaces, `docker top` y árbol de procesos.
- PR #4 se reporta abierto y con `fix(S8)` en head `42390b`, consistente con la corrección del propietario; no repetir esa corrección.

Siguiente avance seguro: verificar en solo lectura la precedencia y carga efectiva de auxiliares; comprobar la pertenencia del proceso Node al contenedor; inspeccionar la tarea de Windows desde el host Windows; y preparar el arranque persistente con plan de corte/rollback. Mantener los servicios actuales. La prueba que requiere reinicio del gateway queda pendiente de autorización expresa.

## Continuación de H-015 (n8n avanza en paralelo con A)

- **B.** Conservar S8 ya resuelto en PR #4. Completar prueba de orden Ed25519 firmada MSI→staging OptiPlex→GitHub→Telegram, con allowlist inocua, deduplicación y rechazo de firma inválida; no activar cron/producción ni fusionar fuera del alcance autorizado.
- **C — en paralelo con A.** Mantener n8n activo. Revisar nombre/estado/trigger/última ejecución de los workflows existentes, efectos y costes por proveedor sin leer secretos; activar los que ya estén configurados para operar, uno por vez, validar sus ejecuciones y registrar fallos. Preservar workflows y datos; no reabrir OAuth/MCP. No borrar ni detener procesos Node. Aislar cualquier flujo concreto con efecto externo o coste no aprobado y continuar los demás. Después preparar integración bidireccional Hermes↔n8n sobre workflow de prueba.
- **D.** Inventario Jev/Jeff, OpenClaw, Claude Code y Codex; integrar gradualmente según permisos, aislamiento y registros, sin instalar duplicados.

## Incidencias abiertas

| ID | Incidencia | Condición de cierre |
| --- | --- | --- |
| A1 | Serve y gateway no demostrados tras reinicio | Arranque único de ambos y acceso privado verificado después de reinicio autorizado |
| A2 | `openrouter/free` se intenta como auxiliar y `free_only` lo rechaza | Configuración efectiva y llamada auxiliar gratuita verificadas; sin fallback de pago |
| A3 | Auth gate del dashboard y rotación previa no verificadas aquí | Acceso anónimo denegado y credencial anterior inválida desde MSI |
| B2 | Circuito firmado no demostrado completo | Una orden inocua una vez, resultado GitHub, aviso Telegram y rechazo de suplantación |
| C1 | Estado y ejecución de workflows n8n por actualizar | Flujos existentes activados según diseño, ejecuciones verificadas y bloqueos específicos documentados |
