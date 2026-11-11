using System.Diagnostics;
using System.IO;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace Banklycs.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        try
        {
            // Keep WebView2 data (cache, localStorage) per-user so the app stays
            // writable when installed to read-only locations later.
            string userDataFolder = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Banklycs", "WebView2");
            var environment = await CoreWebView2Environment.CreateAsync(
                userDataFolder: userDataFolder);
            await WebView.EnsureCoreWebView2Async(environment);
            WebView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            WebView.CoreWebView2.Settings.AreDevToolsEnabled = false;
            WebView.CoreWebView2.Settings.IsStatusBarEnabled = false;
            WebView.CoreWebView2.NewWindowRequested += (s, args) =>
            {
                // Pop-ups (target=_blank) open in the system browser, never inside the app.
                args.Handled = true;
                try
                {
                    Process.Start(new ProcessStartInfo(args.Uri) { UseShellExecute = true });
                }
                catch { /* ignore */ }
            };
        }
        catch (Exception ex)
        {
            LoadingText.Text = $"WebView2 gagal dimuat: {ex.Message}";
            return;
        }

        string? root = FindWorkspaceRoot();
        if (root is null)
        {
            LoadingText.Text = "Folder database/banklycs.db tidak ditemukan.";
            return;
        }

        // The engine serves the console on 127.0.0.1 and announces the real port
        // (5050..5055) through engine/last_port.txt, exactly like START.vbs does.
        string portFile = Path.Combine(root, "engine", "last_port.txt");
        File.WriteAllText(portFile, "0");

        _ = Task.Run(() => Banklycs.StudioServer.Start(root, 5050, openBrowser: false));

        int port = await WaitForPortAsync(portFile, TimeSpan.FromSeconds(20));
        if (port <= 0)
        {
            LoadingText.Text = "Engine gagal start (port 5050-5055 terisi?). Tutup aplikasi lain lalu coba lagi.";
            return;
        }

        await WebView.EnsureCoreWebView2Async();
        WebView.Source = new Uri($"http://127.0.0.1:{port}/");
        WebView.NavigationCompleted += (s, args) =>
            Dispatcher.Invoke(() => LoadingOverlay.Visibility = Visibility.Collapsed);
    }

    private static async Task<int> WaitForPortAsync(string portFile, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            try
            {
                string text = File.ReadAllText(portFile).Trim();
                if (int.TryParse(text, out int port) && port > 0)
                {
                    return port;
                }
            }
            catch (IOException) { /* file being rewritten */ }

            await Task.Delay(200);
        }
        return 0;
    }

    private static string? FindWorkspaceRoot()
    {
        // Walk up from the executable until a directory containing the master
        // database is found. Works for dev builds and the installed layout alike.
        DirectoryInfo? dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "database", "banklycs.db")))
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }
        return null;
    }
}
