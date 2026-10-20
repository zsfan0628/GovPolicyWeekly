param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '1.0.0'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
New-Item -ItemType Directory -Force release, release-check | Out-Null

function Test-ResultFile($Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Application check did not create its result file: $Path"
    }
    $result = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $result.ok) { throw $result.error }
    Write-Host "Passed: $($result.checks -join ', ')"
}

Write-Host 'Checking report export and desktop UI before packaging'
python desktop_app.py --self-test release-check/source.json
if ($LASTEXITCODE -ne 0) {
    Test-ResultFile 'release-check/source.json'
    throw 'Source check failed'
}
Test-ResultFile 'release-check/source.json'

Write-Host 'Building the Windows application'
python -m PyInstaller GovPolicyWeekly.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }

Write-Host 'Checking the actual packaged executable'
$ExePath = Join-Path $ProjectRoot 'dist\GovPolicyWeekly\GovPolicyWeekly.exe'
$CheckPath = Join-Path $ProjectRoot 'release-check\packaged.json'
$process = Start-Process -FilePath $ExePath -ArgumentList @('--self-test', "`"$CheckPath`"") -PassThru
if (-not $process.WaitForExit(120000)) {
    $process.Kill()
    throw 'Packaged executable check timed out'
}
Test-ResultFile $CheckPath
if ($process.ExitCode -ne 0) { throw 'Packaged executable check failed' }

Write-Host 'Building the installer'
$Iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path -LiteralPath $Iscc)) {
    choco install innosetup --yes --no-progress
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup installation failed' }
}
if (-not (Test-Path -LiteralPath $Iscc)) { throw 'Inno Setup compiler was not found' }
& $Iscc "/DMyAppVersion=$Version" 'GovPolicyWeekly.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
Copy-Item "installer_output\GovPolicyWeekly_Setup_$Version.exe" 'release\' -Force

Write-Host 'Creating the portable archive'
python -m zipfile -c release/GovPolicyWeekly_windows_portable.zip dist/GovPolicyWeekly
if ($LASTEXITCODE -ne 0) { throw 'Portable archive creation failed' }

Get-ChildItem release -File | Where-Object { $_.Extension -in @('.exe', '.zip') } |
    Sort-Object Name | ForEach-Object {
        $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
        '{0}  {1}' -f $hash.Hash.ToLowerInvariant(), $_.Name
    } | Set-Content release/SHA256SUMS.txt -Encoding ASCII

Write-Host 'Release files ready:'
Get-ChildItem release -File | Select-Object Name, Length | Format-Table -AutoSize
