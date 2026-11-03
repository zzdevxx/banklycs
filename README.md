# Banklycs 🎵

> **Koleksi 20.300+ Lagu Rohani & Himne Siap Tayang untuk ProPresenter 7.**  
> Dirancang khusus untuk tim multimedia gereja, operator proyektor, dan worship leader agar **tidak perlu lagi mencari & *copy-paste* lirik dari browser saat ibadah.**

---

## 🌟 Fitur Utama

- **20.300+ Lagu Terkurasi & Siap Tayang**:
  - **Praise & Worship Indonesia (14.600+ lagu)**: GMS Live, JPCC Worship, Symphony Worship, NDC Worship, Bethel, Sari Simorangkir, Franky Sihombing, dll.
  - **English Contemporary & Classic Hymns (1.800+ lagu)**: Hillsong Worship, Elevation Worship, Bethel Music, Planetshakers, Chris Tomlin, dll.
  - **Buku Nyanyian & Himne Klasik Lengkap**:
    - **KJ** (Kidung Jemaat) — 1.059 lagu
    - **NKB** (Nyanyikanlah Kidung Baru) — 282 lagu
    - **PKJ** (Pelengkap Kidung Jemaat) — 322 lagu
    - **KK** (Kidung Keesaan) — 766 lagu
    - **KLIK** (Kumpulan Lagu Ibadah Kreatif) — 454 lagu
    - **BE** (Buku Ende HKBP Batak) — 844 lagu
    - **NNBT** (Nyanyian Baru Bagi Tuhan) — 45 lagu
    - **Kidung Pasamuwan Jawi** — 1 lagu
- **Arsitektur Single-File Database (`banklycs.db`)**:
  - Semua 20.301 lagu disimpan dalam **1 file SQLite tunggal (~28 MB)** lengkap dengan indeks **FTS5 (Full-Text Search)**.
  - Tidak ada lagi puluhan ribu file kecil yang memperlambat Windows NTFS atau transfer flashdisk USB.
  - Pencarian lirik super cepat (<2 milidetik) langsung dari RAM/FTS5.
- **Kompilasi On-Demand (<1 ms per lagu)**:
  - File biner ProPresenter (`.pro`) dikompilasi secara *in-memory* hanya saat operator mengklik **INJECT**.
  - ProPresenter tetap bersih, ringan, dan **bebas lag/crash** (hanya menyimpan lagu-lagu ibadah aktif).
- **Studio Console GUI (Anti-Lag & Anti-Crash)**:
  - Antarmuka *dark mode* berkecepatan tinggi tanpa dependensi Python di laptop gereja.
  - Tinjauan lirik langsung (*live slide inspector*) dengan teks 18px yang jelas dan terbaca.
  - Penyusun rundown ibadah dengan fitur **1-Klik Inject ke ProPresenter**.
- **Standar Panggung Profesional**:
  - Maksimal **2 baris teks per slide** (mudah dibaca jemaat dan pemusik).
  - Menggunakan tema panggung teruji: Font `CMGSans-Bold`, ukuran font proporsional (fs134), Canvas 1920x1080.
  - Slide pertama otomatis berupa slide **`BLANK`** berlabel judul lagu.
  - Header bagian terstandarisasi (`VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, dll.).

---

## 🚀 Panduan Memulai Cepat (Quick Start)

### Syarat Sistem
- **Windows 10 / 11 (64-bit)**
- **ProPresenter 7**
- **NOL INSTALASI / DEPENDENSI TAMBAHAN**: **Tidak memerlukan Python sama sekali.** (Karena ProPresenter 7 adalah aplikasi .NET WPF, seluruh komputer yang menjalankan ProPresenter 7 sudah memiliki runtime .NET bawaan Windows).

### Cara Menjalankan Aplikasi
Cukup **double-click** file:
```
START.vbs   (1-Klik Senyap untuk Operator — 100% tanpa jendela terminal hitam)
```

1. Aplikasi **Studio Console** akan langsung terbuka di layar laptop Anda.
2. Ketik judul lagu / artis / nomor buku (misal `KJ 392`, `BE 210`, atau `Kuasa Darah`).
3. Klik tombol `+ TAMBAH KE RUNDOWN` untuk menyusun lagu ibadah minggu ini.
4. Klik tombol **`INJECT KE PROPRESENTER`**.
5. Buka ProPresenter 7 — Playlist ibadah langsung tersedia dan ProPresenter terbuka dalam **1 detik tanpa lag maupun crash!**

---

## 📂 Struktur Repositori Bersih

```text
banklycs/
│
├── 🚀 START.vbs             ← SATU-SATUNYA launcher 1-klik untuk operator gereja (senyap, 0 CMD)
│
├── 📂 database/             ← Database Lirik Tunggal (SQLite + FTS5)
│   └── 🗄️ banklycs.db       ← Master DB seluruh 20.301 lagu (~28 MB, zero disk bloat)
│
├── 📂 app/                  ← Antarmuka Web GUI Studio Console (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── 📂 engine/               ← Engine C# .NET 8 (Server, Protobuf Serializer, & On-Demand Injector)
│   ├── banklycs.exe         ← Binary native mandiri (single-file, embedded SQLite)
│   ├── Program.cs           ← Serializer Google Protobuf, parser, & in-memory builder
│   ├── StudioServer.cs      ← High-performance async server & SQLite catalog (<2ms search)
│   ├── ProEngine.csproj     ← Konfigurasi project .NET 8
│   └── ThemeTemplate        ← Template slide resmi CMGSans-Bold 1920x1080
│
├── 📂 markdowns/            ← Dokumentasi arsitektur, doktrin lirik, & panduan kontribusi
│   ├── RULES.md             ← Aturan wajib format lirik & penamaan
│   ├── GENERATE.md          ← Arsitektur kompilasi on-demand & injeksi ProPresenter
│   ├── GUIDE.md             ← Panduan pengguna, kontribusi gereja, & web scraping
│   └── AGENT.md             ← Konteks wajib untuk AI coding agent & status estafet
│
├── 📂 tools/                ← Skrip scraper & audit (khusus developer/kontributor)
│   ├── audit_cleanliness.py ← Auditor integritas database SQLite & ProPresenter
│   ├── migrate_txt_to_sqlite.py ← Script migrasi database
│   └── ...
│
└── 📄 README.md             ← Panduan pemakaian ini
```

---

## 🛠️ Perintah Berguna untuk Developer / Maintainer

Jika Anda ingin mengekspor seluruh 20.301 lagu kembali menjadi file teks biasa (`.txt`) kapan saja:
```powershell
engine\banklycs.exe export-txt [folder_tujuan]
# Contoh: engine\banklycs.exe export-txt database\txt
```
Dalam hitungan detik, seluruh lagu akan diekspor rapi ke disk.

Untuk mengaudit integritas database kapan saja:
```powershell
python tools\audit_cleanliness.py
```

---

## 📚 Dokumentasi Teknis

Dokumentasi lengkap tersimpan rapi di dalam folder [`markdowns/`](markdowns/):
- 📖 [RULES.md](markdowns/RULES.md) — Doktrin & standarisasi format lirik panggung.
- ⚡ [GENERATE.md](markdowns/GENERATE.md) — Arsitektur teknis kompilasi on-demand C# & injektor realtime ProPresenter.
- 🤝 [GUIDE.md](markdowns/GUIDE.md) — Panduan pemakaian, kontribusi gereja, & web scraping.
- 🤖 [AGENT.md](markdowns/AGENT.md) — Manual operasional AI agent, arsitektur database, & checklist pengerjaan.

---

## ⚖️ Lisensi & Disclaimer

- Tooling, script generator, dan engine compiler dilisensikan di bawah **MIT License**.
- Hak cipta lirik dan lagu sepenuhnya dimiliki oleh pencipta, label musik, penerbit, atau yayasan buku nyanyian gereja terkait (YAMUGER, BPK Gunung Mulia, Sinode HKBP, CCLI, dll.).
- Repositori ini diperuntukkan sebagai alat bantu pelayanan ibadah nirlaba (*non-commercial church ministry presentation tool*).
