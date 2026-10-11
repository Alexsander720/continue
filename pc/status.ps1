[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$NonInteractive,
    [string]$FixtureProfile,
    [string]$FixtureSteam,
    [string]$FixturePython
)
. (Join-Path $PSScriptRoot 'windows_common.ps1')
try {
    $context = Initialize-ContinueContext $FixtureProfile $FixtureSteam $FixturePython
    $manifest = Read-ContinueJson $context.Manifest
    if ($manifest) { Assert-ContinueManifest $manifest; $steam = $manifest.steam } else { $steam = Get-ContinueSteamPath }
    $cdp = Get-ContinueCdpState
    $media = Get-ContinueMediaState
    $running = @(Get-ContinueService $manifest).Count -gt 0
    $steamRunning = Test-ContinueSteamRunning $steam
    $flag = Test-Path -LiteralPath (Join-Path $steam '.cef-enable-remote-debugging') -PathType Leaf
    $task = Get-ContinueTask
    $ownedTask = Test-ContinueOwnedTask $task $manifest
    $latest = $null; $lastLine = $null
    if (Test-Path -LiteralPath $context.Logs) {
        [void](Assert-ContinueSafePath $context.Logs $context.Root)
        $latest = Get-ChildItem -LiteralPath $context.Logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) { [void](Assert-ContinueSafePath $latest.FullName $context.Root); $lastLine = Get-Content -LiteralPath $latest.FullName -Tail 1 -Encoding UTF8 }
    }
    $hint = if (-not $manifest) { 'Continue is not installed. Extract the PC ZIP and double-click pc\setup.cmd.' }
        elseif (-not $steamRunning) { 'Steam is not running. Start Steam, then open Big Picture.' }
        elseif ($media -eq 'other') { 'Port 8793 is occupied by another program. Close that program, then run setup.cmd to start Continue.' }
        elseif ($cdp -eq 'other') { 'Port 8080 is occupied by another program or an unrecognized Steam context. Close that program and restart Steam.' }
        elseif (-not $flag) { 'The local debug flag is missing. Run setup.cmd to repair, then restart Steam.' }
        elseif ($cdp -eq 'closed') { 'The flag exists, but the debug port is closed. Close open games and restart Steam; the flag is loaded only at startup.' }
        elseif (-not $ownedTask) { 'The Continue task is missing or points elsewhere. Run setup.cmd to repair it.' }
        elseif (-not $running) { 'The Continue service is not running. Run setup.cmd to repair and inspect the last log for errors.' }
        else { 'Steam debugging and Continue are available. Open Big Picture to see Continue.' }
    $status = [ordered]@{
        installed = [bool]$manifest; version = $(if ($manifest) { $manifest.version } else { $null })
        app = $context.App; service_running = [bool]$running; task_owned = [bool]$ownedTask
        steam_running = [bool]$steamRunning; debug_flag = [bool]$flag; cdp = $cdp
        cdp_port = 8080; media_port = 8793; media = $media; cache_bytes = (Get-ContinueCacheBytes)
        last_log = $(if ($latest) { $latest.FullName } else { $null }); last_log_line = $lastLine
        hint = $hint
    }
    if ($Json) { $status | ConvertTo-Json -Depth 5 }
    else {
        Write-Host "Continue version: $($status.version)"
        Write-Host "Service running: $($status.service_running); task matches installation: $($status.task_owned)"
        Write-Host "Steam running: $steamRunning; debug flag: $flag; port 8080: $cdp; port 8793: $media"
        Write-Host "Cache: $($status.cache_bytes) bytes; app: $($status.app)"
        Write-Host "Last log: $($status.last_log)"
        if ($lastLine) { Write-Host "Last log line: $lastLine" }
        Write-Host $hint
    }
    exit 0
} catch {
    [Console]::Error.WriteLine('Continue status: ' + $_.Exception.Message)
    exit 1
}
