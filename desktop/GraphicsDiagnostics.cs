using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;

namespace EngineArena;

// Presentation diagnostics only. Two bounded files, independent of the worker DB.
static class GraphicsDiagnostics
{
    static readonly object Gate = new();
    public static void Write(string folder, object entry)
    {
        try
        {
            var line = JsonSerializer.Serialize(new { utc = DateTime.UtcNow, version = "1.9.2", entry }) + "\n";
            if (Encoding.UTF8.GetByteCount(line) > 8192) return;
            lock (Gate)
            {
                var path = Path.Combine(folder, "graphics-diagnostics.jsonl");
                if (File.Exists(path) && new FileInfo(path).Length + Encoding.UTF8.GetByteCount(line) > 1024 * 1024)
                    File.Move(path, path + ".1", true);
                File.AppendAllText(path, line, new UTF8Encoding(false));
            }
        }
        catch (Exception ex) { Debug.WriteLine("Graphics diagnostics unavailable: " + ex.Message); }
    }
}
