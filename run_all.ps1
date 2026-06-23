# run_all.ps1 — otomatik kurulum ve demo başlatma scripti
# Kullanım: PowerShell'i yönetici olarak açmaya gerek yok.
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backend = Join-Path $root 'backend'
$venv = Join-Path $root '.venv'
$pidFile = Join-Path $backend 'process_ids.txt'

if (-not (Test-Path $backend)) { New-Item -ItemType Directory -Path $backend | Out-Null }
if (-not (Test-Path $venv)) {
    Write-Host 'Virtual environment oluşturuluyor...'
    py -3 -m venv $venv
}

$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Python sanal ortamı bulunamadı, py yerine python kullanılıyor.'
    $python = Get-Command python -ErrorAction Stop | Select-Object -ExpandProperty Source
}

Write-Host 'Paketler yükleniyor...'
& $python -m pip install --upgrade pip | Out-Null
& $python -m pip install -r (Join-Path $backend 'requirements.txt') | Out-Null

Write-Host 'Sunucu başlatılıyor...'
$serverProc = Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000' -PassThru
$serverProc.Id | Out-File -FilePath $pidFile -Encoding ascii

Start-Sleep -Seconds 2
Start-Process 'http://127.0.0.1:8000'
Write-Host "Sunucu başlatıldı: PID=$($serverProc.Id)"
Write-Host "Tarayıcı açıldı."
