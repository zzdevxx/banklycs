# AGENT — MANUAL OPERASIONAL & STATUS ESTAFET

> **Tujuan Dokumen**: Panduan wajib bagi AI coding agent berikutnya yang bekerja pada repositori `banklycs`.  
> Dokumen ini memuat arsitektur sistem, aturan ketat (*Golden Rules*), alur kerja harian, status terkini, dan *backlog* tugas.

---

## 1. Peta Arsitektur Proyek

```text
banklycs/
├── START.vbs          ← Launcher senyap 1-klik bagi operator gereja (0 CMD window)
├── database/          ← Database Lirik Tunggal (SQLite + FTS5)
│   └── banklycs.db    ← 24.556 lagu master dalam 1 file (~44 MB, zero disk bloat)
├── app/               ← Antarmuka Web GUI Studio Console (index.html, style.css, app.js)
├── engine/            ← Engine C# .NET 8 (Single-file banklycs.exe, StudioServer.cs, Program.cs)
├── tools/             ← Skrip scraper web, migrasi, & audit integritas (Python)
├── markdowns/         ← Dokumentasi inti: RULES.md, GENERATE.md, GUIDE.md, AGENT.md
├── README.md          ← Dokumentasi publik bagi pengguna
└── .gitignore         ← Aturan ignore Git
```

---

## 2. Doktrin Utama & Aturan Mutlak (Golden Rules)

### A. Anti-Halusinasi AI (Strict Zero-Tolerance)
- **DILARANG KERAS** mengarang lirik lagu menggunakan LLM. Seluruh lirik wajib murni hasil scraping atau transkripsi dari sumber resmi/rekaman asli.
- Jika artis/pencipta lagu tidak diketahui dari sumber: **gunakan nama lagu berupa judul saja** (contoh: `Adalah Baik Untuk`), **JANGAN** mengarang nama artis atau menggunakan label `- No Name` atau `- Praise & Worship`.

### B. Arsitektur Single-File Database (`database/banklycs.db`)
1. **Penyimpanan**: Seluruh 24.556 lagu disimpan di tabel `songs` pada file SQLite tunggal `database/banklycs.db`.
2. **Schema Tabel `songs`**:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `filename`: TEXT NOT NULL UNIQUE (contoh: `Amazing Grace - John Newton.txt`)
   - `title`: TEXT NOT NULL
   - `artist`: TEXT
   - `category`: TEXT (contoh: `ID`, `EN`, `KJ`, `NKB`, `PKJ`, `KK`, `BE`, `KLIK`, `NNBT`, `JAWA`)
   - `content`: TEXT NOT NULL (Lirik lengkap standar panggung)
   - `created_at`: DATETIME DEFAULT CURRENT_TIMESTAMP
3. **Full-Text Search (`songs_fts`)**: Tabel virtual FTS5 mencakup kolom `title`, `artist`, `category`, `content` untuk pencarian instan (<3 ms) di seluruh lirik.
4. **Kompilasi On-Demand**:
   - File `.pro` tidak disimpan di repositori.
   - Saat operator memilih lagu di GUI dan mengklik "INJECT", C# engine (`banklycs.exe`) mengompilasi Google Protobuf secara *in-memory* (<1 ms per lagu) langsung ke ProPresenter `Libraries/Banks/{lagu}.pro`.
   - Playlist dibuat secara langsung di `Playlists/Library`.
   - **Lookup lagu memakai `filename` persis** (bukan `title`). Query lama `filename = @f OR title = @f LIMIT 1` mengembalikan lagu yang salah untuk 1.459 judul yang beredar bersama — jangan mengembalikannya.
5. **Katalog & Reload**:
   - Katalog di-load sekali saat start ke RAM. Setelah `banklycs.db` berubah di disk, katalog menjadi **basi** sampai restart atau `GET /api/reload`.
   - `GET /api/status` melaporkan `catalog_loaded_at`, `catalog_db_mtime`, `catalog_stale`, `catalog_version`.
   - `GET /api/reload` memuat ulang katalog tanpa restart proses.

### C. Ekspor / Dump File TXT
Jika maintainer atau pengguna ingin mengekspor seluruh 24.556 lagu kembali menjadi file `.txt` biasa:
```powershell
engine\banklycs.exe export-txt [target_folder]
```

---

## 3. Remote Git & Kebijakan Push

- **Git Remote Resmi** (ketiganya aktif dan identik):
  - `origin`: `https://gitlab.com/zzdevxx/banklycs.git`
  - `codeberg`: `https://codeberg.org/zzdevxx/banklycs.git`
  - `github`: `https://github.com/zzdevxx/banklycs.git`
- Semua perubahan push ke **ketiga** remote (`origin`, `codeberg`, `github`). Aturan lama "jangan push ke GitHub" **sudah dicabut** — repositori ini publik di ketiga platform.

---

## 4. Status Estafet Terkini (November 2026)

| Metrik / Item | Status | Keterangan |
|---|---|---|
| **Total Lagu di DB** | **24.520 lagu** | Tersimpan di `database/banklycs.db` (~46 MB) |
| **Pencarian FTS5** | **Aktif** | Sub-millisecond full-text search di seluruh teks (0.60 ms) |
| **Engine Native C#** | **`engine/banklycs.exe`** | Single-file self-contained (~75 MB), 0 dependensi luar |
| **Kompilasi On-Demand** | **Terverifikasi** | Injeksi on-demand sukses ke ProPresenter Libraries |
| **Kebersihan Repo** | **100% Bersih** | Tidak ada file loose `txt/` atau `pro/` di disk (~270 MB terpangkas) |
| **Audit Script** | `tools/audit_cleanliness.py` | 100% validasi database & ProPresenter passing |
| **Build Engine** | `dotnet publish` (SDK 8.0.427) | Lihat §5 — SDK hanya ada di `%USERPROFILE%\.dotnet` |

## 5. Membangun Ulang `engine/banklycs.exe`

.NET SDK 8.0.427 terpasang di `%USERPROFILE%\.dotnet\sdk` dan **tidak ada di PATH default**. Build/ publish:

```powershell
$env:DOTNET_ROOT = "$env:USERPROFILE\.dotnet"
$env:PATH = "$env:USERPROFILE\.dotnet;$env:PATH"
dotnet publish engine\ProEngine.csproj -c Release -o engine --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
# hapus artefak sisa (bukan single-file)
Remove-Item engine\banklycs.dll, engine\banklycs.pdb, engine\banklycs.deps.json, engine\banklycs.runtimeconfig.json, engine\Microsoft.Data.Sqlite.dll, engine\SQLitePCLRaw*.dll
```

> **Peringatan**: `dotnet publish` dengan `-o engine` akan gagal jika `banklycs.exe` sedang berjalan (file terkunci). Hentikan proses dulu, publish, baru start ulang. Exe self-contained ~75 MB. `Program.cs` berasal dari dekompilasi (nama variabel `text2`, `flag`); jangan refactor berat tanpa rebuild+uji.

## 6. Kualitas Data (per 2026-11-04)

| Metrik | Nilai | Keterangan |
|---|---|---|
| Total lagu | 24.520 | Setelah dedup & sanitasi filename NTFS 2026-11-04 (sebelumnya 24.556) |
| `filename` <> baris 2 isi lirik | **0** | Golden Rules §2.7 terpenuhi 100% |
| Sufiks `(2)` / `(3)` di filename | **0** | Di-rename ke nama bersih; varian yang tersisa adalah lagu berbeda |
| Placeholder `Various Artists` (bukan seluruh field) | **0** | 10 baris diterjemahkan ke judul yang benar; 2 baris sah `Various Artists` |
| Judul menyisipkan `(KJ n)` | **0** | 528 baris dipindah ke kolom `artist` per RULES §2.5 |
| `artist` mengandung ` - ` (split salah) | **0** | 442 baris di-split ulang dari baris 2 |
| Duplikat `title+artist` | **3 grup** | Hanya pasangan `(2)/(3)` tanpa pasangan bersih — saksikan §2 |
| Konsistensi FTS5 | **100%** | `songs` = `songs_fts` = 24.520, `integrity_check` ok |
| Empty artist | 3.974 | Sah per RULES §2.2 (judul saja bila pencipta tak diketahui) |

Dedup memakai skor kelengkapan (jumlah header bagian + panjang lirik); yang dipertahankan adalah lirik yang lebih lengkap. Kalkulasi: 1.221 baris `(2)/(3)` yang menabrak `title+artist`, 104 varian `(KJ n)` yang bentrok dengan bentuk kanonis `Title - KJ n`, 12 baris `Ade Manahutu` duplikat, dan 45 lagu dengan homoglyph Sirkilik dinormalisasi ke Latin.
