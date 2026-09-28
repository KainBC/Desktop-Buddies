; Inno Setup script. Build from the repo root after PyInstaller:
;   iscc /DAppVersion=1.0.0 packaging\windows.iss
; Paths are relative to this file. Per-user install: no admin prompt.

[Setup]
AppId={{8F1C2A57-3D4B-4E8A-9C61-5B7E2D9A4F10}
AppName=Desktop Buddies
AppVersion={#AppVersion}
AppPublisher=KainBC
AppPublisherURL=https://github.com/KainBC/Desktop-Buddies
DefaultDirName={localappdata}\Programs\Desktop Buddies
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=DesktopBuddies-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\DesktopBuddies.exe
UninstallDisplayName=Desktop Buddies

[Files]
Source: "..\dist\DesktopBuddies\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Desktop Buddies"; Filename: "{app}\DesktopBuddies.exe"

[Run]
Filename: "{app}\DesktopBuddies.exe"; Description: "Launch Desktop Buddies"; Flags: nowait postinstall skipifsilent
