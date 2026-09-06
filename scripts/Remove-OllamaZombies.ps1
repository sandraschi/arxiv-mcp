# Remove-OllamaZombies.ps1 — kill parentless llama-server.exe runners (VRAM leaks).
#
# Background: Ollama (and LM Studio) spawn llama-server.exe workers per loaded
# model. When the parent dies uncleanly, workers stay resident holding GiBs of
# VRAM, and the next engine cannot load — looks exactly like "Ollama is down".
# A worker whose parent is dead is NEVER useful: only its own engine routes
# traffic to it, and a new engine never adopts old workers. So: kill them all.
#
# Never touched: workers whose parent is alive AND a known host (ollama engine,
# ollama app, LM Studio, …). LM Studio's workers are always skipped that way.
#
# Usage:
#   pwsh -NoProfile -File Remove-OllamaZombies.ps1            # one sweep now
#   pwsh -NoProfile -File Remove-OllamaZombies.ps1 -Install   # + 5-min logon task
param([switch]$Install)

$ErrorActionPreference = 'Stop'

$ManagedParents = @('ollama', 'ollama app', 'lm-studio', 'lm studio', 'studio', 'jan', 'gpt4all')

function Get-ProcessInfo([int]$pid) {
    try {
        $w = Get-CimInstance Win32_Process -Filter "ProcessId = $pid" -ErrorAction Stop
        $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
        return @{ Exists = $true; Name = $w.Name; Parent = [int]$w.ParentProcessId; Start = $p.StartTime }
    } catch { return @{ Exists = $false } }
}

function Remove-Zombies {
    $killed = @()
    $kept = @()
    $workers = Get-Process 'llama-server' -ErrorAction SilentlyContinue
    foreach ($w in $workers) {
        $pp = @{ Exists = $false }
        try {
            $pw = Get-CimInstance Win32_Process -Filter "ProcessId = $($w.Id)" -ErrorAction Stop
            $pp = Get-ProcessInfo ([int]$pw.ParentProcessId)
        } catch { $pp = @{ Exists = $false } }
        $managed = $pp.Exists -and ($ManagedParents -contains ($pp.Name -replace '\.exe$', ''))
        if ($managed) { $kept += "$($w.Id) (parent $($pp.Name) alive)"; continue }
        $parentDesc = if ($pp.Exists) { "$($pp.Name) (not a host)" } else { 'parent dead' }
        try {
            Stop-Process -Id $w.Id -Force -ErrorAction Stop
            $killed += "$($w.Id) [$parentDesc]"
        } catch {
            Write-Host "Could not kill $($w.Id): $_" -ForegroundColor Yellow
        }
    }
    foreach ($k in $kept) { Write-Host "keep $k" -ForegroundColor DarkGray }
    foreach ($k in $killed) { Write-Host "killed llama-server $k" -ForegroundColor Green }
    if ($killed.Count -eq 0 -and $kept.Count -eq 0) { Write-Host 'No llama-server processes found.' }
    return $killed.Count
}

if ($Install) {
    $taskName = 'OllamaZombieSweep'
    $script = $MyInvocation.MyCommand.Path
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $trigger.RepetitionInterval = (New-TimeSpan -Minutes 5)
    $trigger.RepetitionDuration = ([TimeSpan]::MaxValue)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -Description 'Kill parentless llama-server.exe VRAM leaks every 5 minutes.' -Force | Out-Null
    Write-Host "Scheduled task '$taskName' installed (logon + every 5 min)." -ForegroundColor Green
}

Remove-Zombies | Out-Null
