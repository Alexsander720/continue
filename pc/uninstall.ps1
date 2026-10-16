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
$lifecycleLock = $null
$removeEmptyRoot = $false
try {
    $context = Initialize-ContinueContext $FixtureProfile $FixtureSteam $FixturePython
    if ($RemoveData -and $KeepData) { throw 'Choose either RemoveData or KeepData.' }
    [void](Assert-ContinueSafePath $context.Manifest $context.Root)
    # Only a fully validated journal may authorize recovery without ownership.
    # Validation, recovery and all subsequent checks share the lifecycle lock.
    $lifecycleLock = Enter-ContinueLifecycleLock
    $recoveredInstall = Restore-ContinueInstallTransaction -PassThru
    $manifest = Read-ContinueJson $context.Manifest
    $recovery = Read-ContinueRecovery
    if (-not $manifest -and $recovery) { $manifest = $recovery.owner }
    if (-not $manifest) {
        if ($recoveredInstall -and -not $recoveredInstall.old -and -not $recoveredInstall.next) {
            # Legacy journals precede the first manifest. Never claim unrelated data.
            foreach ($name in @('bootstrap.py','recover-install.ps1','windows_common.ps1','update-helper.py')) {
                Remove-ContinuePath (Join-Path $context.Root $name)
            }
            $removeEmptyRoot = $true
            Write-Host 'Interrupted first installation was rolled back. Unknown profile objects were preserved.'
            exit 0
        }
        $remaining = @(Get-ChildItem -LiteralPath $context.Root -Force | Where-Object { $_.Name -ne 'update.lock' })
        if ($remaining.Count -gt 0) {
            throw 'Continue profile has no ownership/recovery metadata. Nothing was removed; inspect the unknown files manually.'
        }
        $removeEmptyRoot = $true
        Write-Host 'Continue is not installed in this Windows account.'; exit 0
    }
    Assert-ContinueManifest $manifest
    $task = Get-ContinueTask
    if ($task -and -not (Test-ContinueOwnedTask $task $manifest)) { throw 'ContinueBigPicture belongs to another installation. Nothing was removed.' }
    # Preserve the only record linking a crash backup to its release.
    $journal = Join-Path $context.Root 'update-journal.json'
    [void](Assert-ContinueSafePath $journal $context.Root)
    if (Test-Path -LiteralPath $journal) { throw 'An update recovery journal is pending. Recover the update before uninstalling; its rollback files were preserved.' }
    $bytes = Get-ContinueCacheBytes
    Write-Host "Continue data/cache: $bytes bytes ($([math]::Round($bytes / 1MB, 2)) MiB)."
    $deleteData = if ($KeepData) { $false } elseif ($RemoveData) { $true } else { Confirm-ContinueChoice 'Remove your Continue data/cache, logs and settings?' $true -NonInteractive:$NonInteractive }
    # Durable ownership precedes the first task/file mutation. A retry reads
    # this marker even if install.json or the app has already disappeared.
    $startup = Get-ContinueStartupRecovery $recovery
    $recordBeforeStop = Test-Path -LiteralPath (Join-Path $context.Root 'startup_movie.json')
    $recovery = New-ContinueRecovery $manifest 'cleaning' $startup
    Write-ContinueJson $context.Recovery $recovery
    Stop-ContinueService $manifest
    Stop-ContinueTask $manifest
    Unregister-ContinueTask $manifest
    if ($recordBeforeStop -and -not (Test-Path -LiteralPath (Join-Path $context.Root 'startup_movie.json'))) { $startup = $null }
    else { $startup = Get-ContinueStartupRecovery $recovery }
    $recovery = New-ContinueRecovery $manifest 'cleaning' $startup
    Write-ContinueJson $context.Recovery $recovery
    Remove-ContinueOwnedDebugFlag $manifest
    Remove-ContinuePath $context.App
    if ($manifest.python_created) { Remove-ContinuePath (Join-Path $context.Root 'python') }
    foreach ($name in @('update-helper.py', 'update-result.json', 'service_ready.json', 'injected.json', 'service.lock',
        'bootstrap.py','recover-install.ps1','windows_common.ps1','install-transaction.json','service-error.json')) {
        Remove-ContinuePath (Join-Path $context.Root $name)
    }
    if ($deleteData) {
        foreach ($path in @($context.Data, $context.Logs, (Join-Path $context.Root 'settings.json'),
            (Join-Path $context.Root 'update.json'), (Join-Path $context.Root 'themes.json'),
            (Join-Path $context.Root 'secrets'), (Join-Path $context.Root 'downloads'))) { Remove-ContinuePath $path }
    }
    Remove-ContinuePath $context.Manifest
    $recovery = New-ContinueRecovery $manifest $(if ($startup) { 'pending' } else { 'retained' }) $startup
    if ($deleteData -and -not $startup) { Remove-ContinuePath $context.Recovery; $removeEmptyRoot = $true }
    else { Write-ContinueJson $context.Recovery $recovery }
    Write-Host 'Continue application and its owned task were removed.'
    if (-not $deleteData) { Write-Host 'Data/settings were retained. To purge them later, run pc\uninstall.ps1 -RemoveData from an extracted Continue PC ZIP.' }
    if ($startup) {
        Write-Host 'Startup-movie restoration is not confirmed. Minimal recovery metadata and the movie file were preserved; unrelated data was purged only if requested.'
        Write-Host 'Open Steam Settings > Customization > Startup Movie and restore your previous selection. Alternatively reinstall Continue, enable the Steam startup movie, then remove Continue again.'
        if ($startup.previous) { Write-Host "Previous choice: id=$($startup.previous.id); path=$($startup.previous.path); shuffle=$($startup.previous.shuffle)." }
        Write-Host "Recovery record: $($context.Recovery). No Steam configuration file was edited."
    }
    $remaining = @(Get-ChildItem -LiteralPath $context.Root -Force | Where-Object { $_.Name -ne 'update.lock' })
    if ($remaining.Count -gt 0) { Write-Host "Preserved profile objects: $($remaining.Name -join ', ')." }
    Write-Host 'Removing a debug flag does not close an already open Steam debug port. Please restart Steam manually when your games are closed.'
    if ($RestartSteam -or (Confirm-ContinueChoice 'Restart Steam now? Open games must be closed first.' $false -NonInteractive:$NonInteractive)) { Restart-ContinueSteam $manifest.steam }
    if ($startup) { exit 2 }
    exit 0
} catch {
    [Console]::Error.WriteLine('Continue removal: ' + $_.Exception.Message)
    exit 1
} finally {
    Exit-ContinueLifecycleLock $lifecycleLock
    if ($removeEmptyRoot) {
        # Never recursively remove the root. Any unknown object preserves it.
        # An updater holding an open lock prevents deleting that file on Windows.
        try {
            $lockPath = Join-Path $context.Root 'update.lock'
            [void](Assert-ContinueSafePath $lockPath $context.Root)
            if (Test-Path -LiteralPath $lockPath -PathType Leaf) { Remove-Item -LiteralPath $lockPath -Force }
            [void](Assert-ContinueSafePath $context.Root $context.Local)
            if ((Test-Path -LiteralPath $context.Root) -and @(Get-ChildItem -LiteralPath $context.Root -Force).Count -eq 0) {
                Remove-Item -LiteralPath $context.Root -Force
            }
        } catch { Write-Warning 'A residual profile/lock was preserved because cleanup could not be verified.' }
    }
}
