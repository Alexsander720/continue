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
    $old = Read-ContinueJson $context.Manifest
    Assert-ContinueManifest $old
    if ((Test-Path -LiteralPath $context.App) -and -not $old) { throw 'The Continue app folder already exists without an install manifest. Move it aside before installing.' }
    $existingTask = Get-ContinueTask
    if ($existingTask -and -not (Test-ContinueOwnedTask $existingTask $old)) { throw 'ContinueBigPicture belongs to another installation. No task, Steam flag or app was changed.' }
    Write-Host 'Continue needs Steam local debugging on 127.0.0.1:8080. While the .cef-enable-remote-debugging flag exists, any process on this PC can talk to the Steam interface through that port.'
    Write-Host 'This installation adds that flag, a per-user ContinueBigPicture task, and files under your LocalAppData\Continue folder. Steam must restart to load the flag. No administrator rights are requested.'
    if ($DeclineDebugPort -or ($AcceptDebugPort -and $DeclineDebugPort)) { throw 'Debug-port consent declined; installation cancelled.' }
    if (-not $AcceptDebugPort) {
        if ($NonInteractive -or -not (Confirm-ContinueChoice 'Allow this local Steam debugging port?' $false)) { throw 'Explicit debug-port consent is required; installation cancelled.' }
    }
    [void][IO.Directory]::CreateDirectory($context.Root)
    $python = Find-ContinuePython $SourceRoot
    $stage = Join-Path $context.Root ('app-stage-' + [guid]::NewGuid().ToString('N'))
    $backup = Join-Path $context.Root ('app-backup-' + [guid]::NewGuid().ToString('N'))
    $flag = Join-Path $steam '.cef-enable-remote-debugging'
    [void](Assert-ContinueSafePath $flag $steam)
    $flagCreatedNow = $false
    $swapped = $false
    $manifestWritten = $false
    $manifest = $null
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
        if ((Test-Path -LiteralPath $flag) -and -not (Test-Path -LiteralPath $flag -PathType Leaf)) {
            throw 'The Steam debugging-flag path exists but is not a file. It was left unchanged; inspect it before retrying.'
        }
        if (-not (Test-Path -LiteralPath $flag)) {
            # CreateNew avoids overwriting a flag created concurrently by another tool.
            try { $stream = [IO.File]::Open($flag, [IO.FileMode]::CreateNew); $stream.Dispose(); $flagCreatedNow = $true }
            catch [IO.IOException] { if (-not (Test-Path -LiteralPath $flag)) { throw } }
        }
        $ownedFlag = $flagCreatedNow -or ($old -and $old.debug_flag_created)
        $installId = if ($old) { $old.install_id } else { [guid]::NewGuid().ToString('N') }
        $manifest = [ordered]@{
            schema = 1; install_id = $installId; version = $release.version
            root = $context.Root; app = $context.App; data = $context.Data; logs = $context.Logs
            steam = $steam; debug_flag = $flag; debug_flag_created = [bool]$ownedFlag
            task_name = $context.TaskName; task_created = $true
            pythonw = $python.Pythonw; python_console = $python.Console; python_version = $python.Version
            python_created = [bool]$python.Owned; debug_port_consent = $true
            installed_utc = [DateTime]::UtcNow.ToString('o')
        }
        Write-ContinueJson $context.Manifest $manifest
        $manifestWritten = $true
        Register-ContinueTask ([pscustomobject]$manifest)
        Start-ContinueTask ([pscustomobject]$manifest)
        if (Test-Path -LiteralPath $backup) { Remove-ContinuePath $backup }
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
        if ($flagCreatedNow -and -not ($old -and $old.debug_flag_created)) { [void](Assert-ContinueSafePath $flag $steam); Remove-Item -LiteralPath $flag -Force }
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
}
