$script = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) '..\run_all.ps1'
if (-not (Test-Path $script)) {
    Write-Error "Root script bulunamadı: $script"
    exit 1
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
