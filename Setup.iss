; KyZer YouBe per-user installer
#define MyAppName "KyZer YouBe"
#define MyAppVersion "2.0.2"
#define MyAppPublisher "KyZer_HADOC"
#define MyAppExeName "KyZer YouBe.exe"

[Setup]
AppId={{C1A6E9AA-BB0F-4D2B-95A5-78E442F065A3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\KyZer YouBe
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=KyZer-YouBe-Setup
SetupIconFile=KyZer YouBe.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes
RestartApplications=no
Uninstallable=yes
VersionInfoVersion=2.0.2.0
VersionInfoProductName=KyZer YouBe
VersionInfoCompany=KyZer_HADOC
VersionInfoDescription=KyZer YouBe Windows Installer

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\KyZer YouBe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\KyZer YouBe"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\KyZer YouBe"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch KyZer YouBe"; Flags: nowait postinstall skipifsilent
