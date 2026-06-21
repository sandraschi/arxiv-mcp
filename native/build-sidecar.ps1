#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build PyInstaller backend and embed it in the Tauri bundle resources.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Triple = "x86_64-pc-windows-msvc"

Write-Host "=== arxiv-mcp embedded backend build ===" -ForegroundColor Cyan

Push-Location $Root
try {
    Write-Host "-> uv sync --extra rag" -ForegroundColor Yellow
    uv sync --extra rag
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

    $pi = uv run pyinstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "-> Installing PyInstaller..." -ForegroundColor Yellow
        uv pip install pyinstaller
    } else {
        Write-Host "-> PyInstaller: $pi" -ForegroundColor Gray
    }

    Remove-Item -Recurse -Force "$Root\build\arxiv-mcp-backend" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\arxiv-mcp-backend.exe" -ErrorAction SilentlyContinue

    Write-Host "-> Running PyInstaller..." -ForegroundColor Yellow
    uv run pyinstaller arxiv-mcp-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

    $src = "$Root\dist\arxiv-mcp-backend.exe"
    $resourceDir = "$Root\native\resources"
    $devDir = "$Root\native\binaries"
    $bundled = "$resourceDir\arxiv-mcp-backend.exe"
    $devCopy = "$devDir\arxiv-mcp-backend-$Triple.exe"

    if (-not (Test-Path $src)) { throw "Build output not found: $src" }

    New-Item -ItemType Directory -Path $resourceDir -Force | Out-Null
    New-Item -ItemType Directory -Path $devDir -Force | Out-Null
    Copy-Item $src $bundled -Force
    Copy-Item $src $devCopy -Force

    $sizeMB = [math]::Round((Get-Item $bundled).Length / 1MB, 1)
    Write-Host "=== Backend embedded ===" -ForegroundColor Green
    Write-Host "  bundle resource: $bundled ($sizeMB MB)" -ForegroundColor Cyan
    Write-Host "  dev fallback:    $devCopy" -ForegroundColor Gray
} finally {
    Pop-Location
}
