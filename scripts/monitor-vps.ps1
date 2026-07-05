# monitor-vps.ps1 - Pipeline 01: monitor de infraestructura
# Lee config/ecosistema.json, chequea ping / puertos TCP / endpoints HTTP
# y escribe estado/status-<timestamp>.json. Compatible con Windows PowerShell 5.1.
#
# Uso:  powershell -File scripts/monitor-vps.ps1
#       powershell -File scripts/monitor-vps.ps1 -ConfigPath otra\ruta.json

param(
    [string]$ConfigPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "config\ecosistema.json")
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
$dirEstado = Join-Path $raiz "estado"

if (-not (Test-Path $ConfigPath)) {
    Write-Host "[ERROR] No existe $ConfigPath" -ForegroundColor Red
    Write-Host "        Copia config\ecosistema.example.json a config\ecosistema.json y rellenalo (tarjeta H-001)."
    exit 1
}
if (-not (Test-Path $dirEstado)) { New-Item -ItemType Directory -Path $dirEstado | Out-Null }

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$resultados = @()
$hayCritico = $false
$hayAlerta = $false

function Test-Placeholder {
    # Un valor es placeholder si esta vacio o empieza por TODO (config sin rellenar).
    param($Valor)
    if (-not $Valor) { return $true }
    if ($Valor -match '^\s*TODO') { return $true }
    return $false
}

function Add-Resultado {
    param($Componente, $Chequeo, $Objetivo, $Estado, $Detalle)
    $script:resultados += [pscustomobject]@{
        componente = $Componente
        chequeo    = $Chequeo
        objetivo   = $Objetivo
        estado     = $Estado   # OK | ALERTA | CRITICO | OMITIDO
        detalle    = $Detalle
    }
    if ($Estado -eq "CRITICO") { $script:hayCritico = $true }
    if ($Estado -eq "ALERTA")  { $script:hayAlerta = $true }
    $color = switch ($Estado) { "OK" {"Green"} "ALERTA" {"Yellow"} "CRITICO" {"Red"} default {"Gray"} }
    Write-Host ("  [{0}] {1} :: {2} -> {3}" -f $Estado, $Componente, $Chequeo, $Detalle) -ForegroundColor $color
}

Write-Host "=== Monitor de infraestructura - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan

# --- 1. Ping a cada VPS (IP Tailscale) ---
foreach ($vps in @($config.vps)) {
    if (-not $vps.host) { continue }
    $ok = Test-Connection -ComputerName $vps.host -Count 3 -Quiet -ErrorAction SilentlyContinue
    if ($ok) {
        Add-Resultado $vps.nombre "ping" $vps.host "OK" "responde"
    } else {
        Add-Resultado $vps.nombre "ping" $vps.host "CRITICO" "sin respuesta (3 intentos)"
    }

    # --- 2. Puertos TCP de servicios declarados ---
    foreach ($svc in @($vps.servicios)) {
        if (-not $svc.puerto) { continue }
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect($vps.host, [int]$svc.puerto, $null, $null)
            $conectado = $async.AsyncWaitHandle.WaitOne(5000) -and $tcp.Connected
            $tcp.Close()
        } catch { $conectado = $false }
        if ($conectado) {
            Add-Resultado $vps.nombre "puerto:$($svc.nombre)" "$($vps.host):$($svc.puerto)" "OK" "abierto"
        } else {
            Add-Resultado $vps.nombre "puerto:$($svc.nombre)" "$($vps.host):$($svc.puerto)" "CRITICO" "cerrado o inalcanzable"
        }
    }

    # --- 3. Recursos via SSH (solo si ssh_habilitado) ---
    if ($vps.ssh_habilitado -eq $true) {
        try {
            $destino = "$($vps.ssh_usuario)@$($vps.host)"
            $cmdRemoto = 'df -P / | tail -1 | awk ''{print $5}''; free -m 2>/dev/null | awk ''/^Mem:/{print int($7*100/$2)}'''
            $salida = ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $destino $cmdRemoto
            $lineas = @($salida -split "`n" | Where-Object { $_ -ne "" })
            if ($lineas.Count -eq 0) {
                Add-Resultado $vps.nombre "ssh" $vps.host "ALERTA" "SSH sin salida (exit $LASTEXITCODE): revisar known_hosts o Tailscale SSH"
            }
            if ($lineas.Count -ge 1) {
                $discoPct = [int]($lineas[0] -replace '%','')
                $estadoDisco = if ($discoPct -gt 95) {"CRITICO"} elseif ($discoPct -gt 85) {"ALERTA"} else {"OK"}
                Add-Resultado $vps.nombre "disco" "/" $estadoDisco "$discoPct% usado"
            }
            if ($lineas.Count -ge 2) {
                $memLibrePct = [int]$lineas[1]
                $estadoMem = if ($memLibrePct -lt 5) {"CRITICO"} elseif ($memLibrePct -lt 15) {"ALERTA"} else {"OK"}
                Add-Resultado $vps.nombre "memoria" "libre" $estadoMem "$memLibrePct% disponible"
            }
        } catch {
            Add-Resultado $vps.nombre "ssh" $vps.host "ALERTA" "SSH fallo: $($_.Exception.Message)"
        }

        # --- 3b. Servicios systemd declarados (via SSH) ---
        foreach ($svcSys in @($vps.servicios_systemd)) {
            if (-not $svcSys) { continue }
            try {
                $estadoSvc = ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $destino "systemctl is-active $svcSys"
                if ("$estadoSvc" -match 'active') {
                    Add-Resultado $vps.nombre "systemd:$svcSys" $svcSys "OK" "activo"
                } else {
                    Add-Resultado $vps.nombre "systemd:$svcSys" $svcSys "CRITICO" "estado: $estadoSvc"
                }
            } catch {
                Add-Resultado $vps.nombre "systemd:$svcSys" $svcSys "ALERTA" "no se pudo consultar via SSH"
            }
        }

        # --- 3c. Procesos declarados (via SSH, pgrep -f) ---
        foreach ($proc in @($vps.procesos)) {
            if (-not $proc) { continue }
            try {
                ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $destino "pgrep -f $proc >/dev/null" | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Add-Resultado $vps.nombre "proceso:$proc" $proc "OK" "corriendo"
                } else {
                    Add-Resultado $vps.nombre "proceso:$proc" $proc "CRITICO" "no encontrado"
                }
            } catch {
                Add-Resultado $vps.nombre "proceso:$proc" $proc "ALERTA" "no se pudo consultar via SSH"
            }
        }
    } else {
        Add-Resultado $vps.nombre "recursos" "ssh" "OMITIDO" "ssh_habilitado=false en config"
    }
}

# --- 4. Endpoints HTTP ---
foreach ($ep in @($config.endpoints_http)) {
    if (Test-Placeholder $ep.url) { continue }
    $timeout = 10
    if ($ep.timeout_segundos) { $timeout = [int]$ep.timeout_segundos }
    try {
        $resp = Invoke-WebRequest -Uri $ep.url -UseBasicParsing -TimeoutSec $timeout -ErrorAction Stop
        $code = [int]$resp.StatusCode
        Add-Resultado $ep.nombre "http" $ep.url "OK" "status $code"
    } catch {
        $code = $null
        try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        if ($code) {
            Add-Resultado $ep.nombre "http" $ep.url "ALERTA" "status $code"
        } else {
            Add-Resultado $ep.nombre "http" $ep.url "CRITICO" "timeout o sin conexion"
        }
    }
}

# --- 5. Market Castilla (chequeo superficial; el funcional es del pipeline 03) ---
if ($config.market_castilla -and -not (Test-Placeholder $config.market_castilla.endpoint_salud)) {
    try {
        $resp = Invoke-WebRequest -Uri $config.market_castilla.endpoint_salud -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        Add-Resultado "market_castilla" "salud" $config.market_castilla.endpoint_salud "OK" "status $([int]$resp.StatusCode)"
    } catch {
        Add-Resultado "market_castilla" "salud" $config.market_castilla.endpoint_salud "CRITICO" $_.Exception.Message
    }
}

# --- Persistencia ---
$global = if ($hayCritico) {"CRITICO"} elseif ($hayAlerta) {"ALERTA"} else {"OK"}
$status = [pscustomobject]@{
    timestamp     = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    estado_global = $global
    total_chequeos = $resultados.Count
    criticos      = @($resultados | Where-Object { $_.estado -eq "CRITICO" }).Count
    alertas       = @($resultados | Where-Object { $_.estado -eq "ALERTA" }).Count
    resultados    = $resultados
}
$archivo = Join-Path $dirEstado ("status-" + (Get-Date -Format "yyyy-MM-dd-HHmm") + ".json")
$status | ConvertTo-Json -Depth 5 | Out-File -FilePath $archivo -Encoding utf8

Write-Host ""
Write-Host "Estado global: $global - guardado en $archivo" -ForegroundColor Cyan
if ($global -eq "CRITICO") { exit 2 }
if ($global -eq "ALERTA")  { exit 1 }
exit 0
