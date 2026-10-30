; Build all 3 apps using build/build.py on Windows, then compile with Inno Setup 6.
#define MyAppVersion "1.0.0"
[Setup]
AppId={{6E587271-9588-4E51-809B-5915FAE20510}
AppName=SCV Suite
AppVersion={#MyAppVersion}
AppPublisher=Mattia Mascarello
DefaultDirName={autopf}\SCV Suite
DefaultGroupName=SCV Suite
OutputBaseFilename=SCV-Suite-1.0-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName=SCV Suite
[Files]
Source: "..\..\dist\SCV-Encoder\*"; DestDir: "{app}\SCV-Encoder"; Flags: recursesubdirs createallsubdirs
Source: "..\..\dist\SCV-Player\*"; DestDir: "{app}\SCV-Player"; Flags: recursesubdirs createallsubdirs
Source: "..\..\dist\SCV-Exporter\*"; DestDir: "{app}\SCV-Exporter"; Flags: recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SCV Encoder"; Filename: "{app}\SCV-Encoder\SCV-Encoder.exe"
Name: "{group}\SCV Player"; Filename: "{app}\SCV-Player\SCV-Player.exe"
Name: "{group}\SCV Exporter"; Filename: "{app}\SCV-Exporter\SCV-Exporter.exe"
[Registry]
Root: HKA; Subkey: "Software\Classes\.scv"; ValueType: string; ValueName: ""; ValueData: "SCV.Lecture"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\SCV.Lecture"; ValueType: string; ValueName: ""; ValueData: "SCV Lecture"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SCV.Lecture\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\SCV-Player\SCV-Player.exe"" ""%1"""
[Run]
Filename: "{app}\SCV-Player\SCV-Player.exe"; Description: "Launch SCV Player"; Flags: nowait postinstall skipifsilent
