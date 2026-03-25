# arxiv-mcp dashboard: FastAPI + MCP on 10770, Vite on 10771
$BackendPort = 10770
$FrontendPort = 10771
$ApiHealth = "http://127.0.0.1:$BackendPort/api/health"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$WebRoot = $PSScriptRoot

Write-Host "Syncing Python dependencies (uv sync --extra dev)..." -ForegroundColor Cyan
Set-Location $RepoRoot
uv sync --extra dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($port in @($BackendPort, $FrontendPort)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        $conn | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Cleared port $port" -ForegroundColor Yellow
    }
}
Start-Sleep -Milliseconds 500

Write-Host "Starting arxiv-mcp backend on :$BackendPort ..." -ForegroundColor Cyan
$null = Start-Process -FilePath "uv" `
    -ArgumentList "run", "python", "-m", "arxiv_mcp", "--serve" `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Minimized `
    -PassThru

$waited = 0
$ok = $false
while ($waited -lt 30) {
    try {
        $r = Invoke-WebRequest -Uri $ApiHealth -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
    $waited++
}
if (-not $ok) {
    Write-Host "WARN: Backend health not ready; continuing anyway." -ForegroundColor Yellow
}

Set-Location $WebRoot
if (-not (Test-Path "node_modules")) { npm install }

Write-Host "Starting Vite on :$FrontendPort ..." -ForegroundColor Cyan
$null = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $WebRoot `
    -WindowStyle Minimized `
    -PassThru

Start-Sleep -Seconds 3
Write-Host "Backend  $ApiHealth" -ForegroundColor Green
Write-Host "Frontend http://127.0.0.1:$FrontendPort" -ForegroundColor Green
Start-Process "http://127.0.0.1:$FrontendPort"
