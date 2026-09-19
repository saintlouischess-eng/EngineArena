// Inno Setup 6 is a 32-bit process, including in 64-bit installation mode.
// Use the SDK's x86 loader here; the installed x64 application has its own loader.
function AvailableBrowserVersion(Folder: Longword; var Version: Longword): Integer;
  external 'GetAvailableCoreWebView2BrowserVersionString@files:ArenaWebViewProbe.dll stdcall delayload setuponly';
procedure FreeBrowserVersion(Version: Longword);
  external 'CoTaskMemFree@ole32.dll stdcall';

function ProbeWebViewRuntime: Boolean;
var
  Version: Longword;
  Status: Integer;
begin
  Result := False;
  Version := 0;
  try
    try
      Status := AvailableBrowserVersion(0, Version);
      Result := (Status >= 0) and (Version <> 0);
      Log(Format('WebView2 loader probe: HRESULT %d, available=%d', [Status, Ord(Result)]));
    except
      Log('WebView2 loader probe failed: ' + GetExceptionMessage);
    end;
  finally
    if Version <> 0 then FreeBrowserVersion(Version);
  end;
end;
