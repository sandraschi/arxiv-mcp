<#
.SYNOPSIS
    Register Windows Scheduled Tasks that drive the arxiv-mcp code-hunt loop.

.DESCRIPTION
    Creates two tasks that hit the running arxiv-mcp REST backend:
      - ArxivCodehuntScan   : POST /api/codehunt/scan   (discover new repo/promise drops)
      - ArxivCodehuntRepoll : POST /api/codehunt/repoll  (re-check promised repos, push live)
      - ArxivCodehuntMedia  : POST /api/codehunt/media-check (HN + news, ~7d after pub)
    The scan runs every 12h; the re-poll runs every 12h offset by 6h so the loop
    checks promised repositories twice a day. Live China-signal drops are pushed to
    aiwatcher automatically by the backend (ARXIV_MCP_AIWATCHER_BASE_URL).

    Requires arxiv-mcp running in --serve mode (default http://127.0.0.1:10770).

.PARAMETER BaseUrl
    arxiv-mcp REST base. Default http://127.0.0.1:10770

.PARAMETER Days
    Lookback window for each scan. Default 3.

.PARAMETER Remove
    Unregister the tasks instead of creating them.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\tools\install_codehunt_tasks.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\tools\install_codehunt_tasks.ps1 -Remove
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:10770",
    [int]$Days = 3,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$ScanTask   = "ArxivCodehuntScan"
$RepollTask = "ArxivCodehuntRepoll"
$MediaTask  = "ArxivCodehuntMedia"

if ($Remove) {
    foreach ($name in @($ScanTask, $RepollTask, $MediaTask)) {
        if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $name -Confirm:$false
            Write-Host "Removed task: $name"
        } else {
            Write-Host "Task not found (skipped): $name"
        }
    }
    return
}

# Inline PowerShell each task runs. Uses Invoke-RestMethod; no external script file.
$scanBody = "@{categories=`$null; days=$Days; push=`$true} | ConvertTo-Json"
$scanCmd = "try { Invoke-RestMethod -Method Post -Uri '$BaseUrl/api/codehunt/scan' -ContentType 'application/json' -Body ($scanBody) -TimeoutSec 600 } catch { Write-Error `$_ }"
$repollCmd = "try { Invoke-RestMethod -Method Post -Uri '$BaseUrl/api/codehunt/repoll?push=true' -TimeoutSec 600 } catch { Write-Error `$_ }"
$mediaCmd = "try { Invoke-RestMethod -Method Post -Uri '$BaseUrl/api/codehunt/media-check?push=true' -TimeoutSec 600 } catch { Write-Error `$_ }"

function Register-CodehuntTask {
    param([string]$Name, [string]$Command, [datetime]$StartAt)

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$Command`""
    $trigger = New-ScheduledTaskTrigger -Once -At $StartAt `
        -RepetitionInterval (New-TimeSpan -Hours 12) `
        -RepetitionDuration ([TimeSpan]::MaxValue)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
        -LogonType Interactive -RunLevel Limited

    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    }
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal `
        -Description "arxiv-mcp code-hunt: $Name" | Out-Null
    Write-Host "Registered task: $Name (every 12h, first run $($StartAt.ToString('HH:mm')))"
}

$now = Get-Date
Register-CodehuntTask -Name $ScanTask   -Command $scanCmd   -StartAt $now.AddMinutes(2)
Register-CodehuntTask -Name $RepollTask -Command $repollCmd -StartAt $now.AddHours(6)

$taskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited
$mediaAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$mediaCmd`""
$mediaTrigger = New-ScheduledTaskTrigger -Daily -At "09:00"
$mediaSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew
if (Get-ScheduledTask -TaskName $MediaTask -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $MediaTask -Confirm:$false
}
Register-ScheduledTask -TaskName $MediaTask -Action $mediaAction -Trigger $mediaTrigger `
    -Settings $mediaSettings -Principal $taskPrincipal `
    -Description "arxiv-mcp code-hunt: media traction check" | Out-Null
Write-Host "Registered task: $MediaTask (daily 09:00)"

Write-Host ""
Write-Host "Done. Verify with: Get-ScheduledTask -TaskName Arxiv* | Format-Table TaskName, State"
Write-Host "Ensure arxiv-mcp is running in --serve mode at $BaseUrl"
