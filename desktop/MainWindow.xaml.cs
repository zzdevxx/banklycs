using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Core;
using WF = System.Windows.Forms;

namespace Banklycs.App;

public partial class MainWindow : Window
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(10) };
    private WF.NotifyIcon? _trayIcon;
    private bool _trayHintShown;
    private bool _realExit;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        StateChanged += (_, _) => { if (WindowState == WindowState.Minimized) HideToTray(); };
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        SetupTrayIcon();
        _ = Task.Run(CheckForUpdateAsync);

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

        // Database channel: one quiet availability check after the engine is up.
        _ = Task.Run(() => CheckForDbUpdateAsync(port));
    }

    // ---------- Tray icon & close-to-tray ----------

    private void SetupTrayIcon()
    {
        _trayIcon = new WF.NotifyIcon
        {
            Icon = System.Drawing.Icon.ExtractAssociatedIcon(Process.GetCurrentProcess().MainModule!.FileName!),
            Text = $"Banklycs v{GetAppVersion()} — Studio Console",
            Visible = true
        };
        _trayIcon.DoubleClick += (_, _) => RestoreFromTray();

        var menu = new WF.ContextMenuStrip();
        menu.Items.Add("Buka Banklycs", null, (_, _) => RestoreFromTray());
        menu.Items.Add(new WF.ToolStripSeparator());
        menu.Items.Add("Keluar", null, (_, _) => ExitApplication());
        _trayIcon.ContextMenuStrip = menu;
    }

    private void HideToTray()
    {
        Hide();
        if (!_trayHintShown)
        {
            _trayHintShown = true;
            _trayIcon?.ShowBalloonTip(4000, "Banklycs masih berjalan",
                "Aplikasi tetap aktif di system tray. Klik dua kali ikon untuk membuka kembali.",
                WF.ToolTipIcon.Info);
        }
    }

    public void RestoreFromTray()
    {
        Show();
        WindowState = WindowState.Normal;
        Activate();
        Focus();
    }

    private void ExitApplication()
    {
        _realExit = true;
        _trayIcon?.Dispose();
        System.Windows.Application.Current.Shutdown();
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        // The X button hides to tray (like ProPresenter); only the tray menu exits.
        if (!_realExit)
        {
            e.Cancel = true;
            HideToTray();
            return;
        }
        base.OnClosing(e);
    }

    // ---------- Auto-update check (GitHub Releases) ----------

    private static string GetAppVersion()
    {
        return System.Reflection.Assembly.GetExecutingAssembly()
            .GetName().Version?.ToString(3) ?? "0.0.0";
    }

    private async Task CheckForUpdateAsync()
    {
        try
        {
            // Respect the operator's Settings toggle; the engine and the shell read
            // the same %LOCALAPPDATA%\\Banklycs\\config.json.
            if (!ReadConfigFlag("app_auto_check", defaultValue: true)) return;

            using var req = new HttpRequestMessage(HttpMethod.Get,
                "https://api.github.com/repos/zzdevxx/banklycs-v2/releases/latest");
            req.Headers.UserAgent.ParseAdd("Banklycs-App");
            using var res = await Http.SendAsync(req);
            if (!res.IsSuccessStatusCode) return;

            using var stream = await res.Content.ReadAsStreamAsync();
            using var doc = await JsonDocument.ParseAsync(stream);
            string? tag = doc.RootElement.GetProperty("tag_name").GetString();
            if (string.IsNullOrWhiteSpace(tag)) return;

            // Release tags follow the owner's scheme: v1.0, v1.1, v2.0 (+0.1 per update).
            // Current assembly version 2.0.0 is normalized to the same 2.0 form.
            string digits = tag.TrimStart('v', 'V');
            if (!double.TryParse(digits, System.Globalization.CultureInfo.InvariantCulture, out double latest)) return;
            var asmVersion = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version!;
            double current = asmVersion.Major + asmVersion.Minor / 10.0;

            if (latest > current)
            {
                Dispatcher.Invoke(() =>
                {
                    _trayIcon?.ShowBalloonTip(8000, "Update Banklycs tersedia",
                        $"Versi baru {tag} sudah rilis. Klik untuk membuka halaman unduhan.",
                        WF.ToolTipIcon.Info);
                });
                _trayIcon!.BalloonTipClicked += (_, _) =>
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo(
                            "https://github.com/zzdevxx/banklycs-v2/releases/latest")
                        { UseShellExecute = true });
                    }
                    catch { /* ignore */ }
                };
            }
        }
        catch
        {
            // Offline or API hiccup: the check must never disturb the operator.
        }
    }

    private static bool ReadConfigFlag(string key, bool defaultValue)
    {
        try
        {
            string path = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Banklycs", "config.json");
            if (!File.Exists(path)) return defaultValue;
            using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(path));
            return doc.RootElement.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.True;
        }
        catch
        {
            return defaultValue;
        }
    }

    // Database update channel: the engine reports availability via its manifest
    // check; the shell only turns that into a tray notification.
    private async Task CheckForDbUpdateAsync(int port)
    {
        try
        {
            if (!ReadConfigFlag("db_auto_check", defaultValue: true)) return;

            using var req = new HttpRequestMessage(HttpMethod.Get, $"http://127.0.0.1:{port}/api/update/db");
            using var res = await Http.SendAsync(req);
            if (!res.IsSuccessStatusCode) return;

            using var stream = await res.Content.ReadAsStreamAsync();
            using var doc = await JsonDocument.ParseAsync(stream);
            if (!doc.RootElement.GetProperty("update_available").GetBoolean()) return;

            string? latest = doc.RootElement.TryGetProperty("latest_version", out var v)
                ? v.GetString() : null;

            Dispatcher.Invoke(() =>
            {
                _trayIcon?.ShowBalloonTip(8000, "Database Banklycs baru tersedia",
                    $"Katalog versi {latest} sudah rilis. Buka Settings > Pembaruan Database untuk mengunduh.",
                    WF.ToolTipIcon.Info);
            });
        }
        catch
        {
            // Offline: silent, same policy as the app update check.
        }
    }

    // ---------- Engine bootstrap ----------

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
