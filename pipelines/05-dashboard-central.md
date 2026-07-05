# Pipeline 05 — Dashboard Centralizado de Estado

**Objetivo:** una sola pantalla con la salud de todo el ecosistema y su histórico.

## Entradas
- Histórico acumulado en `estado/status-*.json` (esquema estable del pipeline 01).

## Diseño (decisión por defecto, revisable)

- **v1 — HTML estático autocontenido**: una página generada desde los JSON de `estado/` (semáforos por componente, gráfica de disponibilidad, últimos incidentes). Sin servidor, sin dependencias: se abre en el navegador o se sirve con nginx desde el VPS.
- **v2 — si el histórico crece**: servicio ligero en el VPS (FastAPI/Express) con base SQLite alimentada por el monitor, tras estabilizar la v1.

Se elige HTML estático primero porque el monitor ya produce JSON versionados y no añade superficie de fallo a la infraestructura que precisamente queremos vigilar.

## Fases
1. Definir el esquema consolidado (agregación diaria de los status).
2. Generador `scripts/generar-dashboard.ps1` (se crea al activar H-010) → `dashboard/index.html`.
3. Publicación: copia al VPS vía Tailscale o apertura local.
4. Iteración con feedback del usuario.

## Herramientas que usa Hermes
Archivos, terminal, HTML/JS, SSH para despliegue, navegador para verificación visual.

## Criterio de éxito
El usuario puede responder "¿está todo bien?" en < 10 segundos mirando una sola página, con datos de menos de 15 min de antigüedad.

> **Prerequisito:** ≥ 1 semana de histórico en `estado/` (por eso H-010 está en Programados).
