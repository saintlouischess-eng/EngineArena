#ifndef PayloadDir
  #define PayloadDir "..\build\installer-payload"
#endif
#ifndef RuntimeInstaller
  #define RuntimeInstaller "..\optional-components\WebView2\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"
#endif
#ifndef WebViewLoader
  #define WebViewLoader "..\build\installer-tools\ArenaWebViewProbe.dll"
#endif

[Setup]
AppId={{579ABF77-881B-49B9-ACE4-E7D302683E37}
AppName=Engine Arena
AppVersion=0.2.0-beta.2
AppVerName=Engine Arena 0.2.0 Beta 2
AppPublisher=Engine Arena
AppPublisherURL=https://github.com/saintlouischess-eng/EngineArena
AppSupportURL=https://github.com/saintlouischess-eng/EngineArena/issues
AppUpdatesURL=https://github.com/saintlouischess-eng/EngineArena/releases
DefaultDirName={localappdata}\Programs\Engine Arena
DefaultGroupName=Engine Arena
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.22000
AppMutex=Local\EngineArena.Desktop.Active
SetupMutex=Local\EngineArena.Setup.Active
CloseApplications=no
RestartApplications=no
UninstallDisplayIcon={app}\EngineArena.exe
OutputDir=..\release
OutputBaseFilename=EngineArenaSetup-0.2.0-beta.2-win-x64
VersionInfoVersion=0.2.0.2
Compression=lzma2
SolidCompression=yes
DiskSpanning=no
WizardStyle=modern
SetupLogging=yes
InfoBeforeFile=beta-info.txt
UninstallLogMode=append

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "repairwebview"; Description: "Run Microsoft WebView2 setup again (usually unnecessary)"; GroupDescription: "Optional runtime setup:"; Flags: unchecked

[Files]
Source: "{#WebViewLoader}"; Flags: dontcopy
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RuntimeInstaller}"; Flags: dontcopy

[Icons]
Name: "{group}\Engine Arena"; Filename: "{app}\EngineArena.exe"; WorkingDir: "{app}"
Name: "{group}\Beta testing guide"; Filename: "{app}\docs\BETA_TESTING.html"
Name: "{group}\Uninstall Engine Arena"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Engine Arena"; Filename: "{app}\EngineArena.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Optional\PawnIO_setup.exe"; Description: "Set up optional CPU temperature and core-clock driver (administrator approval)"; Flags: postinstall unchecked shellexec waituntilterminated skipifsilent
Filename: "{app}\EngineArena.exe"; Description: "Launch Engine Arena"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent

[Code]
#include "WebView2Probe.iss"

const
  WebViewKey = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasRuntimeVersion(Root: Integer): Boolean;
var
  Version: String;
  Packed: Int64;
begin
  Result := RegQueryStringValue(Root, WebViewKey, 'pv', Version);
  if Result then
    Result := StrToVersion(Version, Packed) and (Packed > 0);
end;

function RuntimeAvailable: Boolean;
begin
  // Registry state is diagnostic only: stale/missing registration must not
  // override the same loader API used by the actual desktop application.
  Log(Format('WebView2 registry versions: machine32=%d machine64=%d user32=%d user64=%d', [
     Ord(HasRuntimeVersion(HKLM32)), Ord(HasRuntimeVersion(HKLM64)),
     Ord(HasRuntimeVersion(HKCU32)), Ord(HasRuntimeVersion(HKCU64))]));
  Result := ProbeWebViewRuntime;
end;

function RunRuntimeInstaller(var Code: Integer): Boolean;
begin
  WizardForm.StatusLabel.Caption := 'Installing Microsoft Edge WebView2 Runtime...';
  ExtractTemporaryFile('MicrosoftEdgeWebView2RuntimeInstallerX64.exe');
  Result := Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'),
      '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

#include "WebView2Policy.iss"

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := EnsureWebView2(WizardIsTaskSelected('repairwebview'), NeedsRestart);
end;

procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := 'Install Engine Arena 0.2.0 Beta 2 for this Windows account.' + #13#10#13#10 +
    'The app, Python, .NET and the offline Microsoft WebView2 installer are included. Chess engines and opening books are added separately.' + #13#10#13#10 +
    'Close Engine Arena before updating. Existing tournaments and settings are preserved.';
end;
