# Shared, readable Windows lifecycle helpers. All OS effects pass through these
# functions. Explicit fixture profiles never call real registry/task/process APIs.
$ErrorActionPreference = 'Stop'

function Read-ContinueJson([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return ([IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8) | ConvertFrom-Json)
}

function Write-ContinueJson([string]$Path, $Value) {
    $temp = "$Path.tmp-$([guid]::NewGuid().ToString('N'))"
    $backup = "$temp.previous"
    $encoded = ($Value | ConvertTo-Json -Depth 12) + "`n"
    $bytes = (New-Object Text.UTF8Encoding $false).GetBytes($encoded)
    $stream = [IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    try {
        # Windows PowerShell 5 marshals a bare $null string argument as an empty
        # path. A real temporary backup keeps File.Replace atomic on that host.
        if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temp, $Path, $backup) }
        else { [IO.File]::Move($temp, $Path) }
    } finally {
        if ([IO.File]::Exists($temp)) { [IO.File]::Delete($temp) }
        if ([IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
    }
}

function Assert-ContinueSafePath([string]$Path, [string]$Root, [switch]$AllowRoot) {
    $absolute = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $inside = $absolute.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
    if (-not $inside -and -not ($AllowRoot -and $absolute.Equals($base, [StringComparison]::OrdinalIgnoreCase))) {
        throw "Path is outside the Continue profile: $absolute"
    }
    # Lexical containment alone does not protect a recursive remove from junctions.
    $cursor = $absolute
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $entry = Get-Item -LiteralPath $cursor -Force
            if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked paths are not allowed: $cursor" }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
    return $absolute
}

function Initialize-ContinueContext([string]$FixtureProfile, [string]$FixtureSteam, [string]$FixturePython) {
    $fixture = -not [string]::IsNullOrWhiteSpace($FixtureProfile)
    if (-not $fixture -and ($FixtureSteam -or $FixturePython)) { throw 'FixtureSteam/FixturePython require an explicit FixtureProfile.' }
    if ($fixture) {
        $profile = [IO.Path]::GetFullPath($FixtureProfile).TrimEnd('\', '/')
        $marker = Read-ContinueJson (Join-Path $profile '.continue-fixture-profile')
        if (-not $marker -or -not $marker.fixture -or $marker.profile -ne $profile -or $marker.steam -ne $FixtureSteam) {
            throw 'Fixture mode requires an exact .continue-fixture-profile marker; no real operations were run.'
        }
        [void](Assert-ContinueSafePath $FixtureSteam $profile)
        if (-not $FixturePython -or -not (Test-Path -LiteralPath $FixturePython -PathType Leaf)) { throw 'FixturePython must name a fake Python file.' }
        [void](Assert-ContinueSafePath $FixturePython $profile)
        $local = Join-Path $profile 'LocalAppData'
        $statePath = Join-Path $profile 'fixture_state.json'
    } else {
        if ($env:OS -ne 'Windows_NT') { throw 'Continue for PC requires Windows 10 or 11.' }
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA is unavailable for this user.' }
        $local = [IO.Path]::GetFullPath($env:LOCALAPPDATA)
        $profile = $env:USERPROFILE
        $statePath = $null
    }
    $root = Join-Path $local 'Continue'
    [void](Assert-ContinueSafePath $root $local)
    $script:ContinueContext = [pscustomobject]@{
        Fixture = $fixture; Profile = $profile; Local = $local; Root = $root
        App = (Join-Path $root 'app'); Data = (Join-Path $root 'data'); Logs = (Join-Path $root 'logs')
        Manifest = (Join-Path $root 'install.json'); FixtureSteam = $FixtureSteam
        Recovery = (Join-Path $root 'uninstall-recovery.json')
        FixturePython = $FixturePython; StatePath = $statePath; TaskName = 'ContinueBigPicture'
    }
    return $script:ContinueContext
}

function Get-ContinueFixtureState {
    if (-not $script:ContinueContext.Fixture) { throw 'Fixture state was requested outside fixture mode.' }
    $state = Read-ContinueJson $script:ContinueContext.StatePath
    if (-not $state) {
        $state = [pscustomobject]@{ task = $null; operations = @(); service_running = $false; steam_running = $false; cdp = 'closed' }
    }
    foreach ($key in @('service_running', 'steam_running')) {
        if (-not $state.PSObject.Properties[$key]) { $state | Add-Member -NotePropertyName $key -NotePropertyValue $false }
    }
    if (-not $state.PSObject.Properties['cdp']) { $state | Add-Member -NotePropertyName 'cdp' -NotePropertyValue 'closed' }
    return $state
}

function Remove-ContinueOwnedDebugFlag($Manifest) {
    if (-not $Manifest.debug_flag_created -or -not (Test-Path -LiteralPath $Manifest.debug_flag)) { return }
    [void](Assert-ContinueSafePath $Manifest.debug_flag $Manifest.steam)
    $flag = Get-Item -LiteralPath $Manifest.debug_flag
    if ($flag.PSIsContainer -or $flag.Length -ne 0) { Write-Host 'The Steam debug flag was changed after installation and has been preserved.'; return }
    if ($Manifest.debug_flag_stamp -and $flag.LastWriteTimeUtc.Ticks.ToString() -ne $Manifest.debug_flag_stamp) {
        Write-Host 'The Steam debug flag was replaced after installation and has been preserved.'; return
    }
    if (Test-ContinueSharedDebugConsumer) { Write-Host 'Steam debug flag preserved: active GameHubBigPicture also uses local Steam debugging.'; return }
    Remove-Item -LiteralPath $Manifest.debug_flag -Force
}

function Remove-ContinueInstallFlagStage($Journal) {
    if (-not $Journal.flag_stage) { return }
    $candidate = Join-Path $Journal.next.steam $Journal.flag_stage
    [void](Assert-ContinueSafePath $candidate $Journal.next.steam)
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $item = Get-Item -LiteralPath $candidate
        if ($item.Length -eq 0 -and $item.LastWriteTimeUtc.Ticks.ToString() -eq $Journal.next.debug_flag_stamp) {
            Remove-Item -LiteralPath $candidate -Force
        }
    }
}

function Restore-ContinueInstallTransaction([switch]$FromBootstrap, [switch]$PassThru) {
    $ctx = $script:ContinueContext
    $path = Join-Path $ctx.Root 'install-transaction.json'
    [void](Assert-ContinueSafePath $path $ctx.Root)
    if (-not (Test-Path -LiteralPath $path)) { return }
    if ((Get-Item -LiteralPath $path).Length -gt 65536) { throw 'Invalid install transaction.' }
    $journal = Read-ContinueJson $path
    if ($journal.schema -ne 1 -or $journal.state -notin @('prepared','committed') -or
        $journal.stage -notmatch '^app-stage-[a-f0-9]{32}$' -or $journal.backup -notmatch '^app-backup-[a-f0-9]{32}$') { throw 'Invalid install transaction.' }
    Assert-ContinueManifest $journal.old
    Assert-ContinueManifest $journal.next
    if ($journal.state -eq 'committed' -and -not $journal.next) { throw 'Invalid committed install transaction.' }
    if ($journal.flag_stage -and ($journal.flag_stage -notmatch '^\.continue-debug-[a-f0-9]{32}\.tmp$' -or
        -not $journal.next -or $journal.next.debug_flag_stamp -notmatch '^\d{15,19}$')) { throw 'Invalid debugging-flag transaction.' }
    $current = Read-ContinueJson $ctx.Manifest
    Assert-ContinueManifest $current
    if ($current -and -not ($journal.old -and $current.install_id -eq $journal.old.install_id) -and
        -not ($journal.next -and $current.install_id -eq $journal.next.install_id)) { throw 'Install recovery found unrelated ownership; recovery files preserved.' }
    $task = Get-ContinueTask
    if ($task -and -not (Test-ContinueOwnedTask $task $journal.old) -and -not (Test-ContinueOwnedTask $task $journal.next)) {
        throw 'Install recovery found an unrelated task; recovery files preserved.'
    }
    $stage = Join-Path $ctx.Root $journal.stage
    $backup = Join-Path $ctx.Root $journal.backup
    foreach ($item in @($stage,$backup,$ctx.App)) { [void](Assert-ContinueSafePath $item $ctx.Root) }
    if ($journal.flag_stage) { [void](Assert-ContinueSafePath (Join-Path $journal.next.steam $journal.flag_stage) $journal.next.steam) }
    if ((Test-Path -LiteralPath $backup) -and -not $journal.old) { throw 'Install backup has no previous owner; recovery files preserved.' }
    if ($journal.state -eq 'committed') {
        if (-not (Test-Path -LiteralPath (Join-Path $ctx.App 'pc\gamehub_bp.py') -PathType Leaf)) { throw 'Committed app is missing; recovery files preserved.' }
        Remove-ContinuePath $backup
    } elseif (Test-Path -LiteralPath $backup) {
        # A prepared transaction never started its replacement service. When
        # invoked by the stable task, stopping that task would kill the very
        # recovery process holding this lock before it can restore the app.
        if (-not $FromBootstrap) {
            if ($journal.next -and (Test-ContinueOwnedTask $task $journal.next)) { Stop-ContinueService $journal.next; Stop-ContinueTask $journal.next }
            elseif ($journal.old) { Stop-ContinueService $journal.old; Stop-ContinueTask $journal.old }
        }
        Remove-ContinuePath $ctx.App
        Move-Item -LiteralPath $backup -Destination $ctx.App
        Write-ContinueJson $ctx.Manifest $journal.old
        Register-ContinueTask $journal.old
    } elseif ($journal.old) {
        if (-not (Test-Path -LiteralPath $ctx.App)) { throw 'Previous app and backup are both missing; recovery files preserved.' }
        Write-ContinueJson $ctx.Manifest $journal.old
    } else {
        # First install can be interrupted after task registration. Retain an
        # already complete, owned app so the stable task can finish starting it.
        $current = Read-ContinueJson $ctx.Manifest
        Assert-ContinueManifest $current
        if (-not $current -or -not (Test-Path -LiteralPath (Join-Path $ctx.App 'pc\gamehub_bp.py'))) {
            # Persist removal authority before clearing the sole install journal.
            if ($journal.next) {
                Write-ContinueJson $ctx.Recovery (New-ContinueRecovery $journal.next 'retained' $null)
                Remove-ContinueOwnedDebugFlag $journal.next
            }
            Remove-ContinuePath $ctx.App
        }
    }
    if ($journal.state -eq 'prepared' -and $journal.old -and $journal.flag_stage) {
        # A repair can recreate a missing flag. Its new identity must not be
        # left behind with the restored previous manifest's older receipt.
        Remove-ContinueOwnedDebugFlag $journal.next
    }
    Remove-ContinueInstallFlagStage $journal
    Remove-ContinuePath $stage
    Remove-ContinuePath $path
    if ($PassThru) { return $journal }
}

function Install-ContinueBootstrap([string]$SourceRoot) {
    foreach ($pair in @(@('public_bootstrap.py','bootstrap.py'), @('recover-install.ps1','recover-install.ps1'), @('windows_common.ps1','windows_common.ps1'), @('public_update.py','update-helper.py'))) {
        $source = Join-Path $SourceRoot ('pc\' + $pair[0])
        if (-not (Test-Path -LiteralPath $source)) {
            if ($script:ContinueContext.Fixture) { continue }
            throw "Missing recovery file: $($pair[0])"
        }
        $target = Join-Path $script:ContinueContext.Root $pair[1]
        [void](Assert-ContinueSafePath $target $script:ContinueContext.Root)
        $temp = $target + '.new'
        [void](Assert-ContinueSafePath $temp $script:ContinueContext.Root)
        [IO.File]::WriteAllBytes($temp,[IO.File]::ReadAllBytes($source))
        if ([IO.File]::Exists($target)) {
            $previous = $temp + '.previous'
            [void](Assert-ContinueSafePath $previous $script:ContinueContext.Root)
            [IO.File]::Replace($temp,$target,$previous)
            [IO.File]::Delete($previous)
        }
        else { [IO.File]::Move($temp,$target) }
    }
}

function Add-ContinueFixtureOperation([string]$Operation, $Extra = @{}) {
    $state = Get-ContinueFixtureState
    $event = [ordered]@{ operation = $Operation }
    foreach ($key in $Extra.Keys) { $event[$key] = $Extra[$key] }
    $state.operations = @($state.operations) + @([pscustomobject]$event)
    Write-ContinueJson $script:ContinueContext.StatePath $state
}

function Get-ContinueSteamPath {
    if ($script:ContinueContext.Fixture) { $path = $script:ContinueContext.FixtureSteam }
    else {
        # Thin registry wrapper; fixture mode never touches this hive.
        try { $path = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam' -Name SteamPath).SteamPath }
        catch { throw 'Steam was not found. Install and open Steam in this Windows account first.' }
    }
    if (-not $path -or -not (Test-Path -LiteralPath (Join-Path $path 'steam.exe') -PathType Leaf)) {
        throw 'Steam was not found. Install and open Steam in this Windows account first.'
    }
    $absolute = [IO.Path]::GetFullPath($path).TrimEnd('\', '/')
    [void](Assert-ContinueSafePath (Join-Path $absolute 'steam.exe') $absolute)
    return $absolute
}

function Confirm-ContinueChoice([string]$Message, [bool]$DefaultYes, [switch]$NonInteractive) {
    if ($NonInteractive) { return $DefaultYes }
    $suffix = if ($DefaultYes) { '[Y/n]' } else { '[y/N]' }
    $answer = Read-Host "$Message $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer.Trim().ToLowerInvariant() -in @('y', 'yes')
}

function Get-ContinueArguments([string]$App) {
    $bootstrap = Join-Path ([IO.Path]::GetDirectoryName($App)) 'bootstrap.py'
    if (Test-Path -LiteralPath $bootstrap -PathType Leaf) { return '"' + $bootstrap + '" run' }
    return '"' + (Join-Path $App 'pc\gamehub_bp.py') + '" run'
}

function Get-ContinueTask {
    if ($script:ContinueContext.Fixture) { return (Get-ContinueFixtureState).task }
    return (Get-ScheduledTask -TaskName $script:ContinueContext.TaskName -TaskPath '\' -ErrorAction SilentlyContinue)
}

function Test-ContinueOwnedTask($Task, $Manifest) {
    if (-not $Task -or -not $Manifest) { return $false }
    $expected = Get-ContinueArguments $script:ContinueContext.App
    $legacy = '"' + (Join-Path $script:ContinueContext.App 'pc\gamehub_bp.py') + '" run'
    if ($script:ContinueContext.Fixture) {
        return ($Task.name -eq $script:ContinueContext.TaskName -and $Task.execute -eq $Manifest.pythonw -and $Task.arguments -in @($expected,$legacy))
    }
    $actions = @($Task.Actions)
    return ($Task.TaskName -eq $script:ContinueContext.TaskName -and $actions.Count -eq 1 -and
        $actions[0].Execute -eq $Manifest.pythonw -and $actions[0].Arguments -in @($expected,$legacy))
}

function Assert-ContinueManifest($Manifest) {
    if (-not $Manifest) { return }
    if ($Manifest.root -ne $script:ContinueContext.Root -or $Manifest.app -ne $script:ContinueContext.App -or
        $Manifest.task_name -ne $script:ContinueContext.TaskName) { throw 'Install manifest contains unexpected paths or task name.' }
    [void](Assert-ContinueSafePath $Manifest.app $script:ContinueContext.Root)
    if ($Manifest.install_id -notmatch '^[a-fA-F0-9]{32}$' -or $Manifest.schema -ne 1 -or
        $Manifest.data -ne $script:ContinueContext.Data -or $Manifest.logs -ne $script:ContinueContext.Logs -or
        $Manifest.python_created -isnot [bool] -or $Manifest.debug_flag_created -isnot [bool]) {
        throw 'Install manifest does not prove ownership of this profile.'
    }
    if ($Manifest.debug_flag_stamp -and $Manifest.debug_flag_stamp -notmatch '^\d{15,19}$') { throw 'Invalid debugging-flag receipt.' }
    if ($Manifest.python_created -and [IO.Path]::GetDirectoryName($Manifest.pythonw) -ne (Join-Path $script:ContinueContext.Root 'python')) {
        throw 'Owned Python must be inside this Continue profile.'
    }
    $steam = Get-ContinueSteamPath
    if ($Manifest.steam -ne $steam -or $Manifest.debug_flag -ne (Join-Path $steam '.cef-enable-remote-debugging')) {
        throw 'Steam location differs from the recorded installation. Restore the manifest before repairing or removing.'
    }
    if ([IO.Path]::GetFileName($Manifest.pythonw) -ne 'pythonw.exe' -or
        [IO.Path]::GetFileName($Manifest.python_console) -ne 'python.exe' -or
        [IO.Path]::GetDirectoryName($Manifest.pythonw) -ne [IO.Path]::GetDirectoryName($Manifest.python_console)) {
        throw 'Install manifest contains unexpected Python executables.'
    }
    if ($script:ContinueContext.Fixture -and $Manifest.pythonw -ne $script:ContinueContext.FixturePython) {
        throw 'Fixture manifest Python differs from the fake executable.'
    }
}

function Invoke-ContinueCaptured([string]$Executable, [string]$Arguments, [int]$TimeoutSeconds = 15) {
    if ($script:ContinueContext.Fixture) { throw 'Fixture mode must never execute Python or Steam.' }
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Executable; $info.Arguments = $Arguments
    $info.UseShellExecute = $false; $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $info.EnvironmentVariables['PYTHON_MANAGER_AUTOMATIC_INSTALL'] = '0'
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $output = $process.StandardOutput.ReadToEndAsync()
        $errorOutput = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            throw "Command timed out: $Executable"
        }
        return [pscustomobject]@{ Code = $process.ExitCode; Out = $output.Result; Error = $errorOutput.Result }
    } finally { $process.Dispose() }
}

function Test-ContinuePython([string]$Pythonw) {
    if (-not (Test-Path -LiteralPath $Pythonw -PathType Leaf)) { return $null }
    $console = Join-Path ([IO.Path]::GetDirectoryName($Pythonw)) 'python.exe'
    if (-not (Test-Path -LiteralPath $console -PathType Leaf)) { return $null }
    if ($script:ContinueContext.Fixture) {
        if ($Pythonw -ne $script:ContinueContext.FixturePython) { throw 'Only FixturePython can be selected in fixture mode.' }
        return [pscustomobject]@{ Pythonw = $Pythonw; Console = $console; Version = '3.14.8'; Owned = $false }
    }
    try {
        $result = Invoke-ContinueCaptured $console '-I -S -c "import sys; print(''{}.{}.{}''.format(*sys.version_info[:3])); raise SystemExit(sys.version_info < (3, 10))"'
        if ($result.Code -ne 0 -or $result.Out.Trim() -notmatch '^3\.\d+\.\d+$') { return $null }
        $owned = $Pythonw.StartsWith((Join-Path $script:ContinueContext.Root 'python') + '\', [StringComparison]::OrdinalIgnoreCase)
        return [pscustomobject]@{ Pythonw = $Pythonw; Console = $console; Version = $result.Out.Trim(); Owned = $owned }
    } catch { return $null }
}

function Get-ContinueArchitecture {
    $native = $env:PROCESSOR_ARCHITEW6432
    if (-not $native) { $native = $env:PROCESSOR_ARCHITECTURE }
    switch ($native.ToUpperInvariant()) {
        'AMD64' { return 'amd64' }
        'ARM64' { return 'arm64' }
        default { throw 'Automatic Python download supports x64 and ARM64 Windows. Install Python 3.10+ with pythonw.exe for other architectures.' }
    }
}

function Assert-ContinueRuntimeHash([string]$Archive, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Archive -PathType Leaf) -or $Expected -notmatch '^[a-fA-F0-9]{64}$') {
        throw 'Python download failed SHA-256 verification. The downloaded archive will not be used.'
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Archive)
    try {
        $hashBytes = $sha.ComputeHash($stream)
        $actual = ([BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
    if ($actual -ne $Expected.ToLowerInvariant()) {
        throw 'Python download failed SHA-256 verification. The downloaded archive will not be used; run setup.cmd again.'
    }
    return $true
}

function Expand-ContinueRuntime([string]$Archive, [string]$Destination) {
    [void](Assert-ContinueSafePath $Destination $script:ContinueContext.Root)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        $total = [int64]0
        if ($zip.Entries.Count -gt 250) { throw 'Python archive has too many entries.' }
        foreach ($entry in $zip.Entries) {
            $total += $entry.Length
            if ($total -gt 100MB -or $entry.FullName -match '(^[\\/]|^[A-Za-z]:|(^|[\\/])\.\.([\\/]|$))') { throw 'Unsafe Python archive entry.' }
            $target = Join-Path $Destination $entry.FullName
            [void](Assert-ContinueSafePath $target $Destination)
            if ($entry.Name) {
                [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $false)
            } else { [void][IO.Directory]::CreateDirectory($target) }
        }
    } finally { $zip.Dispose() }
}

function Install-ContinueEmbeddedPython([string]$SourceRoot) {
    if ($script:ContinueContext.Fixture) { throw 'Runtime download is forbidden in fixture mode.' }
    $metadata = Read-ContinueJson (Join-Path $SourceRoot 'pc\python_runtime.json')
    $architecture = Get-ContinueArchitecture
    $artifact = $metadata.architectures.PSObject.Properties[$architecture].Value
    $uri = [uri]$artifact.url
    if ($uri.Scheme -ne 'https' -or $uri.Host -ne 'www.python.org' -or $artifact.sha256 -notmatch '^[a-f0-9]{64}$') {
        throw 'Python runtime metadata does not contain an official pinned download.'
    }
    [void][IO.Directory]::CreateDirectory($script:ContinueContext.Root)
    $archive = Join-Path $script:ContinueContext.Root ('python-download-' + [guid]::NewGuid().ToString('N') + '.zip')
    $stage = Join-Path $script:ContinueContext.Root ('python-stage-' + [guid]::NewGuid().ToString('N'))
    $destination = Join-Path $script:ContinueContext.Root 'python'
    try {
        Write-Host "Python 3.10+ was not found. Downloading pinned Python $($metadata.version) ($architecture) from python.org into your user profile."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        try { Invoke-WebRequest -Uri $uri -OutFile $archive -UseBasicParsing -TimeoutSec 120 }
        catch { throw 'Python download failed. Check your internet connection and run setup.cmd again. No system Python was changed.' }
        [void](Assert-ContinueRuntimeHash $archive $artifact.sha256)
        [void][IO.Directory]::CreateDirectory($stage)
        Expand-ContinueRuntime $archive $stage
        $pythonw = Join-Path $stage 'pythonw.exe'
        foreach ($name in @('python.exe', 'pythonw.exe')) {
            $signature = Get-AuthenticodeSignature -LiteralPath (Join-Path $stage $name)
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'Downloaded Python executable did not pass Windows publisher signature verification.'
            }
        }
        # Keep isolated stdlib behavior; no site-packages, PATH or registry changes.
        $pth = @(Get-ChildItem -LiteralPath $stage -Filter 'python*._pth')
        if ($pth.Count -ne 1) { throw 'Python archive is missing its isolated path configuration.' }
        $stdlibZip = @(Get-ChildItem -LiteralPath $stage -Filter 'python*.zip')[0].Name
        [IO.File]::WriteAllText($pth[0].FullName, "$stdlibZip`n.`n..\app\pc`n..\app\plugin\GameHubDeck`n", (New-Object Text.UTF8Encoding $false))
        $candidate = Test-ContinuePython $pythonw
        if (-not $candidate) { throw 'Downloaded Python could not start. Antivirus may have quarantined it; check Windows Security.' }
        if (Test-Path -LiteralPath $destination) { throw 'A damaged Continue Python folder exists. Remove only that folder and run setup.cmd again.' }
        [void](Assert-ContinueSafePath $destination $script:ContinueContext.Root)
        Move-Item -LiteralPath $stage -Destination $destination
        $candidate.Pythonw = Join-Path $destination 'pythonw.exe'
        $candidate.Console = Join-Path $destination 'python.exe'
        $candidate.Owned = $true
        return $candidate
    } finally {
        if (Test-Path -LiteralPath $archive) { Remove-ContinuePath $archive }
        if (Test-Path -LiteralPath $stage) { Remove-ContinuePath $stage }
    }
}

function Find-ContinuePython([string]$SourceRoot) {
    if ($script:ContinueContext.Fixture) { return (Test-ContinuePython $script:ContinueContext.FixturePython) }
    $candidate = Test-ContinuePython (Join-Path $script:ContinueContext.Root 'python\pythonw.exe')
    if ($candidate) { return $candidate }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            $probe = Invoke-ContinueCaptured $launcher.Source '-3 -I -S -c "import sys; print(sys.executable)"'
            if ($probe.Code -eq 0) {
                $candidate = Test-ContinuePython (Join-Path ([IO.Path]::GetDirectoryName($probe.Out.Trim())) 'pythonw.exe')
                if ($candidate) { return $candidate }
            }
        } catch { }
    }
    foreach ($command in @(Get-Command pythonw.exe -All -ErrorAction SilentlyContinue)) {
        $candidate = Test-ContinuePython $command.Source
        if ($candidate) { return $candidate }
    }
    $patterns = @(
        (Join-Path $script:ContinueContext.Local 'Programs\Python\Python*\pythonw.exe'),
        (Join-Path $script:ContinueContext.Local 'Python\pythoncore-*\pythonw.exe')
    )
    if ($env:ProgramFiles) { $patterns += (Join-Path $env:ProgramFiles 'Python*\pythonw.exe') }
    if ($env:SystemDrive) { $patterns += (Join-Path $env:SystemDrive 'Python*\pythonw.exe') }
    foreach ($pattern in $patterns) {
        foreach ($path in @(Get-Item -Path $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)) {
            $candidate = Test-ContinuePython $path.FullName
            if ($candidate) { return $candidate }
        }
    }
    return (Install-ContinueEmbeddedPython $SourceRoot)
}

function Get-ContinueService($Manifest) {
    if (-not $Manifest) { return @() }
    if ($script:ContinueContext.Fixture) {
        if ((Get-ContinueFixtureState).service_running) { return @([pscustomobject]@{ ProcessId = 4242 }) }
        return @()
    }
    $exe = [regex]::Escape($Manifest.pythonw)
    $entry = [regex]::Escape((Join-Path $script:ContinueContext.App 'pc\gamehub_bp.py'))
    $bootstrap = [regex]::Escape((Join-Path $script:ContinueContext.Root 'bootstrap.py'))
    $pattern = '^\s*(?:"' + $exe + '"|' + $exe + ')\s+(?:"' + $entry + '"|' + $entry + '|"' + $bootstrap + '"|' + $bootstrap + ')\s+run\s*$'
    return @(Get-CimInstance -ClassName Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -eq $Manifest.pythonw -and $_.CommandLine -match $pattern })
}

function Stop-ContinueService($Manifest) {
    if (-not $Manifest) { return }
    if ($script:ContinueContext.Fixture) {
        Add-ContinueFixtureOperation 'stop_service' @{ entry = (Join-Path $Manifest.app 'pc\gamehub_bp.py'); python = $Manifest.python_console }
        $state = Get-ContinueFixtureState; $state.service_running = $false
        Write-ContinueJson $script:ContinueContext.StatePath $state
        return
    }
    if (@(Get-ContinueService $Manifest).Count -eq 0) { return }
    $command = '"' + (Join-Path $Manifest.app 'pc\gamehub_bp.py') + '" stop'
    $result = Invoke-ContinueCaptured $Manifest.python_console $command 15
    $deadline = (Get-Date).AddSeconds(15)
    while (@(Get-ContinueService $Manifest).Count -gt 0 -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
    if (@(Get-ContinueService $Manifest).Count -gt 0) {
        # Network workers can outlive the graceful stop. Task ownership is
        # checked again before ending exactly this installation's task tree.
        Write-Host 'Continue network work is still closing; stopping its owned task.'
        Stop-ContinueTask $Manifest
        $deadline = (Get-Date).AddSeconds(5)
        while (@(Get-ContinueService $Manifest).Count -gt 0 -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
    }
    if (@(Get-ContinueService $Manifest).Count -gt 0) { throw 'Continue is still running. Installation was left unchanged.' }
}

function Stop-ContinueTask($Manifest) {
    $task = Get-ContinueTask
    if (-not $task) { return }
    if (-not (Test-ContinueOwnedTask $task $Manifest)) { throw 'ContinueBigPicture belongs to another installation. It was not stopped.' }
    if ($script:ContinueContext.Fixture) { Add-ContinueFixtureOperation 'stop_task' @{ task_name = $script:ContinueContext.TaskName }; return }
    Stop-ScheduledTask -TaskName $script:ContinueContext.TaskName -TaskPath '\'
}

function Register-ContinueTask($Manifest) {
    if ($script:ContinueContext.Fixture) {
        $state = Get-ContinueFixtureState
        if ($state.PSObject.Properties['fail_register'] -and $state.fail_register) {
            # Failure injection represents the attempted replacement only.  A
            # rollback must still be able to restore the previously owned task.
            $state.fail_register = $false
            Write-ContinueJson $script:ContinueContext.StatePath $state
            throw 'Fixture task registration failed.'
        }
        $state.task = [pscustomobject]@{ name = $script:ContinueContext.TaskName; execute = $Manifest.pythonw
            arguments = (Get-ContinueArguments $Manifest.app); working_directory = $script:ContinueContext.Root
            multiple_instances = 'IgnoreNew'; interval_minutes = 10; at_logon = $true; run_level = 'Limited' }
        Write-ContinueJson $script:ContinueContext.StatePath $state
        Add-ContinueFixtureOperation 'register_task' @{ task_name = $script:ContinueContext.TaskName }
        return
    }
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action = New-ScheduledTaskAction -Execute $Manifest.pythonw -Argument (Get-ContinueArguments $Manifest.app) -WorkingDirectory $script:ContinueContext.Root
    $logon = New-ScheduledTaskTrigger -AtLogOn -User $user
    $repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $script:ContinueContext.TaskName -TaskPath '\' -Action $action -Trigger @($logon, $repeat) -Settings $settings -Principal $principal -Description 'Continue for Steam Big Picture, installed in this user profile.' -Force | Out-Null
}

function Start-ContinueTask($Manifest) {
    if (-not (Test-ContinueOwnedTask (Get-ContinueTask) $Manifest)) { throw 'ContinueBigPicture does not match this installation.' }
    if ($script:ContinueContext.Fixture) {
        $state = Get-ContinueFixtureState
        if ($state.PSObject.Properties['fail_start'] -and $state.fail_start) { throw 'Fixture task launch failed.' }
        $state.service_running = $true; Write-ContinueJson $script:ContinueContext.StatePath $state
        Add-ContinueFixtureOperation 'start_service' @{ task_name = $script:ContinueContext.TaskName }
        return
    }
    Start-ScheduledTask -TaskName $script:ContinueContext.TaskName -TaskPath '\'
}

function Unregister-ContinueTask($Manifest) {
    $task = Get-ContinueTask
    if (-not $task) { return }
    if (-not (Test-ContinueOwnedTask $task $Manifest)) { throw 'ContinueBigPicture belongs to another installation. It was not removed.' }
    if ($script:ContinueContext.Fixture) {
        $state = Get-ContinueFixtureState; $state.task = $null
        Write-ContinueJson $script:ContinueContext.StatePath $state
        Add-ContinueFixtureOperation 'unregister_task' @{ task_name = $script:ContinueContext.TaskName }
        return
    }
    Unregister-ScheduledTask -TaskName $script:ContinueContext.TaskName -TaskPath '\' -Confirm:$false
}

function Remove-ContinuePath([string]$Path) {
    [void](Assert-ContinueSafePath $Path $script:ContinueContext.Root)
    if (Test-Path -LiteralPath $Path) {
        foreach ($entry in @(Get-ChildItem -LiteralPath $Path -Force -Recurse -ErrorAction Stop)) {
            [void](Assert-ContinueSafePath $entry.FullName $script:ContinueContext.Root)
        }
        if ($script:ContinueContext.Fixture) {
            $state = Get-ContinueFixtureState
            if ($state.PSObject.Properties['fail_remove'] -and $state.fail_remove -eq $Path) {
                throw 'Fixture cleanup failure; recovery metadata was retained.'
            }
        }
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

# The updater uses a nonblocking lock on byte zero of update.lock. Use the same
# Windows byte-range lock; a second lock name would not serialize the lifecycle.
function Enter-ContinueLifecycleLock {
    [void](Assert-ContinueSafePath $script:ContinueContext.Root $script:ContinueContext.Local)
    [void][IO.Directory]::CreateDirectory($script:ContinueContext.Root)
    $path = Join-Path $script:ContinueContext.Root 'update.lock'
    [void](Assert-ContinueSafePath $path $script:ContinueContext.Root)
    $stream = $null
    try {
        $stream = [IO.File]::Open($path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
        $stream.Lock(0, 1)
        if ($stream.Length -eq 0) { $stream.WriteByte(48); $stream.Flush() }
        return $stream
    } catch {
        if ($stream) { $stream.Dispose() }
        throw 'Continue lifecycle lock is busy or unsafe. Wait for the update/installation to finish, then retry. No task or application files were changed.'
    }
}

function Exit-ContinueLifecycleLock($Stream) {
    if ($Stream) { try { $Stream.Unlock(0, 1) } finally { $Stream.Dispose() } }
}

function Read-ContinueRecovery {
    $path = $script:ContinueContext.Recovery
    [void](Assert-ContinueSafePath $path $script:ContinueContext.Root)
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -gt 65536) { throw 'Invalid Continue recovery metadata.' }
    $recovery = Read-ContinueJson $path
    if (-not $recovery -or $recovery.schema -ne 1 -or $recovery.state -notin @('cleaning', 'retained', 'pending')) { throw 'Invalid Continue recovery metadata.' }
    Assert-ContinueManifest $recovery.owner
    if (-not $recovery.owner) { throw 'Recovery metadata does not prove profile ownership.' }
    return $recovery
}

function New-ContinueRecovery($Manifest, [string]$State, $StartupMovie = $null) {
    # Only ownership and recovery values survive purge, never arbitrary settings,
    # secrets, media, task XML, or an executable recovery command.
    $owner = [ordered]@{}
    foreach ($key in @('schema', 'install_id', 'version', 'root', 'app', 'data', 'logs', 'steam', 'debug_flag',
        'debug_flag_created', 'debug_flag_stamp', 'task_name', 'pythonw', 'python_console', 'python_created')) { $owner[$key] = $Manifest.$key }
    return [pscustomobject]@{ schema = 1; state = $State; owner = [pscustomobject]$owner; startup_movie = $StartupMovie }
}

function Get-ContinueStartupRecovery($PreviousRecovery) {
    $path = Join-Path $script:ContinueContext.Root 'startup_movie.json'
    [void](Assert-ContinueSafePath $path $script:ContinueContext.Root)
    if (-not (Test-Path -LiteralPath $path)) {
        return $(if ($PreviousRecovery) { $PreviousRecovery.startup_movie } else { $null })
    }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -gt 4096) { throw 'Invalid startup-movie recovery record; nothing was purged.' }
    $record = Read-ContinueJson $path
    if ($record.created -isnot [bool] -or $record.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'Invalid startup-movie recovery record; nothing was purged.' }
    $settingsPath = Join-Path $script:ContinueContext.Root 'settings.json'
    [void](Assert-ContinueSafePath $settingsPath $script:ContinueContext.Root)
    $settings = Read-ContinueJson $settingsPath
    $prev = if ($settings -and $settings.PSObject.Properties['startup_movie_prev']) { $settings.startup_movie_prev }
        elseif ($PreviousRecovery -and $PreviousRecovery.startup_movie) { $PreviousRecovery.startup_movie.previous } else { $null }
    if ($prev -and ($prev.id -isnot [string] -or $prev.id -notmatch '^\d{1,20}$' -or $prev.path -isnot [string] -or
        $prev.path.Length -gt 2048 -or $prev.path -match '[\x00-\x1f]' -or $prev.shuffle -isnot [bool])) { throw 'Invalid previous startup-movie choice; settings were preserved for manual recovery.' }
    $cleanPrevious = if ($prev) { [pscustomobject]@{ id = $prev.id; path = $prev.path; shuffle = $prev.shuffle } } else { $null }
    return [pscustomobject]@{ previous = $cleanPrevious; created = $record.created; sha256 = $record.sha256 }
}

function Test-ContinueSharedDebugConsumer {
    if ($script:ContinueContext.Fixture) {
        $state = Get-ContinueFixtureState
        if (-not $state.PSObject.Properties['gamehub_task']) { return $false }
        $task = $state.gamehub_task
        $name = $task.name; $status = $task.state; $execute = $task.execute; $arguments = $task.arguments
    } else {
        $task = Get-ScheduledTask -TaskName 'GameHubBigPicture' -TaskPath '\' -ErrorAction SilentlyContinue
        if (-not $task -or @($task.Actions).Count -ne 1) { return $false }
        $name = $task.TaskName; $status = [string]$task.State; $execute = $task.Actions[0].Execute; $arguments = $task.Actions[0].Arguments
    }
    # Inspect only the known consumer; never stop, launch, or rewrite it. The
    # executable and script must still exist, with an exact service argument.
    if ($name -ne 'GameHubBigPicture' -or $status -ne 'Running' -or
        [IO.Path]::GetFileName($execute) -ne 'pythonw.exe' -or -not (Test-Path -LiteralPath $execute -PathType Leaf)) { return $false }
    if ($arguments -notmatch '^"([^"\r\n]+[\\/]gamehub_bp\.py)" run$') { return $false }
    $entry = $Matches[1]
    return ([IO.Path]::IsPathRooted($entry) -and (Test-Path -LiteralPath $entry -PathType Leaf) -and
        -not $entry.StartsWith($script:ContinueContext.Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase))
}

function Copy-ContinueApplication([string]$Source, [string]$Destination) {
    [void](Assert-ContinueSafePath $Destination $script:ContinueContext.Root)
    [void][IO.Directory]::CreateDirectory($Destination)
    foreach ($entry in @(Get-ChildItem -LiteralPath $Source -Force -Recurse)) {
        [void](Assert-ContinueSafePath $entry.FullName $Source)
        $relative = $entry.FullName.Substring($Source.TrimEnd('\', '/').Length).TrimStart('\', '/')
        $target = Join-Path $Destination $relative
        [void](Assert-ContinueSafePath $target $Destination)
        if ($entry.PSIsContainer) { [void][IO.Directory]::CreateDirectory($target) }
        else {
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            Copy-Item -LiteralPath $entry.FullName -Destination $target
        }
    }
}

function Get-ContinueCacheBytes {
    if (-not (Test-Path -LiteralPath $script:ContinueContext.Data)) { return [int64]0 }
    [void](Assert-ContinueSafePath $script:ContinueContext.Data $script:ContinueContext.Root)
    $sum = [int64]0
    foreach ($file in @(Get-ChildItem -LiteralPath $script:ContinueContext.Data -File -Recurse -Force)) {
        [void](Assert-ContinueSafePath $file.FullName $script:ContinueContext.Root)
        $sum += $file.Length
    }
    return $sum
}

function Test-ContinueSteamRunning([string]$Steam) {
    if ($script:ContinueContext.Fixture) { return [bool](Get-ContinueFixtureState).steam_running }
    $expected = Join-Path $Steam 'steam.exe'
    return (@(Get-CimInstance -ClassName Win32_Process -Filter "Name='steam.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -eq $expected }).Count -gt 0)
}

function Restart-ContinueSteam([string]$Steam) {
    if ($script:ContinueContext.Fixture) { Add-ContinueFixtureOperation 'restart_steam' @{ steam = $Steam }; return }
    $exe = Join-Path $Steam 'steam.exe'
    if (Test-ContinueSteamRunning $Steam) {
        Write-Host 'Asking Steam to close normally. If a game or Steam prevents closing, close it yourself and restart Steam.'
        Start-Process -FilePath $exe -ArgumentList '-shutdown' -WindowStyle Hidden | Out-Null
        $deadline = (Get-Date).AddSeconds(20)
        while ((Test-ContinueSteamRunning $Steam) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
        if (Test-ContinueSteamRunning $Steam) { Write-Host 'Steam is still open; restart it manually when your games are closed.'; return }
    }
    # The UI needs to be visible when the user has explicitly accepted a restart.
    Start-Process -FilePath $exe | Out-Null
}

function Get-ContinueCdpState {
    if ($script:ContinueContext.Fixture) { return (Get-ContinueFixtureState).cdp }
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $connect = $tcp.BeginConnect('127.0.0.1', 8080, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(1000)) { return 'closed' }
        $tcp.EndConnect($connect)
        # A listener is not enough: require a Steam SharedJSContext CDP target.
        try {
            $targets = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/json' -TimeoutSec 2
            if (@($targets | Where-Object { $_.title -eq 'SharedJSContext' -and $_.webSocketDebuggerUrl -match '^ws://(127\.0\.0\.1|localhost):8080/' }).Count -gt 0) { return 'steam' }
        } catch { }
        return 'other'
    } catch { return 'closed' }
    finally { $tcp.Dispose() }
}

function Get-ContinueMediaState {
    if ($script:ContinueContext.Fixture) {
        $state = Get-ContinueFixtureState
        if ($state.PSObject.Properties['media']) { return [string]$state.media }
        return $(if ($state.service_running) { 'continue' } else { 'closed' })
    }
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $connect = $tcp.BeginConnect('127.0.0.1', 8793, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(1000)) { return 'closed' }
        $tcp.EndConnect($connect)
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8793/__continue_health' -TimeoutSec 2
            if ($health.service -eq 'ContinueBigPicture') { return 'continue' }
        } catch { }
        return 'other'
    } catch { return 'closed' }
    finally { $tcp.Dispose() }
}
