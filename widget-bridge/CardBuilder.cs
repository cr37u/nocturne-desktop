using System.Reflection;
using System.Text.Json.Nodes;
using Windows.Graphics.Imaging;
using Windows.Storage;
using Windows.Storage.Streams;

namespace Nocturne.WidgetBridge;

/// <summary>Builds Adaptive Card templates and data for the three widget sizes.</summary>
internal static class CardBuilder
{
    private static readonly Dictionary<string, string> Templates = new();
    private static readonly Dictionary<string, string> Images = new();
    private static readonly Dictionary<string, string> ArtCache = new();

    private static readonly Dictionary<string, Dictionary<string, string>> Strings = new()
    {
        ["ro"] = new()
        {
            ["nowPlaying"] = "SE REDĂ ACUM",
            ["recent"] = "Adăugate recent",
            ["addLink"] = "Adaugă link YouTube",
            ["notRunning"] = "Nocturne nu rulează",
            ["tapToStart"] = "Apasă ▶ ca să pornești muzica",
            ["nothing"] = "Nu se redă nimic",
            ["prev"] = "Anterioara",
            ["play"] = "Redă",
            ["pause"] = "Pauză",
            ["next"] = "Următoarea",
            ["noRecent"] = "Nicio melodie încă",
        },
        ["en"] = new()
        {
            ["nowPlaying"] = "NOW PLAYING",
            ["recent"] = "Recently added",
            ["addLink"] = "Add YouTube link",
            ["notRunning"] = "Nocturne is not running",
            ["tapToStart"] = "Press ▶ to start the music",
            ["nothing"] = "Nothing playing",
            ["prev"] = "Previous",
            ["play"] = "Play",
            ["pause"] = "Pause",
            ["next"] = "Next",
            ["noRecent"] = "No songs yet",
        },
        ["ru"] = new()
        {
            ["nowPlaying"] = "СЕЙЧАС ИГРАЕТ",
            ["recent"] = "Недавно добавленные",
            ["addLink"] = "Добавить ссылку YouTube",
            ["notRunning"] = "Nocturne не запущен",
            ["tapToStart"] = "Нажмите ▶, чтобы включить музыку",
            ["nothing"] = "Ничего не играет",
            ["prev"] = "Предыдущая",
            ["play"] = "Играть",
            ["pause"] = "Пауза",
            ["next"] = "Следующая",
            ["noRecent"] = "Песен пока нет",
        },
    };

    public static string Template(string size)
    {
        var name = size switch
        {
            "small" => "small.json",
            "large" => "large.json",
            _ => "medium.json",
        };
        lock (Templates)
        {
            if (!Templates.TryGetValue(name, out var text))
            {
                text = ReadResourceText(name);
                Templates[name] = text;
            }
            return text;
        }
    }

    public static string Data(PlayerState state)
    {
        var s = Strings.TryGetValue(state.Lang, out var table) ? table : Strings["ro"];
        var hasTrack = state.Connected && state.Title.Length > 0;
        var recent = new JsonArray();
        foreach (var r in state.Recent.Take(2))
        {
            recent.Add(new JsonObject
            {
                ["title"] = r.Title,
                ["artist"] = r.Artist,
                ["duration"] = r.Duration,
                ["art"] = Artwork(r.ArtworkPath, 56),
            });
        }

        var data = new JsonObject
        {
            ["labelNowPlaying"] = s["nowPlaying"],
            ["labelRecent"] = s["recent"],
            ["labelAddLink"] = s["addLink"],
            ["labelPrev"] = s["prev"],
            ["labelNext"] = s["next"],
            ["labelPlayPause"] = state.IsPlaying ? s["pause"] : s["play"],
            ["labelNoRecent"] = s["noRecent"],
            ["title"] = !state.Connected ? s["notRunning"] : hasTrack ? state.Title : s["nothing"],
            ["artist"] = !state.Connected ? s["tapToStart"] : hasTrack ? state.Artist : "Nocturne",
            ["artwork"] = Artwork(state.ArtworkPath, 144),
            ["gradient"] = Image("widget-gradient.png"),
            ["iconPrev"] = Image("icon-previous.png"),
            ["iconNext"] = Image("icon-next.png"),
            ["iconPlayPause"] = Image(state.IsPlaying ? "icon-pause.png" : "icon-play.png"),
            ["iconPlus"] = Image("icon-plus.png"),
            ["btnPrev"] = Image("btn-previous.png"),
            ["btnNext"] = Image("btn-next.png"),
            ["btnPlayPause"] = Image(state.IsPlaying ? "btn-pause.png" : "btn-play.png"),
            ["hasRecent"] = recent.Count > 0,
            ["recent"] = recent,
        };
        return data.ToJsonString();
    }

    private static string Image(string resource)
    {
        lock (Images)
        {
            if (!Images.TryGetValue(resource, out var uri))
            {
                using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(resource);
                if (stream is null)
                {
                    return "";
                }
                using var ms = new MemoryStream();
                stream.CopyTo(ms);
                uri = "data:image/png;base64," + Convert.ToBase64String(ms.ToArray());
                Images[resource] = uri;
            }
            return uri;
        }
    }

    /// <summary>Downscaled artwork as a data URI (the board cannot read arbitrary file paths).</summary>
    private static string Artwork(string path, uint size)
    {
        if (string.IsNullOrEmpty(path) || !File.Exists(path))
        {
            return Image("art-placeholder.png");
        }
        var key = $"{path}|{size}|{File.GetLastWriteTimeUtc(path).Ticks}";
        lock (ArtCache)
        {
            if (ArtCache.TryGetValue(key, out var cached))
            {
                return cached;
            }
        }
        try
        {
            var uri = ScaleAsync(path, size).GetAwaiter().GetResult();
            lock (ArtCache)
            {
                if (ArtCache.Count > 32)
                {
                    ArtCache.Clear();
                }
                ArtCache[key] = uri;
            }
            return uri;
        }
        catch (Exception ex)
        {
            Log.Info($"Artwork failed for {path}: {ex.Message}");
            return Image("art-placeholder.png");
        }
    }

    /// <summary>Scale to size×size and cut rounded corners into the alpha channel (PNG).</summary>
    private static async Task<string> ScaleAsync(string path, uint size)
    {
        var file = await StorageFile.GetFileFromPathAsync(Path.GetFullPath(path));
        using var input = await file.OpenReadAsync();
        var decoder = await BitmapDecoder.CreateAsync(input);
        var transform = new BitmapTransform
        {
            ScaledWidth = size,
            ScaledHeight = size,
            InterpolationMode = BitmapInterpolationMode.Fant,
        };
        var provider = await decoder.GetPixelDataAsync(
            BitmapPixelFormat.Bgra8,
            BitmapAlphaMode.Premultiplied,
            transform,
            ExifOrientationMode.RespectExifOrientation,
            ColorManagementMode.DoNotColorManage);
        var pixels = provider.DetachPixelData();
        RoundCorners(pixels, (int)size, size * 0.14);

        using var output = new InMemoryRandomAccessStream();
        var encoder = await BitmapEncoder.CreateAsync(BitmapEncoder.PngEncoderId, output);
        encoder.SetPixelData(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied, size, size, 96, 96, pixels);
        await encoder.FlushAsync();
        var bytes = new byte[output.Size];
        using var reader = new DataReader(output.GetInputStreamAt(0));
        await reader.LoadAsync((uint)output.Size);
        reader.ReadBytes(bytes);
        return "data:image/png;base64," + Convert.ToBase64String(bytes);
    }

    /// <summary>Anti-aliased rounded-corner mask on premultiplied BGRA pixels.</summary>
    private static void RoundCorners(byte[] px, int size, double radius)
    {
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                // Distance from the pixel centre to the inner rectangle shrunk by `radius`.
                double px0 = x + 0.5, py0 = y + 0.5;
                double cx = Math.Clamp(px0, radius, size - radius);
                double cy = Math.Clamp(py0, radius, size - radius);
                double dx = px0 - cx, dy = py0 - cy;
                double d = Math.Sqrt(dx * dx + dy * dy);
                double coverage = Math.Clamp(radius - d + 0.5, 0, 1);
                if (coverage >= 1)
                {
                    continue;
                }
                int i = (y * size + x) * 4;
                for (int c = 0; c < 4; c++)
                {
                    px[i + c] = (byte)(px[i + c] * coverage);
                }
            }
        }
    }

    private static string ReadResourceText(string name)
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
            ?? throw new InvalidOperationException($"Missing template {name}");
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }
}
