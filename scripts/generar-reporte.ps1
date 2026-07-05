# generar-reporte.ps1 - Pipeline 04: reporte ejecutivo desde el ultimo status
# Lee el estado/status-*.json mas reciente y genera reportes/reporte-<fecha>.md
# Compatible con Windows PowerShell 5.1.
#
# Uso:  powershell -File scripts/generar-reporte.ps1

$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
$dirEstado = Join-Path $raiz "estado"
$dirReportes = Join-Path $raiz "reportes"

if (-not (Test-Path $dirReportes)) { New-Item -ItemType Directory -Path $dirReportes | Out-Null }

$ultimo = Get-ChildItem -Path $dirEstado -Filter "status-*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $ultimo) {
    Write-Host "[ERROR] No hay archivos status-*.json en estado\. Ejecuta antes scripts\monitor-vps.ps1 (tarjeta H-003)." -ForegroundColor Red
    exit 1
}

$status = Get-Content $ultimo.FullName -Raw | ConvertFrom-Json
$historico = @(Get-ChildItem -Path $dirEstado -Filter "status-*.json").Count

$semaforo = switch ($status.estado_global) {
    "OK"      { "🟢 OK" }
    "ALERTA"  { "🟡 ALERTA" }
    "CRITICO" { "🔴 CRITICO" }
    default   { $status.estado_global }
}

$md = @()
$md += "# Reporte Ejecutivo del Ecosistema"
$md += ""
$md += "**Fecha:** $(Get-Date -Format 'yyyy-MM-dd HH:mm') · **Fuente:** $($ultimo.Name) · **Barridos historicos:** $historico"
$md += ""
$md += "## Estado global: $semaforo"
$md += ""
$md += "- Chequeos ejecutados: **$($status.total_chequeos)**"
$md += "- Criticos: **$($status.criticos)** · Alertas: **$($status.alertas)**"
$md += ""

$criticos = @($status.resultados | Where-Object { $_.estado -eq "CRITICO" })
$alertas  = @($status.resultados | Where-Object { $_.estado -eq "ALERTA" })

if ($criticos.Count -gt 0) {
    $md += "## 🔴 Incidencias criticas (accion requerida)"
    $md += ""
    $md += "| Componente | Chequeo | Objetivo | Detalle |"
    $md += "|---|---|---|---|"
    foreach ($r in $criticos) { $md += "| $($r.componente) | $($r.chequeo) | $($r.objetivo) | $($r.detalle) |" }
    $md += ""
}
if ($alertas.Count -gt 0) {
    $md += "## 🟡 Alertas (vigilar)"
    $md += ""
    $md += "| Componente | Chequeo | Objetivo | Detalle |"
    $md += "|---|---|---|---|"
    foreach ($r in $alertas) { $md += "| $($r.componente) | $($r.chequeo) | $($r.objetivo) | $($r.detalle) |" }
    $md += ""
}

$md += "## Detalle completo"
$md += ""
$md += "| Estado | Componente | Chequeo | Detalle |"
$md += "|---|---|---|---|"
foreach ($r in $status.resultados) {
    $icono = switch ($r.estado) { "OK" {"🟢"} "ALERTA" {"🟡"} "CRITICO" {"🔴"} default {"⚪"} }
    $md += "| $icono $($r.estado) | $($r.componente) | $($r.chequeo) | $($r.detalle) |"
}
$md += ""
$md += "---"
$md += "*Generado automaticamente por Hermes (pipeline 04). Los omitidos indican componentes aun no inventariados o sin acceso configurado — ver tablero Kanban.*"

$archivo = Join-Path $dirReportes ("reporte-" + (Get-Date -Format "yyyy-MM-dd-HHmm") + ".md")
($md -join "`r`n") | Out-File -FilePath $archivo -Encoding utf8

Write-Host "Reporte generado: $archivo" -ForegroundColor Green
Write-Host "Estado global: $($status.estado_global) - $($status.criticos) criticos, $($status.alertas) alertas"
