# stop_all.ps1 — demo süreçlerini durdur
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backend = Join-Path $root 'backend'
$pidFile = Join-Path $backend 'process_ids.txt'

if (-not (Test-Path $pidFile)) {
    Write-Host "PID dosyası bulunamadı: $pidFile"
    Write-Host "Önce .\run_all.ps1 çalıştırın veya süreçleri manuel durdurun."
    exit 1
}

$pids = Get-Content $pidFile | ForEach-Object {
    if ($_ -match '^(server|ws_client|telemetry)=(\d+)$') {
        [pscustomobject]@{ Name = $matches[1]; Pid = [int]$matches[2] }
    }
}

foreach ($entry in $pids) {
    try {
        if (Get-Process -Id $entry.Pid -ErrorAction SilentlyContinue) {
            Stop-Process -Id $entry.Pid -Force
            Write-Host "Stopped $($entry.Name) PID $($entry.Pid)"
        }
        else {
            Write-Host "Process not running: $($entry.Name) PID $($entry.Pid)"
        }
    }
    catch {
        Write-Host "Failed to stop $($entry.Name) PID $($entry.Pid): $($_.Exception.Message)"
    }
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Host "Cleanup complete."
