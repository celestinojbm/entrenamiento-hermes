# limpiar-disco.ps1 - Playbook: disco critico (pipeline 04, parte A)
# Libera espacio en un VPS del inventario borrando SOLO las rutas declaradas en
# 'rutas_limpieza_segura'. Por defecto es DRY-RUN (muestra que borraria y cuanto
# ocupa); el borrado real exige -Confirmar, porque borrar siempre pide aprobacion.
#
# Uso:  powershell -File scripts/playbooks/limpiar-disco.ps1 -Nodo openclaw-vps            (dry-run)
#       powershell -File scripts/playbooks/limpiar-disco.ps1 -Nodo openclaw-vps -Confirmar (borra)

param(
    [Parameter(Mandatory=$true)][string]$Nodo,
    [switch]$Confirmar,
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
# $PSScriptRoot puede llegar vacio dentro de param() en PS 5.1: calcular aqui.
$dirScript = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$raiz = Split-Path (Split-Path $dirScript -Parent) -Parent
if (-not $ConfigPath) { $ConfigPath = Join-Path $raiz "config\ecosistema.json" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$vps = @($config.vps) | Where-Object { $_.nombre -eq $Nodo }

if (-not $vps) { Write-Host "[ERROR] Nodo '$Nodo' no esta en el inventario." -ForegroundColor Red; exit 1 }
if ($vps.ssh_habilitado -ne $true) { Write-Host "[ERROR] ssh_habilitado=false para '$Nodo' en la config." -ForegroundColor Red; exit 1 }
$rutas = @($vps.rutas_limpieza_segura)
if ($rutas.Count -eq 0) { Write-Host "[ERROR] '$Nodo' no tiene rutas_limpieza_segura declaradas." -ForegroundColor Red; exit 1 }

$destino = "$($vps.ssh_usuario)@$($vps.host)"
$listaRutas = $rutas -join ' '

Write-Host "Disco en $Nodo ANTES:" -ForegroundColor Cyan
ssh -o ConnectTimeout=10 -o BatchMode=yes $destino "df -h /" 2>&1

Write-Host "Espacio ocupado por rutas de limpieza segura:" -ForegroundColor Cyan
ssh -o ConnectTimeout=10 -o BatchMode=yes $destino "du -shc $listaRutas 2>/dev/null | tail -3" 2>&1

if (-not $Confirmar) {
    Write-Host ""
    Write-Host "DRY-RUN: no se borro nada. Re-ejecuta con -Confirmar para borrar las rutas listadas." -ForegroundColor Yellow
    exit 0
}

Write-Host "Borrando rutas seguras..." -ForegroundColor Yellow
ssh -o ConnectTimeout=10 -o BatchMode=yes $destino "rm -rf $listaRutas 2>/dev/null; df -h /" 2>&1

$fecha = Get-Date -Format "yyyy-MM-dd"
$hora = Get-Date -Format "HH:mm"
$linea = "- [$hora] PLAYBOOK limpiar-disco :: $Nodo -> rutas limpiadas: $listaRutas (con -Confirmar)"
Add-Content -Path (Join-Path $raiz "bitacora\sesion-$fecha.md") -Value $linea -Encoding UTF8
Write-Host "Limpieza registrada en bitacora." -ForegroundColor Green
exit 0
