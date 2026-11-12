using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Google.Protobuf;
using Microsoft.Data.Sqlite;
using Pro.SerializationInterop.RVProtoData;

namespace Banklycs
{
    public class SongCatalogItem
    {
        public string filename { get; set; } = "";
        public string pro { get; set; } = "";
        public string title { get; set; } = "";
        public string artist { get; set; } = "";
        public string category { get; set; } = "";
        public string search_index { get; set; } = "";
    }

    public class LyricsGroup
    {
        public string header { get; set; } = "";
        public List<List<string>> slides { get; set; } = new List<List<string>>();
    }

    public class LyricsResponse
    {
        public string filename { get; set; } = "";
        public string title { get; set; } = "";
        public List<LyricsGroup> groups { get; set; } = new List<LyricsGroup>();
        public string raw { get; set; } = "";
    }

    public class InjectRequest
    {
        public string name { get; set; } = "Ibadah Hari Minggu";
        public List<string> songs { get; set; } = new List<string>();
        public string workspace { get; set; } = "";
    }

    public static class StudioServer
    {
        private static List<SongCatalogItem> Catalog = new List<SongCatalogItem>();
        private static DateTime CatalogLoadedAt = DateTime.MinValue;
        private static int CatalogVersion = 0;
        private static readonly object CatalogLock = new object();
        private static readonly object InjectLock = new object();
        private static bool ThemeEnsured = false;
        private static string ProjectRoot = "";
        private static string DatabasePath = "";
        private static string DatabaseDir = "";
        private static string ProDir = "";
        private static string AppDir = "";
        private static string? ProPresenterDir = null;

        // ----- Settings + dual update channels (app v2.x / database timestamp) -----
        private const string AppVersion = "2.5";
        private const string AppReleaseApiUrl = "https://api.github.com/repos/zzdevxx/banklycs/releases/latest";
        private const string DbManifestRemoteUrl = "https://raw.githubusercontent.com/zzdevxx/banklycs/master/database/db_manifest.json";
        private static readonly HttpClient UpdateHttp = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
        private static string ConfigDir = "";
        private static string ConfigPath = "";
        private static string InjectStatePath = "";
        private static Dictionary<string, string> InjectState = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        private static bool AppAutoCheck = true;
        private static bool DbAutoCheck = true;
        private static bool ProtectUserEdits = true;

        private static readonly Regex HeaderRegex = new Regex(
            @"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        // A plain StartsWith() prefix check accepts a sibling directory whose name
        // merely begins with the root ("...\app" vs "...\app2"). Compare against the
        // root with a trailing separator instead.
        internal static bool IsUnder(string candidateFullPath, string rootFullPath)
        {
            if (string.IsNullOrEmpty(candidateFullPath) || string.IsNullOrEmpty(rootFullPath)) return false;
            string root = Path.GetFullPath(rootFullPath);
            if (!root.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal))
            {
                root += Path.DirectorySeparatorChar;
            }
            string candidate = Path.GetFullPath(candidateFullPath);
            return candidate.StartsWith(root, StringComparison.OrdinalIgnoreCase)
                || candidate.Equals(root.TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase);
        }

        public static string SanitizeDiskFileName(string name)
        {
            if (string.IsNullOrWhiteSpace(name)) return "Presentation";
            char[] invalid = Path.GetInvalidFileNameChars();
            var sb = new StringBuilder(name.Length);
            foreach (char c in name)
            {
                if (c == '"' || c == '?' || c == '*' || c == '<' || c == '>') continue;
                if (c == ':' || c == '/' || c == '\\' || c == '|')
                {
                    sb.Append(" - ");
                }
                else if (invalid.Contains(c))
                {
                    sb.Append('_');
                }
                else
                {
                    sb.Append(c);
                }
            }
            string res = Regex.Replace(sb.ToString(), @"\s+", " ").Trim();
            res = Regex.Replace(res, @"\s*-\s*-\s*", " - ").Trim('-', ' ');
            return string.IsNullOrEmpty(res) ? "Presentation" : res;
        }

        public static string ResolveProPresenterDir()
        {
            try
            {
                string personal = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
                string cand = Path.Combine(personal, "ProPresenter");
                if (Directory.Exists(cand)) return cand;

                string? oneDrive = Environment.GetEnvironmentVariable("OneDrive");
                if (!string.IsNullOrEmpty(oneDrive))
                {
                    cand = Path.Combine(oneDrive, "Documents", "ProPresenter");
                    if (Directory.Exists(cand)) return cand;
                    cand = Path.Combine(oneDrive, "Dokumen", "ProPresenter");
                    if (Directory.Exists(cand)) return cand;
                }

                string? userProfile = Environment.GetEnvironmentVariable("USERPROFILE");
                if (!string.IsNullOrEmpty(userProfile))
                {
                    cand = Path.Combine(userProfile, "Documents", "ProPresenter");
                    if (Directory.Exists(cand)) return cand;
                    cand = Path.Combine(userProfile, "Dokumen", "ProPresenter");
                    if (Directory.Exists(cand)) return cand;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Gagal mendeteksi path ProPresenter: {ex.Message}");
            }

            return "";
        }

        private static string DetermineCategory(string name)
        {
            string upper = name.ToUpperInvariant();
            if (Regex.IsMatch(upper, @"\bKJ\s*\d+")) return "KJ";
            if (Regex.IsMatch(upper, @"\bNKB\s*\d+")) return "NKB";
            if (Regex.IsMatch(upper, @"\bPKJ\s*\d+")) return "PKJ";
            if (Regex.IsMatch(upper, @"\bKK\s*\d+")) return "KK";
            if (Regex.IsMatch(upper, @"\bBE\s*\d+")) return "BE";
            if (Regex.IsMatch(upper, @"\bKLIK\s*\d+")) return "KLIK";
            if (Regex.IsMatch(upper, @"\bNNBT\s*\d+")) return "NNBT";
            if (upper.Contains("KIDUNG JAWA") || upper.Contains("PASAMUWAN")) return "JAWA";
            if (upper.Contains("HILLSONG") || upper.Contains("BETHEL") || upper.Contains("ELEVATION") ||
                upper.Contains("PLANETSHAKERS") || upper.Contains("TOMLIN") || upper.Contains("REDMAN") ||
                upper.Contains("WICKHAM") || upper.Contains("GAITHER"))
                return "EN";
            return "ID";
        }

        public static void LoadCatalog()
        {
            Stopwatch sw = Stopwatch.StartNew();
            List<SongCatalogItem> items = new List<SongCatalogItem>(25000);

            if (File.Exists(DatabasePath))
            {
                Console.WriteLine($"[CATALOG] Memuat seluruh katalog dari SQLite Database: {DatabasePath}...");
                try
                {
                    string connStr = new SqliteConnectionStringBuilder
                    {
                        DataSource = DatabasePath,
                        Mode = SqliteOpenMode.ReadOnly
                    }.ToString();

                    using var conn = new SqliteConnection(connStr);
                    conn.Open();
                    using var cmd = conn.CreateCommand();
                    cmd.CommandText = "SELECT id, filename, title, artist, category FROM songs ORDER BY title COLLATE NOCASE;";
                    using var reader = cmd.ExecuteReader();
                    while (reader.Read())
                    {
                        string filename = reader.GetString(1);
                        string title = reader.GetString(2);
                        string artist = reader.IsDBNull(3) ? "" : reader.GetString(3);
                        string cat = reader.IsDBNull(4) ? "ID" : reader.GetString(4);
                        string baseName = Path.GetFileNameWithoutExtension(filename);
                        string searchIdx = $"{title} {artist} {baseName}".ToLowerInvariant();

                        items.Add(new SongCatalogItem
                        {
                            filename = filename,
                            pro = baseName + ".pro",
                            title = title,
                            artist = artist,
                            category = string.IsNullOrEmpty(cat) ? DetermineCategory(baseName) : cat,
                            search_index = searchIdx
                        });
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[WARN] Gagal membaca SQLite database: {ex.Message}");
                }
            }

            // Fallback: scan disk folder if SQLite is missing or empty
            if (items.Count == 0 && Directory.Exists(DatabaseDir))
            {
                Console.WriteLine($"[CATALOG] Fallback memindai folder database: {DatabaseDir}...");
                try
                {
                    foreach (string filePath in Directory.EnumerateFiles(DatabaseDir, "*.txt", SearchOption.TopDirectoryOnly))
                    {
                        string filename = Path.GetFileName(filePath);
                        string baseName = Path.GetFileNameWithoutExtension(filePath);
                        string title = baseName;
                        string artist = "";

                        int dashIdx = baseName.IndexOf(" - ", StringComparison.Ordinal);
                        if (dashIdx > 0)
                        {
                            title = baseName.Substring(0, dashIdx).Trim();
                            artist = baseName.Substring(dashIdx + 3).Trim();
                        }

                        string cat = DetermineCategory(baseName);
                        string searchIdx = $"{title} {artist} {baseName}".ToLowerInvariant();

                        items.Add(new SongCatalogItem
                        {
                            filename = filename,
                            pro = baseName + ".pro",
                            title = title,
                            artist = artist,
                            category = cat,
                            search_index = searchIdx
                        });
                    }
                    items.Sort((a, b) => string.Compare(a.title, b.title, StringComparison.OrdinalIgnoreCase));
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[WARN] Gagal memindai fallback txt: {ex.Message}");
                }
            }

            lock (CatalogLock)
            {
                Catalog = items;
                CatalogLoadedAt = DateTime.UtcNow;
                CatalogVersion++;
            }
            sw.Stop();
            Console.WriteLine($"[CATALOG] Sukses memuat {Catalog.Count:N0} lagu ke RAM dalam {sw.ElapsedMilliseconds} ms!");
        }

        private static void EnsureProPresenterBanklycsTheme()
        {
            if (ThemeEnsured) return;
            if (string.IsNullOrEmpty(ProPresenterDir) || !Directory.Exists(ProPresenterDir)) return;
            try
            {
                string banklycsThemeDir = Path.Combine(ProPresenterDir, "Themes", "Banklycs");
                string banklycsThemeFile = Path.Combine(banklycsThemeDir, "Theme");
                string srcTemplate = Path.Combine(ProjectRoot, "engine", "ThemeTemplate");

                // Bump when engine/ThemeTemplate content changes so existing installs re-inject once.
                const string ThemeVersion = "2";
                string versionMarker = Path.Combine(banklycsThemeDir, ".theme-version");

                if (File.Exists(srcTemplate))
                {
                    // The official template ships Praise/Worship/Bible. A copy is needed when the
                    // file is missing, a slide is missing, or the installed copy predates the
                    // current template version (marker absent or older).
                    bool needCopy = !File.Exists(banklycsThemeFile);
                    if (!needCopy)
                    {
                        try
                        {
                            string installedVersion = File.Exists(versionMarker)
                                ? File.ReadAllText(versionMarker).Trim()
                                : "";
                            if (installedVersion != ThemeVersion)
                            {
                                needCopy = true;
                            }
                            else
                            {
                                byte[] bBytes = File.ReadAllBytes(banklycsThemeFile);
                                var bDoc = Template.Types.Document.Parser.ParseFrom(bBytes);
                                byte[] sBytes = File.ReadAllBytes(srcTemplate);
                                var sDoc = Template.Types.Document.Parser.ParseFrom(sBytes);
                                needCopy = sDoc.Slides.Any(src =>
                                    !bDoc.Slides.Any(s => s.Name.Equals(src.Name, StringComparison.OrdinalIgnoreCase)));
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[WARN] Gagal membaca Banklycs Theme file: {ex.Message}");
                            needCopy = true;
                        }
                    }

                    if (needCopy)
                    {
                        Directory.CreateDirectory(banklycsThemeDir);
                        if (File.Exists(banklycsThemeFile))
                        {
                            string backup = banklycsThemeFile + ".bak";
                            File.Copy(banklycsThemeFile, backup, overwrite: true);
                            Console.WriteLine($"[THEME] Backup tema lama: {backup}");
                        }
                        File.Copy(srcTemplate, banklycsThemeFile, overwrite: true);
                        File.WriteAllText(versionMarker, ThemeVersion);
                        Console.WriteLine($"[THEME] Auto-injected official Banklycs Theme v{ThemeVersion} to ProPresenter: {banklycsThemeFile}");
                    }
                }

                // Prune Praise & Worship from zz Theme once if present, leaving ONLY Bible
                string zzThemeFile = Path.Combine(ProPresenterDir, "Themes", "zz", "Theme");
                if (File.Exists(zzThemeFile))
                {
                    try
                    {
                        byte[] zzBytes = File.ReadAllBytes(zzThemeFile);
                        var zzDoc = Template.Types.Document.Parser.ParseFrom(zzBytes);
                        bool hasPraiseOrWorship = zzDoc.Slides.Any(s => s.Name.Contains("Praise") || s.Name.Contains("Worship"));
                        if (hasPraiseOrWorship)
                        {
                            string zzBackup = zzThemeFile + ".bak-" + DateTime.UtcNow.ToString("yyyyMMddHHmmss");
                            File.Copy(zzThemeFile, zzBackup, overwrite: false);
                            var keepZz = zzDoc.Slides.Where(s => !s.Name.Contains("Praise") && !s.Name.Contains("Worship")).ToList();
                            zzDoc.Slides.Clear();
                            zzDoc.Slides.AddRange(keepZz);
                            // Atomic: ProPresenter holds this file open, so a partial write
                            // would leave the playlist/theme document unreadable.
                            Program.WriteAllBytesAtomic(zzThemeFile, zzDoc.ToByteArray());
                            Console.WriteLine($"[THEME] Pruned duplicate Praise/Worship from zz Theme (backup: {zzBackup}).");
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[WARN] Gagal memangkas tema zz: {ex.Message}");
                    }
                }

                ThemeEnsured = true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Gagal menyinkronkan tema Banklycs: {ex.Message}");
            }
        }

        // ==========================================================
        // Settings persistence, update channels, inject protection
        // ==========================================================

        private static string DbManifestLocalPath => Path.Combine(
            Path.GetDirectoryName(DatabasePath) ?? ProjectRoot, "db_manifest.json");

        private static void LoadAppConfig()
        {
            try
            {
                if (!File.Exists(ConfigPath)) return;
                using var doc = JsonDocument.Parse(File.ReadAllText(ConfigPath));
                if (doc.RootElement.TryGetProperty("app_auto_check", out var a)) AppAutoCheck = a.GetBoolean();
                if (doc.RootElement.TryGetProperty("db_auto_check", out var b)) DbAutoCheck = b.GetBoolean();
                if (doc.RootElement.TryGetProperty("protect_user_edits", out var c)) ProtectUserEdits = c.GetBoolean();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] config.json tidak valid, memakai default: {ex.Message}");
            }
        }

        private static void SaveAppConfig()
        {
            try
            {
                Directory.CreateDirectory(ConfigDir);
                var obj = new { app_auto_check = AppAutoCheck, db_auto_check = DbAutoCheck, protect_user_edits = ProtectUserEdits };
                File.WriteAllText(ConfigPath, JsonSerializer.Serialize(obj, new JsonSerializerOptions { WriteIndented = true }));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Gagal menyimpan config: {ex.Message}");
            }
        }

        private static void LoadInjectState()
        {
            try
            {
                if (!File.Exists(InjectStatePath)) return;
                var loaded = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(InjectStatePath));
                if (loaded != null) InjectState = new Dictionary<string, string>(loaded, StringComparer.OrdinalIgnoreCase);
            }
            catch
            {
                // Corrupt state: start empty. Protection then treats every existing
                // file as possibly user-edited, which is the safe direction.
            }
        }

        private static void SaveInjectState()
        {
            try
            {
                Directory.CreateDirectory(ConfigDir);
                File.WriteAllText(InjectStatePath, JsonSerializer.Serialize(InjectState));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Gagal menyimpan inject state: {ex.Message}");
            }
        }

        private static string Sha256File(string path)
        {
            using var stream = File.OpenRead(path);
            return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
        }

        private sealed class DbManifest
        {
            public string version { get; set; } = "";
            public string sha256 { get; set; } = "";
            public long size { get; set; }
            public string url { get; set; } = "";
        }

        private static DbManifest? ReadLocalDbManifest()
        {
            try
            {
                if (!File.Exists(DbManifestLocalPath)) return null;
                return JsonSerializer.Deserialize<DbManifest>(File.ReadAllText(DbManifestLocalPath),
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            }
            catch { return null; }
        }

        private static DbManifest? FetchRemoteDbManifest()
        {
            try
            {
                using var req = new HttpRequestMessage(HttpMethod.Get, DbManifestRemoteUrl);
                req.Headers.UserAgent.ParseAdd("Banklycs-Engine");
                using var res = UpdateHttp.SendAsync(req).GetAwaiter().GetResult();
                if (!res.IsSuccessStatusCode) return null;
                string body = res.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                return JsonSerializer.Deserialize<DbManifest>(body,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            }
            catch { return null; }
        }

        private static (string latestTag, bool available, string error) CheckLatestAppRelease()
        {
            try
            {
                using var req = new HttpRequestMessage(HttpMethod.Get, AppReleaseApiUrl);
                req.Headers.UserAgent.ParseAdd("Banklycs-Engine");
                using var res = UpdateHttp.SendAsync(req).GetAwaiter().GetResult();
                if (!res.IsSuccessStatusCode) return ("", false, $"GitHub API HTTP {(int)res.StatusCode}");
                string body = res.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                using var doc = JsonDocument.Parse(body);
                string? tag = doc.RootElement.GetProperty("tag_name").GetString();
                if (string.IsNullOrWhiteSpace(tag)) return ("", false, "Tag rilis tidak terbaca");
                string digits = tag.TrimStart('v', 'V');
                if (!double.TryParse(digits, CultureInfo.InvariantCulture, out double latest))
                    return ("", false, $"Tag tidak dikenali: {tag}");
                if (!double.TryParse(AppVersion, CultureInfo.InvariantCulture, out double current)) current = 0;
                return (tag, latest > current, "");
            }
            catch (Exception ex)
            {
                return ("", false, ex.Message);
            }
        }

        public static void Start(string rootPath, int preferredPort = 5050, bool openBrowser = true)
        {
            ProjectRoot = rootPath;
            DatabasePath = Path.Combine(ProjectRoot, "database", "banklycs.db");
            DatabaseDir = Path.Combine(ProjectRoot, "database", "txt");
            if (!Directory.Exists(DatabaseDir))
            {
                DatabaseDir = Path.Combine(ProjectRoot, "database");
            }
            ProDir = Path.Combine(ProjectRoot, "database", "pro");
            if (!Directory.Exists(ProDir))
            {
                ProDir = Path.Combine(ProjectRoot, "engine", "PRO");
            }
            AppDir = Path.Combine(ProjectRoot, "app");
            ProPresenterDir = ResolveProPresenterDir();
            EnsureProPresenterBanklycsTheme();

            ConfigDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Banklycs");
            ConfigPath = Path.Combine(ConfigDir, "config.json");
            InjectStatePath = Path.Combine(ConfigDir, "inject_state.json");
            LoadAppConfig();
            LoadInjectState();

            LoadCatalog();

            int port = preferredPort;
            HttpListener? listener = null;

            while (port <= preferredPort + 5)
            {
                try
                {
                    listener = new HttpListener();
                    listener.Prefixes.Add($"http://127.0.0.1:{port}/");
                    listener.Start();
                    break;
                }
                catch (HttpListenerException)
                {
                    listener?.Close();
                    port++;
                }
            }

            if (listener == null || !listener.IsListening)
            {
                Console.WriteLine("[ERROR] Tidak dapat membuka port HTTP untuk Studio Console!");
                // Tell the launcher the truth so it does not open a browser at a dead port.
                try
                {
                    File.WriteAllText(Path.Combine(ProjectRoot, "engine", "last_port.txt"), "0");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[WARN] Tidak dapat menulis last_port.txt: {ex.Message}");
                }
                Environment.ExitCode = 1;
                return;
            }

            // Handshake for START.vbs: the port may not be 5050 when it is occupied.
            try
            {
                File.WriteAllText(Path.Combine(ProjectRoot, "engine", "last_port.txt"), port.ToString());
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Tidak dapat menulis last_port.txt: {ex.Message}");
            }

            string serverUrl = $"http://127.0.0.1:{port}";
            Console.WriteLine("==============================================================================");
            Console.WriteLine("  BANKLYCS NATIVE STUDIO CONSOLE (C# .NET 8 / ZERO-DEPENDENCY)");
            Console.WriteLine($"  URL              : {serverUrl}");
            Console.WriteLine($"  ProPresenter Dir : {(string.IsNullOrEmpty(ProPresenterDir) ? "[TIDAK TERDETEKSI]" : ProPresenterDir)}");
            Console.WriteLine($"  Database Vault   : {(File.Exists(DatabasePath) ? DatabasePath : DatabaseDir)} ({Catalog.Count:N0} lagu)");
            Console.WriteLine("==============================================================================");
            Console.WriteLine("[INFO] Tekan Ctrl+C untuk menutup server.");

            if (openBrowser)
            {
                Task.Run(() =>
                {
                    Thread.Sleep(400);
                    try
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = "msedge",
                            Arguments = $"--app={serverUrl} --start-maximized",
                            UseShellExecute = true
                        });
                    }
                    catch (Exception edgeEx)
                    {
                        Console.WriteLine($"[WARN] Edge app-mode launch failed: {edgeEx.Message}");
                        try
                        {
                            Process.Start(new ProcessStartInfo
                            {
                                FileName = serverUrl,
                                UseShellExecute = true
                            });
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[WARN] Browser launch fallback failed: {ex.Message}");
                        }
                    }
                });
            }

            // Listen loop
            while (listener.IsListening)
            {
                try
                {
                    HttpListenerContext context = listener.GetContext();
                    Task.Run(() => ProcessRequest(context));
                }
                catch (HttpListenerException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[WARN] Request listener error: {ex.Message}");
                }
            }
        }

        private static string? ReadBodyWithLimit(HttpListenerRequest req, int maxBytes = 1_000_000)
        {
            if (req.ContentLength64 > maxBytes) return null;
            try
            {
                using var ms = new MemoryStream();
                byte[] buffer = new byte[8192];
                int total = 0;
                int read;
                while ((read = req.InputStream.Read(buffer, 0, buffer.Length)) > 0)
                {
                    total += read;
                    if (total > maxBytes) return null;
                    ms.Write(buffer, 0, read);
                }
                return req.ContentEncoding.GetString(ms.ToArray());
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WARN] Gagal membaca body request: {ex.Message}");
                return null;
            }
        }

        // RFC 9457 Problem Details: application/problem+json and a stable `instance`
        // derived from the request path, so a client can tell two failures apart.
        private static void SendProblem(HttpListenerRequest req, HttpListenerResponse res, int status, string title, string detail)
        {
            var problem = new
            {
                type = $"https://httpstatuses.io/{status}",
                title = title,
                status = status,
                detail = detail,
                instance = req.Url?.AbsolutePath ?? "/"
            };
            SendJson(req, res, problem, status, "application/problem+json; charset=utf-8");
        }

        private static void ProcessRequest(HttpListenerContext context)
        {
            HttpListenerRequest req = context.Request;
            HttpListenerResponse res = context.Response;

            // Security: CORS lockdown to localhost/127.0.0.1 or same-origin local application.
            // Reject any external website origins trying to hijack local APIs.
            string origin = req.Headers["Origin"] ?? "";
            bool isLocalOrigin = string.IsNullOrEmpty(origin) ||
                origin.StartsWith("http://127.0.0.1", StringComparison.OrdinalIgnoreCase) ||
                origin.StartsWith("http://localhost", StringComparison.OrdinalIgnoreCase);

            if (!isLocalOrigin)
            {
                SendProblem(req, res, 403, "Forbidden", "Cross-origin requests from external origins are blocked.");
                return;
            }

            if (!string.IsNullOrEmpty(origin))
            {
                res.Headers.Add("Access-Control-Allow-Origin", origin);
                res.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                res.Headers.Add("Access-Control-Allow-Headers", "Content-Type");
            }

            if (req.HttpMethod.Equals("OPTIONS", StringComparison.OrdinalIgnoreCase))
            {
                res.StatusCode = 204;
                res.Close();
                return;
            }

            string rawPath = req.Url?.AbsolutePath ?? "/";

            try
            {
                // ==========================================================
                // GET / HEAD (Safe Read-Only Methods)
                // ==========================================================
                if (req.HttpMethod.Equals("GET", StringComparison.OrdinalIgnoreCase) ||
                    req.HttpMethod.Equals("HEAD", StringComparison.OrdinalIgnoreCase))
                {
                    if (rawPath.Equals("/api/status", StringComparison.OrdinalIgnoreCase))
                    {
                        DateTime dbMtime = File.Exists(DatabasePath) ? File.GetLastWriteTimeUtc(DatabasePath) : DateTime.MinValue;
                        int banksCount = 0;
                        if (!string.IsNullOrEmpty(ProPresenterDir))
                        {
                            string libBanks = Path.Combine(ProPresenterDir, "Libraries", "Banks");
                            if (Directory.Exists(libBanks))
                            {
                                try { banksCount = Directory.GetFiles(libBanks, "*.pro").Length; }
                                catch (Exception ex) { Console.WriteLine($"[WARN] Banks scan error: {ex.Message}"); }
                            }
                        }

                        long dbSizeBytes = 0;
                        try
                        {
                            if (File.Exists(DatabasePath)) dbSizeBytes = new FileInfo(DatabasePath).Length;
                        }
                        catch (Exception ex) { Console.WriteLine($"[WARN] DB size read error: {ex.Message}"); }

                        var statusData = new
                        {
                            total_songs = Catalog.Count,
                            db_size_bytes = dbSizeBytes,
                            catalog_loaded_at = CatalogLoadedAt == DateTime.MinValue ? "" : CatalogLoadedAt.ToString("o"),
                            catalog_db_mtime = dbMtime == DateTime.MinValue ? "" : dbMtime.ToString("o"),
                            catalog_stale = dbMtime > CatalogLoadedAt,
                            catalog_version = CatalogVersion,
                            propresenter_dir = ProPresenterDir,
                            banks_count = banksCount,
                            project_root = ProjectRoot,
                            db_path = DatabasePath,
                            app_version = AppVersion,
                            db_version = ReadLocalDbManifest()?.version ?? "",
                            protect_user_edits = ProtectUserEdits
                        };
                        SendJson(req, res, statusData);
                        return;
                    }

                    if (rawPath.Equals("/api/settings", StringComparison.OrdinalIgnoreCase))
                    {
                        var settingsManifest = ReadLocalDbManifest();
                        SendJson(req, res, new
                        {
                            app_version = AppVersion,
                            db_version = settingsManifest?.version ?? "",
                            app_auto_check = AppAutoCheck,
                            db_auto_check = DbAutoCheck,
                            protect_user_edits = ProtectUserEdits
                        });
                        return;
                    }

                    if (rawPath.Equals("/api/update/app", StringComparison.OrdinalIgnoreCase))
                    {
                        var (latestTag, appAvailable, appError) = CheckLatestAppRelease();
                        SendJson(req, res, new
                        {
                            current = AppVersion,
                            latest = latestTag,
                            update_available = appAvailable,
                            url = "https://github.com/zzdevxx/banklycs/releases/latest",
                            error = appError
                        });
                        return;
                    }

                    if (rawPath.Equals("/api/update/db", StringComparison.OrdinalIgnoreCase))
                    {
                        var localManifest = ReadLocalDbManifest();
                        var remoteManifest = FetchRemoteDbManifest();
                        bool dbAvailable = false;
                        string dbError = "";
                        if (remoteManifest == null)
                        {
                            dbError = "Tidak dapat mengambil manifest database (offline?)";
                        }
                        else if (localManifest == null || string.IsNullOrEmpty(localManifest.version))
                        {
                            dbError = "Manifest database lokal tidak ditemukan";
                        }
                        else if (DateTime.TryParse(localManifest.version, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var localVersion) &&
                                 DateTime.TryParse(remoteManifest.version, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var remoteVersion))
                        {
                            dbAvailable = remoteVersion > localVersion;
                        }
                        else
                        {
                            dbError = "Format versi database tidak valid";
                        }

                        SendJson(req, res, new
                        {
                            current_version = localManifest?.version ?? "",
                            latest_version = remoteManifest?.version ?? "",
                            size = remoteManifest?.size ?? 0,
                            update_available = dbAvailable,
                            error = dbError
                        });
                        return;
                    }

                    if (rawPath.Equals("/api/themes", StringComparison.OrdinalIgnoreCase))
                    {
                        EnsureProPresenterBanklycsTheme();

                        var themeList = new List<object>();
                        var scannedThemeFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

                        if (!string.IsNullOrEmpty(ProPresenterDir))
                        {
                            string pThemes = Path.Combine(ProPresenterDir, "Themes");
                            if (Directory.Exists(pThemes))
                            {
                                try
                                {
                                    foreach (string tFile in Directory.EnumerateFiles(pThemes, "Theme", SearchOption.AllDirectories))
                                    {
                                        scannedThemeFiles.Add(tFile);
                                    }
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine($"[WARN] Theme scan error: {ex.Message}");
                                }
                            }
                        }

                        if (scannedThemeFiles.Count == 0)
                        {
                            string localTheme = Path.Combine(ProjectRoot, "engine", "ThemeTemplate");
                            if (File.Exists(localTheme))
                            {
                                scannedThemeFiles.Add(localTheme);
                            }
                        }

                        foreach (string tf in scannedThemeFiles)
                        {
                            try
                            {
                                byte[] bytes = File.ReadAllBytes(tf);
                                var doc = Template.Types.Document.Parser.ParseFrom(bytes);
                                string groupName = Path.GetFileName(Path.GetDirectoryName(tf) ?? "");
                                if (string.IsNullOrEmpty(groupName) || groupName.Equals("engine", StringComparison.OrdinalIgnoreCase))
                                {
                                    groupName = "Banklycs";
                                }

                                foreach (var slide in doc.Slides)
                                {
                                    themeList.Add(new
                                    {
                                        id = $"{groupName}:{slide.Name}",
                                        group = groupName,
                                        name = $"{groupName} • {slide.Name}",
                                        slide_name = slide.Name,
                                        file_path = tf,
                                        canvas = "1920 × 1080",
                                        lines = 2
                                    });
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"[WARN] Gagal mengurai file tema {tf}: {ex.Message}");
                            }
                        }

                        var fontsDir = Environment.GetFolderPath(Environment.SpecialFolder.Fonts);
                        // Per-user installs (double-click TTF -> "Install for me") live in
                        // %LOCALAPPDATA%\Microsoft\Windows\Fonts, not the system Fonts dir.
                        string userFontsDir = Path.Combine(
                            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                            "Microsoft", "Windows", "Fonts");
                        bool FileExistsInFonts(string name) =>
                            File.Exists(Path.Combine(fontsDir, name)) || File.Exists(Path.Combine(userFontsDir, name));

                        bool cmgInstalled = FileExistsInFonts("CMGSans-Bold.ttf");
                        bool timesNormalInstalled = FileExistsInFonts("Times New Normal Regular.ttf") ||
                                                    FileExistsInFonts("TimesNewNormal-Regular.ttf");
                        bool timesInstalled = File.Exists(Path.Combine(fontsDir, "times.ttf"));
                        bool arialInstalled = FileExistsInFonts("arial.ttf");

                        SendJson(req, res, new
                        {
                            active_theme = Program.ActiveSlideTemplateName,
                            cmg_font_installed = cmgInstalled,
                            times_font_installed = timesInstalled,
                            times_normal_installed = timesNormalInstalled,
                            arial_font_installed = arialInstalled,
                            themes = themeList,
                            propresenter_dir = ProPresenterDir
                        });
                        return;
                    }

                    if (rawPath.Equals("/api/songs", StringComparison.OrdinalIgnoreCase))
                    {
                        List<SongCatalogItem> snapshot;
                        lock (CatalogLock)
                        {
                            snapshot = Catalog;
                        }
                        string q = (req.QueryString["q"] ?? "").Trim().ToLowerInvariant();
                        string cat = (req.QueryString["category"] ?? "ALL").Trim().ToUpperInvariant();

                        // Clamp limit to prevent unbounded memory allocation
                        int limit = 100;
                        if (int.TryParse(req.QueryString["limit"], out int parsedLimit))
                        {
                            limit = Math.Clamp(parsedLimit, 1, 500);
                        }

                        string[] tokens = q.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                        List<SongCatalogItem> matched = new List<SongCatalogItem>(Math.Min(limit, 500));
                        int totalMatched = 0;

                        foreach (var item in snapshot)
                        {
                            if (cat != "ALL" && !item.category.Equals(cat, StringComparison.OrdinalIgnoreCase))
                            {
                                continue;
                            }

                            if (tokens.Length > 0)
                            {
                                bool matchAll = true;
                                for (int i = 0; i < tokens.Length; i++)
                                {
                                    if (!item.search_index.Contains(tokens[i], StringComparison.OrdinalIgnoreCase))
                                    {
                                        matchAll = false;
                                        break;
                                    }
                                }
                                if (!matchAll) continue;
                            }

                            totalMatched++;
                            if (matched.Count < limit)
                            {
                                matched.Add(item);
                            }
                        }

                        var result = new
                        {
                            count = matched.Count,
                            total_matched = totalMatched,
                            total_catalog = snapshot.Count,
                            songs = matched
                        };
                        SendJson(req, res, result);
                        return;
                    }

                    if (rawPath.Equals("/api/lyrics", StringComparison.OrdinalIgnoreCase))
                    {
                        string filename = (req.QueryString["file"] ?? "").Trim();
                        if (string.IsNullOrEmpty(filename))
                        {
                            SendProblem(req, res, 400, "Bad Request", "Parameter 'file' wajib disertakan.");
                            return;
                        }

                        string content = "";
                        string titleOnly = Path.GetFileNameWithoutExtension(filename);

                        if (File.Exists(DatabasePath))
                        {
                            try
                            {
                                string connStr = new SqliteConnectionStringBuilder
                                {
                                    DataSource = DatabasePath,
                                    Mode = SqliteOpenMode.ReadOnly
                                }.ToString();

                                using var conn = new SqliteConnection(connStr);
                                conn.Open();
                                using var cmd = conn.CreateCommand();
                                // Exact filename only: matching on title returned the wrong
                                // song for the 1,459 titles that exist in more than one hymnal.
                                cmd.CommandText = "SELECT filename, title, content FROM songs WHERE filename = @f LIMIT 1;";
                                cmd.Parameters.AddWithValue("@f", filename.EndsWith(".txt", StringComparison.OrdinalIgnoreCase) ? filename : filename + ".txt");
                                using var reader = cmd.ExecuteReader();
                                if (reader.Read())
                                {
                                    filename = reader.GetString(0);
                                    titleOnly = reader.GetString(1);
                                    content = reader.GetString(2);
                                }
                            }
                            catch (Exception dbEx)
                            {
                                Console.WriteLine($"[WARN] Gagal membaca lirik dari SQLite: {dbEx.Message}");
                            }
                        }

                        // Secure filesystem fallback: strictly forbid path traversal
                        if (string.IsNullOrEmpty(content) && Directory.Exists(DatabaseDir))
                        {
                            try
                            {
                                string safeBase = SanitizeDiskFileName(Path.GetFileNameWithoutExtension(filename)) + ".txt";
                                string targetFile = Path.GetFullPath(Path.Combine(DatabaseDir, safeBase));
                                string dbDirFull = Path.GetFullPath(DatabaseDir);

                                if (IsUnder(targetFile, dbDirFull) && File.Exists(targetFile))
                                {
                                    content = File.ReadAllText(targetFile, Encoding.UTF8);
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"[WARN] Fallback txt read error: {ex.Message}");
                            }
                        }

                        if (string.IsNullOrEmpty(content))
                        {
                            SendProblem(req, res, 404, "Not Found", "Lirik lagu tidak ditemukan dalam database.");
                            return;
                        }

                        string[] lines = content.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);

                        List<LyricsGroup> groups = new List<LyricsGroup>();
                        LyricsGroup curGroup = new LyricsGroup { header = "HEADER" };
                        List<string> curSlide = new List<string>();

                        foreach (string rawLine in lines)
                        {
                            string line = rawLine.Trim();
                            if (string.IsNullOrEmpty(line))
                            {
                                if (curSlide.Count > 0)
                                {
                                    curGroup.slides.Add(new List<string>(curSlide));
                                    curSlide.Clear();
                                }
                                continue;
                            }

                            if (HeaderRegex.IsMatch(line))
                            {
                                if (curSlide.Count > 0)
                                {
                                    curGroup.slides.Add(new List<string>(curSlide));
                                    curSlide.Clear();
                                }
                                if (curGroup.slides.Count > 0)
                                {
                                    groups.Add(curGroup);
                                }
                                curGroup = new LyricsGroup { header = line.ToUpperInvariant() };
                            }
                            else
                            {
                                curSlide.Add(line);
                            }
                        }

                        if (curSlide.Count > 0)
                        {
                            curGroup.slides.Add(new List<string>(curSlide));
                        }
                        if (curGroup.slides.Count > 0)
                        {
                            groups.Add(curGroup);
                        }

                        // Projection rule: max two lines per slide — mirror the
                        // compile-time split in ParseLyricContent so the preview
                        // matches what gets injected into ProPresenter.
                        foreach (LyricsGroup grp in groups)
                        {
                            if (grp.slides.All(s => s.Count <= 2)) continue;
                            var splitSlides = new List<List<string>>();
                            foreach (List<string> slide in grp.slides)
                            {
                                if (slide.Count <= 2)
                                {
                                    splitSlides.Add(slide);
                                    continue;
                                }
                                for (int i = 0; i < slide.Count; i += 2)
                                {
                                    splitSlides.Add(slide.Skip(i).Take(2).ToList());
                                }
                            }
                            grp.slides = splitSlides;
                        }

                        var lyricsData = new LyricsResponse
                        {
                            filename = filename,
                            title = titleOnly,
                            groups = groups,
                            raw = content
                        };

                        SendJson(req, res, lyricsData);
                        return;
                    }

                    // Guard: Block GET on mutating endpoints
                    if (rawPath.Equals("/api/banks/clean", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/banks/open", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/font/install", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/reload", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/themes/select", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/settings", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/update/db/apply", StringComparison.OrdinalIgnoreCase) ||
                        rawPath.Equals("/api/inject", StringComparison.OrdinalIgnoreCase))
                    {
                        SendProblem(req, res, 405, "Method Not Allowed", "Endpoint mutasi wajib dipanggil menggunakan HTTP POST.");
                        return;
                    }

                    // Serve static files from app directory
                    ServeStaticFile(req, res, rawPath);
                    return;
                }

                // ==========================================================
                // POST (State Mutating Endpoints)
                // ==========================================================
                if (req.HttpMethod.Equals("POST", StringComparison.OrdinalIgnoreCase))
                {
                    if (rawPath.Equals("/api/settings", StringComparison.OrdinalIgnoreCase))
                    {
                        string? settingsBody = ReadBodyWithLimit(req, 4_000);
                        if (settingsBody == null)
                        {
                            SendProblem(req, res, 413, "Payload Too Large", "Payload settings terlalu besar.");
                            return;
                        }
                        try
                        {
                            using var doc = JsonDocument.Parse(settingsBody);
                            if (doc.RootElement.TryGetProperty("app_auto_check", out var a)) AppAutoCheck = a.GetBoolean();
                            if (doc.RootElement.TryGetProperty("db_auto_check", out var b)) DbAutoCheck = b.GetBoolean();
                            if (doc.RootElement.TryGetProperty("protect_user_edits", out var c)) ProtectUserEdits = c.GetBoolean();
                            SaveAppConfig();
                        }
                        catch (Exception ex)
                        {
                            SendProblem(req, res, 400, "Bad Request", $"JSON settings tidak valid: {ex.Message}");
                            return;
                        }
                        SendJson(req, res, new
                        {
                            success = true,
                            app_auto_check = AppAutoCheck,
                            db_auto_check = DbAutoCheck,
                            protect_user_edits = ProtectUserEdits
                        });
                        return;
                    }

                    if (rawPath.Equals("/api/update/db/apply", StringComparison.OrdinalIgnoreCase))
                    {
                        var remoteManifest = FetchRemoteDbManifest();
                        if (remoteManifest == null || string.IsNullOrEmpty(remoteManifest.url))
                        {
                            SendProblem(req, res, 502, "Bad Gateway", "Manifest database tidak dapat diambil (offline?).");
                            return;
                        }

                        string tempDb = DatabasePath + ".update-tmp";
                        try
                        {
                            using (var downloadReq = new HttpRequestMessage(HttpMethod.Get, remoteManifest.url))
                            {
                                downloadReq.Headers.UserAgent.ParseAdd("Banklycs-Engine");
                                using var downloadRes = UpdateHttp.SendAsync(downloadReq).GetAwaiter().GetResult();
                                downloadRes.EnsureSuccessStatusCode();
                                using var stream = downloadRes.Content.ReadAsStreamAsync().GetAwaiter().GetResult();
                                using var file = new FileStream(tempDb, FileMode.Create, FileAccess.Write, FileShare.None);
                                stream.CopyTo(file);
                            }

                            string actualHash = Sha256File(tempDb);
                            if (!string.Equals(actualHash, remoteManifest.sha256, StringComparison.OrdinalIgnoreCase))
                            {
                                File.Delete(tempDb);
                                SendProblem(req, res, 502, "Checksum Mismatch", "File database yang diunduh gagal verifikasi SHA-256. Unduhan dibatalkan, database lama tetap utuh.");
                                return;
                            }

                            // Atomic swap: keep a one-step-back backup, replace the DB,
                            // then mirror the remote manifest locally as the new version record.
                            string backup = DatabasePath + ".bak";
                            if (File.Exists(DatabasePath)) File.Copy(DatabasePath, backup, overwrite: true);
                            File.Move(tempDb, DatabasePath, overwrite: true);
                            File.WriteAllText(DbManifestLocalPath,
                                JsonSerializer.Serialize(remoteManifest, new JsonSerializerOptions { WriteIndented = true }));

                            LoadCatalog();

                            SendJson(req, res, new
                            {
                                success = true,
                                db_version = remoteManifest.version,
                                total_songs = Catalog.Count
                            });
                        }
                        catch (Exception ex)
                        {
                            try { File.Delete(tempDb); } catch { }
                            SendProblem(req, res, 500, "Update Failed", $"Gagal memperbarui database: {ex.Message}");
                        }
                        return;
                    }

                    if (rawPath.Equals("/api/reload", StringComparison.OrdinalIgnoreCase))
                    {
                        LoadCatalog();
                        var reloadData = new
                        {
                            total_songs = Catalog.Count,
                            catalog_loaded_at = CatalogLoadedAt == DateTime.MinValue ? "" : CatalogLoadedAt.ToString("o"),
                            catalog_version = CatalogVersion
                        };
                        SendJson(req, res, reloadData);
                        return;
                    }

                    if (rawPath.Equals("/api/font/install", StringComparison.OrdinalIgnoreCase))
                    {
                        string fontPath = Path.Combine(ProjectRoot, "tools", "fonts", "CMGSans-Bold.ttf");
                        bool launched = false;
                        if (File.Exists(fontPath))
                        {
                            try
                            {
                                Process.Start(new ProcessStartInfo
                                {
                                    FileName = fontPath,
                                    UseShellExecute = true
                                });
                                launched = true;
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"[WARN] Font launch error: {ex.Message}");
                            }
                        }
                        SendJson(req, res, new { success = launched, font_path = fontPath });
                        return;
                    }

                    if (rawPath.Equals("/api/banks/open", StringComparison.OrdinalIgnoreCase))
                    {
                        bool opened = false;
                        if (!string.IsNullOrEmpty(ProPresenterDir))
                        {
                            string libBanks = Path.Combine(ProPresenterDir, "Libraries", "Banks");
                            if (Directory.Exists(libBanks))
                            {
                                try
                                {
                                    Process.Start(new ProcessStartInfo
                                    {
                                        FileName = libBanks,
                                        UseShellExecute = true
                                    });
                                    opened = true;
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine($"[WARN] Banks open error: {ex.Message}");
                                }
                            }
                        }
                        SendJson(req, res, new { success = opened });
                        return;
                    }

                    if (rawPath.Equals("/api/banks/clean", StringComparison.OrdinalIgnoreCase))
                    {
                        // Destructive and irreversible. A same-origin-only CSRF token keeps
                        // another localhost page from wiping the operator's library.
                        if (!string.Equals(req.Headers["X-Banklycs-Confirm"], "clean-banks", StringComparison.Ordinal))
                        {
                            SendProblem(req, res, 428, "Precondition Required", "Header X-Banklycs-Confirm: clean-banks wajib disertakan.");
                            return;
                        }

                        lock (InjectLock)
                        {
                            int deleted = 0;
                            int clearedPlaylists = 0;
                            if (!string.IsNullOrEmpty(ProPresenterDir))
                            {
                                string libBanks = Path.Combine(ProPresenterDir, "Libraries", "Banks");
                                if (Directory.Exists(libBanks))
                                {
                                    foreach (string f in Directory.GetFiles(libBanks, "*.pro"))
                                    {
                                        try { File.Delete(f); deleted++; }
                                        catch (Exception ex) { Console.WriteLine($"[WARN] Delete .pro error: {ex.Message}"); }
                                    }
                                }
                                string playlistDoc = Path.Combine(ProPresenterDir, "Playlists", "Library");
                                if (File.Exists(playlistDoc))
                                {
                                    try
                                    {
                                        byte[] bytes = File.ReadAllBytes(playlistDoc);
                                        var doc = PlaylistDocument.Parser.ParseFrom(bytes);
                                        if (doc.RootNode?.Playlists?.Playlists != null)
                                        {
                                            clearedPlaylists = doc.RootNode.Playlists.Playlists.Count;
                                            doc.RootNode.Playlists.Playlists.Clear();
                                            // ProPresenter may hold this file open; a partial in-place
                                            // write would corrupt the whole playlist document.
                                            Program.WriteAllBytesAtomic(playlistDoc, doc.ToByteArray());
                                        }
                                    }
                                    catch (Exception ex)
                                    {
                                        Console.WriteLine($"[WARN] Reset playlist error: {ex.Message}");
                                    }
                                }
                            }

                            SendJson(req, res, new
                            {
                                success = true,
                                deleted_songs = deleted,
                                cleared_playlists = clearedPlaylists,
                                message = $"Bersih: {deleted} presentasi dihapus dari Banks, {clearedPlaylists} playlist direset."
                            });
                            return;
                        }
                    }

                    if (rawPath.Equals("/api/themes/select", StringComparison.OrdinalIgnoreCase))
                    {
                        string? body = ReadBodyWithLimit(req, 100_000);
                        if (body == null)
                        {
                            SendProblem(req, res, 413, "Payload Too Large", "Ukuran payload melebihi batas 100KB.");
                            return;
                        }

                        try
                        {
                            using var jsonDoc = JsonDocument.Parse(body);
                            if (jsonDoc.RootElement.TryGetProperty("slide_name", out var prop))
                            {
                                string chosen = prop.GetString() ?? "";
                                if (!string.IsNullOrWhiteSpace(chosen))
                                {
                                    Program.ActiveSlideTemplateName = chosen.Trim();
                                    Program.ResetThemeCache();
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[WARN] Gagal parse JSON tema: {ex.Message}");
                        }

                        SendJson(req, res, new { success = true, active_theme = Program.ActiveSlideTemplateName });
                        return;
                    }

                    if (rawPath.Equals("/api/inject", StringComparison.OrdinalIgnoreCase))
                    {
                        if (!string.Equals(req.Headers["X-Banklycs-Inject"], "1", StringComparison.Ordinal))
                        {
                            SendProblem(req, res, 428, "Precondition Required", "Header X-Banklycs-Inject: 1 wajib disertakan.");
                            return;
                        }

                        string? body = ReadBodyWithLimit(req, 1_000_000);
                        if (body == null)
                        {
                            SendProblem(req, res, 413, "Payload Too Large", "Ukuran payload melebihi batas 1MB.");
                            return;
                        }

                        InjectRequest? data = null;
                        try
                        {
                            data = JsonSerializer.Deserialize<InjectRequest>(body, new JsonSerializerOptions
                            {
                                PropertyNameCaseInsensitive = true
                            });
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[WARN] Gagal deserialize request inject: {ex.Message}");
                        }

                        if (data == null || data.songs == null || data.songs.Count == 0)
                        {
                            SendProblem(req, res, 400, "Bad Request", "Daftar lagu kosong atau JSON tidak valid.");
                            return;
                        }

                        if (string.IsNullOrEmpty(ProPresenterDir) || !Directory.Exists(ProPresenterDir))
                        {
                            SendProblem(req, res, 500, "ProPresenter Not Found", "Folder ProPresenter tidak ditemukan di sistem.");
                            return;
                        }

                        string libBanks = Path.GetFullPath(Path.Combine(ProPresenterDir, "Libraries", "Banks"));
                        Directory.CreateDirectory(libBanks);

                        // Validate against path traversal
                        foreach (string raw in data.songs)
                        {
                            string probe = raw.Trim();
                            if (probe.EndsWith(".pro", StringComparison.OrdinalIgnoreCase))
                                probe = probe.Substring(0, probe.Length - 4);
                            else if (probe.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                                probe = probe.Substring(0, probe.Length - 4);

                            string safeProbe = SanitizeDiskFileName(probe);
                            try
                            {
                                string target = Path.GetFullPath(Path.Combine(libBanks, safeProbe + ".pro"));
                                if (!IsUnder(target, libBanks))
                                {
                                    SendProblem(req, res, 400, "Invalid Song Name", $"Nama lagu tidak valid: {raw}");
                                    return;
                                }
                            }
                            catch (Exception pathEx)
                            {
                                Console.WriteLine($"[WARN] Nama lagu tidak dapat diresolusi ({raw}): {pathEx.Message}");
                                SendProblem(req, res, 400, "Invalid Song Name", $"Nama lagu tidak valid: {raw}");
                                return;
                            }
                        }

                        lock (InjectLock)
                        {
                            int compiledCount = 0;
                            List<string> missingFiles = new List<string>();
                            List<string> skippedModified = new List<string>();
                            var compiledThisRun = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                            var playlistEligible = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

                            SqliteConnection? dbConn = null;
                            if (File.Exists(DatabasePath))
                            {
                                try
                                {
                                    string connStr = new SqliteConnectionStringBuilder
                                    {
                                        DataSource = DatabasePath,
                                        Mode = SqliteOpenMode.ReadOnly
                                    }.ToString();
                                    dbConn = new SqliteConnection(connStr);
                                    dbConn.Open();
                                }
                                catch (Exception dbEx)
                                {
                                    Console.WriteLine($"[WARN] Gagal membuka banklycs.db untuk inject on-demand: {dbEx.Message}");
                                }
                            }

                            try
                            {
                                foreach (string s in data.songs)
                                {
                                    string cleanName = s.Trim();
                                    if (cleanName.EndsWith(".pro", StringComparison.OrdinalIgnoreCase))
                                    {
                                        cleanName = cleanName.Substring(0, cleanName.Length - 4);
                                    }
                                    else if (cleanName.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                                    {
                                        cleanName = cleanName.Substring(0, cleanName.Length - 4);
                                    }

                                    string safeBaseName = SanitizeDiskFileName(cleanName);
                                    string proFileName = safeBaseName + ".pro";
                                    string dstFile = Path.Combine(libBanks, proFileName);

                                    // Protection: never silently overwrite a .pro file the
                                    // operator edited inside ProPresenter. A file counts as
                                    // "ours" only when its bytes still match what we injected
                                    // last time; anything else is treated as a user edit.
                                    if (ProtectUserEdits && File.Exists(dstFile))
                                    {
                                        string currentHash = Sha256File(dstFile);
                                        InjectState.TryGetValue(proFileName, out string? injectedHash);
                                        if (injectedHash == null || !injectedHash.Equals(currentHash, StringComparison.OrdinalIgnoreCase))
                                        {
                                            skippedModified.Add(proFileName);
                                            // The edited file still exists in the library, so it
                                            // stays playlist-eligible — just not overwritten.
                                            playlistEligible.Add(proFileName);
                                            continue;
                                        }
                                    }

                                    bool compiled = false;
                                    string songTitle = cleanName;
                                    string songContent = "";

                                    if (dbConn != null)
                                    {
                                        using var cmd = dbConn.CreateCommand();
                                        // The exact catalog filename wins; the sanitized form is
                                        // only a legacy fallback, never a silent override.
                                        cmd.CommandText = "SELECT title, content, filename FROM songs WHERE filename = @f OR filename = @safeF ORDER BY (filename = @f) DESC, id LIMIT 1;";
                                        cmd.Parameters.AddWithValue("@f", cleanName + ".txt");
                                        cmd.Parameters.AddWithValue("@safeF", safeBaseName + ".txt");
                                        using var r = cmd.ExecuteReader();
                                        if (r.Read())
                                        {
                                            songTitle = r.GetString(0);
                                            songContent = r.GetString(1);
                                        }
                                    }

                                    if (!string.IsNullOrEmpty(songContent))
                                    {
                                        compiled = Program.CompileAndSaveSong(songTitle, songContent, dstFile, ProjectRoot, ProPresenterDir);
                                    }
                                    else
                                    {
                                        // Fallback: check loose txt file with path traversal guard
                                        try
                                        {
                                            string txtFile = Path.GetFullPath(Path.Combine(DatabaseDir, safeBaseName + ".txt"));
                                            string dbDirFull = Path.GetFullPath(DatabaseDir);
                                            if (IsUnder(txtFile, dbDirFull) && File.Exists(txtFile))
                                            {
                                                songContent = File.ReadAllText(txtFile, Encoding.UTF8);
                                                compiled = Program.CompileAndSaveSong(songTitle, songContent, dstFile, ProjectRoot, ProPresenterDir);
                                            }
                                            else
                                            {
                                                string srcPro = Path.Combine(ProDir, proFileName);
                                                if (File.Exists(srcPro))
                                                {
                                                    File.Copy(srcPro, dstFile, overwrite: true);
                                                    compiled = true;
                                                }
                                            }
                                        }
                                        catch (Exception ex)
                                        {
                                            Console.WriteLine($"[WARN] Fallback compile error: {ex.Message}");
                                        }
                                    }

                                    if (compiled && File.Exists(dstFile))
                                    {
                                        compiledCount++;
                                        compiledThisRun.Add(proFileName);
                                        InjectState[proFileName] = Sha256File(dstFile);
                                    }
                                    else
                                    {
                                        missingFiles.Add(proFileName);
                                    }
                                }
                            }
                            finally
                            {
                                dbConn?.Dispose();
                            }

                            SaveInjectState();

                            // IN-PROCESS ATOMIC CALL TO CREATE PLAYLIST
                            // Register only songs compiled/verified in this exact execution
                            string playlistDocPath = Path.Combine(ProPresenterDir, "Playlists", "Library");
                            List<string> songNamesForPlaylist = new List<string>();
                            foreach (string s in data.songs)
                            {
                                string c = s.Trim();
                                if (c.EndsWith(".pro", StringComparison.OrdinalIgnoreCase))
                                    c = c.Substring(0, c.Length - 4);
                                else if (c.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                                    c = c.Substring(0, c.Length - 4);
                                string safeC = SanitizeDiskFileName(c) + ".pro";
                                if (compiledThisRun.Contains(safeC) || playlistEligible.Contains(safeC))
                                {
                                    songNamesForPlaylist.Add(safeC);
                                }
                            }

                            if (songNamesForPlaylist.Count > 0)
                            {
                                Program.CreatePlaylistDirect(playlistDocPath, data.name, songNamesForPlaylist, libBanks);
                            }

                            string outputMsg = $"[OK] Playlist '{data.name}': {compiledCount} dari {data.songs.Count} lagu dikompilasi";
                            if (skippedModified.Count > 0)
                                outputMsg += $", {skippedModified.Count} dilewati (sudah diedit di ProPresenter)";
                            if (missingFiles.Count > 0)
                                outputMsg += $", {missingFiles.Count} gagal";
                            outputMsg += ".";

                            var injectResult = new
                            {
                                success = missingFiles.Count == 0,
                                partial = missingFiles.Count > 0 && compiledCount > 0,
                                playlist = data.name,
                                songs_count = data.songs.Count,
                                compiled_to_library = compiledCount,
                                skipped_modified = skippedModified,
                                skipped_count = skippedModified.Count,
                                missing_in_pro = missingFiles,
                                engine_output = outputMsg
                            };

                            SendJson(req, res, injectResult, missingFiles.Count == data.songs.Count ? 500 : 200);
                            return;
                        }
                    }
                }

                SendProblem(req, res, 404, "Not Found", "Endpoint tidak ditemukan.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Handler error: {ex.Message}");
                SendProblem(req, res, 500, "Internal Server Error", "Terjadi kesalahan internal pada server.");
            }
        }

        private static void ServeStaticFile(HttpListenerRequest req, HttpListenerResponse res, string urlPath)
        {
            string relPath = urlPath.TrimStart('/');
            if (string.IsNullOrEmpty(relPath)) relPath = "index.html";

            // Sanitize against directory traversal
            relPath = relPath.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
            string fullPath = Path.GetFullPath(Path.Combine(AppDir, relPath));
            string appDirFull = Path.GetFullPath(AppDir);

            if (!IsUnder(fullPath, appDirFull) || !File.Exists(fullPath))
            {
                SendProblem(req, res, 404, "File Not Found", "Berkas tidak ditemukan.");
                return;
            }

            string ext = Path.GetExtension(fullPath).ToLowerInvariant();
            string contentType = ext switch
            {
                ".html" or ".htm" => "text/html; charset=utf-8",
                ".css" => "text/css; charset=utf-8",
                ".js" => "application/javascript; charset=utf-8",
                ".json" => "application/json; charset=utf-8",
                ".png" => "image/png",
                ".jpg" or ".jpeg" => "image/jpeg",
                ".svg" => "image/svg+xml",
                ".ico" => "image/x-icon",
                ".ttf" => "font/ttf",
                _ => "application/octet-stream"
            };

            byte[] bytes = File.ReadAllBytes(fullPath);
            res.ContentType = contentType;
            res.ContentLength64 = bytes.Length;
            res.StatusCode = 200;
            // Local console: no framing, no MIME sniffing, no remote origins.
            // Inline styles stay allowed for the --pro-scale custom property;
            // the favicon is a data: SVG.
            res.Headers.Add("X-Content-Type-Options", "nosniff");
            res.Headers.Add("X-Frame-Options", "DENY");
            res.Headers.Add("Referrer-Policy", "no-referrer");
            res.Headers.Add("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");

            if (!req.HttpMethod.Equals("HEAD", StringComparison.OrdinalIgnoreCase))
            {
                res.OutputStream.Write(bytes, 0, bytes.Length);
            }
            res.Close();
        }

        private static void SendJson(HttpListenerRequest req, HttpListenerResponse res, object data, int statusCode = 200, string contentType = "application/json; charset=utf-8")
        {
            string json = JsonSerializer.Serialize(data, new JsonSerializerOptions
            {
                WriteIndented = false
            });
            byte[] bytes = Encoding.UTF8.GetBytes(json);

            res.ContentType = contentType;
            res.ContentLength64 = bytes.Length;
            res.StatusCode = statusCode;

            if (!req.HttpMethod.Equals("HEAD", StringComparison.OrdinalIgnoreCase))
            {
                res.OutputStream.Write(bytes, 0, bytes.Length);
            }
            res.Close();
        }
    }
}
