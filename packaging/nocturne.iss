; Inno Setup script — NocturneSetup-x.y.z.exe
;   iscc /DAppVersion=1.0.0 packaging\nocturne.iss
; Expects the PyInstaller onedir output in dist\Nocturne.
; Registers the nocturne:// protocol (used by toasts and the Win+W widget bridge).
; This edition has the desktop widget; the Windows 11 Widgets board needs the MSIX edition.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Nocturne"
#define AppExe "Nocturne.exe"
#define RootDir ".."

[Setup]
AppId={{6B3F1C52-6E2D-4C1B-9B5E-4F3E7B7A9C11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Nocturne
DefaultDirName={localappdata}\Programs\Nocturne
DefaultGroupName=Nocturne
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#RootDir}\dist
OutputBaseFilename=NocturneSetup-{#AppVersion}
SetupIconFile={#RootDir}\nocturne\assets\icons\nocturne.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "romanian"; MessagesFile: "innosetup\Romanian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
romanian.StartWithWindows=Pornește Nocturne cu Windows
english.StartWithWindows=Start Nocturne with Windows
russian.StartWithWindows=Запускать Nocturne вместе с Windows
romanian.LaunchNow=Pornește Nocturne acum
english.LaunchNow=Launch Nocturne now
russian.LaunchNow=Запустить Nocturne

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#RootDir}\dist\Nocturne\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nocturne"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Nocturne.MusicPlayer"
Name: "{group}\{cm:UninstallProgram,Nocturne}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Nocturne"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "Nocturne.MusicPlayer"

[Registry]
; nocturne:// protocol
Root: HKCU; Subkey: "Software\Classes\nocturne"; ValueType: string; ValueName: ""; ValueData: "URL:Nocturne"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\nocturne"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\nocturne\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"
Root: HKCU; Subkey: "Software\Classes\nocturne\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
; Toast notifications identity
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\Nocturne.MusicPlayer"; ValueType: string; ValueName: "DisplayName"; ValueData: "Nocturne"; Flags: uninsdeletekey
; Optional autostart (the in-app setting edits the same value)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Nocturne"; ValueData: """{app}\{#AppExe}"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchNow}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "KillNocturne"

[UninstallDelete]
Type: dirifempty; Name: "{app}"
