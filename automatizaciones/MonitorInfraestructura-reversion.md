# Reversión: retirada del monitor antiguo «Monitor de infraestructura»

Identificación (MSI, usuario celes):
- Tarea programada: `\EntrenamientoHermes\MonitorInfraestructura`
- Acción: powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\celes\entrenamiento hermes\scripts\monitor-vps.ps1"
- Disparador: temporizado, repetición cada 15 min (PT15M), desde 2026-07-04T23:24
- Consultaba hermes-dona-vps (100.115.171.50) y openclaw-vps (100.118.80.120)

Acción aplicada:
1. Parada de la instancia en curso (no había proceso activo).
2. Deshabilitada la tarea con `schtasks /Change /TN "\EntrenamientoHermes\MonitorInfraestructura" /DISABLE`.
3. Definición exportada a `MonitorInfraestructura.xml` (este directorio).
4. Script, logs y archivos del monitor CONSERVADOS sin modificar.

Reversión (un comando):
    schtasks /Change /TN "\EntrenamientoHermes\MonitorInfraestructura" /ENABLE
o, para recrearla desde la exportación:
    schtasks /Create /TN "\EntrenamientoHermes\MonitorInfraestructura" /XML MonitorInfraestructura.xml

No se ha detenido Hermes, ni gateways, ni WSL, ni Docker, ni n8n, ni demos, ni Hermes-Cola-HomeLab.
