# Runs outside the installation after the GUI has closed. Only program-owned
# entries are swapped; settings, reports and other portable-root files stay put.
$ErrorActionPreference = 'Stop'
$target = $env:GPW_TARGET
$payload = $env:GPW_PAYLOAD
$exe = Join-Path $target 'GovPolicyWeekly.exe'
$backup = $null
$moved = @()
$placed = @()
$installStarted = $false
try {
    $old = Get-Process -Id ([int]$env:GPW_PID) -ErrorAction SilentlyContinue
    if ($old -and -not $old.WaitForExit(90000)) { throw 'Application did not exit.' }
    $names = @('GovPolicyWeekly.exe', '_internal')
    if ($env:GPW_MODE -eq 'installer') {
        if (-not (Test-Path -LiteralPath (Join-Path $target 'installer.channel'))) { throw 'Installer channel mismatch.' }
        if ((Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash -ne $env:GPW_SHA) { throw 'Installer checksum mismatch.' }
    } elseif ($env:GPW_MODE -eq 'portable') {
        $names += 'portable.channel'
        if ((Test-Path -LiteralPath $exe) -and -not (Test-Path -LiteralPath (Join-Path $target 'portable.channel'))) {
            throw 'Portable channel mismatch.'
        }
    } else { throw 'Invalid update channel.' }
    $backup = Join-Path $target ('.gov-backup-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($name in $names) {
        $path = Join-Path $target $name
        if (Test-Path -LiteralPath $path) {
            Move-Item -LiteralPath $path -Destination (Join-Path $backup $name)
            $moved += $name
        }
    }
    if ($env:GPW_MODE -eq 'installer') {
        $installStarted = $true
        $p = Start-Process -FilePath $payload -ArgumentList @('/SILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',('/DIR="' + $target + '"')) -PassThru -Wait
        if ($p.ExitCode -ne 0) { throw 'Installer failed.' }
    } else {
        foreach ($name in $names) {
            Move-Item -LiteralPath (Join-Path (Join-Path $payload 'new') $name) -Destination (Join-Path $target $name)
            $placed += $name
        }
    }
    $check = Join-Path $PSScriptRoot 'updated-check.json'
    $p = Start-Process -FilePath $exe -ArgumentList @('--self-test', ('"' + $check + '"')) -PassThru
    if (-not $p.WaitForExit(150000)) { $p.Kill(); $p.WaitForExit(); throw 'Update check timed out.' }
    if ($p.ExitCode -ne 0 -or -not (Get-Content -LiteralPath $check -Raw -Encoding UTF8 | ConvertFrom-Json).ok) { throw 'Update check failed.' }
    Start-Process -FilePath $exe -WorkingDirectory $target
} catch {
    $failure = $_.Exception.Message
    if ($installStarted) { $placed = $names }
    foreach ($name in $placed) {
        $path = Join-Path $target $name
        if (Test-Path -LiteralPath $path) { Move-Item -LiteralPath $path -Destination (Join-Path $backup ('failed-' + $name)) }
    }
    foreach ($name in $moved) { Move-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $target $name) }
    $failure | Set-Content (Join-Path $PSScriptRoot 'update-error.txt')
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("Update failed. Check update-error.txt in $PSScriptRoot") | Out-Null
    exit 1
}
Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction SilentlyContinue
if ($env:GPW_MODE -eq 'portable') { Remove-Item -LiteralPath $payload -Recurse -Force -ErrorAction SilentlyContinue }
Set-Location -LiteralPath $target
Remove-Item -LiteralPath $PSScriptRoot -Recurse -Force -ErrorAction SilentlyContinue
