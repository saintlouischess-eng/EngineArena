using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
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
    readonly CancellationTokenSource startupCancellation = new();
    readonly TextBlock startupMessage = new() { Foreground = System.Windows.Media.Brushes.LightSlateGray, FontSize = 15, TextWrapping = TextWrapping.Wrap, TextAlignment = TextAlignment.Center, Margin = new Thickness(0, 12, 0, 16) };
    readonly TextBlock startupElapsed = new() { Foreground = System.Windows.Media.Brushes.LightSlateGray, FontSize = 13, TextWrapping = TextWrapping.Wrap, TextAlignment = TextAlignment.Center, Margin = new Thickness(0, 12, 0, 16) };
    readonly object startupLogLock = new();
    Task? initialization;
    readonly Stopwatch startupWatch = new();
    readonly System.Windows.Threading.DispatcherTimer startupTimer = new() { Interval = TimeSpan.FromSeconds(1) };
    WorkerConnection? connection;
    string startupLog = "";
    readonly ProcessJob job = new();
    readonly string sensorSession = Guid.NewGuid().ToString("N");
    Process? sensorReader;
    bool startingSensor;
    Mutex? workspaceGuard;
    bool ownsWorkspace;
    readonly TextBlock closingMessage = new() { FontSize = 18, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 18, 0, 18) };
    readonly ProgressBar closingProgress = new() { Height = 6, IsIndeterminate = true, Maximum = 100 };
    Process? worker; string token = "", origin = "", ready = "", workspaceFolder = ""; bool closing, shutdownComplete;
    public ArenaWindow()
    {
        L.LoadFromArguments();
        Title = L.T("Engine Arena — 1.12.6"); Width = 1600; Height = 1000; MinWidth = 1050; MinHeight = 700;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(16, 19, 24));
        Icon = System.Windows.Media.Imaging.BitmapFrame.Create(new Uri("pack://application:,,,/assets/engine-arena.ico", UriKind.Absolute));
        var startup = new StackPanel { VerticalAlignment = VerticalAlignment.Center, HorizontalAlignment = HorizontalAlignment.Center, MaxWidth = 520, Margin = new Thickness(40) };
        startup.Children.Add(new Image { Source = Icon, Width = 88, Height = 88, Margin = new Thickness(0, 0, 0, 20) });
        startup.Children.Add(new TextBlock { Text = "Engine Arena", Foreground = System.Windows.Media.Brushes.White, FontSize = 32, FontWeight = FontWeights.SemiBold, TextAlignment = TextAlignment.Center });
        startupMessage.Text = L.T("Starting Engine Arena…");
        startup.Children.Add(startupMessage);
        startup.Children.Add(new ProgressBar { Height = 3, Width = 220, IsIndeterminate = true });
        startup.Children.Add(startupElapsed);
        var cancelStartup = new Button { Content = L.T("Close"), Padding = new Thickness(24, 8, 24, 8), HorizontalAlignment = HorizontalAlignment.Center };
        cancelStartup.Click += (_, _) => Close(); startup.Children.Add(cancelStartup);
        browser.DefaultBackgroundColor = System.Drawing.Color.FromArgb(16, 19, 24);
        Content = startup;
        Loaded += async (_, _) =>
        {
            startupWatch.Restart(); startupTimer.Start();
            try { initialization = Initialize(); await initialization; }
            catch (OperationCanceledException) when (closing) { }
            catch (Exception ex) { LogStartup(ex.ToString()); if (!closing) ShowStartupError(ex); }
            finally { startupTimer.Stop(); }
        };
        startupTimer.Tick += (_, _) =>
        {
            var elapsed = startupWatch.Elapsed;
            startupElapsed.Text = L.T("Elapsed") + $" {elapsed.TotalSeconds:0}s" + (elapsed.TotalSeconds >= 15 ? "\n" + L.T("Large workspaces can take longer to check. You can safely close this window and try again later.") : "");
        };
        Closing += async (_, e) =>
        {
            if (closing) { e.Cancel = !shutdownComplete; return; } e.Cancel = true; closing = true; exportCancellation.Cancel(); startupCancellation.Cancel();
            Title = L.T("Engine Arena — finishing saved games and backup…");
            var closingPanel = new StackPanel { Margin = new Thickness(48), MaxWidth = 650, VerticalAlignment = VerticalAlignment.Center };
            closingPanel.Children.Add(new TextBlock { Text = L.T("Saving your workspace"), FontSize = 28 });
            closingMessage.Text = L.T("Finishing game records and checking the recovery backup. Large histories can take a little longer.");
            closingPanel.Children.Add(closingMessage); closingPanel.Children.Add(closingProgress);
            closingPanel.Children.Add(new TextBlock { Text = L.T("Engine Arena will close automatically when saving finishes."), Margin = new Thickness(0, 20, 0, 0), TextWrapping = TextWrapping.Wrap });
            closingPanel.SetValue(TextBlock.ForegroundProperty, System.Windows.Media.Brushes.White);
            Content = closingPanel;
            // Large verified backups can exceed twelve seconds. Let the worker
            // finish its durable shutdown instead of killing a healthy save.
            try
            {
                // Cancel startup before disposing WebView or the worker. Otherwise
                // a late readiness notification can reopen a window during Close.
                if (initialization is not null) { try { await initialization; } catch (Exception) { } }
                if (worker is not null) await WorkerStartup.StopAsync(worker, ready, token, connection, client, LogStartup);
            }
            catch (Exception ex) { LogStartup("Shutdown: " + ex); }
            finally { job.Dispose(); browser.Dispose(); client.Dispose(); exportClient.Dispose(); if (ownsWorkspace) workspaceGuard?.ReleaseMutex(); workspaceGuard?.Dispose(); shutdownComplete = true; Close(); }
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
        if (dataIndex >= 0) Title = L.T("Engine Arena — ") + new DirectoryInfo(data).Name + " · 1.12.6";
        workspaceFolder = data; L.Load(data);
        // Claim the workspace before touching its readiness file. A second desktop
        // must not erase the live worker's connection record or launch a rival worker.
        var workspaceKey = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(data.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar).ToUpperInvariant())));
        workspaceGuard = new Mutex(false, @"Local\EngineArena.Workspace." + workspaceKey);
        try { ownsWorkspace = workspaceGuard.WaitOne(0); }
        catch (AbandonedMutexException) { ownsWorkspace = true; }
        if (!ownsWorkspace)
        {
            workspaceGuard.Dispose(); workspaceGuard = null;
            var panel = new StackPanel { Margin = new Thickness(48), MaxWidth = 650, VerticalAlignment = VerticalAlignment.Center };
            panel.SetValue(TextBlock.ForegroundProperty, System.Windows.Media.Brushes.White);
            panel.Children.Add(new TextBlock { Text = L.T("This workspace is already open"), FontSize = 28, TextWrapping = TextWrapping.Wrap });
            panel.Children.Add(new TextBlock { Text = L.T("Return to the existing Engine Arena window to continue. Your games are still running there. To use a separate workspace, start Engine Arena with a different data folder."), FontSize = 16, Margin = new Thickness(0, 18, 0, 18), TextWrapping = TextWrapping.Wrap });
            panel.Children.Add(new TextBlock { Text = data, FontSize = 13, TextWrapping = TextWrapping.Wrap });
            var dismiss = new Button { Content = L.T("Close"), Padding = new Thickness(24, 10, 24, 10), Margin = new Thickness(0, 24, 0, 0), HorizontalAlignment = HorizontalAlignment.Left };
            dismiss.Click += (_, _) => Close(); panel.Children.Add(dismiss); Content = panel;
            return;
        }
        Directory.CreateDirectory(data); ready = Path.Combine(data, "worker-ready.json");
        startupLog = Path.Combine(data, "startup.log");
        try { if (File.Exists(startupLog)) File.Move(startupLog, startupLog + ".previous", true); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { }
        LogStartup("Starting Engine Arena " + typeof(Program).Assembly.GetName().Version);
        if (File.Exists(ready)) File.Delete(ready);
        var baseDir = AppContext.BaseDirectory;
        var workerExe = Path.Combine(baseDir, "worker", "ArenaWorker.exe");
        var start = new ProcessStartInfo { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
        if (File.Exists(workerExe)) start.FileName = workerExe;
        else
        {
            Title += " (development)";
            var dir = new DirectoryInfo(baseDir);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, "worker.py"))) dir = dir.Parent;
            if (dir == null) throw new FileNotFoundException(L.T("Worker missing. Run the reproducible build or use the complete portable folder."));
            start.FileName = Path.Combine(dir.FullName, ".venv", "Scripts", "python.exe"); start.ArgumentList.Add(Path.Combine(dir.FullName, "worker.py")); start.WorkingDirectory = dir.FullName;
        }
        token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        foreach (var a in new[] { "--data", data, "--ready", ready, "--token", token }) start.ArgumentList.Add(a);
        start.Environment["ARENA_CPU_SENSOR_PIPE"] = $"EngineArena.Cpu.{Environment.ProcessId}.{sensorSession}";
        start.Environment["ARENA_CPU_SENSOR_HELPER"] = Path.Combine(baseDir, "ArenaSensors.exe");
        worker = Process.Start(start) ?? throw new InvalidOperationException(L.T("Could not launch worker.")); job.Assign(worker);
        var errors = ReadWorkerErrors(worker.StandardError); _ = ReadWorkerProgress(worker.StandardOutput);
        var cancellation = startupCancellation.Token;
        connection = await WorkerStartup.WaitAsync(worker, ready, token, errors, cancellation);
        token = connection.Token; origin = connection.Origin;
        LogStartup("Worker connected. Initializing WebView2.");
        startupMessage.Text = L.T("Loading the interface…");
        var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(data, "WebView2")).WaitAsync(cancellation);
        cancellation.ThrowIfCancellationRequested();
        // WPF requires the control in the visual tree to finish initialization.
        // Keep it hidden until navigation succeeds so there is no blank flash.
        var startupView = Content as UIElement;
        Content = null;
        var surface = new Grid(); browser.Visibility = Visibility.Hidden;
        surface.Children.Add(browser);
        if (startupView is not null) surface.Children.Add(startupView);
        Content = surface;
        await browser.EnsureCoreWebView2Async(env).WaitAsync(cancellation);
        cancellation.ThrowIfCancellationRequested();
        browser.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        browser.CoreWebView2.Settings.IsStatusBarEnabled = false;
        browser.CoreWebView2.WebMessageReceived += MessageReceived;
        browser.CoreWebView2.ProcessFailed += (_, e) => GraphicsDiagnostics.Write(workspaceFolder,
            new { source = "WebView2", kind = e.ProcessFailedKind.ToString(), reason = e.Reason.ToString(), exitCode = e.ExitCode, runtime = env.BrowserVersionString });
        browser.CoreWebView2.DownloadStarting += (_, e) =>
        {
            // Other export links use WebView downloads; always let the user choose.
            var save = new SaveFileDialog { Title = L.T("Save export as"), FileName = Path.GetFileName(e.ResultFilePath), Filter = L.T("All files") + "|*.*", AddExtension = true };
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
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "exportError", error = L.T("Export did not finish: ") + operation.InterruptReason }));
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
        // Keep the startup panel visible until the local page has actually loaded.
        // A WebView error is explained instead of leaving an empty white surface.
        var loaded = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        browser.CoreWebView2.NavigationCompleted += (_, e) =>
        {
            if (e.IsSuccess) loaded.TrySetResult();
            else loaded.TrySetException(new IOException(L.T("The interface could not load: ") + e.WebErrorStatus));
        };
        browser.CoreWebView2.Navigate(origin + "/?token=" + Uri.EscapeDataString(token));
        await loaded.Task.WaitAsync(cancellation);
        cancellation.ThrowIfCancellationRequested();
        if (startupView is not null) surface.Children.Remove(startupView);
        browser.Visibility = Visibility.Visible; LogStartup("Interface ready.");
    }
    void LogStartup(string message)
    {
        if (startupLog.Length == 0) return;
        lock (startupLogLock)
        {
            try
            {
                if (File.Exists(startupLog) && new FileInfo(startupLog).Length > 65536) return;
                File.AppendAllText(startupLog, DateTimeOffset.Now.ToString("O") + " " + message[..Math.Min(message.Length, 16384)] + Environment.NewLine);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { }
        }
    }
    async Task<string> ReadWorkerErrors(StreamReader reader)
    {
        var tail = new StringBuilder();
        try
        {
            while (await reader.ReadLineAsync() is string line)
            {
                LogStartup(line); tail.AppendLine(line);
                if (tail.Length > 16384) tail.Remove(0, tail.Length - 16384);
            }
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException) { }
        return tail.ToString();
    }
    void ShowStartupError(Exception ex)
    {
        var panel = new StackPanel { Margin = new Thickness(40), MaxWidth = 850, VerticalAlignment = VerticalAlignment.Center };
        panel.SetValue(TextBlock.ForegroundProperty, System.Windows.Media.Brushes.White);
        panel.Children.Add(new TextBlock { Text = L.T("Engine Arena could not start"), FontSize = 28, TextWrapping = TextWrapping.Wrap });
        var explanation = ex is WebView2RuntimeNotFoundException
            ? L.T("Microsoft Edge WebView2 Runtime is missing.\n\nRun EngineArenaSetup again to install the included runtime, then reopen Engine Arena. Your saved tournaments are preserved.")
            : L.T("Your saved workspace has not been reset. Close this window, then try opening Engine Arena again. If this continues, share the details below.");
        panel.Children.Add(new TextBlock { Text = explanation, FontSize = 16, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 18, 0, 18) });
        panel.Children.Add(new TextBox { Text = ex + (startupLog.Length > 0 ? "\n\n" + L.T("Startup log: ") + startupLog : ""), IsReadOnly = true, TextWrapping = TextWrapping.Wrap, MaxHeight = 280, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, Padding = new Thickness(12), Foreground = System.Windows.Media.Brushes.White, Background = Background });
        var dismiss = new Button { Content = L.T("Close"), Padding = new Thickness(24, 10, 24, 10), Margin = new Thickness(0, 20, 0, 0), HorizontalAlignment = HorizontalAlignment.Left };
        dismiss.Click += (_, _) => Close(); panel.Children.Add(dismiss); Content = panel;
    }
    async Task ReadWorkerProgress(StreamReader output)
    {
        try
        {
            while (await output.ReadLineAsync() is string line)
            {
                if (line.StartsWith("ARENA_STARTUP ", StringComparison.Ordinal))
                {
                    LogStartup(line);
                    try
                    {
                        using var progress = JsonDocument.Parse(line[14..]);
                        var phase = progress.RootElement.GetProperty("phase").GetString() ?? "Starting Engine Arena…";
                        await Dispatcher.InvokeAsync(() => { if (!closing && origin.Length == 0) startupMessage.Text = L.T(phase) + "…"; });
                    }
                    catch (JsonException) { }
                    continue;
                }
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
                            "copying" => L.T("Creating the recovery copy…") + $" {percent:0}%",
                            "verifying" => L.T("Checking the recovery copy for errors…"),
                            "flushing" => L.T("Finishing the verified backup on disk…"),
                            "ready" => L.T("Your workspace is saved. Closing…"),
                            "error" => L.T("The backup could not finish. Committed game records remain in the database; check Worker & recovery after reopening."),
                            _ => L.T("Finishing saved game records…")
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
        catch (OperationCanceledException) { }
    }
    string PhotoFolder()
    {
        var preference = Path.Combine(workspaceFolder, "photo-folder.txt");
        if (File.Exists(preference))
        {
            var chosen = File.ReadAllText(preference).Trim();
            if (Path.IsPathFullyQualified(chosen) && Directory.Exists(chosen)) return chosen;
        }
        var folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures), "Engine Arena");
        Directory.CreateDirectory(folder);
        return folder;
    }
    async Task SavePhotoFolder(string folder)
    {
        var preference = Path.Combine(workspaceFolder, "photo-folder.txt");
        await File.WriteAllTextAsync(preference + ".tmp", folder);
        File.Move(preference + ".tmp", preference, true);
    }
    async void MessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (!e.Source.StartsWith(origin + "/", StringComparison.Ordinal)) return;
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson); var m = doc.RootElement;
            var type = m.GetProperty("type").GetString();
            if (type == "graphicsDiagnostic")
            {
                if (e.WebMessageAsJson.Length <= 4096 && m.TryGetProperty("entry", out var entry) && entry.ValueKind == JsonValueKind.Object)
                    GraphicsDiagnostics.Write(workspaceFolder, new { source = "3D", detail = entry });
                return;
            }
            if (type == "language") { L.Save(workspaceFolder, m.GetProperty("language").GetString() ?? "en"); return; }
            if (type == "enableCpuSensors")
            {
                if (startingSensor) return;
                startingSensor = true;
                try
                {
                    if (sensorReader is null || sensorReader.HasExited)
                    {
                        var sensorPath = Path.Combine(AppContext.BaseDirectory, "ArenaSensors.exe");
                        if (!File.Exists(sensorPath)) throw new FileNotFoundException(L.T("The CPU sensor reader is missing from this build. Use the complete Engine Arena build or reinstall the app. Games continue normally."));
                        var sensorStart = new ProcessStartInfo(sensorPath)
                        { UseShellExecute = true, Verb = "runas", WindowStyle = ProcessWindowStyle.Hidden };
                        using var current = Process.GetCurrentProcess();
                        foreach (var arg in new[] { "--serve", Environment.ProcessId.ToString(), current.StartTime.ToUniversalTime().Ticks.ToString(), sensorSession,
                            System.Security.Principal.WindowsIdentity.GetCurrent().User!.Value, "cpu-only" }) sensorStart.ArgumentList.Add(arg);
                        sensorReader = Process.Start(sensorStart) ?? throw new IOException(L.T("Could not start CPU sensor reader."));
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
                        message = ex is System.ComponentModel.Win32Exception w && w.NativeErrorCode == 1223 ? L.T("CPU sensor permission was cancelled. Games continue normally.") : L.T("CPU sensor reader could not start: ") + ex.Message }));
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
                    if (url.GetLeftPart(UriPartial.Authority) != origin || !(System.Text.RegularExpressions.Regex.IsMatch(url.AbsolutePath, @"^/api/export/[a-f0-9]{32}/pgn$") || url.AbsolutePath == "/api/player/pgn"))
                        throw new InvalidOperationException(L.T("Invalid local PGN export URL."));
                    var textExport = Array.Exists(url.Query.TrimStart('?').Split('&'), part => part == "filetype=txt");
                    var save = new SaveFileDialog { Title = L.T(textExport ? "Save text as" : "Save PGN as…"), FileName = Path.GetFileName(m.GetProperty("name").GetString() ?? (textExport ? "tournament.txt" : "tournament.pgn")), DefaultExt = textExport ? ".txt" : ".pgn", Filter = (textExport ? L.T("Text files") + " (*.txt)|*.txt|" : L.T("Chess games") + " (*.pgn)|*.pgn|") + L.T("All files") + " (*.*)|*.*", AddExtension = true, OverwritePrompt = true };
                    if (save.ShowDialog(this) != true)
                    {
                        browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "pgnSaved", id = exportId, cancelled = true }));
                        return;
                    }
                    using var request = new HttpRequestMessage(HttpMethod.Get, url);
                    request.Headers.Add("X-Arena-Token", token);
                    using var response = await exportClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, exportCancellation.Token);
                    if (!response.IsSuccessStatusCode) throw new IOException(L.T("PGN export failed: ") + await response.Content.ReadAsStringAsync(exportCancellation.Token));
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
                var save = new SaveFileDialog { Title = L.T("Save export"), FileName = name, DefaultExt = Path.GetExtension(name), Filter = L.T("All files") + "|*.*", AddExtension = true };
                if (save.ShowDialog(this) == true)
                {
                    await File.WriteAllTextAsync(save.FileName, m.GetProperty("text").GetString() ?? "", new System.Text.UTF8Encoding(false));
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "downloaded", name = Path.GetFileName(save.FileName) }));
                }
                return;
            }
            if (type == "photoFolder")
            {
                var folderId = m.GetProperty("id").GetInt32();
                try
                {
                    var folder = PhotoFolder();
                    if (m.TryGetProperty("choose", out var choose) && choose.GetBoolean())
                    {
                        var dialog = new OpenFolderDialog { Title = L.T("Photo folder"), InitialDirectory = folder };
                        if (dialog.ShowDialog(this) == true) { folder = dialog.FolderName; await SavePhotoFolder(folder); }
                    }
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id = folderId, saved = true, folder }));
                }
                catch (Exception ex) { browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id = folderId, error = ex.Message })); }
                return;
            }
            if (type == "imageExport")
            {
                var exportId = m.GetProperty("id").GetInt32();
                try
                {
                    var data = m.GetProperty("data").GetString() ?? "";
                    const string prefix = "data:image/png;base64,";
                    if (!data.StartsWith(prefix) || data.Length > 64 * 1024 * 1024) throw new InvalidOperationException("Invalid PNG image.");
                    var bytes = Convert.FromBase64String(data[prefix.Length..]);
                    if (bytes.Length < 8 || !bytes.AsSpan(0, 8).SequenceEqual(new byte[] {137,80,78,71,13,10,26,10})) throw new InvalidOperationException("Invalid PNG image.");
                    var picker = new SaveFileDialog { Title = L.T("Save board photo"), InitialDirectory = PhotoFolder(), ClientGuid = new Guid("d61832aa-17ae-4dfb-a6dd-7db8e289c94d"), FileName = Path.GetFileName(m.GetProperty("name").GetString() ?? "EngineArena-board.png"), DefaultExt = ".png", Filter = "PNG|*.png", AddExtension = true, OverwritePrompt = true };
                    var saved = picker.ShowDialog(this) == true;
                    if (saved) { await File.WriteAllBytesAsync(picker.FileName, bytes); await SavePhotoFolder(Path.GetDirectoryName(picker.FileName)!); }
                    browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id = exportId, saved, folder = PhotoFolder(), path = saved ? picker.FileName : null }));
                }
                catch (Exception ex) { browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id = exportId, error = ex.Message })); }
                return;
            }
            if (type == "pgnOutputPath")
            {
                var picker = new SaveFileDialog { Title = L.T("Automatic PGN file"), DefaultExt = ".pgn", Filter = L.T("Chess games") + "|*.pgn", AddExtension = true, OverwritePrompt = false };
                // Select a path only. The worker separately enforces New versus Append.
                var chosen = picker.ShowDialog(this) == true ? new[] { picker.FileName } : Array.Empty<string>();
                browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id = m.GetProperty("id").GetInt32(), paths = chosen }));
                return;
            }
            if (type != "browse") return;
            var id = m.GetProperty("id").GetInt32(); string[] paths = [];
            if (m.GetProperty("folder").GetBoolean())
            {
                var dialog = new OpenFolderDialog { Title = L.T("Select folder") }; if (dialog.ShowDialog(this) == true) paths = [dialog.FolderName];
            }
            else
            {
                var dialog = new OpenFileDialog { Filter = m.GetProperty("filter").GetString() ?? L.T("All files") + "|*.*", Multiselect = m.GetProperty("multiple").GetBoolean() }; if (dialog.ShowDialog(this) == true) paths = dialog.FileNames;
            }
            browser.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { id, paths }));
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, L.T("File operation"), MessageBoxButton.OK, MessageBoxImage.Error); }
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
