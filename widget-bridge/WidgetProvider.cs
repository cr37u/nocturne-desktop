using System.Runtime.InteropServices;
using Microsoft.Windows.Widgets;
using Microsoft.Windows.Widgets.Providers;

namespace Nocturne.WidgetBridge;

internal sealed class CompactWidgetInfo
{
    public required string WidgetId { get; init; }
    public required string Size { get; set; }
    public bool IsActive { get; set; } = true;
}

[ComVisible(true)]
[ComDefaultInterface(typeof(IWidgetProvider))]
[Guid("924D4929-3BA1-4F76-ABA8-61E9DECD5333")]
public sealed class WidgetProvider : IWidgetProvider, IWidgetProvider2
{
    public const string DefinitionId = "Nocturne_Player";

    public static readonly ManualResetEvent EmptyWidgetListEvent = new(false);
    private static readonly Dictionary<string, CompactWidgetInfo> RunningWidgets = new();
    private static readonly object Gate = new();
    private static bool _subscribed;

    public WidgetProvider()
    {
        lock (Gate)
        {
            if (!_subscribed)
            {
                PipeLink.Instance.StateChanged += _ => UpdateAll();
                _subscribed = true;
            }
        }

        // Recover widgets that existed before the provider (re)started.
        foreach (var info in WidgetManager.GetDefault().GetWidgetInfos())
        {
            var ctx = info.WidgetContext;
            lock (Gate)
            {
                if (!RunningWidgets.ContainsKey(ctx.Id))
                {
                    RunningWidgets[ctx.Id] = new CompactWidgetInfo { WidgetId = ctx.Id, Size = SizeName(ctx.Size) };
                }
            }
        }
        UpdateAll();
    }

    private static string SizeName(WidgetSize size) => size switch
    {
        WidgetSize.Small => "small",
        WidgetSize.Large => "large",
        _ => "medium",
    };

    public void CreateWidget(WidgetContext widgetContext)
    {
        Log.Info($"CreateWidget {widgetContext.Id} ({widgetContext.Size})");
        var info = new CompactWidgetInfo { WidgetId = widgetContext.Id, Size = SizeName(widgetContext.Size) };
        lock (Gate)
        {
            RunningWidgets[widgetContext.Id] = info;
        }
        Update(info);
    }

    public void DeleteWidget(string widgetId, string customState)
    {
        Log.Info($"DeleteWidget {widgetId}");
        lock (Gate)
        {
            RunningWidgets.Remove(widgetId);
            if (RunningWidgets.Count == 0)
            {
                EmptyWidgetListEvent.Set();
            }
        }
    }

    public void OnActionInvoked(WidgetActionInvokedArgs actionInvokedArgs)
    {
        var verb = actionInvokedArgs.Verb;
        Log.Info($"Action {verb}");
        switch (verb)
        {
            case "play_pause":
            case "next":
            case "previous":
            case "open_add_link":
                PipeLink.Instance.Send(verb);
                break;
        }
    }

    public void OnWidgetContextChanged(WidgetContextChangedArgs contextChangedArgs)
    {
        var ctx = contextChangedArgs.WidgetContext;
        CompactWidgetInfo? info;
        lock (Gate)
        {
            RunningWidgets.TryGetValue(ctx.Id, out info);
            if (info is not null)
            {
                info.Size = SizeName(ctx.Size);
            }
        }
        if (info is not null)
        {
            Update(info);
        }
    }

    public void Activate(WidgetContext widgetContext)
    {
        CompactWidgetInfo? info;
        lock (Gate)
        {
            if (!RunningWidgets.TryGetValue(widgetContext.Id, out info))
            {
                info = new CompactWidgetInfo { WidgetId = widgetContext.Id, Size = SizeName(widgetContext.Size) };
                RunningWidgets[widgetContext.Id] = info;
            }
            info.IsActive = true;
            info.Size = SizeName(widgetContext.Size);
        }
        Update(info);
    }

    public void Deactivate(string widgetId)
    {
        lock (Gate)
        {
            if (RunningWidgets.TryGetValue(widgetId, out var info))
            {
                info.IsActive = false;
            }
        }
    }

    public void OnCustomizationRequested(WidgetCustomizationRequestedArgs customizationRequestedArgs)
    {
        // No customization: the widget always mirrors the player.
    }

    private static void UpdateAll()
    {
        List<CompactWidgetInfo> widgets;
        lock (Gate)
        {
            widgets = RunningWidgets.Values.ToList();
        }
        foreach (var w in widgets)
        {
            Update(w);
        }
    }

    private static void Update(CompactWidgetInfo info)
    {
        try
        {
            var options = new WidgetUpdateRequestOptions(info.WidgetId)
            {
                Template = CardBuilder.Template(info.Size),
                Data = CardBuilder.Data(PipeLink.Instance.State),
                CustomState = info.Size,
            };
            WidgetManager.GetDefault().UpdateWidget(options);
        }
        catch (Exception ex)
        {
            Log.Info($"UpdateWidget failed for {info.WidgetId}: {ex.Message}");
        }
    }
}
