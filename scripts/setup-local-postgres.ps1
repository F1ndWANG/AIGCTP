param(
  [string]$PsqlPath = "W:\PostgreSQL\16\bin\psql.exe",
  [string]$CreatedbPath = "W:\PostgreSQL\16\bin\createdb.exe",
  [string]$AdminUser = "postgres",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 5432,
  [string]$AppUser = "lifeai",
  [string]$AppPassword = "lifeai_dev",
  [string]$TestDatabase = "life_recommender_test"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $PsqlPath)) {
  throw "psql not found at $PsqlPath. Pass -PsqlPath with your PostgreSQL bin path."
}

if (-not (Test-Path -LiteralPath $CreatedbPath)) {
  throw "createdb not found at $CreatedbPath. Pass -CreatedbPath with your PostgreSQL bin path."
}

& $PsqlPath -h $HostName -p $Port -U $AdminUser -d postgres -v ON_ERROR_STOP=1 -c @"
DO `$do`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppUser') THEN
    CREATE ROLE $AppUser LOGIN PASSWORD '$AppPassword';
  ELSE
    ALTER ROLE $AppUser WITH LOGIN PASSWORD '$AppPassword';
  END IF;
END
`$do`$;
"@

$exists = (& $PsqlPath -h $HostName -p $Port -U $AdminUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$TestDatabase'") -join ""
if ([string]::IsNullOrWhiteSpace($exists) -or $exists.Trim() -ne "1") {
  & $CreatedbPath -h $HostName -p $Port -U $AdminUser -O $AppUser $TestDatabase
}

Write-Host "PostgreSQL test database is ready."
Write-Host "DATABASE_URL=postgresql+asyncpg://$AppUser`:$AppPassword@$HostName`:$Port/$TestDatabase`?ssl=disable"
