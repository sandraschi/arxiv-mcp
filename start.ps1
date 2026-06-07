Param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser
)

# Delegate to web_sota\start.ps1 which handles everything:
# winget prereqs, uv sync, npm install, port clearing, backend + frontend launch.
$webStart = Join-Path $PSScriptRoot "web_sota\start.ps1"
if (-not (Test-Path $webStart)) {
    Write-Host "ERROR: web_sota\start.ps1 not found." -ForegroundColor Red
    exit 1
}
& $webStart `
    -Headless:$Headless `
    -BackendOnly:$BackendOnly `
    -FrontendOnly:$FrontendOnly `
    -NoBrowser:$NoBrowser
