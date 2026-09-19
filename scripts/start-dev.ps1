param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"

$repositoryDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repositoryDir "backend"
$frontendDir = Join-Path $repositoryDir "frontend"
$nginxTemplate = Join-Path $repositoryDir "nginx/development.conf.template"

$nginxPort = if ($env:ERP_DEV_NGINX_PORT) { $env:ERP_DEV_NGINX_PORT } else { "8080" }
$backendPort = if ($env:ERP_DEV_BACKEND_PORT) { $env:ERP_DEV_BACKEND_PORT } else { "8000" }
$frontendPort = if ($env:ERP_DEV_FRONTEND_PORT) { $env:ERP_DEV_FRONTEND_PORT } else { "5173" }

function Assert-Command {
    param(
        [string]$Name,
        [string]$InstallationHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallationHint"
    }
}

function ConvertTo-ValidatedPort {
    param(
        [string]$Name,
        [string]$Value
    )

    $port = 0
    if (-not [int]::TryParse($Value, [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
        throw "$Name must be a number between 1 and 65535."
    }
    return $port
}

function Test-PortListening {
    param([int]$Port)

    try {
        return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1)
    }
    catch {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            return $result.AsyncWaitHandle.WaitOne(200) -and $client.Connected
        }
        catch {
            return $false
        }
        finally {
            $client.Dispose()
        }
    }
}

function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process -or $Process.HasExited) {
        return
    }

    $taskkill = Get-Command taskkill.exe -ErrorAction SilentlyContinue
    if ($taskkill) {
        & $taskkill.Source /PID $Process.Id /T /F 2>$null | Out-Null
        return
    }

    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
}

Assert-Command -Name "uv" -InstallationHint "Install uv before starting the backend."
Assert-Command -Name "bun" -InstallationHint "Install Bun before starting the frontend."
Assert-Command -Name "nginx" -InstallationHint "Install nginx and add nginx.exe to PATH."

$nginxPort = ConvertTo-ValidatedPort -Name "ERP_DEV_NGINX_PORT" -Value $nginxPort
$backendPort = ConvertTo-ValidatedPort -Name "ERP_DEV_BACKEND_PORT" -Value $backendPort
$frontendPort = ConvertTo-ValidatedPort -Name "ERP_DEV_FRONTEND_PORT" -Value $frontendPort

if ((@($nginxPort, $backendPort, $frontendPort) | Sort-Object -Unique).Count -ne 3) {
    throw "Nginx, backend, and frontend ports must be different."
}

foreach ($requiredPath in @(
    (Join-Path $backendDir "manage.py"),
    (Join-Path $frontendDir "package.json"),
    $nginxTemplate
)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file not found: $requiredPath"
    }
}

$backendEnvFile = Join-Path $backendDir ".env.development"
if (-not (Test-Path -LiteralPath $backendEnvFile -PathType Leaf)) {
    throw "Backend environment file not found: $backendEnvFile`nCopy backend/.env.development.example and fill in the development values."
}

$runtimeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("erp-nginx-dev-" + [guid]::NewGuid().ToString("N"))
$null = New-Item -ItemType Directory -Path $runtimeDir
$nginxConfig = Join-Path $runtimeDir "nginx.conf"
$startupErrorLog = Join-Path $runtimeDir "startup-error.log"
$backendProcess = $null
$frontendProcess = $null
$nginxProcess = $null

try {
    $config = [System.IO.File]::ReadAllText($nginxTemplate)
    $config = $config.Replace("__NGINX_PORT__", [string]$nginxPort)
    $config = $config.Replace("__BACKEND_PORT__", [string]$backendPort)
    $config = $config.Replace("__FRONTEND_PORT__", [string]$frontendPort)
    [System.IO.File]::WriteAllText(
        $nginxConfig,
        $config,
        [System.Text.UTF8Encoding]::new($false)
    )

    $nginxPrefix = $runtimeDir.Replace("\", "/") + "/"
    $nginxConfigPath = $nginxConfig.Replace("\", "/")
    $startupErrorLogPath = $startupErrorLog.Replace("\", "/")
    $nginxBaseArguments = @(
        "-e", $startupErrorLogPath,
        "-p", $nginxPrefix,
        "-c", $nginxConfigPath
    )

    & nginx @nginxBaseArguments -t
    if ($LASTEXITCODE -ne 0) {
        throw "Nginx configuration validation failed with exit code $LASTEXITCODE."
    }

    if ($Check) {
        Write-Host "Development command and nginx configuration checks passed."
        return
    }

    foreach ($port in @($nginxPort, $backendPort, $frontendPort)) {
        if (Test-PortListening -Port $port) {
            throw "Port $port is already in use. Stop the existing process or override the ERP_DEV_*_PORT values."
        }
    }

    $backendProcess = Start-Process `
        -FilePath "uv" `
        -ArgumentList @("run", "python", "manage.py", "runserver", "127.0.0.1:$backendPort", "--noreload") `
        -WorkingDirectory $backendDir `
        -NoNewWindow `
        -PassThru

    $frontendProcess = Start-Process `
        -FilePath "bun" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", [string]$frontendPort, "--strictPort") `
        -WorkingDirectory $frontendDir `
        -NoNewWindow `
        -PassThru

    $nginxProcess = Start-Process `
        -FilePath "nginx" `
        -ArgumentList @(
            "-e", "`"$startupErrorLogPath`"",
            "-p", "`"$nginxPrefix`"",
            "-c", "`"$nginxConfigPath`"",
            "-g", "`"daemon off;`""
        ) `
        -WorkingDirectory $runtimeDir `
        -NoNewWindow `
        -PassThru

    Write-Host ""
    Write-Host "ERP development environment is starting:"
    Write-Host "  Nginx:    http://localhost:$nginxPort"
    Write-Host "  Backend:  http://127.0.0.1:$backendPort"
    Write-Host "  Frontend: http://127.0.0.1:$frontendPort"
    Write-Host "  Health:   http://localhost:$nginxPort/api/health/"
    Write-Host "Press Ctrl+C to stop all three processes."

    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited -and -not $nginxProcess.HasExited) {
        Start-Sleep -Seconds 1
        $backendProcess.Refresh()
        $frontendProcess.Refresh()
        $nginxProcess.Refresh()
    }

    throw "A development process stopped unexpectedly. Shutting down the remaining processes."
}
finally {
    Stop-ProcessTree -Process $nginxProcess
    Stop-ProcessTree -Process $frontendProcess
    Stop-ProcessTree -Process $backendProcess
    Remove-Item -LiteralPath $runtimeDir -Recurse -Force -ErrorAction SilentlyContinue
}
