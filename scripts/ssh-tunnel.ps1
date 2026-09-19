param(
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Write-Error "Environment file not found: $EnvFile`nCopy .env.example to .env and fill in the SSH connection values."
    exit 1
}

$config = @{
    SSH_PORT = "22"
    SSH_IDENTITY_FILE = ""
    SSH_TUNNEL_BIND_HOST = "127.0.0.1"
    DB_TUNNEL_LOCAL_PORT = "5432"
    DB_TUNNEL_REMOTE_HOST = "127.0.0.1"
    DB_TUNNEL_REMOTE_PORT = "5432"
    REDIS_TUNNEL_LOCAL_PORT = "6379"
    REDIS_TUNNEL_REMOTE_HOST = "127.0.0.1"
    REDIS_TUNNEL_REMOTE_PORT = "6379"
}

$supportedKeys = @(
    "SSH_HOST",
    "SSH_USER",
    "SSH_PORT",
    "SSH_IDENTITY_FILE",
    "SSH_TUNNEL_BIND_HOST",
    "DB_TUNNEL_LOCAL_PORT",
    "DB_TUNNEL_REMOTE_HOST",
    "DB_TUNNEL_REMOTE_PORT",
    "REDIS_TUNNEL_LOCAL_PORT",
    "REDIS_TUNNEL_REMOTE_HOST",
    "REDIS_TUNNEL_REMOTE_PORT"
)

$renamedKeys = @{
    DB_PORT = "DB_TUNNEL_LOCAL_PORT"
    DB_REMOTE_HOST = "DB_TUNNEL_REMOTE_HOST"
    DB_REMOTE_PORT = "DB_TUNNEL_REMOTE_PORT"
    REDIS_PORT = "REDIS_TUNNEL_LOCAL_PORT"
    REDIS_REMOTE_HOST = "REDIS_TUNNEL_REMOTE_HOST"
    REDIS_REMOTE_PORT = "REDIS_TUNNEL_REMOTE_PORT"
}

foreach ($line in Get-Content -LiteralPath $EnvFile) {
    $trimmedLine = $line.Trim()
    if (-not $trimmedLine -or $trimmedLine.StartsWith("#")) {
        continue
    }

    if ($trimmedLine.StartsWith("export ")) {
        $trimmedLine = $trimmedLine.Substring(7)
    }

    $separatorIndex = $trimmedLine.IndexOf("=")
    if ($separatorIndex -lt 1) {
        continue
    }

    $key = $trimmedLine.Substring(0, $separatorIndex).Trim()
    if ($renamedKeys.ContainsKey($key)) {
        Write-Error "$key was renamed to $($renamedKeys[$key]). Update $EnvFile from .env.example."
        exit 1
    }

    if ($supportedKeys -notcontains $key) {
        continue
    }

    $value = $trimmedLine.Substring($separatorIndex + 1).Trim()
    if (
        $value.Length -ge 2 -and
        (($value.StartsWith('"') -and $value.EndsWith('"')) -or
         ($value.StartsWith("'") -and $value.EndsWith("'")))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    $config[$key] = $value
}

foreach ($requiredKey in @("SSH_HOST", "SSH_USER")) {
    if (-not $config[$requiredKey]) {
        Write-Error "$requiredKey must be set in $EnvFile."
        exit 1
    }
}

foreach ($portKey in @(
    "SSH_PORT",
    "DB_TUNNEL_LOCAL_PORT",
    "DB_TUNNEL_REMOTE_PORT",
    "REDIS_TUNNEL_LOCAL_PORT",
    "REDIS_TUNNEL_REMOTE_PORT"
)) {
    $port = 0
    if (-not [int]::TryParse($config[$portKey], [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
        Write-Error "$portKey must be a number between 1 and 65535."
        exit 1
    }
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Error "OpenSSH client not found. Install ssh and try again."
    exit 1
}

$sshArguments = @(
    "-N",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=60",
    "-o", "ServerAliveCountMax=3",
    "-p", $config.SSH_PORT
)

if ($config.SSH_IDENTITY_FILE) {
    $sshArguments += @("-i", $config.SSH_IDENTITY_FILE)
}

$sshArguments += @(
    "-L", ("{0}:{1}:{2}:{3}" -f $config.SSH_TUNNEL_BIND_HOST, $config.DB_TUNNEL_LOCAL_PORT, $config.DB_TUNNEL_REMOTE_HOST, $config.DB_TUNNEL_REMOTE_PORT),
    "-L", ("{0}:{1}:{2}:{3}" -f $config.SSH_TUNNEL_BIND_HOST, $config.REDIS_TUNNEL_LOCAL_PORT, $config.REDIS_TUNNEL_REMOTE_HOST, $config.REDIS_TUNNEL_REMOTE_PORT),
    ("{0}@{1}" -f $config.SSH_USER, $config.SSH_HOST)
)

Write-Host "Opening PostgreSQL tunnel on $($config.SSH_TUNNEL_BIND_HOST):$($config.DB_TUNNEL_LOCAL_PORT)"
Write-Host "Opening Redis tunnel on $($config.SSH_TUNNEL_BIND_HOST):$($config.REDIS_TUNNEL_LOCAL_PORT)"
Write-Host "Keep this terminal open. Press Ctrl+C to close the tunnels."

& ssh @sshArguments
exit $LASTEXITCODE
