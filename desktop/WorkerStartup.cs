using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;

namespace EngineArena;

internal sealed record WorkerConnection(int Port, string Token)
{
    public string Origin => "http://127.0.0.1:" + Port;
}

internal static class WorkerStartup
{
    // Recovery and integrity checks are proportional to the saved workspace.
    // Wait for readiness or an explicit cancellation, never an arbitrary 60s cutoff.
    internal static async Task<WorkerConnection> WaitAsync(Process process, string path, string expectedToken,
        Task<string> errors, CancellationToken cancellation, Action<TimeSpan>? progress = null)
    {
        var elapsed = Stopwatch.StartNew();
        while (true)
        {
            cancellation.ThrowIfCancellationRequested();
            if (process.HasExited)
                throw new InvalidOperationException("Worker startup failed:\n" + await errors);
            if (await ReadAsync(path, expectedToken, cancellation) is { } connection) return connection;
            progress?.Invoke(elapsed.Elapsed);
            await Task.Delay(100, cancellation);
        }
    }

    internal static async Task<WorkerConnection?> ReadAsync(string path, string expectedToken, CancellationToken cancellation = default)
    {
        if (string.IsNullOrEmpty(path)) return null;
        try
        {
            using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(path, cancellation));
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object ||
                !root.TryGetProperty("pid", out var p) || !p.TryGetInt32(out var actualPid) || actualPid < 1 ||
                !root.TryGetProperty("port", out var port) || !port.TryGetInt32(out var n) || n is < 1 or > 65535 ||
                !root.TryGetProperty("token", out var token) || token.ValueKind != JsonValueKind.String ||
                string.IsNullOrWhiteSpace(expectedToken) || token.GetString() != expectedToken) return null;
            return new(n, token.GetString()!);
        }
        catch (IOException) { return null; }
        catch (JsonException) { return null; } // Also tolerates readiness from older, non-atomic writers.
        catch (InvalidOperationException) { return null; }
    }

    internal static async Task StopAsync(Process process, string ready, string expectedToken, WorkerConnection? connection,
        HttpClient client, Action<string>? log = null)
    {
        if (process.HasExited) return;
        // Startup may have finished just as Close was clicked. Deliver shutdown
        // in that case even though the window did not finish its own handshake.
        // The venv/packaged launcher can have a different PID from its Python
        // child. The fresh per-launch secret identifies our own server instead.
        connection ??= await ReadAsync(ready, expectedToken);
        if (connection is not null)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, connection.Origin + "/api/shutdown");
                request.Headers.Add("X-Arena-Token", connection.Token);
                request.Content = new StringContent("{}");
                using var response = await client.SendAsync(request);
                response.EnsureSuccessStatusCode();
                log?.Invoke("Shutdown accepted; waiting for durable save and backup.");
                // A large, healthy recovery backup must be allowed to finish.
                await process.WaitForExitAsync();
                return;
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
            { log?.Invoke("Worker shutdown request failed: " + ex.Message); }
        }
        // No request was accepted, so waiting for a running server to exit on
        // its own would deadlock. Abort only this window's owned process tree.
        // SQLite preserves committed records; unfinished work recovers next time.
        if (!process.HasExited)
        {
            log?.Invoke("Stopping owned worker before connection/shutdown completed.");
            process.Kill(entireProcessTree: true);
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            await process.WaitForExitAsync(timeout.Token);
        }
    }
}
