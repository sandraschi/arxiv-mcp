param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser,
    [switch]$ReuseIfRunning)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FleetStartPath = Join-Path $RepoRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly

$portResolve = @{
    Ports      = @($BackendPort, $FrontendPort)
    Label      = "arxiv-mcp"
    AllowReuse = $ReuseIfRunning
}
if ($ReuseIfRunning) {
    $portResolve.HealthChecks = @{
        $BackendPort = "http://127.0.0.1:$BackendPort/api/health"
        $FrontendPort = "http://127.0.0.1:$FrontendPort/"
    }
}
$portState = Resolve-FleetPortConflict @portResolve
if ($portState.Action -eq 'Blocked') { exit 1 }
if ($portState.Reuse) { return }$WindowStyle = $FleetStart.WindowStyle
# --- Ensure full user PATH is available (subprocess contexts may start bare) ---
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("PATH","User")
# -------------------------------------------------------------------------------

$BackendPort  = 10770
$FrontendPort = 10771
$ApiHealth    = "http://127.0.0.1:$BackendPort/api/health"
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

# Ensure known Node.js install dir is on PATH if node isn't already visible
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $nodeDir = "C:\Program Files\nodejs"
    if (Test-Path "$nodeDir\node.exe") {
        $env:PATH = "$nodeDir;" + $env:PATH
    } else {
        Write-Host "ERROR: node not found. Install Node.js LTS from https://nodejs.org/" -ForegroundColor Red
        exit 1
    }
}

# Resolve uv: prefer known install path, fall back to PATH
$uvExe = "C:\Users\sandr\.local\bin\uv.exe"
if (-not (Test-Path $uvExe)) {
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue; $uvExe = if ($uvCmd) { $uvCmd.Source } else { $null }
    if (-not $uvExe) {
        Write-Host "ERROR: uv not found. Install from https://docs.astral.sh/uv/" -ForegroundColor Red
        exit 1
    }
}
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) { Write-Host "ERROR: npm not found after PATH setup." -ForegroundColor Red; exit 1 }
# Prefer npm.cmd over npm.ps1 for reliable invocation
$npmExe = if ($npmCmd.Source -match '\.ps1$') {
    $npmCmd.Source -replace '\.ps1$', '.cmd'
} else { $npmCmd.Source }

# Python deps
$LASTEXITCODE = 0  # reset stale exit code from prereq checks
Write-Host "Syncing Python deps (uv sync) ..." -ForegroundColor Cyan
Write-Host "(first run: uv may download Python 3.11 -- this can take 30s)" -ForegroundColor DarkGray
& $uvExe sync --project $RepoRoot --extra dev --extra rag
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: uv sync failed." -ForegroundColor Red; exit 1 }

# Frontend deps (npm install only if node_modules absent)
if ($startFrontend) {
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
}

function Test-ArxivBackendHealthy {
    try {
        $r = Invoke-WebRequest -Uri $ApiHealth -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

$startBackend = $FleetStart.RunBackend
$startFrontend = $FleetStart.RunFrontend
$backendAlreadyUp = $false

if ($startBackend -and (Test-ArxivBackendHealthy)) {
    Write-Host "Backend already healthy at $ApiHealth  --  reusing existing listener." -ForegroundColor Green
    $backendAlreadyUp = $true
    $startBackend = $false
}

if ($startFrontend) {
    $frontendListening = @(Get-FleetPortListenerPids -Port $FrontendPort)
    if ($frontendListening.Count -gt 0) {
        Write-Host "Frontend already listening on :$FrontendPort  --  reusing." -ForegroundColor Green
        $startFrontend = $false
    }
}

if ($startBackend -or $startFrontend) {
    Stop-FleetPortSquatters -Ports @($BackendPort, $FrontendPort) -Label "arxiv-mcp"
    if (-not (Assert-FleetPortsAvailable -Ports @($BackendPort, $FrontendPort) -Label "arxiv-mcp")) {
        if ($env:FLEET_PROBE_RUN -ne '1') { Read-Host "Press Enter to close" }
        exit 1
    }
}

Start-Sleep -Milliseconds 500

$backendProc = $null
if ($startBackend) {
    Write-Host "Starting arxiv-mcp backend on :$BackendPort ..." -ForegroundColor Cyan
    $backendArgs = if ($env:FLEET_PROBE_RUN -eq '1') {
        @("-NoProfile", "-Command", "& '$uvExe' run --project '$RepoRoot' python -m arxiv_mcp --serve")
    } else {
        @("-NoProfile", "-NoExit", "-Command", "& '$uvExe' run --project '$RepoRoot' python -m arxiv_mcp --serve")
    }
    $backendProc = Start-FleetDetachedShell -Label "backend" -Exe "powershell.exe" `
        -Args $backendArgs -WorkingDirectory $RepoRoot -WindowStyle $WindowStyle

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
    Write-Host "Backend   $ApiHealth" -ForegroundColor Green
}

if ($startFrontend) {
    Write-Host "Starting Vite on :$FrontendPort ..." -ForegroundColor Cyan
    $null = Start-FleetDetachedShell -Label "frontend" -Exe "cmd.exe" `
        -Args @("/c", "npm run dev") -WorkingDirectory $WebRoot -WindowStyle $WindowStyle

    if (-not $FleetStart.SkipBrowser -and $env:FLEET_PROBE_RUN -ne '1') {
        $frontendUrl  = "http://127.0.0.1:$FrontendPort/"
        $pollAndOpen  = "for (`$i=0;`$i -lt 60;`$i++) { try { `$null=Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep 1 } }"
        Start-Process powershell.exe -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command",$pollAndOpen
        Write-Host "Browser will open automatically when Vite is ready." -ForegroundColor Gray
    }

    Write-Host "Frontend  http://127.0.0.1:$FrontendPort" -ForegroundColor Green
}

if ($BackendOnly -and $null -ne $backendProc) {
    Write-Host "Backend-only mode. Ctrl+C in backend window to stop." -ForegroundColor DarkGray
}

if (-not $startFrontend -and -not $FleetStart.SkipBrowser -and $env:FLEET_PROBE_RUN -ne '1') {
    $frontendUrl = "http://127.0.0.1:$FrontendPort/"
    try {
        $null = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Start-Process $frontendUrl
        Write-Host "Opened $frontendUrl" -ForegroundColor Gray
    } catch {}
}

Write-Host "Backend   $ApiHealth" -ForegroundColor Green
Write-Host "Frontend  http://127.0.0.1:$FrontendPort" -ForegroundColor Green


