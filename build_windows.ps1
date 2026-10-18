param(
    [switch]$SkipPlaywrightBrowser,
    [switch]$BundleLibreOffice,
    [switch]$AllowWingetLibreOffice,
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Format-Size($Bytes) {
    if ($Bytes -ge 1GB) {
        return "{0:N1} GB" -f ($Bytes / 1GB)
    }
    if ($Bytes -ge 1MB) {
        return "{0:N1} MB" -f ($Bytes / 1MB)
    }
    if ($Bytes -ge 1KB) {
        return "{0:N1} KB" -f ($Bytes / 1KB)
    }
    return "$Bytes B"
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PipIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple"
$PlaywrightDownloadHosts = @(
    "https://npmmirror.com/mirrors/playwright",
    ""
)
$PythonVersion = "3.10.11"
$PythonNugetUrl = "https://www.nuget.org/api/v2/package/python/$PythonVersion"
$LocalPythonDir = Join-Path $ProjectRoot "python310"
$BuildCacheDir = Join-Path $ProjectRoot ".build_cache"
$Script:BundledPlaywrightBrowserSource = $null
$Script:BundledPlaywrightBrowserExe = $null

function Test-PythonCommand($Command) {
    try {
        $version = & $Command --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$version" -match "Python 3\.") {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

function Ensure-Pip($Command) {
    & $Command -m pip --version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return
    }
    Write-Host "pip not found. Running ensurepip."
    & $Command -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install pip for Python: $Command"
    }
}

function Get-PythonCommand {
    $common = @(
        (Join-Path $LocalPythonDir "python.exe"),
        (Join-Path $LocalPythonDir "tools\python.exe"),
        "$env:LocalAppData\Programs\Python\Python310\python.exe",
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "C:\Program Files\Python310\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe"
    )
    foreach ($path in $common) {
        if (Test-Path $path) {
            if (Test-PythonCommand $path) {
                return $path
            }
        }
    }
    $candidates = @("python", "py")
    foreach ($candidate in $candidates) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            if (Test-PythonCommand $candidate) {
                return $candidate
            }
        }
    }
    return $null
}

function Install-NugetPython {
    Write-Step "Python not found, unpacking NuGet Python $PythonVersion"
    if (-not (Test-Path $BuildCacheDir)) {
        New-Item -ItemType Directory -Path $BuildCacheDir | Out-Null
    }
    if (Test-Path $LocalPythonDir) {
        Remove-Item $LocalPythonDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $LocalPythonDir | Out-Null

    $nugetPackage = Join-Path $BuildCacheDir "python-$PythonVersion.nupkg"
    if ((Test-Path $nugetPackage) -and ((Get-Item $nugetPackage).Length -lt 10000000)) {
        Write-Host "Cached NuGet Python package looks incomplete. Re-downloading."
        Remove-Item $nugetPackage -Force
    }
    if (-not (Test-Path $nugetPackage)) {
        Write-Host "Downloading: $PythonNugetUrl"
        Invoke-WebRequest -Uri $PythonNugetUrl -OutFile $nugetPackage | Out-Null
    }
    $nugetZip = Join-Path $BuildCacheDir "python-$PythonVersion-nupkg.zip"
    Copy-Item $nugetPackage $nugetZip -Force
    Expand-Archive -Path $nugetZip -DestinationPath $LocalPythonDir -Force
    $cmd = Get-PythonCommand
    if (Test-PythonCommand $cmd) {
        return $cmd
    }
    throw "NuGet Python was unpacked, but python.exe cannot run."
}

function Ensure-Python {
    $cmd = Get-PythonCommand
    if ($cmd) {
        return $cmd
    }

    if (Test-Path $LocalPythonDir) {
        Write-Host "Existing local Python cannot run. Removing: $LocalPythonDir"
        Remove-Item $LocalPythonDir -Recurse -Force
    }

    return Install-NugetPython
}

function Find-LibreOffice {
    $candidates = @(
        "C:\Program Files\LibreOffice",
        "C:\Program Files (x86)\LibreOffice"
    )
    foreach ($path in $candidates) {
        if (Test-Path (Join-Path $path "program\soffice.exe")) {
            return $path
        }
    }
    return $null
}

function Ensure-LibreOffice {
    $path = Find-LibreOffice
    if ($path) {
        return $path
    }
    if (-not $AllowWingetLibreOffice) {
        throw "LibreOffice was not found. Install LibreOffice manually, then rerun with -BundleLibreOffice; or add -AllowWingetLibreOffice if you want this script to try winget installation."
    }
    Write-Step "LibreOffice not found, installing with winget"
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "LibreOffice was not found and winget is unavailable. Install LibreOffice manually, then rerun this script with -BundleLibreOffice."
    }
    winget install --id TheDocumentFoundation.LibreOffice -e --silent --accept-package-agreements --accept-source-agreements 2>&1 | ForEach-Object { Write-Host $_ }
    $path = Find-LibreOffice
    if (-not $path) {
        throw "LibreOffice installation finished, but soffice.exe was not found."
    }
    return $path
}

function Get-PlaywrightBrowserSource($PythonExe) {
    if (-not (Test-Path $BuildCacheDir)) {
        New-Item -ItemType Directory -Path $BuildCacheDir | Out-Null
    }
    $probe = Join-Path $BuildCacheDir "find_playwright_browsers.py"
    $script = @'
from pathlib import Path
import playwright
path = Path(playwright.__file__).resolve().parent.joinpath("driver", "package", ".local-browsers")
print(path)
'@
    Set-Content -Path $probe -Value $script -Encoding ASCII

    $oldErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $result = & $PythonExe $probe 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorAction
    }
    if ($exitCode -ne 0) {
        Write-Host "Python probe could not locate Playwright browsers. Falling back to folder search."
        $result | ForEach-Object { Write-Host $_ }
        $fallback = Find-PlaywrightBrowserSourceBySearch
        return $fallback
    }
    $lastLine = $result | Select-Object -Last 1
    if (-not $lastLine) {
        $fallback = Find-PlaywrightBrowserSourceBySearch
        return $fallback
    }
    $path = $lastLine.ToString().Trim()
    if ($path -and (Test-Path $path)) {
        return $path
    }
    $fallback = Find-PlaywrightBrowserSourceBySearch
    return $fallback
}

function Find-PlaywrightBrowserSourceBySearch {
    $roots = @(
        (Join-Path $ProjectRoot ".venv"),
        (Join-Path $ProjectRoot "python310")
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) {
            continue
        }
        $matches = Get-ChildItem $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq ".local-browsers" } |
            Select-Object -First 1
        if ($matches) {
            return $matches.FullName
        }
    }
    return $null
}

function Find-BrowserExecutable($BrowserDir) {
    if (-not $BrowserDir -or -not (Test-Path $BrowserDir)) {
        return $null
    }
    $exe = Get-ChildItem $BrowserDir -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @("chrome-headless-shell.exe", "chrome.exe", "msedge.exe") } |
        Select-Object -First 1
    if ($exe) {
        return $exe.FullName
    }
    return $null
}

function Find-SystemBrowserExecutable {
    $roots = @(
        [Environment]::GetEnvironmentVariable("ProgramFiles"),
        [Environment]::GetEnvironmentVariable("ProgramFiles(x86)"),
        [Environment]::GetEnvironmentVariable("LocalAppData")
    )
    $relatives = @(
        "Microsoft\Edge\Application\msedge.exe",
        "Google\Chrome\Application\chrome.exe",
        "Chromium\Application\chrome.exe"
    )
    foreach ($root in $roots) {
        if (-not $root) {
            continue
        }
        foreach ($relative in $relatives) {
            $candidate = Join-Path $root $relative
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }
    return $null
}

function Clear-IncompletePlaywrightBrowsers($PythonExe) {
    $BrowserSource = Get-PlaywrightBrowserSource $PythonExe
    if ($BrowserSource -and (Test-Path $BrowserSource)) {
        $ExistingBrowserExe = Find-BrowserExecutable $BrowserSource
        if (-not $ExistingBrowserExe) {
            Write-Host "Removing incomplete Playwright browser folder:"
            Write-Host $BrowserSource
            Remove-Item $BrowserSource -Recurse -Force
        }
    }
}

function Invoke-PlaywrightInstall {
    param(
        [string]$PythonExe,
        [string[]]$Browsers,
        [AllowEmptyString()][string]$DownloadHost
    )
    if ($DownloadHost) {
        $env:PLAYWRIGHT_DOWNLOAD_HOST = $DownloadHost
        Write-Host "Using Playwright download host: $DownloadHost"
    } else {
        Remove-Item Env:\PLAYWRIGHT_DOWNLOAD_HOST -ErrorAction SilentlyContinue
        Write-Host "Using Playwright default download hosts."
    }
    $oldErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $PythonExe -m playwright install @Browsers
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorAction
    }
    if ($exitCode -ne 0) {
        throw "Playwright install failed for: $($Browsers -join ', '). Host: $DownloadHost. Exit code: $exitCode"
    }
}

function Try-PlaywrightInstall {
    param(
        [string]$PythonExe,
        [string[]]$Browsers,
        [AllowEmptyString()][string]$DownloadHost
    )
    Clear-IncompletePlaywrightBrowsers $PythonExe
    try {
        Invoke-PlaywrightInstall -PythonExe $PythonExe -Browsers $Browsers -DownloadHost $DownloadHost
    } catch {
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        return $null
    }

    $BrowserSource = Get-PlaywrightBrowserSource $PythonExe
    $BrowserExe = Find-BrowserExecutable $BrowserSource
    if ($BrowserExe) {
        return $BrowserExe
    }

    Write-Host "Playwright install completed, but no browser executable was found under $BrowserSource." -ForegroundColor Yellow
    return $null
}

function Ensure-PlaywrightBrowsers($PythonExe) {
    $env:PLAYWRIGHT_BROWSERS_PATH = "0"

    foreach ($browser in @("chromium", "chromium-headless-shell")) {
        foreach ($downloadHost in $PlaywrightDownloadHosts) {
            $BrowserExe = Try-PlaywrightInstall -PythonExe $PythonExe -Browsers @($browser) -DownloadHost $downloadHost
            if ($BrowserExe) {
                $Script:BundledPlaywrightBrowserSource = Get-PlaywrightBrowserSource $PythonExe
                $Script:BundledPlaywrightBrowserExe = $BrowserExe
                Write-Host "Installed Playwright browser:"
                Write-Host $BrowserExe -ForegroundColor Green
                return
            }
        }
    }

    $SystemBrowser = Find-SystemBrowserExecutable
    if ($SystemBrowser) {
        Write-Host "Playwright browser installation failed from all configured download hosts." -ForegroundColor Yellow
        Write-Host "A system browser was found and will be used at runtime:"
        Write-Host $SystemBrowser -ForegroundColor Green
        return
    }

    Write-Host "Playwright browser installation failed and no system Edge/Chrome was found." -ForegroundColor Yellow
    Write-Host "The app can still be built, but browser fallback will require Edge or Chrome on the target Windows machine." -ForegroundColor Yellow
}

function Copy-PlaywrightBrowsers($PythonExe) {
    $BrowserSource = $Script:BundledPlaywrightBrowserSource
    if (-not $BrowserSource) {
        $BrowserSource = Get-PlaywrightBrowserSource $PythonExe
    }
    if (-not $BrowserSource) {
        Write-Host "Playwright browser folder was not found. Browser fallback will use system Edge/Chrome." -ForegroundColor Yellow
        return
    }

    $BrowserExe = Find-BrowserExecutable $BrowserSource
    if (-not $BrowserExe) {
        $SystemBrowser = Find-SystemBrowserExecutable
        if ($SystemBrowser) {
            Write-Host "Playwright Chromium was not found in $BrowserSource." -ForegroundColor Yellow
            Write-Host "Skipping bundled browser copy; runtime will use system browser:"
            Write-Host $SystemBrowser -ForegroundColor Green
            return
        }
        Write-Host "Playwright Chromium was not found in $BrowserSource, and no system Edge/Chrome was found." -ForegroundColor Yellow
        Write-Host "Skipping bundled browser copy. Install Edge/Chrome on the target Windows machine if browser fallback is needed." -ForegroundColor Yellow
        return
    }

    $BrowserDest = Join-Path $ProjectRoot "dist\GovPolicyWeekly\_internal\playwright\driver\package\.local-browsers"
    if (Test-Path $BrowserDest) {
        Remove-Item $BrowserDest -Recurse -Force
    }
    New-Item -ItemType Directory -Path $BrowserDest | Out-Null
    robocopy $BrowserSource $BrowserDest /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to copy Playwright browsers. Robocopy exit code: $LASTEXITCODE"
    }

    $BundledBrowserExe = Find-BrowserExecutable $BrowserDest
    if (-not $BundledBrowserExe) {
        throw "Playwright browser copy finished, but no browser executable exists in $BrowserDest."
    }
    Write-Host "Bundled Playwright browser:"
    Write-Host $BundledBrowserExe -ForegroundColor Green
}

function Show-DistSizeReport {
    $DistRoot = Join-Path $ProjectRoot "dist\GovPolicyWeekly"
    if (-not (Test-Path $DistRoot)) {
        return
    }
    Write-Step "Size report"
    $files = Get-ChildItem $DistRoot -Recurse -File -ErrorAction SilentlyContinue
    $total = ($files | Measure-Object -Property Length -Sum).Sum
    Write-Host "Dist folder size: $(Format-Size $total)"

    $groups = $files | ForEach-Object {
        $relative = $_.FullName.Substring($DistRoot.Length).TrimStart("\")
        $top = $relative.Split("\")[0]
        [PSCustomObject]@{ Top = $top; Length = $_.Length }
    } | Group-Object Top | ForEach-Object {
        [PSCustomObject]@{
            Path = $_.Name
            Bytes = ($_.Group | Measure-Object -Property Length -Sum).Sum
        }
    } | Sort-Object Bytes -Descending | Select-Object -First 12

    foreach ($group in $groups) {
        Write-Host ("{0,10}  {1}" -f (Format-Size $group.Bytes), $group.Path)
    }
}

Write-Step "Checking Python"
$PythonCommand = Ensure-Python
$PythonCommand = @($PythonCommand)[-1]
& $PythonCommand --version

Write-Step "Creating virtual environment"
$BuildPython = $null
try {
    $ExistingVenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if ((Test-Path $ExistingVenvPython) -and (-not (Test-PythonCommand $ExistingVenvPython))) {
        Write-Host "Existing .venv Python cannot run. Recreating .venv."
        Remove-Item ".venv" -Recurse -Force
    }
    if (-not (Test-Path ".venv")) {
        & $PythonCommand -m venv .venv
    }
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if ((Test-Path $VenvPython) -and (Test-PythonCommand $VenvPython)) {
        $BuildPython = $VenvPython
    }
} catch {
    Write-Host "Virtual environment creation failed. Using local Python directly."
}
if (-not $BuildPython) {
    $BuildPython = $PythonCommand
}

Write-Step "Installing Python packages"
Ensure-Pip $BuildPython
& $BuildPython -m pip install --upgrade pip -i $PipIndexUrl
& $BuildPython -m pip install -r requirements-windows-build.txt -i $PipIndexUrl

if (-not $SkipPlaywrightBrowser) {
    Write-Step "Installing bundled Playwright Chromium"
    Ensure-PlaywrightBrowsers $BuildPython
}

Write-Step "Building Windows executable"
if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}
if (Test-Path "dist\GovPolicyWeekly") {
    Remove-Item "dist\GovPolicyWeekly" -Recurse -Force
}
& $BuildPython -m PyInstaller GovPolicyWeekly.spec --clean --noconfirm

if (-not $SkipPlaywrightBrowser) {
    Write-Step "Copying Playwright Chromium into executable folder"
    Copy-PlaywrightBrowsers $BuildPython
}

if ($BundleLibreOffice) {
    Write-Step "Bundling LibreOffice into dist folder"
    $LibreOfficePath = Ensure-LibreOffice
    $Dest = Join-Path $ProjectRoot "dist\GovPolicyWeekly\LibreOffice"
    if (Test-Path $Dest) {
        Remove-Item $Dest -Recurse -Force
    }
    robocopy $LibreOfficePath $Dest /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to copy LibreOffice. Robocopy exit code: $LASTEXITCODE"
    }
}

$PortableZip = Join-Path $ProjectRoot "GovPolicyWeekly_windows_portable.zip"
if (Test-Path $PortableZip) {
    Remove-Item $PortableZip -Force
}
Compress-Archive -Path (Join-Path $ProjectRoot "dist\GovPolicyWeekly\*") -DestinationPath $PortableZip -Force
Show-DistSizeReport

if ($BuildInstaller) {
    Write-Step "Building installer with Inno Setup"
    if (-not (Get-Command iscc -ErrorAction SilentlyContinue)) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        }
    }
    $Iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        $CommonIscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if (Test-Path $CommonIscc) {
            $Iscc = $CommonIscc
        }
    }
    if (-not $Iscc) {
        throw "Inno Setup compiler was not found. Install Inno Setup 6, then rerun with -BuildInstaller."
    }
    & $Iscc GovPolicyWeekly.iss
}

Write-Step "Build complete"
Write-Host "Executable folder:"
Write-Host (Join-Path $ProjectRoot "dist\GovPolicyWeekly") -ForegroundColor Green
Write-Host ""
Write-Host "Run:"
Write-Host (Join-Path $ProjectRoot "dist\GovPolicyWeekly\GovPolicyWeekly.exe") -ForegroundColor Green
Write-Host ""
Write-Host "Portable zip:"
Write-Host $PortableZip -ForegroundColor Green
Write-Host ""
Write-Host "PDF note: PDF can be generated directly by reportlab. LibreOffice is optional only for DOCX-to-PDF conversion."
if ($BundleLibreOffice) {
    Write-Host "LibreOffice was bundled into the app folder." -ForegroundColor Green
}
if ($BuildInstaller) {
    Write-Host "Installer output folder:"
    Write-Host (Join-Path $ProjectRoot "installer_output") -ForegroundColor Green
}
