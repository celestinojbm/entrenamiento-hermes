# Pipeline 03 — Salud y Operación de Market Castilla

**Objetivo:** garantizar que el panel y los servicios de Market Castilla estén operativos y que sus flujos críticos funcionen de extremo a extremo.

## Entradas
- `config/ecosistema.json` → sección `market_castilla` (URL del panel, API, endpoint de salud, flujos críticos).

## Fases

1. **Chequeo superficial** — GET al panel y al endpoint de salud; verificar certificado TLS y tiempo de respuesta. Se integra al monitor (pipeline 01).
2. **Chequeo funcional (H-005)** — recorrer los flujos críticos declarados (p. ej. login, listado de productos, alta de pedido de prueba si existe entorno seguro para ello). Con navegador automatizado o llamadas API directas.
3. **Observación de fondo** — revisar logs de la aplicación en el VPS (errores 5xx, excepciones recurrentes, lentitud de queries).
4. **Incidencias** — cualquier fallo funcional genera tarjeta en Triage con evidencia (respuesta HTTP, captura, extracto de log).

## Herramientas que usa Hermes
HTTP/API, navegador, SSH, análisis de logs, documentación.

## Salidas
- Chequeos integrados en `estado/status-*.json` (clave `market_castilla`).
- Sección propia en el reporte ejecutivo.

## Criterio de éxito
Los flujos críticos se verifican al menos a diario; ninguna caída del panel pasa desapercibida más de 15 min.

> ⚠️ **Regla de seguridad:** ningún chequeo funcional escribe datos reales de negocio (pedidos, clientes) salvo que exista un entorno/flag de prueba explícito. Si no existe, el chequeo funcional es solo de lectura.
