# arxiv-mcp: backend 10770, Vite 10771. Run from repo root.
$BackendPort = 10770
$FrontendPort = 10771
$ApiHealth = "http://127.0.0.1:$BackendPort/api/health"
$MaxWaitSec = 30

$RepoRoot = $PSScriptRoot
$WebSotaRoot = Join-Path $RepoRoot "web_sota"

function Stop-PortProcess {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = $conn.OwningProcess | Select-Object -First 1 -Unique
        if ($procId) {
            Write-Host "Stopping process on port $Port (PID: $procId)"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
}

Write-Host "Clearing ports $BackendPort and $FrontendPort..."
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort

Write-Host "Starting Python backend on port $BackendPort ..."
$backendProc = Start-Process -FilePath "uv" -ArgumentList "run", "python", "-m", "arxiv_mcp", "--serve" -WorkingDirectory $RepoRoot -PassThru -NoNewWindow

$waited = 0
$BackendStarted = $false
while ($waited -lt $MaxWaitSec) {
    try {
        $r = Invoke-WebRequest -Uri $ApiHealth -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            $BackendStarted = $true
            Write-Host "Backend ready at $ApiHealth"
            break
        }
    } catch {
        if (-not $backendProc.HasExited) {
            Start-Sleep -Seconds 2
        }
    }
    $waited += 2
}
if (-not $BackendStarted) {
    Write-Host "WARNING: Backend did not respond at $ApiHealth within ${MaxWaitSec}s."
}

Write-Host "Starting Vite on port $FrontendPort ..."
Set-Location $WebSotaRoot
npm install
npm run dev
