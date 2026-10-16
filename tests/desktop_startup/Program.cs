using System.Diagnostics;
using System.Net;
using System.Reflection;
using System.Text.Json;
using EngineArena;

if (args.Length > 0 && args[0] == "child")
{
    var file = args[1]; var delay = int.Parse(args[2]);
    if (delay == -2) { Console.Error.WriteLine("deliberate worker failure"); return 23; }
    if (delay >= 0)
    {
        await Task.Delay(delay);
        await File.WriteAllTextAsync(file, "{"); // An older writer's incomplete write must be tolerated.
        await Task.Delay(150);
        await File.WriteAllTextAsync(file, JsonSerializer.Serialize(new { port = 12345, token = "test-only", pid = Environment.ProcessId }));
    }
    while (!File.Exists(file + ".stop")) await Task.Delay(20);
    await Task.Delay(500); // Simulate the final durable backup after HTTP acknowledgement.
    return 0;
}

var root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
var results = new List<object>();
async Task Run(string name, int delay, Func<Process, string, Task<string>, Handler, Task> body)
{
    var folder = Path.Combine(root, name + "-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(folder);
    var ready = Path.Combine(folder, "ready.json");
    var start = new ProcessStartInfo("dotnet") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true };
    foreach (var arg in new[] { Assembly.GetExecutingAssembly().Location, "child", ready, delay.ToString() }) start.ArgumentList.Add(arg);
    using var process = Process.Start(start)!;
    var errors = process.StandardError.ReadToEndAsync(); var watch = Stopwatch.StartNew();
    var handler = new Handler(ready);
    try
    {
        await body(process, ready, errors, handler);
        if (!process.HasExited) throw new Exception("Owned worker was left running");
        results.Add(new { name, seconds = watch.Elapsed.TotalSeconds, passed = true }); Console.WriteLine("PASS " + name);
    }
    finally { if (!process.HasExited) process.Kill(true); }
}

await Run("slow-start-beyond-60s", 65000, async (process, ready, errors, handler) =>
{
    var ticks = 0; var elapsed = Stopwatch.StartNew();
    using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(85));
    var connection = await WorkerStartup.WaitAsync(process, ready, "test-only", errors, limit.Token, _ => ticks++);
    if (elapsed.Elapsed.TotalSeconds < 65 || ticks < 500) throw new Exception("Slow-start test did not exercise old timeout");
    using var client = new HttpClient(handler);
    await WorkerStartup.StopAsync(process, ready, "test-only", connection, client);
    if (handler.Requests != 1 || process.ExitCode != 0) throw new Exception("Slow-start worker was not closed gracefully");
});
await Run("close-during-unready-startup", -1, async (process, ready, errors, handler) =>
{
    using var cancel = new CancellationTokenSource(250);
    try { await WorkerStartup.WaitAsync(process, ready, "test-only", errors, cancel.Token); throw new Exception("Cancellation ignored"); }
    catch (OperationCanceledException) { }
    using var client = new HttpClient(handler);
    await WorkerStartup.StopAsync(process, ready, "test-only", null, client).WaitAsync(TimeSpan.FromSeconds(5));
    if (handler.Requests != 0) throw new Exception("Unready process should not receive guessed HTTP request");
});
await Run("late-ready-close-saves", 0, async (process, ready, errors, handler) =>
{
    using var limit = new CancellationTokenSource(5000);
    await WorkerStartup.WaitAsync(process, ready, "test-only", errors, limit.Token);
    using var client = new HttpClient(handler); var saving = Stopwatch.StartNew();
    // Simulate a desktop which never adopted the ready connection.
    await WorkerStartup.StopAsync(process, ready, "test-only", null, client);
    if (handler.Requests != 1 || process.ExitCode != 0 || saving.ElapsedMilliseconds < 450) throw new Exception("Did not wait for durable shutdown");
});
await Run("worker-error-details", -2, async (process, ready, errors, handler) =>
{
    using var limit = new CancellationTokenSource(5000);
    try { await WorkerStartup.WaitAsync(process, ready, "test-only", errors, limit.Token); throw new Exception("Expected startup failure"); }
    catch (InvalidOperationException ex) { if (!ex.Message.Contains("deliberate worker failure")) throw; }
});
await Run("ignore-foreign-readiness", -1, async (process, ready, errors, handler) =>
{
    await File.WriteAllTextAsync(ready, JsonSerializer.Serialize(new { port = 12345, token = "foreign", pid = Environment.ProcessId }));
    using var cancel = new CancellationTokenSource(250);
    try { await WorkerStartup.WaitAsync(process, ready, "test-only", errors, cancel.Token); throw new Exception("Foreign readiness accepted"); }
    catch (OperationCanceledException) { }
    using var client = new HttpClient(handler);
    await WorkerStartup.StopAsync(process, ready, "test-only", null, client).WaitAsync(TimeSpan.FromSeconds(5));
    if (handler.Requests != 0) throw new Exception("Contacted another process");
});
await Run("failed-shutdown-does-not-hang", 0, async (process, ready, errors, handler) =>
{
    using var limit = new CancellationTokenSource(5000);
    var connection = await WorkerStartup.WaitAsync(process, ready, "test-only", errors, limit.Token);
    handler.Reject = true;
    using var client = new HttpClient(handler);
    await WorkerStartup.StopAsync(process, ready, "test-only", connection, client).WaitAsync(TimeSpan.FromSeconds(5));
});
await File.WriteAllTextAsync(Path.Combine(root, "result.json"), JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true }));
return 0;

sealed class Handler(string ready) : HttpMessageHandler
{
    internal int Requests;
    internal bool Reject;
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Requests++;
        if (request.Method != HttpMethod.Post || request.RequestUri?.AbsolutePath != "/api/shutdown" ||
            request.Headers.GetValues("X-Arena-Token").Single() != "test-only") throw new Exception("Bad shutdown request");
        if (!Reject) File.WriteAllText(ready + ".stop", "stop");
        return Task.FromResult(new HttpResponseMessage(Reject ? HttpStatusCode.Forbidden : HttpStatusCode.OK));
    }
}
