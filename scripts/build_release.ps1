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
$InstallerPath = Join-Path $ProjectRoot "installer_output\GovPolicyWeekly_Setup_$Version.exe"

Write-Host 'Installing and checking the actual installer in an isolated folder'
$InstalledRoot = Join-Path $ProjectRoot 'release-check\installed-app'
$InstallLog = Join-Path $ProjectRoot 'release-check\installer.log'
$install = Start-Process -FilePath $InstallerPath -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
    "/DIR=`"$InstalledRoot`"", "/LOG=`"$InstallLog`""
) -PassThru
if (-not $install.WaitForExit(180000)) {
    $install.Kill()
    throw 'Installer check timed out'
}
if ($install.ExitCode -ne 0) { throw "Installer failed with exit code $($install.ExitCode)" }
$InstalledExe = Join-Path $InstalledRoot 'GovPolicyWeekly.exe'
if (-not (Test-Path -LiteralPath $InstalledExe)) { throw 'Installer did not create the executable' }
$InstalledCheck = Join-Path $ProjectRoot 'release-check\installed.json'
$installed = Start-Process -FilePath $InstalledExe -ArgumentList @('--self-test', "`"$InstalledCheck`"") -PassThru
if (-not $installed.WaitForExit(120000)) {
    $installed.Kill()
    throw 'Installed application check timed out'
}
Test-ResultFile $InstalledCheck
if ($installed.ExitCode -ne 0) { throw 'Installed application check failed' }
Copy-Item $InstallerPath 'release\' -Force

Write-Host 'Creating the portable archive'
python -m zipfile -c release/GovPolicyWeekly_windows_portable.zip dist/GovPolicyWeekly
if ($LASTEXITCODE -ne 0) { throw 'Portable archive creation failed' }
python -m zipfile -t release/GovPolicyWeekly_windows_portable.zip
if ($LASTEXITCODE -ne 0) { throw 'Portable archive integrity check failed' }

Get-ChildItem release -File | Where-Object { $_.Extension -in @('.exe', '.zip') } |
    Sort-Object Name | ForEach-Object {
        $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
        '{0}  {1}' -f $hash.Hash.ToLowerInvariant(), $_.Name
    } | Set-Content release/SHA256SUMS.txt -Encoding ASCII

Write-Host 'Release files ready:'
Get-ChildItem release -File | Select-Object Name, Length | Format-Table -AutoSize
