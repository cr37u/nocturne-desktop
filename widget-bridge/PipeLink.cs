using System.Diagnostics;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;

namespace Nocturne.WidgetBridge;

internal sealed record RecentTrack(string Title, string Artist, string Duration, string ArtworkPath);

internal sealed record PlayerState(
    bool Connected,
    string Title,
    string Artist,
    string ArtworkPath,
    bool IsPlaying,
    int Position,
    int Duration,
    IReadOnlyList<RecentTrack> Recent,
    string Lang)
{
    public static readonly PlayerState Offline = new(false, "", "", "", false, 0, 0, Array.Empty<RecentTrack>(), "ro");
}

/// <summary>JSON-lines link to the Python app over \\.\pipe\nocturne (auto-reconnecting).</summary>
internal sealed class PipeLink
{
    public static PipeLink Instance { get; } = new();

    private readonly object _gate = new();
    private CancellationTokenSource? _cts;
    private NamedPipeClientStream? _pipe;
    private StreamWriter? _writer;
    private string _lastLang = "ro";

    public PlayerState State { get; private set; } = PlayerState.Offline;

    public event Action<PlayerState>? StateChanged;

    public void Start()
    {
        _cts = new CancellationTokenSource();
        _ = Task.Run(() => RunAsync(_cts.Token));
    }

    public void Stop()
    {
        _cts?.Cancel();
        lock (_gate)
        {
            _pipe?.Dispose();
            _pipe = null;
            _writer = null;
        }
    }

    private async Task RunAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                using var pipe = new NamedPipeClientStream(".", "nocturne", PipeDirection.InOut, PipeOptions.Asynchronous);
                await pipe.ConnectAsync(2000, token).ConfigureAwait(false);
                var writer = new StreamWriter(pipe, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };
                lock (_gate)
                {
                    _pipe = pipe;
                    _writer = writer;
                }
                Log.Info("Connected to Nocturne");
                await writer.WriteLineAsync("{\"cmd\":\"hello\"}").ConfigureAwait(false);

                using var reader = new StreamReader(pipe, Encoding.UTF8);
                while (!token.IsCancellationRequested)
                {
                    var line = await reader.ReadLineAsync(token).ConfigureAwait(false);
                    if (line is null)
                    {
                        break;
                    }
                    HandleLine(line);
                }
            }
            catch (OperationCanceledException) when (token.IsCancellationRequested)
            {
                return;
            }
            catch (TimeoutException)
            {
                // App not running yet.
            }
            catch (Exception ex)
            {
                Log.Info($"Pipe error: {ex.Message}");
            }

            lock (_gate)
            {
                _pipe = null;
                _writer = null;
            }
            if (State.Connected)
            {
                SetState(PlayerState.Offline with { Lang = _lastLang });
            }
            try
            {
                await Task.Delay(1500, token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private void HandleLine(string line)
    {
        try
        {
            using var doc = JsonDocument.Parse(line);
            var root = doc.RootElement;
            if (!root.TryGetProperty("type", out var type) || type.GetString() != "state")
            {
                return;
            }
            var recent = new List<RecentTrack>();
            if (root.TryGetProperty("recent", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in arr.EnumerateArray())
                {
                    recent.Add(new RecentTrack(Str(r, "title"), Str(r, "artist"), Str(r, "duration"), Str(r, "artworkPath")));
                }
            }
            _lastLang = Str(root, "lang") is { Length: > 0 } l ? l : "ro";
            SetState(new PlayerState(
                true,
                Str(root, "title"),
                Str(root, "artist"),
                Str(root, "artworkPath"),
                root.TryGetProperty("isPlaying", out var p) && p.ValueKind == JsonValueKind.True,
                Int(root, "position"),
                Int(root, "duration"),
                recent,
                _lastLang));
        }
        catch (JsonException ex)
        {
            Log.Info($"Bad state line: {ex.Message}");
        }
    }

    private static string Str(JsonElement e, string name) =>
        e.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() ?? "" : "";

    private static int Int(JsonElement e, string name) =>
        e.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetInt32() : 0;

    private void SetState(PlayerState state)
    {
        State = state;
        StateChanged?.Invoke(state);
    }

    /// <summary>Send a command; if Nocturne is not running, start it through nocturne:// and retry.</summary>
    public void Send(string command)
    {
        StreamWriter? writer;
        lock (_gate)
        {
            writer = _writer;
        }
        if (writer is not null)
        {
            try
            {
                lock (_gate)
                {
                    writer.WriteLine("{\"cmd\":\"" + command + "\"}");
                }
                return;
            }
            catch (Exception ex)
            {
                Log.Info($"Send failed: {ex.Message}");
            }
        }

        try
        {
            Process.Start(new ProcessStartInfo($"nocturne://{command}") { UseShellExecute = true });
            Log.Info($"Launched Nocturne for '{command}'");
        }
        catch (Exception ex)
        {
            Log.Info($"Could not launch Nocturne: {ex.Message}");
        }
    }
}
