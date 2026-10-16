[CmdletBinding()]
param(
    [string]$SourceRoot,
    [switch]$AcceptDebugPort,
    [switch]$DeclineDebugPort,
    [switch]$RestartSteam,
    [switch]$NonInteractive,
    [string]$FixtureProfile,
    [string]$FixtureSteam,
    [string]$FixturePython
)
. (Join-Path $PSScriptRoot 'windows_common.ps1')
$lifecycleLock = $null

try {
    $context = Initialize-ContinueContext $FixtureProfile $FixtureSteam $FixturePython
    if (-not $SourceRoot) { $SourceRoot = [IO.Path]::GetDirectoryName($PSScriptRoot) }
    $SourceRoot = [IO.Path]::GetFullPath($SourceRoot).TrimEnd('\', '/')
    $release = Read-ContinueJson (Join-Path $SourceRoot 'RELEASE.json')
    if (-not $release -or $release.channel -ne 'public' -or $release.platform -ne 'windows' -or
        $release.version -notmatch '^\d+\.\d+\.\d+$' -or
        -not (Test-Path -LiteralPath (Join-Path $SourceRoot 'pc\gamehub_bp.py') -PathType Leaf)) {
        throw 'Only the public PC package with RELEASE.json can be installed. Download and extract the complete Continue PC ZIP.'
    }
    $steam = Get-ContinueSteamPath
    [void](Assert-ContinueSafePath $context.Manifest $context.Root)
    $old = Read-ContinueJson $context.Manifest
    $recovery = Read-ContinueRecovery
    if (-not $old -and $recovery) { $old = $recovery.owner }
    Assert-ContinueManifest $old
    Write-Host 'Continue needs Steam local debugging on 127.0.0.1:8080. While the .cef-enable-remote-debugging flag exists, any process on this PC can talk to the Steam interface through that port.'
    Write-Host 'This installation adds that flag, a per-user ContinueBigPicture task, and files under your LocalAppData\Continue folder. Steam must restart to load the flag. No administrator rights are requested.'
    if ($DeclineDebugPort -or ($AcceptDebugPort -and $DeclineDebugPort)) { throw 'Debug-port consent declined; installation cancelled.' }
    if (-not $AcceptDebugPort) {
        if ($NonInteractive -or -not (Confirm-ContinueChoice 'Allow this local Steam debugging port?' $false)) { throw 'Explicit debug-port consent is required; installation cancelled.' }
    }
    $lifecycleLock = Enter-ContinueLifecycleLock
    [void](Restore-ContinueInstallTransaction)
    # Re-read ownership after acquiring the lock; the pre-consent snapshot may
    # have become stale while another installer/updater was finishing.
    $old = Read-ContinueJson $context.Manifest
    $recovery = Read-ContinueRecovery
    if (-not $old -and $recovery) { $old = $recovery.owner }
    Assert-ContinueManifest $old
    if ((Test-Path -LiteralPath $context.App) -and -not $old) { throw 'The Continue app folder already exists without an install manifest. Move it aside before installing.' }
    $existingTask = Get-ContinueTask
    if ($existingTask -and -not (Test-ContinueOwnedTask $existingTask $old)) { throw 'ContinueBigPicture belongs to another installation. Nothing was changed.' }
    if ((Test-Path -LiteralPath (Join-Path $context.Root 'update-journal.json'))) { throw 'An update recovery journal is pending. Recover the update before installing; its rollback files were preserved.' }
    $python = Find-ContinuePython $SourceRoot
    Install-ContinueBootstrap $SourceRoot
    $stage = Join-Path $context.Root ('app-stage-' + [guid]::NewGuid().ToString('N'))
    $backup = Join-Path $context.Root ('app-backup-' + [guid]::NewGuid().ToString('N'))
    $flag = Join-Path $steam '.cef-enable-remote-debugging'
    [void](Assert-ContinueSafePath $flag $steam)
    $flagCreatedNow = $false
    $swapped = $false
    $manifestWritten = $false
    $manifest = $null
    $transactionPath = Join-Path $context.Root 'install-transaction.json'
    $willCreateFlag = -not (Test-Path -LiteralPath $flag)
    $willOwnFlag = $willCreateFlag -or ($old -and $old.debug_flag_created)
    $installId = if ($old) { $old.install_id } else { [guid]::NewGuid().ToString('N') }
    $manifest = [ordered]@{
        schema = 1; install_id = $installId; version = $release.version
        root = $context.Root; app = $context.App; data = $context.Data; logs = $context.Logs
        steam = $steam; debug_flag = $flag; debug_flag_created = [bool]$willOwnFlag
        task_name = $context.TaskName; task_created = $true
        pythonw = $python.Pythonw; python_console = $python.Console; python_version = $python.Version
        python_created = [bool]$python.Owned; debug_port_consent = $true
        installed_utc = [DateTime]::UtcNow.ToString('o')
    }
    # The receipt and the identity of the empty file precede every side effect.
    # Rename a stamped candidate without overwriting a concurrent consumer's flag.
    $flagStage = '.continue-debug-' + [guid]::NewGuid().ToString('N') + '.tmp'
    $flagStamp = if ($willCreateFlag) { [DateTime]::UtcNow.Ticks.ToString() } else { $old.debug_flag_stamp }
    $manifest['debug_flag_stamp'] = $flagStamp
    $transaction = [ordered]@{schema=1;state='prepared';stage=[IO.Path]::GetFileName($stage);backup=[IO.Path]::GetFileName($backup);old=$old;next=$manifest}
    if ($willCreateFlag) { $transaction['flag_stage'] = $flagStage }
    Write-ContinueJson $transactionPath $transaction
    try {
        Copy-ContinueApplication $SourceRoot $stage
        if (-not $context.Fixture) {
            $entry = Join-Path $stage 'pc\gamehub_bp.py'
            $check = Invoke-ContinueCaptured $python.Console ('-I -S -c "import ast,pathlib; ast.parse(pathlib.Path(r''' + $entry.Replace("'", "\'") + ''').read_text(encoding=''utf-8''))"')
            if ($check.Code -ne 0) { throw "The package Python service failed syntax validation: $($check.Error)" }
        }
        if ($old) { Stop-ContinueService $old; Stop-ContinueTask $old }
        if (Test-Path -LiteralPath $context.App) {
            [void](Assert-ContinueSafePath $context.App $context.Root)
            [void](Assert-ContinueSafePath $backup $context.Root)
            Move-Item -LiteralPath $context.App -Destination $backup
        }
        [void](Assert-ContinueSafePath $stage $context.Root)
        [void](Assert-ContinueSafePath $context.App $context.Root)
        Move-Item -LiteralPath $stage -Destination $context.App
        $swapped = $true
        foreach ($dir in @($context.Data, $context.Logs)) { [void](Assert-ContinueSafePath $dir $context.Root); [void][IO.Directory]::CreateDirectory($dir) }
        $settings = Join-Path $context.Root 'settings.json'
        if (-not (Test-Path -LiteralPath $settings)) { Write-ContinueJson $settings ([ordered]@{}) }
        if ($recovery -and $recovery.startup_movie -and $recovery.startup_movie.previous) {
            $values = Read-ContinueJson $settings
            if (-not $values.PSObject.Properties['startup_movie_prev']) {
                $values | Add-Member -NotePropertyName 'startup_movie_prev' -NotePropertyValue $recovery.startup_movie.previous
                Write-ContinueJson $settings $values
            }
        }
        if ((Test-Path -LiteralPath $flag) -and -not (Test-Path -LiteralPath $flag -PathType Leaf)) {
            throw 'The Steam debugging-flag path exists but is not a file. It was left unchanged; inspect it before retrying.'
        }
        if ($willCreateFlag) {
            $candidate = Join-Path $steam $flagStage
            [void](Assert-ContinueSafePath $candidate $steam)
            $stream = [IO.File]::Open($candidate, [IO.FileMode]::CreateNew)
            try { $stream.Flush($true) } finally { $stream.Dispose() }
            [IO.File]::SetLastWriteTimeUtc($candidate, [DateTime]::new([long]$flagStamp, [DateTimeKind]::Utc))
            try { [IO.File]::Move($candidate, $flag); $flagCreatedNow = $true }
            catch [IO.IOException] { if (-not (Test-Path -LiteralPath $flag -PathType Leaf)) { throw } }
        }
        $ownedFlag = $flagCreatedNow -or ($old -and $old.debug_flag_created)
        Remove-ContinueInstallFlagStage ([pscustomobject]$transaction)
        $manifest.debug_flag_created = [bool]$ownedFlag
        if (-not $flagCreatedNow) { $manifest.debug_flag_stamp = $old.debug_flag_stamp }
        $transaction['next'] = $manifest
        Write-ContinueJson $transactionPath $transaction
        Write-ContinueJson $context.Manifest $manifest
        $manifestWritten = $true
        Register-ContinueTask ([pscustomobject]$manifest)
        $transaction.state = 'committed'
        Write-ContinueJson $transactionPath $transaction
        # The task cannot acquire the lifecycle lock until this process exits.
        Start-ContinueTask ([pscustomobject]$manifest)
        if (Test-Path -LiteralPath $backup) { Remove-ContinuePath $backup }
        Remove-ContinuePath $transactionPath
        if ($recovery -and -not $recovery.startup_movie) { Remove-ContinuePath $context.Recovery }
    } catch {
        $failure = $_
        if ($manifestWritten) {
            try { Stop-ContinueService ([pscustomobject]$manifest); Stop-ContinueTask ([pscustomobject]$manifest); Unregister-ContinueTask ([pscustomobject]$manifest) } catch { }
        }
        if ($swapped -and (Test-Path -LiteralPath $context.App)) { Remove-ContinuePath $context.App }
        if (Test-Path -LiteralPath $backup) { [void](Assert-ContinueSafePath $backup $context.Root); [void](Assert-ContinueSafePath $context.App $context.Root); Move-Item -LiteralPath $backup -Destination $context.App }
        if ($old) {
            Write-ContinueJson $context.Manifest $old
            try { Register-ContinueTask $old; Start-ContinueTask $old } catch { Write-Warning 'Previous app files were restored, but Continue could not be restarted. Run setup.cmd to repair.' }
        } elseif ($manifestWritten) { Remove-ContinuePath $context.Manifest }
        if ($flagCreatedNow) { Remove-ContinueOwnedDebugFlag ([pscustomobject]$manifest) }
        Remove-ContinueInstallFlagStage ([pscustomobject]$transaction)
        Remove-ContinuePath $transactionPath
        throw $failure
    } finally { if (Test-Path -LiteralPath $stage) { Remove-ContinuePath $stage } }
    Write-Host "Continue $($release.version) installed in $($context.App). Its service starts with pythonw, without a console window."
    Write-Host 'Close your open games before restarting Steam. Big Picture will show Continue after Steam loads the debug flag.'
    if ($RestartSteam -or (Confirm-ContinueChoice 'Restart Steam now? Open games must be closed first.' $false -NonInteractive:$NonInteractive)) { Restart-ContinueSteam $steam }
    else { Write-Host 'Please restart Steam manually when your games are closed, then open Big Picture.' }
    exit 0
} catch {
    [Console]::Error.WriteLine('Continue installation: ' + $_.Exception.Message)
    exit 1
} finally { Exit-ContinueLifecycleLock $lifecycleLock }
