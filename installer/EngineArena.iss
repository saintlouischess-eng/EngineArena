#ifndef PayloadDir
  #define PayloadDir "..\build\installer-payload"
#endif
#ifndef RuntimeInstaller
  #define RuntimeInstaller "..\optional-components\WebView2\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"
#endif

[Setup]
AppId={{579ABF77-881B-49B9-ACE4-E7D302683E37}
AppName=Engine Arena
AppVersion=0.2.0-beta.1
AppVerName=Engine Arena 0.2.0 Beta 1
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
OutputBaseFilename=EngineArenaSetup-0.2.0-beta.1-win-x64
VersionInfoVersion=0.2.0.1
Compression=lzma2
SolidCompression=yes
DiskSpanning=no
WizardStyle=modern
SetupLogging=yes
InfoBeforeFile=beta-info.txt
UninstallLogMode=append

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "repairwebview"; Description: "Repair or update WebView2 using the included Microsoft installer"; GroupDescription: "Optional repair:"; Flags: unchecked

[Files]
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

function WebViewInstalled: Boolean;
begin
  Result := HasRuntimeVersion(HKLM32) or HasRuntimeVersion(HKCU32) or HasRuntimeVersion(HKCU64);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Result := '';
  if WebViewInstalled and not WizardIsTaskSelected('repairwebview') then begin
    Log('WebView2 is already installed; bundled runtime installer skipped.');
    exit;
  end;
  WizardForm.StatusLabel.Caption := 'Installing Microsoft Edge WebView2 Runtime...';
  ExtractTemporaryFile('MicrosoftEdgeWebView2RuntimeInstallerX64.exe');
  if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'),
      '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, Code) then begin
    Result := 'Could not start the included Microsoft WebView2 installer. ' + SysErrorMessage(Code);
    exit;
  end;
  Log(Format('WebView2 installer exit code: %d', [Code]));
  if Code = 3010 then begin
    NeedsRestart := True;
    Result := 'WebView2 needs a Windows restart. Restart Windows, then run EngineArenaSetup again. Your tournament data is preserved.';
    exit;
  end;
  if (Code <> 0) or not WebViewInstalled then
    Result := Format('WebView2 setup did not finish (code %d). Restart Windows and retry setup. No tournament data was changed.', [Code]);
end;

procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := 'Install Engine Arena 0.2.0 Beta 1 for this Windows account.' + #13#10#13#10 +
    'The app, Python, .NET and the offline Microsoft WebView2 installer are included. Chess engines and opening books are added separately.' + #13#10#13#10 +
    'Close Engine Arena before updating. Existing tournaments and settings are preserved.';
end;
