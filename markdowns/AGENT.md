# AGENT — MANUAL OPERASIONAL & STATUS ESTAFET

> **Tujuan Dokumen**: Panduan wajib bagi AI coding agent berikutnya yang bekerja pada repositori `banklycs`.  
> Dokumen ini memuat arsitektur sistem, aturan ketat (*Golden Rules*), alur kerja harian, status terkini, dan *backlog* tugas.

---

## 1. Peta Arsitektur Proyek

```text
banklycs/
├── START.vbs          ← Launcher senyap 1-klik bagi operator gereja (0 CMD window)
├── database/          ← Database Lirik Tunggal (SQLite + FTS5)
│   └── banklycs.db    ← 20.301 lagu master dalam 1 file (~28.9 MB, zero disk bloat)
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
1. **Penyimpanan**: Seluruh 20.301 lagu disimpan di tabel `songs` pada file SQLite tunggal `database/banklycs.db`.
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

### C. Ekspor / Dump File TXT
Jika maintainer atau pengguna ingin mengekspor seluruh 20.301 lagu kembali menjadi file `.txt` biasa:
```powershell
engine\banklycs.exe export-txt [target_folder]
```

---

## 3. Remote Git & Kebijakan Push

- **Git Remote Resmi**:
  - `origin`: `https://gitlab.com/zzdevxx/banklycs.git`
  - `codeberg`: `https://codeberg.org/zzdevxx/banklycs.git`
- **PENTING**: **JANGAN PUSH KE GITHUB**. Repositori ini dikelola di GitLab dan Codeberg.

---

## 4. Status Estafet Terkini (November 2026)

| Metrik / Item | Status | Keterangan |
|---|---|---|
| **Total Lagu di DB** | **20.301 lagu** | Tersimpan di `database/banklycs.db` (28.97 MB) |
| **Pencarian FTS5** | **Aktif** | Sub-millisecond full-text search di seluruh teks |
| **Engine Native C#** | **`engine/banklycs.exe`** | Single-file executable, 0 dependensi luar |
| **Kompilasi On-Demand** | **Terverifikasi** | Injeksi 2 lagu tes sukses ke ProPresenter Libraries |
| **Kebersihan Repo** | **100% Bersih** | Tidak ada file loose `txt/` atau `pro/` di disk (~270 MB terpangkas) |
| **Audit Script** | `tools/audit_cleanliness.py` | 100% validasi database & ProPresenter passing |
