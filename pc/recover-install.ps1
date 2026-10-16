. (Join-Path $PSScriptRoot 'windows_common.ps1')
$lock = $null
try {
    $context = Initialize-ContinueContext
    if ($context.Root -ne $PSScriptRoot) { throw 'Recovery must run from this account Continue profile.' }
    $deadline = (Get-Date).AddSeconds(90)
    while (-not $lock) {
        try { $lock = Enter-ContinueLifecycleLock }
        catch { if ((Get-Date) -ge $deadline) { throw }; Start-Sleep -Milliseconds 250 }
    }
    Restore-ContinueInstallTransaction -FromBootstrap
    exit 0
} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }
finally { Exit-ContinueLifecycleLock $lock }
