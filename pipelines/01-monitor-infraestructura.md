# Pipeline 01 — Monitor de Infraestructura (VPS + Tailscale)

**Objetivo:** detectar cualquier degradación del ecosistema en < 15 minutos, sin intervención humana.

## Entradas
- `config/ecosistema.json` → secciones `vps`, `tailscale`, `endpoints_http`.

## Fases

1. **Conectividad** — ping a la IP Tailscale de cada nodo (`Test-Connection`). Nodo sin respuesta = **CRÍTICO**.
2. **Servicios** — test de puerto TCP por cada servicio declarado (`Test-NetConnection -Port`). Puerto cerrado = **CRÍTICO**.
3. **Endpoints HTTP** — GET a cada endpoint declarado; status 200–399 = OK; 4xx/5xx o timeout = **ALERTA**.
4. **Recursos (vía SSH)** — en cada VPS: `df -h` (disco), `free -m` (memoria), `uptime` (carga). Disco > 85% = **ALERTA**, > 95% = **CRÍTICO**.
5. **Persistencia** — todo se escribe en `estado/status-<timestamp>.json` con esquema estable (lo consume el pipeline 04 y el dashboard 05).

## Definiciones operativas (H-008)

Estas definiciones fijan cuándo Hermes debe tratar un componente como caído, degradado o simplemente pendiente de inventario:

- **Nodo caído (CRÍTICO):** un VPS declarado en `config/ecosistema.json` no responde a 3 pings consecutivos por Tailscale, o todos sus servicios críticos declarados aparecen cerrados/inalcanzables en el mismo barrido.
- **Servicio caído (CRÍTICO):** un puerto declarado en `vps[].servicios` no abre conexión TCP en 5 segundos. Si el servicio no está inventariado, no se asume caída: se registra como pendiente en H-001.
- **Endpoint degradado (ALERTA):** respuesta HTTP 4xx/5xx o tiempo de respuesta mayor que 10 segundos. **Endpoint caído (CRÍTICO):** timeout total o sin conexión.
- **Disco en riesgo:** > 85% usado = ALERTA; > 95% usado = CRÍTICO.
- **Memoria en riesgo:** < 15% libre = ALERTA; < 5% libre = CRÍTICO.
- **OMITIDO no es OK real:** un chequeo omitido significa que faltan datos o credenciales (por ejemplo `ssh_habilitado=false`). No dispara incidente, pero mantiene bloqueadas las tarjetas dependientes del inventario completo.

## Herramientas que usa Hermes
Terminal (PowerShell + ssh), lectura/escritura de archivos, análisis de salidas, HTTP.

## Salidas
- `estado/status-YYYY-MM-DD-HHmm.json`
- Si hay CRÍTICO: entrada inmediata en `bitacora/` + tarjeta de incidencia en Triage.

## Umbrales (ajustar en H-008)
| Chequeo | ALERTA | CRÍTICO |
|---|---|---|
| Ping | — | sin respuesta (3 intentos) |
| Puerto TCP | — | cerrado |
| HTTP | ≥ 400 o > 10 s | timeout total |
| Disco | > 85% | > 95% |
| Memoria libre | < 15% | < 5% |

## Criterio de éxito
Ejecución programada cada 15 min (H-007) durante 7 días sin falsos positivos, con al menos una detección real verificada.
