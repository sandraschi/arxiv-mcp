# MCPB pack script - sync src into mcpb/, then mcpb pack to dist/.
# Run from repo root:  .\mcpb\pack.ps1
# Standards: mcp-central-docs/standards/MCPB_PACKAGING_STANDARDS.md
$ErrorActionPreference = "Stop"
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$mcpbDir = Join-Path $repoRoot "mcpb"
$distDir = Join-Path $repoRoot "dist"

function Resolve-McpbExe {
    $cmd = Get-Command mcpb.cmd -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $npmMcpb = Join-Path $env:APPDATA "npm\mcpb.cmd"
    if (Test-Path $npmMcpb) {
        return $npmMcpb
    }
    throw "mcpb CLI not found. Install: npm install -g @anthropic-ai/mcpb"
}

function Get-ProjectVersion {
    $pyproject = Join-Path $repoRoot "pyproject.toml"
    if (-not (Test-Path $pyproject)) {
        return "0.0.0"
    }
    foreach ($line in Get-Content $pyproject) {
        if ($line -match '^\s*version\s*=\s*"(.+)"\s*$') {
            return $Matches[1]
        }
    }
    return "0.0.0"
}

Write-Host "Syncing source into mcpb/" -ForegroundColor Cyan
Remove-Item -Path (Join-Path $mcpbDir "src") -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $repoRoot "src") -Destination (Join-Path $mcpbDir "src") -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "pyproject.toml") -Destination (Join-Path $mcpbDir "pyproject.toml") -Force
Copy-Item -Path (Join-Path $repoRoot "README.md") -Destination (Join-Path $mcpbDir "README.md") -Force
if (Test-Path (Join-Path $repoRoot "LICENSE")) {
    Copy-Item -Path (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $mcpbDir "LICENSE") -Force
}
if (Test-Path (Join-Path $repoRoot "CHANGELOG.md")) {
    Copy-Item -Path (Join-Path $repoRoot "CHANGELOG.md") -Destination (Join-Path $mcpbDir "CHANGELOG.md") -Force
}

Get-ChildItem -Path (Join-Path $mcpbDir "src") -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path (Join-Path $mcpbDir "src") -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path (Join-Path $mcpbDir "src") -Recurse -File -Filter "*.bak" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Exporting requirements.txt for MCPB runtime" -ForegroundColor Cyan
Set-Location $repoRoot
uv export --no-dev --no-hashes --no-emit-project -o (Join-Path $mcpbDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "uv export failed"
}

$version = Get-ProjectVersion
$bundleName = "arxiv-mcp-v$version.mcpb"
$bundlePath = Join-Path $distDir $bundleName

New-Item -ItemType Directory -Force -Path $distDir | Out-Null
if (Test-Path $bundlePath) {
    Remove-Item $bundlePath -Force
}

$mcpbExe = Resolve-McpbExe
Write-Host "Validating manifest.json" -ForegroundColor Cyan
Set-Location $mcpbDir
& $mcpbExe validate manifest.json
if ($LASTEXITCODE -ne 0) {
    throw "mcpb validate manifest.json failed"
}

Write-Host "Packing $bundleName" -ForegroundColor Green
& $mcpbExe pack . $bundlePath
if ($LASTEXITCODE -ne 0) {
    throw "mcpb pack failed"
}

Write-Host "Inspecting bundle" -ForegroundColor Cyan
& $mcpbExe info $bundlePath
if ($LASTEXITCODE -ne 0) {
    throw "mcpb info failed"
}

Set-Location $repoRoot
$sizeKb = [math]::Round((Get-Item $bundlePath).Length / 1KB, 1)
Write-Host "Built: $bundlePath ($sizeKb KB)" -ForegroundColor Green
