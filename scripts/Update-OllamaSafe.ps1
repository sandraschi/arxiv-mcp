# Update-OllamaSafe.ps1 — the ONLY supported way to update Ollama on Goliath.
#
# Root cause it guards against (2026-10-10): the Ollama Inno Setup updater
# deletes old runner files before writing new ones, with no atomic rollback.
# Our NSSM service `ollama-serve` runs ollama.exe as LocalSystem FROM the
# install dir, so the updater (running as user) hits locked files, skips
# them, reports success, and leaves lib/ gutted — every /api/generate then
# 500s with "llama-server binary not found" while /api/tags still works.
# Ollama's stock updater only knows its own per-user processes; our SYSTEM
# service is invisible to it. So: stop service, update, VERIFY runners,
# start service. Never let auto-update run against a live service.
#
# Usage:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File Update-OllamaSafe.ps1
#   pwsh -NoProfile -ExecutionPolicy Bypass -File Update-OllamaSafe.ps1 -SkipStart
param([switch]$SkipStart)

$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\Ollama'
$RunnerProbe = Join-Path $InstallDir 'lib\ollama'

function Assert-RunnersPresent {
    $backends = Get-ChildItem -Path $RunnerProbe -Directory -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Name
    if (-not $backends -or $backends.Count -eq 0) {
        throw "Runner check FAILED: $RunnerProbe has no backend dirs. Refusing to (re)start service."
    }
    $exes = Get-ChildItem -Path $RunnerProbe -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $exes) {
        throw 'Runner check FAILED: no runner .exe under lib\ollama. Refusing to (re)start service.'
    }
    Write-Host "Runners OK: $($backends -join ', ')" -ForegroundColor Green
}

Write-Host 'Step 1/5: stopping ollama-serve (NSSM, never taskkill)...' -ForegroundColor Cyan
sc.exe stop ollama-serve | Out-Null
Start-Sleep -Seconds 5
$state = (sc.exe query ollama-serve | Select-String 'STATE').ToString()
Write-Host "  $state"
if ($state -notmatch 'STOPPED') { throw 'Service did not stop. Aborting update.' }

Write-Host 'Step 2/5: winget upgrade...' -ForegroundColor Cyan
$winget = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
& $winget upgrade Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
if ($LASTEXITCODE -ne 0) { throw "winget exited with code $LASTEXITCODE. Aborting." }

Write-Host 'Step 3/5: verifying runners BEFORE restart...' -ForegroundColor Cyan
& (Join-Path $InstallDir 'ollama.exe') --version
Assert-RunnersPresent

if ($SkipStart) {
    Write-Host 'SkipStart set: leaving service stopped.' -ForegroundColor Yellow
    return
}

Write-Host 'Step 4/5: starting ollama-serve...' -ForegroundColor Cyan
sc.exe start ollama-serve | Out-Null
Start-Sleep -Seconds 8
$running = (sc.exe query ollama-serve | Select-String 'STATE').ToString()
Write-Host "  $running"
if ($running -notmatch 'RUNNING') { throw 'Service did not start. Check NSSM logs.' }

Write-Host 'Step 5/5: smoke test (port owner + real inference)...' -ForegroundColor Cyan
$owner = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty OwningProcess
Write-Host "  11434 Listen owner PID: $owner"
$body = @{ model = 'llama3.2:3b'; prompt = 'Reply with exactly: OK'; stream = $false } | ConvertTo-Json
$response = Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/generate' -Method POST `
    -Body $body -ContentType 'application/json' -TimeoutSec 120 -UseBasicParsing
if ($response.StatusCode -ne 200 -or $response.Content -notmatch '"response":"OK"') {
    throw "Smoke test FAILED: $($response.StatusCode) $($response.Content.Substring(0, 200))"
}
Write-Host '  generate OK (llama3.2:3b replied OK). Update complete.' -ForegroundColor Green
