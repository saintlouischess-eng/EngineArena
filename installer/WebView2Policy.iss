// The two adapters are supplied by setup, or by the compiled regression harness.
// Only a successful loader probe can satisfy the prerequisite.
function EnsureWebView2(RepairRequested: Boolean; var NeedsRestart: Boolean): String;
var
  Code: Integer;
  Available: Boolean;
begin
  Result := '';
  if RuntimeAvailable and not RepairRequested then begin
    Log('WebView2 is available; bundled runtime installer skipped.');
    exit;
  end;
  if not RunRuntimeInstaller(Code) then begin
    Result := 'Could not start the included Microsoft WebView2 installer. ' + SysErrorMessage(Code);
    exit;
  end;
  Log(Format('WebView2 installer exit code: %d', [Code]));
  if Code = 3010 then begin
    NeedsRestart := True;
    Result := 'WebView2 needs a Windows restart. Restart Windows, then run EngineArenaSetup again. Your tournament data is preserved.';
    exit;
  end;
  Available := RuntimeAvailable;
  if ((Code = 0) or (Code = -2147219416)) and Available then begin
    if Code = -2147219416 then
      Log('Microsoft reports WebView2 already installed (0x80040828); loader probe passed. Continuing setup.');
    exit;
  end;
  if Code = -2147219416 then
    Result := 'Microsoft reports WebView2 is already installed (0x80040828), but its runtime could not be detected for this Windows account. Repair Microsoft Edge WebView2 Runtime using Windows Installed apps or Microsoft''s WebView2 installer, then retry Engine Arena setup.'
  else
    Result := Format('WebView2 setup did not finish (code %d). The runtime was not accepted. Retry setup after repairing WebView2.', [Code]);
  Result := Result + #13#10#13#10 + 'Your tournament data was not changed. For support, include this setup log: ' + ExpandConstant('{log}');
end;
