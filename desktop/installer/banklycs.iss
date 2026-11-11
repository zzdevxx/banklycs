; Banklycs v2.1.0 — Inno Setup script
; Per-user install (no UAC), LZMA2 max compression.
; Compile: ISCC.exe banklycs.iss  (payload must exist in dist\staging\)

#define MyAppName "Banklycs"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "zzdevxx"
#define MyAppExeName "Banklycs.App.exe"
#define MyAppID "{{8F4A2D61-9C3E-4B7A-A1D5-2E6F80B3C942}}"

[Setup]
AppId={#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Banklycs-Setup-{#MyAppVersion}
SetupIconFile=..\app.ico
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Messages]
WelcomeLabel2=Ini akan memasang [name/ver] di komputer Anda.%n%nBanklycs adalah Studio Console untuk ProPresenter 7:%n24.520 lagu rohani siap tayang, satu klik inject.%n%nKlik Next untuk melanjutkan.
FinishedLabelNoIcons=[name] telah terpasang.%n%nBuka dari shortcut di Desktop atau Start Menu.

[Files]
Source: "..\dist\staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di &Desktop"; GroupDescription: "Shortcut:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan {#MyAppName} sekarang"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; bersihkan file runtime yang dibuat engine saat dipakai (last_port.txt, dsb.)
Type: filesandordirs; Name: "{app}\engine"
