# Exercise both production update paths against throwaway Windows installations.
param([Parameter(Mandatory)][string]$Installer)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$checkRoot = Join-Path $project ('release-check\upgrade-' + [guid]::NewGuid().ToString('N'))
$shell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
New-Item -ItemType Directory -Path $checkRoot | Out-Null
$passed = @()
foreach ($channel in @('portable','installer')) {
    $target = Join-Path $checkRoot $channel
    $job = Join-Path $checkRoot ($channel + '-helper')
    New-Item -ItemType Directory -Path $target, $job | Out-Null
    $helper = Join-Path $job 'apply-update.ps1'
    Copy-Item -LiteralPath (Join-Path $project 'config\apply-update.ps1') -Destination $helper
    if ($channel -eq 'installer') {
        $p = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT','/NORESTART','/SP-',('/DIR="' + $target + '"')) -PassThru -Wait
        if ($p.ExitCode -ne 0) { throw 'Cannot install upgrade fixture' }
        $payload = $Installer
        $env:GPW_SHA = (Get-FileHash -LiteralPath $Installer).Hash
    } else {
        $payload = Join-Path $target '.gov-update-test'
        New-Item -ItemType Directory -Path $payload | Out-Null
        $archive = Join-Path $project 'release\GovPolicyWeekly_windows_portable.zip'
        python -c "import sys; from gov_report.updates import unpack_portable; unpack_portable(sys.argv[1], sys.argv[2])" $archive (Join-Path $payload 'new')
        if ($LASTEXITCODE -ne 0) { throw 'Cannot prepare portable upgrade fixture' }
        Copy-Item (Join-Path $payload 'new\GovPolicyWeekly.exe') $target
        Copy-Item (Join-Path $payload 'new\portable.channel') $target
        New-Item -ItemType Directory -Path (Join-Path $target '_internal') | Out-Null
    }
    $sentinel = Join-Path $target 'existing-report.txt'
    'preserve me' | Set-Content -LiteralPath $sentinel
    $obsolete = Join-Path $target '_internal\old-program-file.txt'
    'obsolete' | Set-Content -LiteralPath $obsolete
    $env:GPW_MODE = $channel
    $env:GPW_TARGET = $target
    $env:GPW_PAYLOAD = $payload
    $old = Start-Process -FilePath $shell -ArgumentList @('-NoProfile','-Command','Start-Sleep -Seconds 1') -PassThru
    $env:GPW_PID = "$($old.Id)"
    $p = Start-Process -FilePath $shell -ArgumentList @('-NoProfile','-NonInteractive','-File',('"' + $helper + '"')) -PassThru
    try {
        if (-not $p.WaitForExit(240000)) { $p.Kill(); throw "$channel upgrade timed out" }
        if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $sentinel) -or (Get-Content -LiteralPath $sentinel) -ne 'preserve me' -or (Test-Path -LiteralPath $obsolete)) {
            throw "$channel upgrade failed to replace only managed files"
        }
        $passed += $channel
    } finally {
        $exe = Join-Path $target 'GovPolicyWeekly.exe'
        Get-Process -Name GovPolicyWeekly -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $exe } | Stop-Process -Force
    }
}
@{ok=$true; channels=$passed} | ConvertTo-Json | Set-Content (Join-Path $project 'release-check\upgrade.json')
Remove-Item -LiteralPath $checkRoot -Recurse -Force -ErrorAction SilentlyContinue
