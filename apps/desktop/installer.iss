; Inno Setup script: packs apps/desktop/dist/LedgerLens into LedgerLens-Setup-<version>.exe
;   iscc /DAppVersion=0.1.0 installer.iss
#define AppName "LedgerLens"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6F1D5E8A-3B7C-4C0E-9A52-8D4B1E7F2C93}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Hamzo069
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Installs for the current user only, so no administrator rights are needed.
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=LedgerLens-Setup-{#AppVersion}
SetupIconFile=ledgerlens.ico
UninstallDisplayIcon={app}\LedgerLens.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(CompilerPath + "Languages\German.isl")
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\LedgerLens\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\LedgerLens.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\LedgerLens.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LedgerLens.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Uninstalling removes the program only. The user's data in %APPDATA%\LedgerLens is kept.
