param(
  [string]$DatabaseUrl = "postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender_test",
  [string]$PythonPath = "backend\venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root $PythonPath

if (-not (Test-Path -LiteralPath $python)) {
  throw "Python not found at $python. Pass -PythonPath or create backend\venv first."
}

$previousDatabaseUrl = $env:DATABASE_URL
try {
  $env:DATABASE_URL = $DatabaseUrl
  Push-Location $root
  & $python -m pytest backend/tests -q
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Pop-Location
  $env:DATABASE_URL = $previousDatabaseUrl
}
