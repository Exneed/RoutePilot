# backend\stop_all.ps1 — root stop_all.ps1'i backend dizininden çağırır
$backend = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Split-Path -Parent $backend
$script = Join-Path $root 'stop_all.ps1'

if (-not (Test-Path $script)) {
    Write-Error "Root stop_all.ps1 bulunamadı: $script"
    exit 1
}

Write-Host "Running root script: $script"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
