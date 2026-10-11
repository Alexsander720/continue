[CmdletBinding()]
param(
    [switch]$RemoveData,
    [switch]$KeepData,
    [switch]$RestartSteam,
    [switch]$NonInteractive,
    [string]$FixtureProfile,
    [string]$FixtureSteam,
    [string]$FixturePython
)
. (Join-Path $PSScriptRoot 'windows_common.ps1')
try {
    $context = Initialize-ContinueContext $FixtureProfile $FixtureSteam $FixturePython
    if ($RemoveData -and $KeepData) { throw 'Choose either RemoveData or KeepData.' }
    $manifest = Read-ContinueJson $context.Manifest
    if (-not $manifest) { Write-Host 'Continue is not installed in this Windows account.'; exit 0 }
    Assert-ContinueManifest $manifest
    $task = Get-ContinueTask
    if ($task -and -not (Test-ContinueOwnedTask $task $manifest)) { throw 'ContinueBigPicture belongs to another installation. Nothing was removed.' }
    $bytes = Get-ContinueCacheBytes
    Write-Host "Continue data/cache: $bytes bytes ($([math]::Round($bytes / 1MB, 2)) MiB)."
    $deleteData = if ($KeepData) { $false } elseif ($RemoveData) { $true } else { Confirm-ContinueChoice 'Remove your Continue data/cache, logs and settings?' $true -NonInteractive:$NonInteractive }
    Stop-ContinueService $manifest
    Stop-ContinueTask $manifest
    Unregister-ContinueTask $manifest
    if ($manifest.debug_flag_created -and (Test-Path -LiteralPath $manifest.debug_flag)) {
        [void](Assert-ContinueSafePath $manifest.debug_flag $manifest.steam)
        # We created an empty flag. A subsequently edited file may have a new owner.
        if ((Get-Item -LiteralPath $manifest.debug_flag).Length -eq 0) { Remove-Item -LiteralPath $manifest.debug_flag -Force }
        else { Write-Host 'The Steam debug flag was changed after installation and has been preserved.' }
    }
    Remove-ContinuePath $context.App
    if ($manifest.python_created) { Remove-ContinuePath (Join-Path $context.Root 'python') }
    # These files belong to the installed service/update mechanism rather than
    # to the user's retained settings or media cache.  Leaving a copied helper
    # or a stale readiness/journal record after uninstall makes status and a
    # later clean install ambiguous.
    foreach ($path in @(
        (Join-Path $context.Root 'update-helper.py'),
        (Join-Path $context.Root 'update-journal.json'),
        (Join-Path $context.Root 'update-result.json'),
        (Join-Path $context.Root 'service_ready.json'),
        (Join-Path $context.Root 'injected.json'),
        (Join-Path $context.Root 'service.lock'),
        (Join-Path $context.Root 'update.lock')
    )) { Remove-ContinuePath $path }
    if ($deleteData) {
        foreach ($path in @(
            $context.Data,
            $context.Logs,
            (Join-Path $context.Root 'settings.json'),
            (Join-Path $context.Root 'update.json'),
            (Join-Path $context.Root 'downloads')
        )) { Remove-ContinuePath $path }
    }
    Remove-ContinuePath $context.Manifest
    Write-Host 'Continue was removed. The injected Steam script stays in memory until you restart Steam. Close open games before restarting.'
    if ($RestartSteam -or (Confirm-ContinueChoice 'Restart Steam now? Open games must be closed first.' $false -NonInteractive:$NonInteractive)) { Restart-ContinueSteam $manifest.steam }
    else { Write-Host 'Please restart Steam manually when your games are closed.' }
    exit 0
} catch {
    [Console]::Error.WriteLine('Continue removal: ' + $_.Exception.Message)
    exit 1
}
