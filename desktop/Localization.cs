using System.Globalization;
using System.IO;
using System.Text.Json;

namespace EngineArena;

internal static class L
{
    static readonly HashSet<string> Languages = ["en", "es", "fr", "de", "pt", "it", "nl", "pl"];
    static Dictionary<string, string> messages = [];
    public static string Language { get; private set; } = "en";
    public static void Use(string? code)
    {
        Language = code != null && Languages.Contains(code) ? code : "en";
        messages = [];
        if (Language == "en") return;
        var folder = new DirectoryInfo(AppContext.BaseDirectory);
        while (folder != null)
        {
            var file = Path.Combine(folder.FullName, "locales", Language + ".json");
            if (File.Exists(file))
            {
                try
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(file));
                    messages = doc.RootElement.GetProperty("messages").EnumerateObject()
                        .ToDictionary(p => p.Name, p => p.Value.GetString() ?? p.Name);
                }
                catch (Exception ex) when (ex is IOException or JsonException or InvalidOperationException or UnauthorizedAccessException) { }
                return;
            }
            folder = folder.Parent;
        }
    }
    public static void Load(string data)
    {
        try { Use(File.ReadAllText(Path.Combine(data, "language.txt")).Trim()); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { Use("en"); }
    }
    public static void LoadFromArguments()
    {
        try
        {
            var args = Environment.GetCommandLineArgs(); var index = Array.IndexOf(args, "--data");
            var data = index >= 0 && index + 1 < args.Length ? Path.GetFullPath(args[index + 1]) : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "EngineArena", "Data");
            Load(data);
        }
        catch (Exception ex) when (ex is IOException or ArgumentException or UnauthorizedAccessException) { Use("en"); }
    }
    public static void Save(string data, string code)
    {
        if (!Languages.Contains(code)) return;
        var file = Path.Combine(data, "language.txt");
        File.WriteAllText(file + ".tmp", code);
        File.Move(file + ".tmp", file, true);
        Use(code);
    }
    public static string T(string source) => messages.TryGetValue(source, out var result) ? result : source;
    public static string F(FormattableString source)
    {
        try { return string.Format(CultureInfo.GetCultureInfo(Language), T(source.Format), source.GetArguments()); }
        catch (FormatException) { return source.ToString(CultureInfo.GetCultureInfo(Language)); }
    }
}
