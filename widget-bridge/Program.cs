using System.Runtime.InteropServices;

namespace Nocturne.WidgetBridge;

internal static class Program
{
    [DllImport("ole32.dll")]
    private static extern int CoRegisterClassObject(
        [MarshalAs(UnmanagedType.LPStruct)] Guid rclsid,
        [MarshalAs(UnmanagedType.IUnknown)] object pUnk,
        uint dwClsContext,
        uint flags,
        out uint lpdwRegister);

    [DllImport("ole32.dll")]
    private static extern int CoRevokeClassObject(uint dwRegister);

    private const uint CLSCTX_LOCAL_SERVER = 0x4;
    private const uint REGCLS_MULTIPLEUSE = 0x1;

    [MTAThread]
    private static int Main(string[] args)
    {
        Log.Info($"Started with: {string.Join(' ', args)}");
        WinRT.ComWrappersSupport.InitializeComWrappers();

        if (!args.Contains("-RegisterProcessAsComServer"))
        {
            // Started by hand: there is nothing to show; the Widgets host launches us.
            Log.Info("Not started by the Widgets host; exiting.");
            return 0;
        }

        PipeLink.Instance.Start();

        int hr = CoRegisterClassObject(
            typeof(WidgetProvider).GUID,
            new WidgetProviderFactory<WidgetProvider>(),
            CLSCTX_LOCAL_SERVER,
            REGCLS_MULTIPLEUSE,
            out uint cookie);
        if (hr != 0)
        {
            Log.Info($"CoRegisterClassObject failed: 0x{hr:X8}");
            return hr;
        }

        // Keep the COM server alive until the last widget is removed.
        WidgetProvider.EmptyWidgetListEvent.WaitOne();
        CoRevokeClassObject(cookie);
        PipeLink.Instance.Stop();
        Log.Info("Exiting: no widgets left.");
        return 0;
    }
}

internal static class Log
{
    private static readonly string FilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Nocturne", "widget-bridge.log");
    private static readonly object Gate = new();

    public static void Info(string message)
    {
        try
        {
            lock (Gate)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(FilePath)!);
                var info = new FileInfo(FilePath);
                if (info.Exists && info.Length > 512 * 1024)
                {
                    info.Delete();
                }
                File.AppendAllText(FilePath, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} {message}{Environment.NewLine}");
            }
        }
        catch
        {
            // Logging must never crash the provider.
        }
    }
}
