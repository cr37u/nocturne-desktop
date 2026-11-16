<#
.SYNOPSIS
  Builds the "full" Windows edition of Nocturne as ONE MSIX (Python app + Win+W widget bridge),
  signs it with a free self-signed certificate and installs it for personal use.

.DESCRIPTION
  1. PyInstaller onedir (packaging\nocturne-windows.spec)      -> layout\Nocturne\
  2. dotnet publish widget-bridge (self-contained .NET 8)        -> layout\WidgetBridge\
  3. AppxManifest.xml (+ Assets, Public)                         -> layout\
  4. makeappx pack                                               -> dist\Nocturne-<ver>.msix
  5. Self-signed certificate "CN=Nocturne Dev" (created once, reused), signtool sign
  6. Trust the certificate (LocalMachine\TrustedPeople, one UAC prompt) and Add-AppxPackage
     together with the Windows App Runtime framework package it depends on.

.PARAMETER NoInstall      Build and sign only.
.PARAMETER SkipPyInstaller Reuse an existing dist\Nocturne.
.PARAMETER TestCert       CI mode: create a throw-away certificate, do not trust/install.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File packaging\msix\build_msix.ps1
#>
param(
    [switch]$NoInstall,
    [switch]$SkipPyInstaller,
    [switch]$TestCert,
    [string]$Publisher = "CN=Nocturne Dev",
    [string]$CertPassword = "nocturne"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$MsixDir = Join-Path $Root "packaging\msix"
$Layout = Join-Path $Root "build\msix\layout"
$Py = Join-Path $Root ".venv\Scripts\python.exe"

function Step([string]$what) { Write-Host "==> $what" -ForegroundColor Cyan }
function Check([string]$what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

# --- dotnet -------------------------------------------------------------------------------
$Dotnet = (Get-Command dotnet -ErrorAction SilentlyContinue).Source
if (-not $Dotnet -and (Test-Path "$env:ProgramFiles\dotnet\dotnet.exe")) { $Dotnet = "$env:ProgramFiles\dotnet\dotnet.exe" }
if (-not $Dotnet) { throw ".NET 8 SDK not found. Install it: winget install Microsoft.DotNet.SDK.8" }
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"

# --- 1. Python app ------------------------------------------------------------------------
if (-not $SkipPyInstaller -or -not (Test-Path "dist\Nocturne\Nocturne.exe")) {
    Step "Building the Python app (build_windows.ps1 -SkipInstaller)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "packaging\build_windows.ps1") -SkipInstaller
    Check "build_windows.ps1"
}
$Version = (& $Py -c "import nocturne; print(nocturne.__version__)").Trim()
$MsixVersion = "$Version.0"

# --- 2. Widget bridge ---------------------------------------------------------------------
Step "Publishing the widget bridge"
if (Test-Path $Layout) { Remove-Item -Recurse -Force $Layout }
New-Item -ItemType Directory -Force $Layout | Out-Null
& $Dotnet publish (Join-Path $Root "widget-bridge\NocturneWidgetBridge.csproj") -c Release -r win-x64 --self-contained true -nologo -o (Join-Path $Layout "WidgetBridge")
Check "dotnet publish"

# --- Tools from NuGet (Windows SDK build tools + Windows App Runtime) --------------------
$NuGet = Join-Path $Root "build\nuget"
$MakeAppx = Get-ChildItem $NuGet -Recurse -Filter makeappx.exe | Where-Object { $_.FullName -match "\\x64\\" } | Select-Object -First 1
$SignTool = Get-ChildItem $NuGet -Recurse -Filter signtool.exe | Where-Object { $_.FullName -match "\\x64\\" } | Select-Object -First 1
if (-not $MakeAppx -or -not $SignTool) { throw "makeappx/signtool not found under build\nuget (restore of widget-bridge failed?)" }
$RuntimeMsix = Get-ChildItem $NuGet -Recurse -Filter "Microsoft.WindowsAppRuntime.*.msix" |
    Where-Object { $_.FullName -match "win10-x64" -and $_.Name -match "^Microsoft\.WindowsAppRuntime\.\d+\.\d+\.msix$" } |
    Select-Object -First 1
if (-not $RuntimeMsix) { throw "Windows App Runtime framework .msix not found in the NuGet cache" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($RuntimeMsix.FullName)
try {
    $entry = $zip.Entries | Where-Object { $_.FullName -eq "AppxManifest.xml" }
    $reader = New-Object System.IO.StreamReader($entry.Open())
    [xml]$rtManifest = $reader.ReadToEnd()
    $reader.Close()
} finally { $zip.Dispose() }
$RtName = $rtManifest.Package.Identity.Name
$RtVersion = $rtManifest.Package.Identity.Version
Write-Host "Windows App Runtime dependency: $RtName $RtVersion"

# --- 3. Layout ----------------------------------------------------------------------------
Step "Assembling the package layout"
Copy-Item -Recurse "dist\Nocturne" (Join-Path $Layout "Nocturne")
Copy-Item -Recurse (Join-Path $MsixDir "Assets") (Join-Path $Layout "Assets")
New-Item -ItemType Directory -Force (Join-Path $Layout "Public") | Out-Null
Set-Content (Join-Path $Layout "Public\README.txt") "Nocturne widget provider" -Encoding utf8
$manifest = Get-Content (Join-Path $MsixDir "AppxManifest.xml") -Raw
$manifest = $manifest.Replace("{{PUBLISHER}}", $Publisher).Replace("{{VERSION}}", $MsixVersion)
$manifest = $manifest.Replace("{{WINAPPRUNTIME_NAME}}", $RtName).Replace("{{WINAPPRUNTIME_VERSION}}", $RtVersion)
[IO.File]::WriteAllText((Join-Path $Layout "AppxManifest.xml"), $manifest, (New-Object Text.UTF8Encoding $false))

# resources.pri: lets Windows pick the scale/targetsize/"unplated" logo variants
# (without it the taskbar and Start show the icon on a grey/accent plate).
Step "makepri (logo resources)"
$MakePri = Join-Path $MakeAppx.DirectoryName "makepri.exe"
$PriRoot = Join-Path $Root "build\msix\pri"
if (Test-Path $PriRoot) { Remove-Item -Recurse -Force $PriRoot }
New-Item -ItemType Directory -Force $PriRoot | Out-Null
Copy-Item -Recurse (Join-Path $MsixDir "Assets") (Join-Path $PriRoot "Assets")
Copy-Item (Join-Path $Layout "AppxManifest.xml") (Join-Path $PriRoot "AppxManifest.xml")
$PriConfig = Join-Path $PriRoot "priconfig.xml"
& $MakePri createconfig /cf $PriConfig /dq "en-US_ro-RO_ru-RU" /pv 10.0.0 /o | Out-Null
Check "makepri createconfig"
& $MakePri new /pr $PriRoot /cf $PriConfig /mn (Join-Path $PriRoot "AppxManifest.xml") /of (Join-Path $Layout "resources.pri") /o
Check "makepri new"

# --- 4. Pack --------------------------------------------------------------------------------
Step "makeappx pack"
New-Item -ItemType Directory -Force "dist" | Out-Null
$Msix = Join-Path $Root "dist\Nocturne-$Version.msix"
& $MakeAppx.FullName pack /d $Layout /p $Msix /o
Check "makeappx"

# --- 5. Certificate + sign ------------------------------------------------------------------
Step "Signing"
$Pfx = Join-Path $MsixDir "NocturneDev.pfx"
$Cer = Join-Path $MsixDir "NocturneDev.cer"
$Secure = ConvertTo-SecureString $CertPassword -AsPlainText -Force
if ($TestCert -or -not (Test-Path $Pfx)) {
    $cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature `
        -FriendlyName "Nocturne self-signed (personal use)" -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") -NotAfter (Get-Date).AddYears(5)
    Export-PfxCertificate -Cert $cert -FilePath $Pfx -Password $Secure | Out-Null
    Export-Certificate -Cert $cert -FilePath $Cer | Out-Null
    Write-Host "Created certificate $($cert.Thumbprint) ($Publisher)"
}
& $SignTool.FullName sign /fd SHA256 /f $Pfx /p $CertPassword $Msix
Check "signtool"

if ($NoInstall -or $TestCert) {
    Write-Host "Built: $Msix" -ForegroundColor Green
    exit 0
}

# --- 6. Trust + install ---------------------------------------------------------------------
Step "Trusting the certificate (LocalMachine\TrustedPeople - one UAC prompt)"
$thumb = (New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($Cer)).Thumbprint
$trusted = Get-ChildItem Cert:\LocalMachine\TrustedPeople | Where-Object { $_.Thumbprint -eq $thumb }
if (-not $trusted) {
    $cmd = "Import-Certificate -FilePath '$Cer' -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null"
    $p = Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList "-NoProfile", "-Command", $cmd
    if ($p.ExitCode -ne 0) { throw "Certificate import was cancelled or failed" }
}

Step "Installing"
Get-AppxPackage -Name "Nocturne.MusicPlayer" | Remove-AppxPackage -ErrorAction SilentlyContinue
$haveRuntime = Get-AppxPackage -Name $RtName | Where-Object { [version]$_.Version -ge [version]$RtVersion }
if ($haveRuntime) {
    Add-AppxPackage -Path $Msix
} else {
    Add-AppxPackage -Path $Msix -DependencyPath $RuntimeMsix.FullName
}

Write-Host ""
Write-Host "Installed Nocturne $Version (MSIX)." -ForegroundColor Green
Write-Host "Open the Widgets board (Win+W) > + (Add widgets) > Nocturne."
