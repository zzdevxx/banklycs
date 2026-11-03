using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;

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
        private static string ProjectRoot = "";
        private static string DatabasePath = "";
        private static string DatabaseDir = "";
        private static string ProDir = "";
        private static string AppDir = "";
        private static string? ProPresenterDir = null;

        private static readonly Regex HeaderRegex = new Regex(
            @"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        private static string ResolveProPresenterDir()
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

        private static void LoadCatalog()
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

            Catalog = items;
            sw.Stop();
            Console.WriteLine($"[CATALOG] Sukses memuat {Catalog.Count:N0} lagu ke RAM dalam {sw.ElapsedMilliseconds} ms!");
        }

        public static void Start(string rootPath, int preferredPort = 5050)
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
                return;
            }

            string serverUrl = $"http://127.0.0.1:{port}";
            Console.WriteLine("==============================================================================");
            Console.WriteLine("  BANKLYCS NATIVE STUDIO CONSOLE (C# .NET 8 / ZERO-DEPENDENCY)");
            Console.WriteLine($"  URL              : {serverUrl}");
            Console.WriteLine($"  ProPresenter Dir : {(string.IsNullOrEmpty(ProPresenterDir) ? "[TIDAK TERDETEKSI]" : ProPresenterDir)}");
            Console.WriteLine($"  Database Vault   : {(File.Exists(DatabasePath) ? DatabasePath : DatabaseDir)} ({Catalog.Count:N0} lagu)");
            Console.WriteLine("==============================================================================");
            Console.WriteLine("[INFO] Tekan Ctrl+C untuk menutup server.");

            // Launch Native Edge App Window
            Task.Run(() =>
            {
                Thread.Sleep(400);
                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = "msedge",
                        Arguments = $"--app={serverUrl} --window-size=1600,900",
                        UseShellExecute = true
                    });
                }
                catch
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = serverUrl,
                            UseShellExecute = true
                        });
                    }
                    catch { }
                }
            });

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

        private static void ProcessRequest(HttpListenerContext context)
        {
            HttpListenerRequest req = context.Request;
            HttpListenerResponse res = context.Response;

            // Add CORS
            res.Headers.Add("Access-Control-Allow-Origin", "*");
            res.Headers.Add("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS");
            res.Headers.Add("Access-Control-Allow-Headers", "Content-Type");

            if (req.HttpMethod.Equals("OPTIONS", StringComparison.OrdinalIgnoreCase))
            {
                res.StatusCode = 204;
                res.Close();
                return;
            }

            string rawPath = req.Url?.AbsolutePath ?? "/";

            try
            {
                if (req.HttpMethod.Equals("GET", StringComparison.OrdinalIgnoreCase) ||
                    req.HttpMethod.Equals("HEAD", StringComparison.OrdinalIgnoreCase))
                {
                    if (rawPath.Equals("/api/status", StringComparison.OrdinalIgnoreCase))
                    {
                        var statusData = new
                        {
                            total_songs = Catalog.Count,
                            propresenter_dir = ProPresenterDir,
                            project_root = ProjectRoot
                        };
                        SendJson(req, res, statusData);
                        return;
                    }

                    if (rawPath.Equals("/api/songs", StringComparison.OrdinalIgnoreCase))
                    {
                        string q = (req.QueryString["q"] ?? "").Trim().ToLowerInvariant();
                        string cat = (req.QueryString["category"] ?? "ALL").Trim().ToUpperInvariant();
                        int limit = 100;
                        if (int.TryParse(req.QueryString["limit"], out int parsedLimit) && parsedLimit > 0)
                        {
                            limit = parsedLimit;
                        }

                        string[] tokens = q.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                        List<SongCatalogItem> matched = new List<SongCatalogItem>(Math.Min(limit, 500));

                        foreach (var item in Catalog)
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

                            matched.Add(item);
                            if (matched.Count >= limit) break;
                        }

                        var result = new
                        {
                            count = matched.Count,
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
                            SendJson(req, res, new { error = "Parameter file kosong" }, 400);
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
                                cmd.CommandText = "SELECT filename, title, content FROM songs WHERE filename = @f OR title = @f OR filename = @f_txt LIMIT 1;";
                                cmd.Parameters.AddWithValue("@f", filename);
                                cmd.Parameters.AddWithValue("@f_txt", filename.EndsWith(".txt", StringComparison.OrdinalIgnoreCase) ? filename : filename + ".txt");
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

                        if (string.IsNullOrEmpty(content))
                        {
                            string filePath = Path.Combine(DatabaseDir, filename);
                            if (!File.Exists(filePath) && !filename.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                            {
                                filePath = Path.Combine(DatabaseDir, filename + ".txt");
                            }
                            if (File.Exists(filePath))
                            {
                                content = File.ReadAllText(filePath, Encoding.UTF8);
                            }
                        }

                        if (string.IsNullOrEmpty(content))
                        {
                            SendJson(req, res, new { error = "File lagu tidak ditemukan" }, 404);
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

                    // Serve static files from app directory
                    ServeStaticFile(req, res, rawPath);
                    return;
                }

                if (req.HttpMethod.Equals("POST", StringComparison.OrdinalIgnoreCase))
                {
                    if (rawPath.Equals("/api/inject", StringComparison.OrdinalIgnoreCase))
                    {
                        using var reader = new StreamReader(req.InputStream, req.ContentEncoding);
                        string body = reader.ReadToEnd();

                        InjectRequest? data = null;
                        try
                        {
                            data = JsonSerializer.Deserialize<InjectRequest>(body, new JsonSerializerOptions
                            {
                                PropertyNameCaseInsensitive = true
                            });
                        }
                        catch { }

                        if (data == null || data.songs == null || data.songs.Count == 0)
                        {
                            SendJson(req, res, new { error = "Daftar lagu kosong" }, 400);
                            return;
                        }

                        if (string.IsNullOrEmpty(ProPresenterDir) || !Directory.Exists(ProPresenterDir))
                        {
                            SendJson(req, res, new { error = "Folder ProPresenter tidak ditemukan di sistem" }, 500);
                            return;
                        }

                        string libBanks = Path.Combine(ProPresenterDir, "Libraries", "Banks");
                        Directory.CreateDirectory(libBanks);

                        int compiledCount = 0;
                        List<string> missingFiles = new List<string>();

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

                                string proFileName = cleanName + ".pro";
                                string dstFile = Path.Combine(libBanks, proFileName);

                                bool compiled = false;
                                string songTitle = cleanName;
                                string songContent = "";

                                if (dbConn != null)
                                {
                                    using var cmd = dbConn.CreateCommand();
                                    cmd.CommandText = "SELECT title, content FROM songs WHERE filename = @f OR title = @f OR filename = @f_txt LIMIT 1;";
                                    cmd.Parameters.AddWithValue("@f", cleanName);
                                    cmd.Parameters.AddWithValue("@f_txt", cleanName + ".txt");
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
                                    // Fallback: check loose txt file
                                    string txtFile = Path.Combine(DatabaseDir, cleanName + ".txt");
                                    if (File.Exists(txtFile))
                                    {
                                        songContent = File.ReadAllText(txtFile, Encoding.UTF8);
                                        compiled = Program.CompileAndSaveSong(songTitle, songContent, dstFile, ProjectRoot, ProPresenterDir);
                                    }
                                    else
                                    {
                                        // Fallback: check pre-existing .pro file in ProDir
                                        string srcPro = Path.Combine(ProDir, proFileName);
                                        if (File.Exists(srcPro))
                                        {
                                            File.Copy(srcPro, dstFile, overwrite: true);
                                            compiled = true;
                                        }
                                    }
                                }

                                if (compiled && File.Exists(dstFile))
                                {
                                    compiledCount++;
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

                        // IN-PROCESS ATOMIC CALL TO CREATE PLAYLIST (ZERO SUBPROCESS!)
                        string playlistDocPath = Path.Combine(ProPresenterDir, "Playlists", "Library");
                        List<string> songNamesForPlaylist = data.songs
                            .Select(s => s.EndsWith(".pro", StringComparison.OrdinalIgnoreCase) ? s : s + ".pro")
                            .ToList();

                        Program.CreatePlaylistDirect(playlistDocPath, data.name, songNamesForPlaylist, libBanks);

                        var injectResult = new
                        {
                            success = true,
                            playlist = data.name,
                            songs_count = data.songs.Count,
                            compiled_to_library = compiledCount,
                            missing_in_pro = missingFiles,
                            engine_output = $"[OK] Playlist '{data.name}' berhasil disuntikkan secara on-demand ({data.songs.Count} lagu)!"
                        };

                        SendJson(req, res, injectResult);
                        return;
                    }
                }

                SendJson(req, res, new { error = "Endpoint tidak ditemukan" }, 404);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Handler error: {ex.Message}");
                try
                {
                    SendJson(req, res, new { error = ex.Message }, 500);
                }
                catch { }
            }
        }

        private static void ServeStaticFile(HttpListenerRequest req, HttpListenerResponse res, string urlPath)
        {
            string relPath = urlPath.TrimStart('/');
            if (string.IsNullOrEmpty(relPath)) relPath = "index.html";

            // Sanitize against directory traversal
            relPath = relPath.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
            string fullPath = Path.GetFullPath(Path.Combine(AppDir, relPath));

            if (!fullPath.StartsWith(AppDir, StringComparison.OrdinalIgnoreCase) || !File.Exists(fullPath))
            {
                SendJson(req, res, new { error = "File not found" }, 404);
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
                _ => "application/octet-stream"
            };

            byte[] bytes = File.ReadAllBytes(fullPath);
            res.ContentType = contentType;
            res.ContentLength64 = bytes.Length;
            res.StatusCode = 200;

            if (!req.HttpMethod.Equals("HEAD", StringComparison.OrdinalIgnoreCase))
            {
                res.OutputStream.Write(bytes, 0, bytes.Length);
            }
            res.Close();
        }

        private static void SendJson(HttpListenerRequest req, HttpListenerResponse res, object data, int statusCode = 200)
        {
            string json = JsonSerializer.Serialize(data, new JsonSerializerOptions
            {
                WriteIndented = false
            });
            byte[] bytes = Encoding.UTF8.GetBytes(json);

            res.ContentType = "application/json; charset=utf-8";
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
