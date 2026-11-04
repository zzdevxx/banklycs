# GENERATE — KOMPILER ENGINE & INJEKTOR PROPRESENTER

> **Proyek**: `banklycs` — Arsitektur Kompilasi On-Demand & Injeksi Cepat ProPresenter 7  
> **Binary Utama**: `engine/banklycs.exe` (Single-file Native C# .NET 8, Google Protobuf + Embedded SQLite)  
> **Master Database**: `database/banklycs.db` (SQLite single-file; tabel `songs_fts` FTS5 dipakai untuk audit, bukan oleh runtime)  
> **Terakhir diperbarui**: 2026-11-04

---

## 1. Diagram Alur Data & Injeksi On-Demand

```
┌────────────────────────────────────────────────────────┐
│             database/banklycs.db (61 MB)            │
│  - 24.520 Lagu Terkurasi dalam 1 File Database SQLite  │
│  - songs_fts (FTS5) untuk audit; runtime pakai RAM      │
│  - Zero Filesystem Bloat / Zero NTFS Overhead          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│     engine/banklycs.exe (Studio Console Native C#)     │
│  - In-Memory RAM Search Catalog (Load: ~140ms)         │
│  - Multi-token Instant Filter (<2ms search)            │
│  - Rundown Builder (Pilih 5–10 lagu ibadah)            │
└───────────────────────────┬────────────────────────────┘
                            │
         [ Operator Klik: "INJECT KE PROPRESENTER" ]
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│     Direct On-Demand In-Memory Compilation (<1 ms)     │
│  1. Query lirik lagu dari database/banklycs.db         │
│  2. Program.CompileAndSaveSong() mengompilasi Protobuf │
│     langsung ke Libraries/Banks/{lagu}.pro             │
│  3. Program.CreatePlaylistDirect() mendaftarkan        │
│     playlist ibadah ke Playlists/Library               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            ProPresenter 7 (Instance Aktif)             │
│  - Startup Instan (<1 detik, Tanpa Crash)              │
│  - Playlist Ibadah langsung muncul & siap tayang       │
│  - Bebas dari beban 20.000 file tak terpakai           │
└────────────────────────────────────────────────────────┘
```

---

## 2. Mengapa Arsitektur On-Demand Jauh Lebih Unggul?

Sebelumnya, repositori menyimpan 20.301 file `.txt` dan 20.301 file `.pro` (total >40.600 file terpisah berukuran ~300 MB). Hal ini menimbulkan masalah:
1. **NTFS Slowdown**: Windows Explorer dan antivirus melambat saat membaca/memindahkan 40.000 file kecil.
2. **Transfer USB Lambat**: Meng-copy 40.000 file ke flashdisk membutuhkan waktu 10–15 menit karena overhead metadata file.
3. **ProPresenter Overload**: Memuat 20.000 presentasi sekaligus di ProPresenter menyebabkan startup lambat dan potensi crash.

**Dengan Arsitektur Baru**:
1. **Single Database File (`banklycs.db`)**: Seluruh 24.520 lagu berada dalam satu file **~61 MB** (61.415.424 byte).
2. 25.904 → kini **24.520 lagu** setelah dedup & sanitasi filename NTFS 2026-11-04.
3. **Kompilasi Realtime**: Protobuf serializer C# sangat cepat (<1 ms per lagu). Mengompilasi 5–10 lagu saat klik tombol "INJECT" hanya butuh waktu ~5 ms, sehingga tidak perlu menyimpan file `.pro` yang tidak terpakai di harddisk.
4. **ProPresenter Tetap Ringan**: ProPresenter hanya memuat lagu-lagu ibadah aktif di `Libraries/Banks/`.

---

## 3. Spesifikasi Template Presentasi Panggung

- **Slide Template**: `Lyric - Praise`
- **Font**: `CMGSans-Bold`
- **Font Size**: `134` (dengan perataan tengah vertikal dan horizontal)
- **Canvas**: `1920 x 1080` (Full HD 16:9)
- **Aturan Baris**: Maksimal 2 baris per slide tampilan.
- **Slide Awal**: Selalu diawali slide kosong (`BLANK`) dengan label judul lagu.

---

## 4. Perintah CLI Maintainer

### A. Ekspor Lirik ke Format Teks Biasa
Jika ingin mengekspor seluruh lirik ke disk untuk keperluan batch inspect:
```powershell
engine\banklycs.exe export-txt [target_folder]
# Contoh:
engine\banklycs.exe export-txt database\txt
```

### B. Audit Integritas Database
```powershell
python tools\audit_cleanliness.py
```
