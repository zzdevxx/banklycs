using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using Google.Protobuf;
using Microsoft.Data.Sqlite;
using Pro.SerializationInterop.RVProtoData;

internal class Program
{
	public class ParsedGroup
	{
		public string Name { get; set; } = "";
		public string RawHeader { get; set; } = "";
		public List<List<string>> Slides { get; set; } = new List<List<string>>();
	}

	// BAIT/REFF are the Indonesian section names used by KJ/NKB/PKJ hymnals.
	// RULES.md promises the engine normalizes them, so they are part of the header set here.
	private static readonly Regex HeaderRegex = new Regex("^(BLANK|INTRO|VERSE(\\s+\\d+)?|PRE[\\s\\-]*CHORUS(\\s+\\d+)?|CHORUS(\\s+\\d+)?|BRIDGE(\\s+\\d+)?|TAG|INTERLUDE|ENDING|OUTRO|BAIT(\\s+\\d+)?|REFF(\\s+\\d+)?)$", RegexOptions.IgnoreCase | RegexOptions.Compiled);

	// ProPresenter keeps its .pro files and Playlists/Library open while it runs.
	// An in-place partial write would leave a corrupt protobuf, so every mutation goes
	// through a same-directory temp file and an atomic rename over the target.
	internal static void WriteAllBytesAtomic(string targetPath, byte[] bytes)
	{
		string dir = Path.GetDirectoryName(targetPath) ?? "";
		if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
		{
			Directory.CreateDirectory(dir);
		}
		string tmp = targetPath + ".tmp-" + Guid.NewGuid().ToString("N");
		try
		{
			File.WriteAllBytes(tmp, bytes);
			File.Move(tmp, targetPath, overwrite: true);
		}
		finally
		{
			if (File.Exists(tmp))
			{
				try { File.Delete(tmp); }
				catch (Exception cleanupEx) { Console.WriteLine($"[WARN] Temp cleanup failed for {tmp}: {cleanupEx.Message}"); }
			}
		}
	}

	public static void CreatePlaylistDirect(string playlistDocPath, string playlistName, List<string> songFileNames, string proBanksDir)
	{
		CreatePlaylist(playlistDocPath, playlistName, songFileNames, proBanksDir);
	}

	private static string ResolveWorkspaceRoot(string[] args)
	{
		if (args.Length > 0 && !string.IsNullOrWhiteSpace(args[0]) && Directory.Exists(args[0]) && !args[0].StartsWith("-"))
		{
			return Path.GetFullPath(args[0]);
		}

		string currentDir = Directory.GetCurrentDirectory();
		if (Directory.Exists(Path.Combine(currentDir, "database")) || Directory.Exists(Path.Combine(currentDir, "TXT")))
		{
			return currentDir;
		}

		string baseDir = AppContext.BaseDirectory;
		if (Directory.Exists(Path.Combine(baseDir, "database")) || Directory.Exists(Path.Combine(baseDir, "TXT")))
		{
			return baseDir;
		}

		string parent = Directory.GetParent(baseDir)?.FullName;
		if (parent != null && (Directory.Exists(Path.Combine(parent, "database")) || Directory.Exists(Path.Combine(parent, "TXT"))))
		{
			return parent;
		}

		string grandParent = Directory.GetParent(parent ?? "")?.FullName;
		if (grandParent != null && (Directory.Exists(Path.Combine(grandParent, "database")) || Directory.Exists(Path.Combine(grandParent, "TXT"))))
		{
			return grandParent;
		}

		return Directory.GetCurrentDirectory();
	}

	private static void Main(string[] args)
	{
		Console.OutputEncoding = Encoding.UTF8;

		// Sub-command: create-playlist <json_path>
		if (args.Length >= 2 && args[0].Equals("create-playlist", StringComparison.OrdinalIgnoreCase))
		{
			HandleCreatePlaylistCommand(args[1]);
			return;
		}

		string path = ResolveWorkspaceRoot(args);

		// Sub-command: export-txt [target_dir]
		if (args.Length >= 1 && args[0].Equals("export-txt", StringComparison.OrdinalIgnoreCase))
		{
			string target = args.Length >= 2 ? args[1] : Path.Combine(path, "database", "txt");
			ExportTxt(path, target);
			return;
		}

		// Sub-command: clean-propresenter / clean
		if (args.Length >= 1 && (args[0].Equals("clean-propresenter", StringComparison.OrdinalIgnoreCase) ||
		                         args[0].Equals("clean", StringComparison.OrdinalIgnoreCase)))
		{
			CleanProPresenter(path);
			return;
		}

		// Default execution (Double-Click or --server): Start Native Studio Console
		bool isCompile = args.Any(a => a.Equals("--compile", StringComparison.OrdinalIgnoreCase) ||
		                              a.Equals("--full", StringComparison.OrdinalIgnoreCase) ||
		                              a.Equals("-Full", StringComparison.OrdinalIgnoreCase));

		if (!isCompile)
		{
			int port = 5050;
			for (int i = 0; i < args.Length; i++)
			{
				if (args[i].Equals("--server", StringComparison.OrdinalIgnoreCase) && i + 1 < args.Length && int.TryParse(args[i + 1], out int p))
				{
					port = p;
				}
			}
			bool noBrowser = args.Any(a => a.Equals("--no-browser", StringComparison.OrdinalIgnoreCase));
			Banklycs.StudioServer.Start(path, port, openBrowser: !noBrowser);
			return;
		}

		Console.WriteLine("==============================================================================");
		Console.WriteLine("PROPRESENTER 7 MASTER ENGINE (THEME ZZ - MASTER BANKS UNIFIED)");
		Console.WriteLine("==============================================================================");
		Console.WriteLine($"[INFO] Workspace Path : {path}");

		// 2. Resolve ProPresenter documents path
		string proPresenterDir = null;
		if (args.Length > 1 && !string.IsNullOrWhiteSpace(args[1]) && Directory.Exists(args[1]))
		{
			proPresenterDir = Path.GetFullPath(args[1]);
		}
		else
		{
			string personal = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
			string candidate = Path.Combine(personal, "ProPresenter");
			if (Directory.Exists(candidate))
			{
				proPresenterDir = candidate;
			}
			else
			{
				string oneDrive = Environment.GetEnvironmentVariable("OneDrive");
				if (!string.IsNullOrEmpty(oneDrive))
				{
					candidate = Path.Combine(oneDrive, "Documents", "ProPresenter");
					if (Directory.Exists(candidate)) proPresenterDir = candidate;
					else
					{
						candidate = Path.Combine(oneDrive, "Dokumen", "ProPresenter");
						if (Directory.Exists(candidate)) proPresenterDir = candidate;
					}
				}
			}
		}

		// 3. Resolve Theme Template
		string themePath = null;
		if (proPresenterDir != null)
		{
			string t = Path.Combine(proPresenterDir, "Themes\\zz\\Theme");
			if (File.Exists(t)) themePath = t;
			else
			{
				t = Path.Combine(proPresenterDir, "Themes\\xx\\Theme");
				if (File.Exists(t)) themePath = t;
			}
		}

		if (themePath == null || !File.Exists(themePath))
		{
			string localTheme = Path.Combine(path, "Engine\\ThemeTemplate");
			if (File.Exists(localTheme)) themePath = localTheme;
			else
			{
				localTheme = Path.Combine(AppContext.BaseDirectory, "ThemeTemplate");
				if (File.Exists(localTheme)) themePath = localTheme;
			}
		}

		if (themePath == null || !File.Exists(themePath))
		{
			Console.WriteLine("[ERROR] File Tema tidak ditemukan di ProPresenter maupun Engine local fallback!");
			Environment.ExitCode = 1;
			return;
		}

		byte[] data = File.ReadAllBytes(themePath);
		Template.Types.Document themeDoc = Template.Types.Document.Parser.ParseFrom(data);
		Template.Types.Slide slidePraise = themeDoc.Slides.FirstOrDefault((Template.Types.Slide s) => s.Name == "Lyric - Praise");
		if (slidePraise == null)
		{
			slidePraise = themeDoc.Slides.FirstOrDefault();
		}
		if (slidePraise == null)
		{
			Console.WriteLine("[ERROR] Tidak ada slide template yang ditemukan di Tema!");
			Environment.ExitCode = 1;
			return;
		}
		Console.WriteLine("[OK] Tema berhasil dimuat (" + themePath + "):");
		Console.WriteLine($"     - Total slide dalam tema : {themeDoc.Slides.Count}");
		Console.WriteLine("     - Default Template Slide : " + slidePraise.Name + " (CMGSans-Bold, fs134, Canvas 1920x1080)");

		// 4. Clean & Register Libraries
		string libBanks = null;
		bool fullRun = args.Any((string a) => a.Equals("--full", StringComparison.OrdinalIgnoreCase));
		// Only an explicit --full may delete anything. A fresh clone without a manifest
		// used to take this path and wipe the operator's Banks and playlists.
		bool destructiveRun = fullRun;
		if (proPresenterDir != null && Directory.Exists(Path.Combine(proPresenterDir, "Libraries")))
		{
			string text2 = Path.Combine(proPresenterDir, "Libraries");
			if (destructiveRun)
			{
				Console.WriteLine("\n[1/3] Membersihkan & Mengatur ProPresenter Libraries (REBUILD Penuh)...");
				string[] array = new string[8] { "A - IP26", "B - IP26", "A - Statics", "B - Statics", "X - Andreas", "Sesi 1", "Sesi 2", "Temp" };
				foreach (string text3 in array)
				{
					string path3 = Path.Combine(text2, text3);
					if (Directory.Exists(path3))
					{
						try
						{
							Directory.Delete(path3, recursive: true);
							Console.WriteLine("  -> Menghapus library lama/sesi: " + text3);
						}
						catch (Exception ex)
						{
							Console.WriteLine("  [WARN] Tidak dapat menghapus " + text3 + ": " + ex.Message);
						}
					}
				}
				libBanks = Path.Combine(text2, "Banks");
				Directory.CreateDirectory(libBanks);
				foreach (string path4 in Directory.GetFiles(libBanks, "*.pro"))
				{
					try { File.Delete(path4); }
					catch (Exception delEx) { Console.WriteLine($"  [WARN] Tidak dapat menghapus {path4}: {delEx.Message}"); }
				}
				Console.WriteLine("  -> Folder ProPresenter Library 'Banks' dibersihkan total.");
			}
			else
			{
				Console.WriteLine("\n[1/3] Mode Incremental: library lain & file .pro existing DIAMANKAN (tidak dibersihkan).");
				libBanks = Path.Combine(text2, "Banks");
				Directory.CreateDirectory(libBanks);
			}
			RegisterLibraries(text2);
		}
		else
		{
			Console.WriteLine("\n[1/3] Skip library ProPresenter (tidak ada folder Libraries aktif), fokus ke direktori output workspace...");
		}

		string path5 = Path.Combine(path, "database", "txt");
		if (!Directory.Exists(path5)) path5 = Path.Combine(path, "database");
		if (!Directory.Exists(path5)) path5 = Path.Combine(path, "TXT");

		string proBanksDir = Path.Combine(path, "database", "pro");
		if (!Directory.Exists(proBanksDir)) proBanksDir = Path.Combine(path, "engine", "PRO");
		if (!Directory.Exists(proBanksDir)) proBanksDir = Path.Combine(path, "PRO");
		Directory.CreateDirectory(proBanksDir);

		// Deteksi mode penuh lebih awal: penghapusan massal HANYA terjadi pada rebuild --full.
		string manifestPathEarly = Path.Combine(path, "engine", "compile_manifest.json");
		if (!File.Exists(manifestPathEarly) && File.Exists(Path.Combine(path, "Engine", "compile_manifest.json")))
		{
			manifestPathEarly = Path.Combine(path, "Engine", "compile_manifest.json");
		}
		bool fullRebuildEarly = args.Any((string a) => a.Equals("--full", StringComparison.OrdinalIgnoreCase));
		if (fullRebuildEarly)
		{
			foreach (string path6 in Directory.GetFiles(proBanksDir, "*.pro"))
			{
				try { File.Delete(path6); }
				catch (Exception delEx) { Console.WriteLine($"[WARN] Tidak dapat menghapus {path6}: {delEx.Message}"); }
			}
		}

		string[] bankFiles = Directory.GetFiles(path5, "*.txt", SearchOption.AllDirectories);
		string manifestPath = manifestPathEarly;
		bool fullRebuild = args.Any((string a) => a.Equals("--full", StringComparison.OrdinalIgnoreCase));
		Dictionary<string, string> oldManifest = LoadManifest(manifestPath);
		Dictionary<string, string> newManifest = new Dictionary<string, string>();
		long skipCount = 0L;
		bool incremental = (!fullRebuild && oldManifest.Count > 0);
		Console.WriteLine($"\n[2/3] Mengompilasi Master BANKS ({bankFiles.Length} Lagu menggunakan '{slidePraise.Name}')...");
		if (incremental)
		{
			Console.WriteLine("     Mode INCREMENTAL: lagu yang tidak berubah dilewati (pakai --full untuk rebuild total).");
		}
		Stopwatch sw = Stopwatch.StartNew();
		int processedCount = 0;
		int copiedCount = 0;
		System.Collections.Concurrent.ConcurrentQueue<string> errorQueue = new System.Collections.Concurrent.ConcurrentQueue<string>();
		object manifestLock = new object();
		Parallel.ForEach((IEnumerable<string>)bankFiles, new ParallelOptions
		{
			MaxDegreeOfParallelism = Environment.ProcessorCount
		}, (Action<string>)delegate(string f)
		{
			try
			{
				string fileNameWithoutExtension = Path.GetFileNameWithoutExtension(f);
				string srcHash = ComputeFileHash(f);
				string text4 = Path.Combine(proBanksDir, fileNameWithoutExtension + ".pro");
				bool flag = false;
				lock (manifestLock)
				{
					newManifest[fileNameWithoutExtension] = srcHash;
					if (incremental && oldManifest.TryGetValue(fileNameWithoutExtension, out string value) && value == srcHash)
					{
						if (File.Exists(text4) && (libBanks == null || File.Exists(Path.Combine(libBanks, fileNameWithoutExtension + ".pro"))))
						{
							flag = true;
						}
					}
				}
				if (!flag)
				{
					List<ParsedGroup> parsedGroups = ParseLyricFile(f);
					BuildPresentation(slidePraise, fileNameWithoutExtension, parsedGroups, "Praise", text4, themeDoc.ApplicationInfo);
					Interlocked.Increment(ref processedCount);
				}
				else
				{
					Interlocked.Increment(ref skipCount);
				}
				if (libBanks != null)
				{
					string destFileName = Path.Combine(libBanks, fileNameWithoutExtension + ".pro");
					if (!File.Exists(destFileName) || (new FileInfo(destFileName).Length != new FileInfo(text4).Length))
					{
						File.Copy(text4, destFileName, overwrite: true);
						Interlocked.Increment(ref copiedCount);
					}
				}
			}
			catch (Exception ex)
			{
				errorQueue.Enqueue(Path.GetFileName(f) + " => " + ex.Message);
			}
			int num = processedCount + (int)skipCount + errorQueue.Count;
			if (num % 2000 == 0)
			{
				Console.WriteLine($"     Progress: {num} / {bankFiles.Length} lagu diproses ({sw.ElapsedMilliseconds} ms)");
			}
		});
		sw.Stop();
		List<string> errors = errorQueue.ToList();
		if (errors.Count > 0)
		{
			string errorLog = Path.Combine(path, "Engine", "last_errors.txt");
			File.WriteAllLines(errorLog, errors, Encoding.UTF8);
			Console.WriteLine($"  [WARNING] {errors.Count} file GAGAL dikompilasi (yang lain tetap diproses). Detail: {errorLog}");
			foreach (string err in errors.Take(10))
			{
				Console.WriteLine("    - " + err);
			}
		}
		Console.WriteLine($"  -> Baru/diubah: {processedCount} | Dilewati (unchanged): {skipCount} | Disalin ke library: {copiedCount} | Waktu: {(double)sw.ElapsedMilliseconds / 1000.0:F1} detik.");
		// Bersihkan .pro yatim (TXT sudah dihapus) pada mode incremental.
		if (incremental)
		{
			HashSet<string> validNames = new HashSet<string>(bankFiles.Select((string f) => Path.GetFileNameWithoutExtension(f)), StringComparer.OrdinalIgnoreCase);
			int removedOrphans = 0;
			foreach (string orphan in Directory.GetFiles(proBanksDir, "*.pro"))
			{
				if (!validNames.Contains(Path.GetFileNameWithoutExtension(orphan)))
				{
					try
					{
						File.Delete(orphan);
						if (libBanks != null)
						{
							string libOrphan = Path.Combine(libBanks, Path.GetFileName(orphan));
							if (File.Exists(libOrphan))
							{
								File.Delete(libOrphan);
							}
						}
						removedOrphans++;
					}
					catch (Exception delEx)
					{
						Console.WriteLine($"[WARN] Tidak dapat menghapus {orphan}: {delEx.Message}");
					}
				}
			}
			if (removedOrphans > 0)
			{
				Console.WriteLine($"  -> {removedOrphans} file .pro yatim (TXT sudah dihapus) ikut dibersihkan.");
			}
		}
		if (processedCount > 0 || !incremental || errors.Count > 0)
		{
			SaveManifest(manifestPath, newManifest);
		}

		if (proPresenterDir != null && destructiveRun)
		{
			Console.WriteLine("\n[3/3] Membersihkan Playlist ProPresenter (HANYA pada REBUILD Penuh)...");
			string playlistDocPath = Path.Combine(proPresenterDir, "Playlists\\Library");
			if (File.Exists(playlistDocPath) || Directory.Exists(Path.GetDirectoryName(playlistDocPath)))
			{
				ClearPlaylists(playlistDocPath);
			}
		}
		else if (proPresenterDir != null)
		{
			Console.WriteLine("\n[3/3] Playlist ibadah existing DIAMANKAN (mode incremental).");
		}
		Console.WriteLine("\n==============================================================================");
		if (errors.Count > 0)
		{
			Console.WriteLine($"SELESAI DENGAN {errors.Count} ERROR — periksa Engine\\last_errors.txt sebelum tayang!");
			Environment.ExitCode = 1;
		}
		else
		{
			Console.WriteLine("SUKSES! BANK LAGU TERKOMPILASI & TERSENTRYASI (playlist/library lain aman).");
		}
		Console.WriteLine("==============================================================================");
	}

	private static void RegisterLibraries(string proLibDir)
	{
		string path = Path.Combine(proLibDir, "Library");
		string path2 = Path.Combine(proLibDir, "LibraryData");
		Library library = new Library
		{
			LibraryChildren = new Library.Types.LibraryArray()
		};
		// MERGE: pertahankan library lain yang sudah terdaftar di metadata existing, jangan cuma Banks.
		foreach (string metaFile in new string[2] { path2, path })
		{
			try
			{
				if (File.Exists(metaFile))
				{
					Library existing = Library.Parser.ParseFrom(File.ReadAllBytes(metaFile));
					if (existing?.LibraryChildren != null)
					{
						foreach (Library child in existing.LibraryChildren.Libraries)
						{
							string childPath = child.Url?.AbsoluteString ?? "";
							if (childPath.EndsWith("Banks", StringComparison.OrdinalIgnoreCase) || string.IsNullOrEmpty(childPath))
							{
								continue;
							}
							if (Directory.Exists(childPath) || childPath.Contains("Libraries"))
							{
								library.LibraryChildren.Libraries.Add(child);
							}
						}
					}
					break;
				}
			}
			catch (Exception regEx)
			{
				Console.WriteLine($"[WARN] Gagal membaca metadata Library ({metaFile}): {regEx.Message}");
			}
		}
		string absoluteString = Path.Combine(proLibDir, "Banks");
		Library item = new Library
		{
			Url = new URL
			{
				AbsoluteString = absoluteString,
				Platform = URL.Types.Platform.Win32,
				Local = new URL.Types.LocalRelativePath
				{
					Root = URL.Types.LocalRelativePath.Types.Root.Show,
					Path = "Libraries/Banks"
				}
			}
		};
		library.LibraryChildren.Libraries.Add(item);
		byte[] bytes = library.ToByteArray();
		WriteAllBytesAtomic(path, bytes);
		WriteAllBytesAtomic(path2, bytes);
		Console.WriteLine($"  -> Metadata Library terdaftar: {library.LibraryChildren.Libraries.Count} library (termasuk 'Banks', library lain dipertahankan).");
	}

	private static void ClearPlaylists(string playlistDocPath)
	{
		try
		{
			Directory.CreateDirectory(Path.GetDirectoryName(playlistDocPath));
			byte[] bytes = new PlaylistDocument
			{
				RootNode = new Playlist
				{
					Uuid = new UUID
					{
						String = Guid.NewGuid().ToString()
					},
					Name = "Library",
					Type = Playlist.Types.Type.Root,
					Playlists = new Playlist.Types.PlaylistArray()
				}
			}.ToByteArray();
			WriteAllBytesAtomic(playlistDocPath, bytes);
			Console.WriteLine("  -> Berhasil membersihkan Playlist (Playlist Kosong).");
		}
		catch (Exception ex)
		{
			Console.WriteLine("  [WARN] Tidak dapat membersihkan playlist: " + ex.Message);
		}
	}

	public class PlaylistRequest
	{
		public string Name { get; set; } = "New Playlist";
		public List<string> Songs { get; set; } = new List<string>();
		public string Workspace { get; set; }
	}

	private static void HandleCreatePlaylistCommand(string jsonPath)
	{
		if (!File.Exists(jsonPath))
		{
			Console.WriteLine("[ERROR] File JSON playlist tidak ditemukan: " + jsonPath);
			return;
		}

		try
		{
			string jsonText = File.ReadAllText(jsonPath, Encoding.UTF8);
			PlaylistRequest req = JsonSerializer.Deserialize<PlaylistRequest>(jsonText, new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true
			});

			if (req == null || req.Songs == null || req.Songs.Count == 0)
			{
				Console.WriteLine("[ERROR] Playlist kosong atau format JSON tidak valid.");
				return;
			}

			// Resolve ProPresenter Dir
			string personal = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
			string candidate = Path.Combine(personal, "ProPresenter");
			string proPresenterDir = null;
			if (Directory.Exists(candidate)) proPresenterDir = candidate;
			else
			{
				string oneDrive = Environment.GetEnvironmentVariable("OneDrive");
				if (!string.IsNullOrEmpty(oneDrive))
				{
					candidate = Path.Combine(oneDrive, "Documents", "ProPresenter");
					if (Directory.Exists(candidate)) proPresenterDir = candidate;
					else
					{
						candidate = Path.Combine(oneDrive, "Dokumen", "ProPresenter");
						if (Directory.Exists(candidate)) proPresenterDir = candidate;
					}
				}
			}

		if (proPresenterDir == null)
		{
			Console.WriteLine("[ERROR] Folder ProPresenter tidak ditemukan di sistem!");
			Environment.ExitCode = 1;
			return;
		}

			string workspace;
			if (!string.IsNullOrWhiteSpace(req.Workspace) && Directory.Exists(req.Workspace))
			{
				workspace = req.Workspace;
			}
			else
			{
				// Fallback: cari folder "PRO" dari lokasi exe (naik hingga 3 level), baru hardcode lama.
				workspace = null;
				string probe = AppContext.BaseDirectory;
				for (int i = 0; i < 4 && probe != null; i++)
				{
					if (Directory.Exists(Path.Combine(probe, "database", "pro")))
					{
						workspace = probe;
						break;
					}
					if (Directory.Exists(Path.Combine(probe, "PRO")))
					{
						workspace = probe;
						break;
					}
					probe = Directory.GetParent(probe)?.FullName;
				}
				workspace ??= Directory.GetCurrentDirectory();
			}
			string proBanksDir = Path.Combine(workspace, "database", "pro");
			if (!Directory.Exists(proBanksDir)) proBanksDir = Path.Combine(workspace, "PRO");
			string playlistDocPath = Path.Combine(proPresenterDir, "Playlists\\Library");

			CreatePlaylist(playlistDocPath, req.Name, req.Songs, proBanksDir);
		}
		catch (Exception ex)
		{
			Console.WriteLine("[ERROR] Gagal memproses perintah create-playlist: " + ex.Message);
			Environment.ExitCode = 1;
		}
	}

	private static void CreatePlaylist(string playlistDocPath, string playlistName, List<string> songFileNames, string proBanksDir)
	{
		try
		{
			Directory.CreateDirectory(Path.GetDirectoryName(playlistDocPath));
			PlaylistDocument playlistDocument;
			if (File.Exists(playlistDocPath))
			{
				try
				{
					byte[] existingBytes = File.ReadAllBytes(playlistDocPath);
					playlistDocument = PlaylistDocument.Parser.ParseFrom(existingBytes);
				}
				catch (Exception playlistEx)
				{
					Console.WriteLine($"[WARN] Playlist tidak valid: {playlistEx.Message}");
					playlistDocument = new PlaylistDocument();
				}
			}
			else
			{
				playlistDocument = new PlaylistDocument();
			}

			if (playlistDocument.RootNode == null)
			{
				playlistDocument.RootNode = new Playlist
				{
					Uuid = new UUID { String = Guid.NewGuid().ToString() },
					Name = "Library",
					Type = Playlist.Types.Type.Root,
					Playlists = new Playlist.Types.PlaylistArray()
				};
			}

			if (playlistDocument.RootNode.Playlists == null)
			{
				playlistDocument.RootNode.Playlists = new Playlist.Types.PlaylistArray();
			}

			// Remove existing playlist with same name if any
			Playlist existing = playlistDocument.RootNode.Playlists.Playlists.FirstOrDefault(p => p.Name.Equals(playlistName, StringComparison.OrdinalIgnoreCase));
			if (existing != null)
			{
				playlistDocument.RootNode.Playlists.Playlists.Remove(existing);
			}

			Playlist newPlaylist = new Playlist
			{
				Uuid = new UUID { String = Guid.NewGuid().ToString() },
				Name = playlistName,
				Type = Playlist.Types.Type.Playlist,
				Items = new Playlist.Types.PlaylistItems()
			};

			foreach (string songFile in songFileNames)
			{
				string cleanFile = songFile.Trim();
				if (!cleanFile.EndsWith(".pro", StringComparison.OrdinalIgnoreCase))
				{
					cleanFile += ".pro";
				}
				string songTitle = Path.GetFileNameWithoutExtension(cleanFile);
				string absPath = Path.Combine(proBanksDir, cleanFile);

				PlaylistItem item = new PlaylistItem
				{
					Uuid = new UUID { String = Guid.NewGuid().ToString() },
					Name = songTitle,
					Presentation = new PlaylistItem.Types.Presentation
					{
						DocumentPath = new URL
						{
							AbsoluteString = absPath,
							Platform = URL.Types.Platform.Win32,
							Local = new URL.Types.LocalRelativePath
							{
								Root = URL.Types.LocalRelativePath.Types.Root.Show,
								Path = "Libraries/Banks/" + cleanFile
							}
						}
					}
				};
				newPlaylist.Items.Items.Add(item);
			}

			playlistDocument.RootNode.Playlists.Playlists.Add(newPlaylist);
			byte[] bytes = playlistDocument.ToByteArray();
			WriteAllBytesAtomic(playlistDocPath, bytes);
			Console.WriteLine($"[OK] Playlist '{playlistName}' berhasil didaftarkan ke ProPresenter ({songFileNames.Count} lagu)!");
		}
		catch (Exception ex)
		{
			Console.WriteLine($"[ERROR] Gagal membuat playlist: {ex.Message}");
		}
	}

	private static Color GetGroupColor(string groupName)
	{
		Color color = new Color
		{
			Alpha = 1f
		};
		string text = groupName.ToLower().Trim();
		if (text.Contains("blank"))
		{
			color.Red = 0f;
			color.Green = 0f;
			color.Blue = 0f;
		}
		else if (text.Contains("verse"))
		{
			color.Red = 0f;
			color.Green = 0.4666667f;
			color.Blue = 0.8f;
		}
		else if (Regex.IsMatch(text, "pre[\\s\\-]*chorus"))
		{
			color.Red = 0.9686275f;
			color.Green = 48f / 85f;
			color.Blue = 0.1019608f;
		}
		else if (text.Contains("chorus"))
		{
			color.Red = 0.8f;
			color.Green = 0f;
			color.Blue = 0.3058824f;
		}
		else if (text.Contains("bridge"))
		{
			color.Red = 0.5490196f;
			color.Green = 0.1803922f;
			color.Blue = 0.7490196f;
		}
		else if (text.Contains("intro") || text.Contains("interlude"))
		{
			color.Red = 0.1411765f;
			color.Green = 0.7019608f;
			color.Blue = 0.2980392f;
		}
		else if (text.Contains("tag"))
		{
			color.Red = 0f;
			color.Green = 0.7f;
			color.Blue = 0.7f;
		}
		else if (text.Contains("ending") || text.Contains("outro"))
		{
			color.Red = 0.6f;
			color.Green = 0.5607843f;
			color.Blue = 0.1215686f;
		}
		else
		{
			color.Red = 0.5f;
			color.Green = 0.5f;
			color.Blue = 0.5f;
		}
		return color;
	}

	private static string GetRtfString(List<string> lines, string genre, Template.Types.Slide? typoSlide = null)
	{
		// Prefer typography recovered from the native template slide (exact ProPresenter match).
		// Fall back to genre-based defaults if template was not loaded.
		// typoSlide = slide template yang dipilih untuk lagu ini (praise/worship),
		// bukan template aktif global — lagu worship harus dapat tipografi worship.
		string font = s_tplFont;
		double pt = s_tplFontPt;
		bool isBold = s_tplBold;
		if (typoSlide != null)
		{
			(var tf, double tpt, bool tb) = ParseTemplateRtfTypo(typoSlide);
			font = tf; pt = tpt; isBold = tb;
		}

		if (s_baseSlideTemplate == null)
		{
			if (genre == "Worship") { font = "TimesNewNormal-Regular"; pt = 75.0; isBold = false; }
			else if (genre == "Bible") { font = "ArialMT"; pt = 50.0; isBold = false; }
			else { font = "CMGSans-Bold"; pt = 67.0; isBold = true; }
		}

		int fs = (int)Math.Round(pt * 2); // RTF \fs is half-points
		string boldFlag = isBold ? "" : "0";

		string text = $@"{{\rtf0\ansi\ansicpg1252{{\fonttbl\f0\fnil {font};}}{{\colortbl;\red255\green255\blue255;\red255\green255\blue255;}}{{\*\expandedcolortbl;\csgenericrgb\c100000\c100000\c100000\c100000;\csgenericrgb\c100000\c100000\c100000\c0;}}{{\*\listtable{{\list\listid1\listtemplateid1\listhybrid{{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1{{\leveltext\leveltemplateid1 \'01陹 ?;}}{{\levelnumbers;}}}}{{\*\listoverridetable{{\listoverride\listid1\listoverridecount0\ls1}}}}\uc1\paperw38400\margl0\margr0\margt0\margb0";
		string text2 = $@"\pard\li0\fi0\ri0\qc\sb0\sa0\sl240\slmult1\slleading0\f0\b{boldFlag}\i0\ul0\strike0\fs{fs}\expnd0\expndtw0\CocoaLigature1\cf1\strokewidth0\strokec1\nosupersub\ulc0\highlight2\cb2 ";
		List<string> list = new List<string>();
		foreach (string line in lines)
		{
			list.Add(text2 + EscapeRtf(line));
		}
		return text + string.Join("\\par", list) + "}";
	}

	// Escape RTF yang benar: karakter non-ASCII -> \uNNNN? (karena header RTF mendeklarasikan ansicpg1252)
	private static string EscapeRtf(string input)
	{
		StringBuilder sb = new StringBuilder(input.Length + 16);
		foreach (char c in input)
		{
			if (c == '\\' || c == '{' || c == '}')
			{
				sb.Append('\\').Append(c);
			}
			else if (c >= 32 && c <= 126)
			{
				sb.Append(c);
			}
			else if (c == '\t')
			{
				sb.Append("\\tab ");
			}
			else if (c <= 255)
			{
				sb.Append("\\'").Append(((int)c).ToString("x2"));
			}
			else
			{
				// signed 16-bit unicode escape + fallback char '?'
				sb.Append("\\u").Append((int)(short)c).Append('?');
			}
		}
		return sb.ToString();
	}

	private static Dictionary<string, string> LoadManifest(string manifestPath)
	{
		try
		{
			if (File.Exists(manifestPath))
			{
				return JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(manifestPath, Encoding.UTF8)) ?? new Dictionary<string, string>();
			}
		}
		catch (Exception manifestEx)
		{
			Console.WriteLine($"[WARN] Manifest tidak terbaca ({manifestPath}): {manifestEx.Message}");
		}
		return new Dictionary<string, string>();
	}

	private static void SaveManifest(string manifestPath, Dictionary<string, string> manifest)
	{
		try
		{
			File.WriteAllText(manifestPath, JsonSerializer.Serialize(manifest), Encoding.UTF8);
		}
		catch (Exception ex)
		{
			Console.WriteLine("  [WARN] Gagal menyimpan manifest: " + ex.Message);
		}
	}

	private static string ComputeFileHash(string file)
	{
		using System.Security.Cryptography.SHA256 sha = System.Security.Cryptography.SHA256.Create();
		using FileStream fs = File.OpenRead(file);
		return Convert.ToHexString(sha.ComputeHash(fs));
	}

	public static List<ParsedGroup> ParseLyricContent(string content)
	{
		string[] array = content.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
		List<ParsedGroup> list = new List<ParsedGroup>();
		ParsedGroup parsedGroup = null;
		List<string> list2 = new List<string>();
		string[] array2 = array;
		for (int i = 0; i < array2.Length; i++)
		{
			string text = array2[i].Trim();
			if (HeaderRegex.IsMatch(text))
			{
				if (list2.Count > 0 && parsedGroup != null)
				{
					parsedGroup.Slides.Add(new List<string>(list2));
					list2.Clear();
				}
				string text2 = text;
				string text3 = text2.ToUpperInvariant();
				switch (text3)
				{
				case "BLANK":
					text2 = "Blank";
					break;
				case "INTRO":
					text2 = "Intro";
					break;
				case "OUTRO":
					text2 = "Outro";
					break;
				case "ENDING":
					text2 = "Ending";
					break;
				case "INTERLUDE":
					text2 = "Interlude";
					break;
				case "TAG":
					text2 = "Tag";
					break;
				case "BRIDGE":
					text2 = "Bridge";
					break;
				default:
					if (Regex.IsMatch(text3, "^BRIDGE\\s+(\\d+)$"))
					{
						Match match = Regex.Match(text3, "^BRIDGE\\s+(\\d+)$");
						text2 = "Bridge " + match.Groups[1].Value;
					}
					else if (text3 == "VERSE")
					{
						text2 = "Verse";
					}
					else if (Regex.IsMatch(text3, "^VERSE\\s+(\\d+)$"))
					{
						Match match2 = Regex.Match(text3, "^VERSE\\s+(\\d+)$");
						text2 = "Verse " + match2.Groups[1].Value;
					}
					else if (text3 == "CHORUS")
					{
						text2 = "Chorus";
					}
					else if (Regex.IsMatch(text3, "^CHORUS\\s+(\\d+)$"))
					{
						Match match3 = Regex.Match(text3, "^CHORUS\\s+(\\d+)$");
						text2 = "Chorus " + match3.Groups[1].Value;
					}
					else if (Regex.IsMatch(text3, "^PRE[\\s\\-]*CHORUS$"))
					{
						text2 = "Pre-Chorus";
					}
					else if (Regex.IsMatch(text3, "^PRE[\\s\\-]*CHORUS\\s+(\\d+)$"))
					{
						Match match4 = Regex.Match(text3, "^PRE[\\s\\-]*CHORUS\\s+(\\d+)$");
						text2 = "Pre-Chorus " + match4.Groups[1].Value;
					}
					break;
				}
				parsedGroup = new ParsedGroup
				{
					Name = text2,
					RawHeader = text
				};
				list.Add(parsedGroup);
			}
			else if (string.IsNullOrWhiteSpace(text))
			{
				if (list2.Count > 0 && parsedGroup != null)
				{
					parsedGroup.Slides.Add(new List<string>(list2));
					list2.Clear();
				}
			}
			else
			{
				list2.Add(text);
			}
		}
		if (list2.Count > 0)
		{
			parsedGroup?.Slides.Add(new List<string>(list2));
		}

		// Projection rule: a slide carries at most two lyric lines. Sections
		// written without blank-line breaks (most of the catalog) arrive as one
		// tall slide; split them into consecutive two-line slides so the
		// congregation is never shown a wall of text.
		foreach (ParsedGroup groupToSplit in list)
		{
			if (groupToSplit.Slides.All(s => s.Count <= 2)) continue;
			var splitSlides = new List<List<string>>();
			foreach (List<string> slide in groupToSplit.Slides)
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
			groupToSplit.Slides = splitSlides;
		}

		return list;
	}

	private static List<ParsedGroup> ParseLyricFile(string path)
	{
		return ParseLyricContent(File.ReadAllText(path, Encoding.UTF8));
	}

	private static Template.Types.Slide? s_baseSlideTemplate = null;
	private static Template.Types.Document? s_themeDocFull = null;
	private static ApplicationInfo? s_appInfo = null;
	private static readonly object s_themeLock = new object();
	private static string s_tplFont = "CMGSans-Bold";
	private static double s_tplFontPt = 67.0;
	private static bool s_tplBold = true;
	private static string s_tplFile = "";
	public static string ActiveSlideTemplateName = "Lyric - Praise";

	public static string GetActiveSlideTemplateName() => ActiveSlideTemplateName;

	public static (string font, double pt, bool bold, string file) GetActiveTemplateTypo() => (s_tplFont, s_tplFontPt, s_tplBold, s_tplFile);

	public static void ResetThemeCache()
	{
		lock (s_themeLock)
		{
			// Every cached value belongs to the previous template; leaving the typography
			// behind made /api/themes report stale font data after a theme switch.
			s_baseSlideTemplate = null;
			s_themeDocFull = null;
			s_appInfo = null;
			s_tplFont = "CMGSans-Bold";
			s_tplFontPt = 67.0;
			s_tplBold = true;
			s_tplFile = "";
		}
	}

	public static Template.Types.Slide? PickSlideFromDoc(Template.Types.Document doc)
	{
		if (doc == null || doc.Slides == null || doc.Slides.Count == 0) return null;
		string wanted = GetActiveSlideTemplateName();
		var slide = doc.Slides.FirstOrDefault(s => s.Name.Equals(wanted, StringComparison.OrdinalIgnoreCase));
		if (slide != null) return slide;
		slide = doc.Slides.FirstOrDefault(s => s.Name == "Lyric - Praise");
		if (slide != null) return slide;
		return doc.Slides.FirstOrDefault();
	}

	// Pilih slide template berdasarkan gaya lagu: "worship" pakai slide
	// "Lyric - Worship" dari tema yang sama, selain itu pakai template aktif.
	public static Template.Types.Slide? GetSlideForStyle(string? style)
	{
		if (style != null && style.Equals("worship", StringComparison.OrdinalIgnoreCase)
			&& s_themeDocFull?.Slides != null)
		{
			var w = s_themeDocFull.Slides.FirstOrDefault(s => s.Name.Equals("Lyric - Worship", StringComparison.OrdinalIgnoreCase));
			if (w != null) return w;
		}
		return s_baseSlideTemplate;
	}

	// Cache the resolved slide's RTF typography recovered from its native template.
	// Returns (fontName, fontSizePt, isBold). Font size comes from \fs (half-points) in RTF.
	private static (string font, double pt, bool bold) ParseTemplateRtfTypo(Template.Types.Slide? slide)
	{
		string font = "CMGSans-Bold";
		double pt = 67.0;
		bool bold = true;
		try
		{
			if (slide?.BaseSlide?.Elements == null || slide.BaseSlide.Elements.Count == 0) return (font, pt, bold);
			var el = slide.BaseSlide.Elements[0].Element_?.Text?.RtfData;
			if (el == null || el.Length == 0) return (font, pt, bold);
			string rtf = Encoding.UTF8.GetString(el.ToByteArray());

			// font name from font table: {\fonttbl\f0\fnil NAME;}
			var fm = Regex.Match(rtf, @"\\fonttbl\\f0\\fnil\s+([^;]+);");
			if (fm.Success) font = fm.Groups[1].Value.Trim();

			// bold flag: first occurrence of \b followed by non-digit (or \b then space) = bold; \b0 = not bold
			var bm = Regex.Match(rtf, @"\\b(\d*)");
			if (bm.Success) bold = string.IsNullOrEmpty(bm.Groups[1].Value) || bm.Groups[1].Value != "0";

			// font size: \fsNN (half-points)
			var sm = Regex.Match(rtf, @"\\fs(\d+)");
			if (sm.Success) pt = int.Parse(sm.Groups[1].Value) / 2.0;
		}
		catch (Exception ex)
		{
			Console.WriteLine($"[WARN] Tidak dapat membaca tipografi RTF dari tema: {ex.Message}");
		}
		return (font, pt, bold);
	}

	public static bool EnsureThemeLoaded(string? rootPath = null, string? proPresenterDir = null)
	{
		if (s_baseSlideTemplate != null) return true;
		lock (s_themeLock)
		{
			if (s_baseSlideTemplate != null) return true;

			var candidateThemeFiles = new List<string>();

			if (!string.IsNullOrEmpty(proPresenterDir) && Directory.Exists(proPresenterDir))
			{
				string themesRoot = Path.Combine(proPresenterDir, "Themes");
				if (Directory.Exists(themesRoot))
				{
					try
					{
						var allThemeFiles = Directory.GetFiles(themesRoot, "Theme", SearchOption.AllDirectories);
						// Prefer Banklycs group first, otherwise alphabetical group order for determinism
						var ordered = allThemeFiles
							.OrderBy(f => Path.GetFileName(Path.GetDirectoryName(f) ?? "").Equals("Banklycs", StringComparison.OrdinalIgnoreCase) ? 0 : 1)
							.ThenBy(f => Path.GetFileName(Path.GetDirectoryName(f) ?? ""), StringComparer.OrdinalIgnoreCase)
							.ToList();
						candidateThemeFiles.AddRange(ordered);
					}
					catch (Exception ex)
					{
						Console.WriteLine($"[WARN] Gagal memindai folder Themes ProPresenter: {ex.Message}");
					}
				}
			}

			if (!string.IsNullOrEmpty(rootPath))
			{
				string localTheme = Path.Combine(rootPath, "engine", "ThemeTemplate");
				if (File.Exists(localTheme)) candidateThemeFiles.Add(localTheme);
				localTheme = Path.Combine(rootPath, "Engine", "ThemeTemplate");
				if (File.Exists(localTheme)) candidateThemeFiles.Add(localTheme);
			}

			string baseDirTheme = Path.Combine(AppContext.BaseDirectory, "ThemeTemplate");
			if (File.Exists(baseDirTheme)) candidateThemeFiles.Add(baseDirTheme);
			baseDirTheme = Path.Combine(AppContext.BaseDirectory, "engine", "ThemeTemplate");
			if (File.Exists(baseDirTheme)) candidateThemeFiles.Add(baseDirTheme);

			// De-duplicate by full path
			candidateThemeFiles = candidateThemeFiles
				.GroupBy(p => p.ToLowerInvariant())
				.Select(g => g.First())
				.ToList();

			if (candidateThemeFiles.Count == 0)
			{
				Console.WriteLine("[WARN] File Tema tidak ditemukan di ProPresenter maupun engine/ThemeTemplate fallback!");
				return false;
			}

			try
			{
				Template.Types.Slide? slide = null;
				ApplicationInfo? appInfo = null;
				string usedFile = "";
				byte[] usedData = Array.Empty<byte>();

				// First pass: exact slide name match across all theme files/profiles
				foreach (string tf in candidateThemeFiles)
				{
					byte[] data = File.ReadAllBytes(tf);
					var doc = Template.Types.Document.Parser.ParseFrom(data);
					var found = doc.Slides?.FirstOrDefault(s => s.Name.Equals(GetActiveSlideTemplateName(), StringComparison.OrdinalIgnoreCase));
					if (found != null)
					{
						slide = found;
						appInfo = doc.ApplicationInfo;
						usedFile = tf;
						usedData = data;
						s_themeDocFull = doc;
						break;
					}
				}

				// Fallback: Lyric - Praise across files (or first slide of first file)
				if (slide == null)
				{
					foreach (string tf in candidateThemeFiles)
					{
						byte[] data = File.ReadAllBytes(tf);
						var doc = Template.Types.Document.Parser.ParseFrom(data);
						var found = doc.Slides?.FirstOrDefault(s => s.Name == "Lyric - Praise") ?? doc.Slides?.FirstOrDefault();
						if (found != null)
						{
							slide = found;
							appInfo = doc.ApplicationInfo;
							usedFile = tf;
							usedData = data;
							s_themeDocFull = doc;
							break;
						}
					}
				}

				if (slide == null)
				{
					Console.WriteLine("[WARN] Slide template kosong di semua file Theme!");
					return false;
				}

				s_baseSlideTemplate = slide;
				s_appInfo = appInfo;

				// Recover font/size/bold from native template slide and cache it
				s_tplFont = ParseTemplateRtfTypo(slide).font;
				s_tplFontPt = ParseTemplateRtfTypo(slide).pt;
				s_tplBold = ParseTemplateRtfTypo(slide).bold;
				s_tplFile = usedFile;

				Console.WriteLine($"[THEME] Loaded slide '{slide.Name}' from {usedFile} | font={s_tplFont} pt={s_tplFontPt} bold={s_tplBold}");
				return true;
			}
			catch (Exception ex)
			{
				Console.WriteLine($"[ERROR] Gagal memuat tema: {ex.Message}");
				return false;
			}
		}
	}

	public static bool CompileAndSaveSong(string songName, string lyricContent, string targetFile, string? rootPath = null, string? proPresenterDir = null, string? style = null)
	{
		if (!EnsureThemeLoaded(rootPath, proPresenterDir) || s_baseSlideTemplate == null)
		{
			return false;
		}

		List<ParsedGroup> parsedGroups = ParseLyricContent(lyricContent);
		string dir = Path.GetDirectoryName(targetFile) ?? "";
		if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
		{
			Directory.CreateDirectory(dir);
		}

		var chosenSlide = GetSlideForStyle(style) ?? s_baseSlideTemplate;
		string genre = "Praise";
		if (chosenSlide.Name.Contains("Worship", StringComparison.OrdinalIgnoreCase)) genre = "Worship";
		else if (chosenSlide.Name.Contains("Bible", StringComparison.OrdinalIgnoreCase)) genre = "Bible";

		return BuildPresentation(chosenSlide, songName, parsedGroups, genre, targetFile, s_appInfo);
	}

	public static void ExportTxt(string rootPath, string targetDir)
	{
		string dbPath = Path.Combine(rootPath, "database", "banklycs.db");
		if (!File.Exists(dbPath))
		{
			Console.WriteLine($"[ERROR] Database tidak ditemukan di: {dbPath}");
			return;
		}

		if (!Directory.Exists(targetDir))
		{
			Directory.CreateDirectory(targetDir);
		}

		Console.WriteLine($"[EXPORT] Mengekspor lirik dari {dbPath} ke {targetDir}...");
		Stopwatch sw = Stopwatch.StartNew();

		string connStr = new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder
		{
			DataSource = dbPath,
			Mode = Microsoft.Data.Sqlite.SqliteOpenMode.ReadOnly
		}.ToString();

		int count = 0;
		using (var conn = new Microsoft.Data.Sqlite.SqliteConnection(connStr))
		{
			conn.Open();
			using var cmd = conn.CreateCommand();
			cmd.CommandText = "SELECT filename, content FROM songs;";
			using var reader = cmd.ExecuteReader();
			while (reader.Read())
			{
				string filename = reader.GetString(0);
				string content = reader.GetString(1);
				string outPath = Path.Combine(targetDir, filename);
				File.WriteAllText(outPath, content, Encoding.UTF8);
				count++;
			}
		}

		sw.Stop();
		Console.WriteLine($"[OK] Sukses mengekspor {count:N0} lagu ke '{targetDir}' dalam {sw.ElapsedMilliseconds} ms ({sw.Elapsed.TotalSeconds:F2} detik)!");
	}

	public static void CleanProPresenter(string rootPath)
	{
		string pDir = Banklycs.StudioServer.ResolveProPresenterDir();
		if (string.IsNullOrEmpty(pDir) || !Directory.Exists(pDir))
		{
			Console.WriteLine("[WARN] Folder ProPresenter tidak ditemukan di sistem.");
			return;
		}

		// 1. Delete all .pro files in Libraries/Banks
		string libBanks = Path.Combine(pDir, "Libraries", "Banks");
		int deletedSongs = 0;
		if (Directory.Exists(libBanks))
		{
			foreach (string f in Directory.GetFiles(libBanks, "*.pro"))
			{
				try
				{
					File.Delete(f);
					deletedSongs++;
				}
				catch (Exception delEx)
				{
					Console.WriteLine($"[WARN] Tidak dapat menghapus {f}: {delEx.Message}");
				}
			}
		}

		// 2. Clear playlists in Playlists/Library
		string playlistDoc = Path.Combine(pDir, "Playlists", "Library");
		int clearedPlaylists = 0;
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
					WriteAllBytesAtomic(playlistDoc, doc.ToByteArray());
				}
			}
			catch (Exception plEx)
			{
				Console.WriteLine($"[WARN] Reset playlist gagal: {plEx.Message}");
			}
		}

		Console.WriteLine($"[CLEAN] Selesai: {deletedSongs} file .pro dibersihkan dari Libraries/Banks, {clearedPlaylists} playlist direset dari Playlists/Library.");
	}

	private static bool BuildPresentation(Template.Types.Slide baseSlideTemplate, string songName, List<ParsedGroup> parsedGroups, string genre, string targetFile, ApplicationInfo appInfo)
	{
		Presentation presentation = new Presentation
		{
			Name = songName,
			Uuid = new UUID
			{
				String = Guid.NewGuid().ToString()
			},
			LastModifiedDate = new Timestamp
			{
				Seconds = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
			}
		};
		if (appInfo != null)
		{
			presentation.ApplicationInfo = appInfo.Clone();
		}
		int num = 0;
		foreach (ParsedGroup parsedGroup in parsedGroups)
		{
			Pro.SerializationInterop.RVProtoData.Group group = new Pro.SerializationInterop.RVProtoData.Group
			{
				Name = parsedGroup.Name,
				Uuid = new UUID
				{
					String = Guid.NewGuid().ToString()
				},
				Color = GetGroupColor(parsedGroup.Name)
			};
			Presentation.Types.CueGroup cueGroup = new Presentation.Types.CueGroup
			{
				Group = group
			};
			foreach (List<string> slide in parsedGroup.Slides)
			{
				Cue cue = new Cue
				{
					Uuid = new UUID
					{
						String = Guid.NewGuid().ToString()
					},
					IsEnabled = true
				};
				if (parsedGroup.Name == "Blank")
				{
					cue.Name = "";
				}
				else
				{
					num++;
					cue.Name = $" {num}";
				}
				Pro.SerializationInterop.RVProtoData.Action action = new Pro.SerializationInterop.RVProtoData.Action
				{
					Uuid = new UUID
					{
						String = Guid.NewGuid().ToString()
					},
					Type = Pro.SerializationInterop.RVProtoData.Action.Types.ActionType.PresentationSlide,
					IsEnabled = true,
					Slide = new Pro.SerializationInterop.RVProtoData.Action.Types.SlideType
					{
						Presentation = new PresentationSlide
						{
							BaseSlide = baseSlideTemplate.BaseSlide.Clone()
						}
					}
				};
				Slide baseSlide = action.Slide.Presentation.BaseSlide;
				baseSlide.Uuid = new UUID
				{
					String = Guid.NewGuid().ToString()
				};
				Graphics.Types.Element element_ = baseSlide.Elements[0].Element_;
				element_.Uuid = new UUID
				{
					String = Guid.NewGuid().ToString()
				};
				string rtfString = GetRtfString(slide, genre, baseSlideTemplate);
				element_.Text.RtfData = ByteString.CopyFrom(Encoding.UTF8.GetBytes(rtfString));
				cue.Actions.Add(action);
				presentation.Cues.Add(cue);
				cueGroup.CueIdentifiers.Add(new UUID
				{
					String = cue.Uuid.String
				});
			}
			presentation.CueGroups.Add(cueGroup);
		}
		byte[] bytes = presentation.ToByteArray();
		WriteAllBytesAtomic(targetFile, bytes);
		return true;
	}
}
