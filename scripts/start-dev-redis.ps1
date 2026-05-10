param(
  [string]$WslDistro = "Ubuntu-24.04"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendEnv = Join-Path $repoRoot "backend\.env"

function Invoke-WslBash {
  param([string]$Command)
  & wsl -d $WslDistro -- bash -lc $Command
}

Write-Host "Checking Redis in WSL distro '$WslDistro'..."

$hasRedis = Invoke-WslBash "command -v redis-server >/dev/null 2>&1 && echo yes || echo no"
if (($hasRedis | Select-Object -Last 1).Trim() -ne "yes") {
  Write-Host "Installing redis-server..."
  Invoke-WslBash "apt-get update && apt-get install -y redis-server"
}

Write-Host "Configuring Redis for Windows-to-WSL development access..."
Invoke-WslBash "sed -i 's/^bind .*/bind 0.0.0.0 ::1/' /etc/redis/redis.conf; sed -i 's/^protected-mode .*/protected-mode no/' /etc/redis/redis.conf"

Write-Host "Starting Redis..."
Invoke-WslBash "service redis-server restart >/dev/null 2>&1 || (pkill redis-server >/dev/null 2>&1 || true; redis-server /etc/redis/redis.conf --daemonize yes)"

$ping = Invoke-WslBash "redis-cli ping"
if (($ping | Select-Object -Last 1).Trim() -ne "PONG") {
  throw "Redis did not respond to PING in WSL."
}

$ip = (Invoke-WslBash "hostname -I | awk '{print `$1}'" | Select-Object -Last 1).Trim()
if (-not $ip) {
  throw "Could not determine WSL IP address."
}

$redisUrl = "redis://$ip`:6379/0"

if (Test-Path $backendEnv) {
  $content = Get-Content -Raw -Path $backendEnv
  if ($content -match "(?m)^REDIS_URL=") {
    $content = $content -replace "(?m)^REDIS_URL=.*$", "REDIS_URL=$redisUrl"
  } elseif ($content -match "(?m)^DATABASE_URL=.*$") {
    $content = $content -replace "(?m)(^DATABASE_URL=.*$)", "`$1`r`n`r`n# Cache / jobs - WSL Redis IP is refreshed by scripts/start-dev-redis.ps1.`r`nREDIS_URL=$redisUrl"
  } else {
    $content = "REDIS_URL=$redisUrl`r`n$content"
  }
  Set-Content -Path $backendEnv -Value $content -Encoding UTF8
}

Write-Host "Redis is ready: $redisUrl"
Write-Host "backend/.env has been updated."
