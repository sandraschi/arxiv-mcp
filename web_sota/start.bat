@echo off
setlocal
REM arxiv-mcp — do not symlink .bat: %%~dp0 must resolve to web_sota, not starts\
set "WEBAPP=%~dp0..\..\arxiv-mcp\web_sota"
cd /d "%WEBAPP%"
if not exist "start.ps1" (
  echo [ERROR] arxiv-mcp web_sota not found. Expected: %CD%\start.ps1
  echo Fix: clone arxiv-mcp next to mcp-central-docs under the same parent folder.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\start.ps1" %*
endlocal & exit /b %ERRORLEVEL%
