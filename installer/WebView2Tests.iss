// Compiles the production prerequisite policy with deterministic adapters.
// Never installs/repairs/uninstalls WebView2 or changes its registry entries.
[Setup]
AppName=Engine Arena WebView2 regression checks
AppVersion=1
DefaultDirName={tmp}\ArenaWebViewTests
CreateAppDir=no
Uninstallable=no
PrivilegesRequired=lowest
OutputDir=..\build\installer-tests
OutputBaseFilename=WebView2Tests
SetupLogging=yes

[Files]
Source: "..\build\installer-tools\ArenaWebViewProbe.dll"; Flags: dontcopy

[Code]
#include "WebView2Probe.iss"

var
  Before, After, Launched: Boolean;
  ExitCode, ProbeCalls, InstallerCalls, Passed: Integer;

function RuntimeAvailable: Boolean;
begin
  ProbeCalls := ProbeCalls + 1;
  if ProbeCalls = 1 then Result := Before else Result := After;
end;

function RunRuntimeInstaller(var Code: Integer): Boolean;
begin
  InstallerCalls := InstallerCalls + 1;
  Code := ExitCode;
  Result := Launched;
end;

#include "WebView2Policy.iss"

procedure CheckCase(Name: String; HasBefore, HasAfter, Repair, Launch: Boolean;
  Code: Integer; ExpectedSuccess, ExpectedRestart: Boolean; ExpectedCalls: Integer);
var
  Restart: Boolean;
  Error: String;
begin
  Before := HasBefore; After := HasAfter; Launched := Launch; ExitCode := Code;
  ProbeCalls := 0; InstallerCalls := 0; Restart := False;
  Error := EnsureWebView2(Repair, Restart);
  if ((Error = '') <> ExpectedSuccess) or (Restart <> ExpectedRestart) or
      (InstallerCalls <> ExpectedCalls) then
    RaiseException('FAILED ' + Name + ': ' + Error);
  if (Code = -2147219416) and not ExpectedSuccess and (Pos('already installed', Error) = 0) then
    RaiseException('Missing already-installed diagnostic');
  Passed := Passed + 1;
  Log('PASSED: ' + Name);
end;

function InitializeSetup: Boolean;
var
  ExpectedAvailable: Boolean;
begin
  CheckCase('existing runtime skips install', True, True, False, True, 0, True, False, 0);
  CheckCase('missing runtime installs and is detected', False, True, False, True, 0, True, False, 1);
  CheckCase('repair already-installed runtime succeeds', True, True, True, True, -2147219416, True, False, 1);
  CheckCase('already-installed race rechecks successfully', False, True, False, True, -2147219416, True, False, 1);
  CheckCase('broken already-installed runtime remains blocked', False, False, False, True, -2147219416, False, False, 1);
  CheckCase('success code without runtime remains blocked', False, False, False, True, 0, False, False, 1);
  CheckCase('unknown error is not ignored', True, True, True, True, 1603, False, False, 1);
  CheckCase('restart-required is preserved', False, True, False, True, 3010, False, True, 1);
  CheckCase('installer launch failure is reported', False, False, False, False, 2, False, False, 1);
  CheckCase('ordinary repair succeeds', True, True, True, True, 0, True, False, 1);
  ExpectedAvailable := ExpandConstant('{param:EXPECTAVAILABLE|1}') = '1';
  if ProbeWebViewRuntime <> ExpectedAvailable then RaiseException('Real WebView2 loader probe mismatch');
  Log(Format('WEBVIEW_REGRESSION_PASS: %d policy cases plus real loader probe', [Passed]));
  Result := False; // End without making an installation.
end;
