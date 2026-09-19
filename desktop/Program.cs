using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using Microsoft.Win32;

namespace EngineArena;

public sealed class Program : Application
{
    // Setup checks existence, not ownership. Multiple isolated workspaces remain allowed.
    [STAThread] public static void Main()
    {
        using var installerGuard = new Mutex(false, @"Local\EngineArena.Desktop.Active");
        new Program().Run(new ArenaWindow());
        GC.KeepAlive(installerGuard);
    }
}

public sealed class ArenaWindow : Window
{
    readonly WebView2 browser = new();
    readonly HttpClient client = new() { Timeout = TimeSpan.FromSeconds(8) };
    readonly HttpClient exportClient = new() { Timeout = Timeout.InfiniteTimeSpan };
    readonly CancellationTokenSource exportCancellation = new();
    readonly ProcessJob job = new();
    readonly string sensorSession = Guid.NewGuid().ToString("N");
    Process? sensorReader;
    bool startingSensor;
    readonly TextBlock closingMessage = new() { FontSize = 18, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 18, 0, 18) };
    readonly ProgressBar closingProgress = new() { Height = 6, IsIndeterminate = true, Maximum = 100 };
    Process? worker; string token = "", origin = "", ready = ""; bool closing, shutdownComplete;
    public ArenaWindow()
    {
        Title = "Engine Arena — 0.2.0 Beta 1"; Width = 1600; Height = 1000; MinWidth = 1050; MinHeight = 700;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Background = System.Windows.Media.Brushes.Black;
        Content = new TextBlock { Text = "Starting Engine Arena…", Foreground = System.Windows.Media.Brushes.White, Margin = new Thickness(40), FontSize = 22 };
        Loaded += async (_, _) => { try { await Initialize(); } catch (Exception ex) { Content = new TextBox { Text = ex is WebView2RuntimeNotFoundException ? "Microsoft Edge WebView2 Runtime is missing.\n\nRun EngineArenaSetup again to install the included runtime, then reopen Engine Arena. Your saved tournaments are preserved." : "Engine Arena could not start.\n\n" + ex, IsReadOnly = true, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(30) }; } };
        Closing += async (_, e) =>
        {
            if (closing) { e.Cancel = !shutdownComplete; return; } e.Cancel = true; closing = true; exportCancellation.Cancel();
            Title = "Engine Arena — finishing saved games and backup…";
            var closingPanel = new StackPanel { Margin = new Thickness(48), MaxWidth = 650, VerticalAlignment = VerticalAlignment.Center };
            closingPanel.Children.Add(new TextBlock { Text = "Saving your workspace", FontSize = 28 });
            closingMessage.Text = "Finishing game records and checking the recovery backup. Large histories can take a little longer.";
            closingPanel.Children.Add(closingMessage); closingPanel.Children.Add(closingProgress);
            closingPanel.Children.Add(new TextBlock { Text = "Engine Arena will close automatically when saving finishes.", Margin = new Thickness(0, 20, 0, 0), TextWrapping = TextWrapping.Wrap });
            closingPanel.SetValue(TextBlock.ForegroundProperty, System.Windows.Media.Brushes.White);
            Content = closingPanel;
            // Large verified backups can exceed twelve seconds. Let the worker
            // finish its durable shutdown instead of killing a healthy save.
            try { if (origin.Length > 0) { using var req = new HttpRequestMessage(HttpMethod.Post, origin + "/api/shutdown"); req.Headers.Add("X-Arena-Token", token); req.Content = new StringContent("{}"); await client.SendAsync(req); } if (worker is { HasExited: false }) await worker.WaitForExitAsync(); }
            catch { if (worker is { HasExited: false }) worker.Kill(true); }
            finally { job.Dispose(); browser.Dispose(); client.Dispose(); exportClient.Dispose(); shutdownComplete = true; Close(); }
        };
        AllowDrop = true;
        DragOver += (_, e) => { e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None; e.Handled = true; };
        Drop += (_, e) => { if (e.Data.GetData(DataFormats.FileDrop) is string[] paths) browser.CoreWebView2?.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "paths", paths = paths.Where(p => p.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)).ToArray() })); };
    }
    async Task Initialize()
    {
        // Detect a missing runtime before starting a tournament worker.
        _ = CoreWebView2Environment.GetAvailableBrowserVersionString();
        var args = Environment.GetCommandLineArgs();
        var dataIndex = Array.IndexOf(args, "--data");
        var data = dataIndex >= 0 && dataIndex + 1 < args.Length ? Path.GetFullPath(args[dataIndex + 1]) : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "EngineArena", "Data");
        if (dataIndex >= 0) Title = "Engine Arena — " + new DirectoryInfo(data).Name + " · 0.2.0 Beta 1";
        Directory.CreateDirectory(data); ready = Path.Combine(data, "worker-ready.json");
        if (File.Exists(ready)) File.Delete(ready);
        var baseDir = AppContext.BaseDirectory;
        var workerExe = Path.Combine(baseDir, "worker", "ArenaWorker.exe");
        var start = new ProcessStartInfo { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
        if (File.Exists(workerExe)) start.FileName = workerExe;
        else
        {
            var dir = new DirectoryInfo(baseDir);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, "worker.py"))) dir = dir.Parent;
            if (dir == null) throw new FileNotFoundException("Worker missing. Run the reproducible build or use the complete portable folder.");
            start.FileName = Path.Combine(dir.FullName, ".venv", "Scripts", "python.exe"); start.ArgumentList.Add(Path.Combine(dir.FullName, "worker.py")); start.WorkingDirectory = dir.FullName;
        }
        foreach (var a in new[] { "--data", data, "--ready", ready }) start.ArgumentList.Add(a);
        start.Environment["ARENA_CPU_SENSOR_PIPE"] = $"EngineArena.Cpu.{Environment.ProcessId}.{sensorSession}";
        worker = Process.Start(start) ?? throw new InvalidOperationException("Could not launch worker."); job.Assign(worker);
        var errors = worker.StandardError.ReadToEndAsync(); _ = ReadWorkerProgress(worker.StandardOutput);
        for (int i = 0; i < 600 && !File.Exists(ready); i++)
        {
            if (worker.HasExited) throw new InvalidOperationException("Worker startup failed:\n" + await errors);
            await Task.Delay(100);
        }
        if (!File.Exists(ready)) throw new TimeoutException("Worker readiness file did not arrive. Check the data folder and available disk space.");
        using var info = JsonDocument.Parse(await File.ReadAllTextAsync(ready)); token = info.RootElement.GetProperty("token").GetString()!;
        origin = "http://127.0.0.1:" + info.RootElement.GetProperty("port").GetInt32();
        var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(data, "WebView2"));
        Content = browser; await browser.EnsureCoreWebView2Async(env);
        browser.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        browser.CoreWebView2.Settings.IsStatusBarEnabled = false;
        browser.CoreWebView2.WebMessageReceived += MessageReceived;
        browser.CoreWebView2.DownloadStarting += (_, e) =>
        {
            // Other export links use WebView downloads; always let the user choose.
            var save = new SaveFileDialog { Title = "Save export as", FileName = Path.GetFileName(e.ResultFilePath), Filter = "All files|*.*", AddExtension = true };
            e.Handled = true;
            if (save.ShowDialog(this) != true) { e.Cancel = true; return; }
            e.ResultFilePath = save.FileName;
            var operation = e.DownloadOperation;
            operation.StateChanged += (_, _) =>
            {
                if (closing) return;
                if (operation.State == CoreWebView2DownloadState.Completed)
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "downloaded", name = save.FileName }));
                else if (operation.State == CoreWebView2DownloadState.Interrupted)
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "exportError", error = "Export did not finish: " + operation.InterruptReason }));
            };
        };
        browser.CoreWebView2.NavigationStarting += (_, e) => { if (!e.Uri.StartsWith(origin + "/", StringComparison.Ordinal)) e.Cancel = true; };
        browser.CoreWebView2.NewWindowRequested += (_, e) =>
        {
            e.Handled = true;
            if (!Uri.TryCreate(e.Uri, UriKind.Absolute, out var target) || target.GetLeftPart(UriPartial.Authority) != origin) return;
            var path = target.AbsolutePath;
            var report = path.StartsWith("/api/tournaments/", StringComparison.Ordinal) && (path.EndsWith("/openings", StringComparison.Ordinal) || path.EndsWith("/ratings", StringComparison.Ordinal));
            if (path.StartsWith("/api/export/", StringComparison.Ordinal) || report) browser.CoreWebView2.Navigate(e.Uri);
        };
        browser.CoreWebView2.Navigate(origin + "/?token=" + Uri.EscapeDataString(token));
    }
    async Task ReadWorkerProgress(StreamReader output)
    {
        try
        {
            while (await output.ReadLineAsync() is string line)
            {
                if (!line.StartsWith("ARENA_BACKUP ", StringComparison.Ordinal)) continue;
                try
                {
                    using var doc = JsonDocument.Parse(line[13..]);
                    var phase = doc.RootElement.GetProperty("phase").GetString();
                    var percent = doc.RootElement.TryGetProperty("percent", out var p) && p.ValueKind == JsonValueKind.Number ? p.GetDouble() : (double?)null;
                    await Dispatcher.InvokeAsync(() =>
                    {
                        if (!closing) return;
                        closingMessage.Text = phase switch
                        {
                            "copying" => $"Creating the recovery copy… {percent:0}%",
                            "verifying" => "Checking the recovery copy for errors…",
                            "flushing" => "Finishing the verified backup on disk…",
                            "ready" => "Your workspace is saved. Closing…",
                            "error" => "The backup could not finish. Committed game records remain in the database; check Worker & recovery after reopening.",
                            _ => "Finishing saved game records…"
                        };
                        closingProgress.IsIndeterminate = percent is null;
                        if (percent is double value) closingProgress.Value = value;
                    });
                }
                catch (JsonException) { }
            }
        }
        catch (IOException) { }
        catch (ObjectDisposedException) { }
    }
    async void MessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (!e.Source.StartsWith(origin + "/", StringComparison.Ordinal)) return;
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson); var m = doc.RootElement;
            var type = m.GetProperty("type").GetString();
            if (type == "enableCpuSensors")
            {
                if (startingSensor) return;
                startingSensor = true;
                try
                {
                    if (sensorReader is null || sensorReader.HasExited)
                    {
                        var sensorStart = new ProcessStartInfo(Path.Combine(AppContext.BaseDirectory, "ArenaSensors.exe"))
                        { UseShellExecute = true, Verb = "runas", WindowStyle = ProcessWindowStyle.Hidden };
                        using var current = Process.GetCurrentProcess();
                        foreach (var arg in new[] { "--serve", Environment.ProcessId.ToString(), current.StartTime.ToUniversalTime().Ticks.ToString(), sensorSession,
                            System.Security.Principal.WindowsIdentity.GetCurrent().User!.Value, "cpu-only" }) sensorStart.ArgumentList.Add(arg);
                        sensorReader = Process.Start(sensorStart) ?? throw new IOException("Could not start CPU sensor reader.");
                    }
                    using var pipe = new System.IO.Pipes.NamedPipeClientStream(".", $"EngineArena.Cpu.{Environment.ProcessId}.{sensorSession}", System.IO.Pipes.PipeDirection.In, System.IO.Pipes.PipeOptions.Asynchronous);
                    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(12));
                    await pipe.ConnectAsync(timeout.Token);
                    using var sensorOutput = new StreamReader(pipe);
                    using var sensorResult = JsonDocument.Parse(await sensorOutput.ReadLineAsync(timeout.Token) ?? "{}");
                    var result = sensorResult.RootElement;
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "cpuSensorsEnabled", ok = result.GetProperty("status").GetString() == "ok", message = result.GetProperty("message").GetString() }));
                }
                catch (Exception ex)
                {
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "cpuSensorsEnabled", ok = false,
                        message = ex is System.ComponentModel.Win32Exception w && w.NativeErrorCode == 1223 ? "CPU sensor permission was cancelled. Games continue normally." : "CPU sensor reader could not start: " + ex.Message }));
                }
                finally { startingSensor = false; }
                return;
            }
            if (type == "cpuSensorSetup")
            {
                var bundledDriver = Path.Combine(AppContext.BaseDirectory, "Optional", "PawnIO_setup.exe");
                Process.Start(new ProcessStartInfo(File.Exists(bundledDriver) ? bundledDriver : "https://pawnio.eu/") { UseShellExecute = true });
                return;
            }
            if (type == "savePgn")
            {
                var exportId = m.GetProperty("id").GetInt32();
                string? temporary = null;
                try
                {
                    var url = new Uri(new Uri(origin), m.GetProperty("url").GetString()!);
                    if (url.GetLeftPart(UriPartial.Authority) != origin || !System.Text.RegularExpressions.Regex.IsMatch(url.AbsolutePath, @"^/api/export/[a-f0-9]{32}/pgn$"))
                        throw new InvalidOperationException("Invalid local PGN export URL.");
                    var save = new SaveFileDialog { Title = "Save tournament PGN as", FileName = Path.GetFileName(m.GetProperty("name").GetString() ?? "tournament.pgn"), DefaultExt = ".pgn", Filter = "Chess games (*.pgn)|*.pgn|All files (*.*)|*.*", AddExtension = true, OverwritePrompt = true };
                    if (save.ShowDialog(this) != true)
                    {
                        browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "pgnSaved", id = exportId, cancelled = true }));
                        return;
                    }
                    using var request = new HttpRequestMessage(HttpMethod.Get, url);
                    request.Headers.Add("X-Arena-Token", token);
                    using var response = await exportClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, exportCancellation.Token);
                    if (!response.IsSuccessStatusCode) throw new IOException("PGN export failed: " + await response.Content.ReadAsStringAsync(exportCancellation.Token));
                    temporary = Path.Combine(Path.GetDirectoryName(save.FileName)!, "." + Path.GetFileName(save.FileName) + "." + Guid.NewGuid().ToString("N") + ".tmp");
                    await using (var output = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 65536, FileOptions.Asynchronous))
                    {
                        await response.Content.CopyToAsync(output, exportCancellation.Token);
                        await output.FlushAsync(exportCancellation.Token);
                        output.Flush(true);
                    }
                    File.Move(temporary, save.FileName, true); temporary = null;
                    if (!closing) browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "pgnSaved", id = exportId, path = save.FileName }));
                }
                catch (Exception ex)
                {
                    if (!closing) browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "pgnSaved", id = exportId, error = ex.Message }));
                }
                finally { if (temporary != null) try { File.Delete(temporary); } catch { /* A partial file never replaces the selected destination. */ } }
                return;
            }
            if (type == "droppedFiles")
            {
                // The WebView has its own HWND; file drops inside the page do
                // not reliably bubble to WPF's Window.Drop event.
                var droppedPaths = e.AdditionalObjects.OfType<FileInfo>()
                    .Where(f => f.Extension.Equals(".exe", StringComparison.OrdinalIgnoreCase))
                    .Select(f => f.FullName).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
                browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "paths", paths = droppedPaths }));
                return;
            }
            if (type == "download")
            {
                var name = Path.GetFileName(m.GetProperty("name").GetString() ?? "export.txt");
                var save = new SaveFileDialog { Title = "Save export", FileName = name, DefaultExt = Path.GetExtension(name), Filter = "All files|*.*", AddExtension = true };
                if (save.ShowDialog(this) == true)
                {
                    await File.WriteAllTextAsync(save.FileName, m.GetProperty("text").GetString() ?? "", new System.Text.UTF8Encoding(false));
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "downloaded", name = Path.GetFileName(save.FileName) }));
                }
                return;
            }
            if (type != "browse") return;
            var id = m.GetProperty("id").GetInt32(); string[] paths = [];
            if (m.GetProperty("folder").GetBoolean())
            {
                var dialog = new OpenFolderDialog { Title = "Select folder" }; if (dialog.ShowDialog(this) == true) paths = [dialog.FolderName];
            }
            else
            {
                var dialog = new OpenFileDialog { Filter = m.GetProperty("filter").GetString() ?? "All files|*.*", Multiselect = m.GetProperty("multiple").GetBoolean() }; if (dialog.ShowDialog(this) == true) paths = dialog.FileNames;
            }
            browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id, paths }));
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "File operation", MessageBoxButton.OK, MessageBoxImage.Error); }
    }
}

internal sealed class ProcessJob : IDisposable
{
    IntPtr handle;
    [StructLayout(LayoutKind.Sequential)] struct Basic { public long ProcessTime, JobTime; public uint Flags; public UIntPtr Minimum, Maximum; public uint Active; public UIntPtr Affinity; public uint Priority, Scheduling; }
    [StructLayout(LayoutKind.Sequential)] struct Io { public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes; }
    [StructLayout(LayoutKind.Sequential)] struct Extended { public Basic Basic; public Io Io; public UIntPtr ProcessMemory, JobMemory, PeakProcess, PeakJob; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern IntPtr CreateJobObject(IntPtr attributes, string? name);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool SetInformationJobObject(IntPtr job, int cls, ref Extended info, int length);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    public ProcessJob() { handle = CreateJobObject(IntPtr.Zero, null); var info = new Extended(); info.Basic.Flags = 0x2000; if (handle == IntPtr.Zero || !SetInformationJobObject(handle, 9, ref info, Marshal.SizeOf<Extended>())) throw new System.ComponentModel.Win32Exception(); }
    public void Assign(Process process) { if (!AssignProcessToJobObject(handle, process.Handle)) throw new System.ComponentModel.Win32Exception(); }
    public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
}
