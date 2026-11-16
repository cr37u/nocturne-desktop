<#
.SYNOPSIS
  Builds Nocturne for Windows: PyInstaller onedir -> portable .zip + Inno Setup installer.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -SkipInstaller

  Output (dist\):
    Nocturne\                         onedir build
    Nocturne-<ver>-windows-portable.zip
    NocturneSetup-<ver>.exe
#>
param(
    [switch]$SkipInstaller,
    [string]$Python = "py -3.12"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Invoke-Checked([string]$what, [scriptblock]$block) {
    Write-Host "==> $what" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

# 1. Virtual environment with pinned dependencies
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Checked "Create venv" { Invoke-Expression "$Python -m venv .venv" }
}
$Py = Join-Path $Root ".venv\Scripts\python.exe"
Invoke-Checked "Install dependencies" { & $Py -m pip install --disable-pip-version-check -q -r requirements-build.txt }

# 2. Generated assets: icons, version resource, translations
Invoke-Checked "Generate assets" { & $Py tools\make_assets.py }
Invoke-Checked "Compile translations" { & $Py tools\i18n_tool.py release }

$Version = (& $Py -c "import nocturne; print(nocturne.__version__)").Trim()
Write-Host "Nocturne $Version"

# 3. PyInstaller onedir
Invoke-Checked "PyInstaller" {
    & $Py -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\nocturne-windows.spec
}

# 4. Portable zip
$Zip = "dist\Nocturne-$Version-windows-portable.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Write-Host "==> Portable zip" -ForegroundColor Cyan
Compress-Archive -Path "dist\Nocturne" -DestinationPath $Zip -CompressionLevel Optimal

# 5. Inno Setup installer
if (-not $SkipInstaller) {
    $Iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) {
        $cmd = Get-Command iscc -ErrorAction SilentlyContinue
        if ($cmd) { $Iscc = $cmd.Source }
    }
    if (-not $Iscc) { throw "Inno Setup 6 not found. Install it: winget install JRSoftware.InnoSetup" }
    Invoke-Checked "Inno Setup" { & $Iscc "/DAppVersion=$Version" "packaging\nocturne.iss" }
}

Write-Host ""
Write-Host "Done:" -ForegroundColor Green
Get-ChildItem dist -File | ForEach-Object { Write-Host ("  {0}  ({1:N1} MB)" -f $_.Name, ($_.Length / 1MB)) }
