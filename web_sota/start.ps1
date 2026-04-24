Param([switch]$Headless)

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch "Hidden")) {
    Start-Process powershell.exe -ArgumentList "-NoProfile","-File",$PSCommandPath,"-Headless" -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { "Hidden" } else { "Normal" }
# ------------------------------

$BackendPort  = 10770
$FrontendPort = 10771
$ApiHealth    = "http://127.0.0.1:$BackendPort/api/health"
$RepoRoot     = Split-Path -Parent $PSScriptRoot
$WebRoot      = $PSScriptRoot

# ===========================================================================
# Prereq check -- installs uv and Node via winget if absent.
# vite is LOCAL (devDependencies) -- never required globally.
# ===========================================================================
function Require-Command {
    param([string]$Cmd, [string]$WingetId, [string]$Label)
    if (Get-Command $Cmd -ErrorAction SilentlyContinue) { return }
    Write-Host "  $Label not found - installing via winget ..." -ForegroundColor Yellow
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: winget unavailable. Install $Label manually ($WingetId)." -ForegroundColor Red
        exit 1
    }
    winget install --id $WingetId --silent --accept-source-agreements --accept-package-agreements
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) {
        Write-Host "Installed $Label but '$Cmd' still not in PATH. Reopen PowerShell and retry." -ForegroundColor Yellow
        exit 1
    }
}

Require-Command "uv"   "Astral.uv"          "uv (Python package manager)"
Require-Command "node" "OpenJS.NodeJS.LTS"   "Node.js LTS"
Require-Command "npm"  "OpenJS.NodeJS.LTS"   "npm"
Require-Command "just" "Casey.Just"          "just (command runner)"

$uvExe  = (Get-Command uv).Source
$npmExe = (Get-Command npm).Source

# Python deps
Write-Host "Syncing Python deps (uv sync) ..." -ForegroundColor Cyan
Write-Host "(first run: uv may download Python 3.11 -- this can take 30s)" -ForegroundColor DarkGray
& $uvExe sync --project $RepoRoot --extra dev
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: uv sync failed." -ForegroundColor Red; exit 1 }

# Frontend deps (npm install only if node_modules absent)
if (-not (Test-Path (Join-Path $WebRoot "node_modules"))) {
    Write-Host "Installing frontend deps (npm install) ..." -ForegroundColor Cyan
    Push-Location $WebRoot
    & $npmExe install --prefer-offline 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: npm install failed." -ForegroundColor Red; Pop-Location; exit 1 }
    Pop-Location
}

# Guard: vite must exist locally after install
$viteLocal = Join-Path $WebRoot "node_modules\.bin\vite"
if (-not (Test-Path $viteLocal)) {
    Write-Host "ERROR: vite missing from node_modules after npm install." -ForegroundColor Red
    Write-Host "Delete '$WebRoot\node_modules' and re-run." -ForegroundColor Yellow
    exit 1
}

# Clear ports
foreach ($port in @($BackendPort, $FrontendPort)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        try { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
    }
}
Start-Sleep -Milliseconds 500

# Start backend
Write-Host "Starting arxiv-mcp backend on :$BackendPort ..." -ForegroundColor Cyan
$backendProc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile","-Command","& '$uvExe' run --project '$RepoRoot' python -m arxiv_mcp --serve" `
    -WorkingDirectory $RepoRoot -WindowStyle $WindowStyle -PassThru

$waited = 0
$ok = $false
while ($waited -lt 60) {
    try {
        $r = Invoke-WebRequest -Uri $ApiHealth -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
    $waited++
}
if (-not $ok) { Write-Host "WARN: backend health not ready after ${waited}s -- continuing." -ForegroundColor Yellow }

# Start frontend
Write-Host "Starting Vite on :$FrontendPort ..." -ForegroundColor Cyan
$null = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c","npm run dev" `
    -WorkingDirectory $WebRoot -WindowStyle $WindowStyle -PassThru

# Open browser
if (-not $Headless) {
    $frontendUrl  = "http://127.0.0.1:$FrontendPort/"
    $pollAndOpen  = "for (`$i=0;`$i -lt 60;`$i++) { try { `$null=Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep 1 } }"
    Start-Process powershell.exe -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command",$pollAndOpen
    Write-Host "Browser will open automatically when Vite is ready." -ForegroundColor Gray
}

Write-Host "Backend   $ApiHealth" -ForegroundColor Green
Write-Host "Frontend  http://127.0.0.1:$FrontendPort" -ForegroundColor Green
