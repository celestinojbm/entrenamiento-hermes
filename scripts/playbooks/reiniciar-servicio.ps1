# reiniciar-servicio.ps1 - Playbook: servicio caido (pipeline 04, parte A)
# Reinicia un servicio systemd en un VPS del inventario via SSH (Tailscale) y
# re-verifica su estado. Registra el resultado en la bitacora del dia.
#
# Uso:  powershell -File scripts/playbooks/reiniciar-servicio.ps1 -Nodo hermes-dona-vps -Servicio nginx

param(
    [Parameter(Mandatory=$true)][string]$Nodo,
    [Parameter(Mandatory=$true)][string]$Servicio,
    [string]$ConfigPath = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "config\ecosistema.json")
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$vps = @($config.vps) | Where-Object { $_.nombre -eq $Nodo }

if (-not $vps) { Write-Host "[ERROR] Nodo '$Nodo' no esta en el inventario." -ForegroundColor Red; exit 1 }
if ($vps.ssh_habilitado -ne $true) { Write-Host "[ERROR] ssh_habilitado=false para '$Nodo' en la config." -ForegroundColor Red; exit 1 }

$destino = "$($vps.ssh_usuario)@$($vps.host)"
Write-Host "Reiniciando '$Servicio' en $Nodo..." -ForegroundColor Cyan

$salida = ssh -o ConnectTimeout=10 -o BatchMode=yes $destino "systemctl restart $Servicio && sleep 2 && systemctl is-active $Servicio" 2>&1
$activo = ($LASTEXITCODE -eq 0) -and ("$salida" -match 'active')

$fecha = Get-Date -Format "yyyy-MM-dd"
$hora = Get-Date -Format "HH:mm"
$resultado = if ($activo) { "OK: servicio activo tras reinicio" } else { "FALLO: $salida" }
$linea = "- [$hora] PLAYBOOK reiniciar-servicio :: $Nodo/$Servicio -> $resultado"
Add-Content -Path (Join-Path $raiz "bitacora\sesion-$fecha.md") -Value $linea -Encoding UTF8

Write-Host $resultado -ForegroundColor $(if ($activo) {"Green"} else {"Red"})
if (-not $activo) { exit 2 }
exit 0
