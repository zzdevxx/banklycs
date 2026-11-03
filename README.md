# 🎶 Banklycs — ProPresenter 7 Worship Lyrics Engine & Database

[![Catalog](https://img.shields.io/badge/Catalog-25%2C904%20Songs-blue?style=flat-square&logo=musicbrainz)](https://github.com/zzdevxx/banklycs)
[![Database](https://img.shields.io/badge/Database-SQLite%20FTS5%20(44MB)-success?style=flat-square&logo=sqlite)](https://github.com/zzdevxx/banklycs)
[![Target](https://img.shields.io/badge/Target-ProPresenter%207-orange?style=flat-square)](https://renewedvision.com/propresenter/)
[![Engine](https://img.shields.io/badge/Engine-C%23%20.NET%208%20Native-purple?style=flat-square&logo=dotnet)](https://github.com/zzdevxx/banklycs)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> **Koleksi 25.904+ Lagu Rohani & Himne Siap Tayang untuk ProPresenter 7.**  
> Dirancang khusus untuk tim multimedia gereja, operator proyektor, dan worship leader agar **tidak perlu lagi mencari & *copy-paste* lirik dari browser saat ibadah.**

---

## ⚡ Fitur Utama

- **25.904 Lagu Terkurasi & Siap Tayang (100% Zero-Duplicate)**:
  - **Praise & Worship Indonesia (15.350+ lagu)**: GMS Live, JPCC Worship, Symphony Worship, NDC Worship, Bethel, Sari Simorangkir, Franky Sihombing, dll.
  - **English Contemporary & Classic Hymns (6.370+ lagu)**: Hillsong Worship, Elevation Worship, Bethel Music, Planetshakers, Chris Tomlin, Matt Redman, Songs of Fellowship, Martin Luther, John Newton, dll.
  - **Buku Nyanyian & Himne Gereja Lengkap**:
    - **KJ** (Kidung Jemaat) — 1.296 lagu
    - **BE** (Buku Ende HKBP Batak) — 844 lagu
    - **KK** (Kidung Keesaan) — 766 lagu
    - **KLIK** (Kumpulan Lagu Ibadah Kreatif) — 462 lagu
    - **PKJ** (Pelengkap Kidung Jemaat) — 401 lagu
    - **NKB** (Nyanyikanlah Kidung Baru) — 364 lagu
    - **NNBT** (Nyanyian Baru Bagi Tuhan) — 46 lagu
    - **Kidung Pasamuwan Jawi** — 4 lagu
- **Arsitektur Single-File Database (`database/banklycs.db`)**:
  - Semua 25.904 lagu tersimpan dalam **1 file SQLite tunggal (~44 MB)** lengkap dengan indeks **FTS5 (Full-Text Search)**.
  - Tidak ada lagi puluhan ribu file kecil yang memperlambat Windows NTFS atau proses transfer flashdisk USB.
  - Pencarian lirik super cepat (<0.4 milidetik) langsung dari RAM/FTS5.
- **Kompilasi On-Demand (<1 ms per lagu)**:
  - File biner ProPresenter (`.pro`) dikompilasi secara *in-memory* hanya saat operator mengklik **INJECT**.
  - ProPresenter tetap bersih, ringan, dan **bebas lag/crash** (hanya menyimpan lagu-lagu ibadah aktif di disk).
- **Studio Console GUI (Anti-Lag & Anti-Crash)**:
  - Antarmuka *dark mode* berkecepatan tinggi tanpa dependensi Python di laptop gereja.
  - Tinjauan lirik langsung (*live slide inspector*) dengan teks yang jelas dan terbaca.
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
- **Nol Instalasi Tambahan**: Tidak memerlukan instalasi Python di laptop ibadah. Seluruh komputer yang menjalankan ProPresenter 7 sudah memiliki runtime .NET bawaan.

### Cara Menjalankan Aplikasi
Cukup **double-click** file:
```
START.vbs   (1-Klik Senyap untuk Operator — 100% tanpa jendela terminal CMD)
```

1. Aplikasi **Studio Console** akan langsung terbuka di browser/Edge App.
2. Ketik judul lagu / artis / nomor buku (misal `KJ 392`, `BE 210`, atau `Kuasa Darah`).
3. Klik tombol `+ TAMBAH KE RUNDOWN` untuk menyusun lagu ibadah minggu ini.
4. Klik tombol **`INJECT KE PROPRESENTER`**.
5. Buka ProPresenter 7 — Playlist ibadah langsung tersedia dan ProPresenter terbuka dalam **1 detik tanpa lag maupun crash!**

---

## 📂 Struktur Repositori

```text
banklycs/
├── START.vbs              <- Launcher 1-klik untuk operator gereja (senyap, 0 CMD)
├── database/
│   └── banklycs.db        <- Master SQLite DB seluruh 20.301 lagu (~30 MB, FTS5)
├── app/                   <- Antarmuka Web GUI Studio Console (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── engine/                <- Engine C# .NET 8 (Server, Protobuf Serializer, & On-Demand Injector)
│   ├── banklycs.exe       <- Binary native mandiri (single-file, embedded SQLite)
│   ├── Program.cs         <- Serializer Google Protobuf & in-memory builder
│   ├── StudioServer.cs    <- High-performance async server & SQLite catalog (<2ms search)
│   ├── ProEngine.csproj   <- Konfigurasi project .NET 8
│   └── ThemeTemplate      <- Template slide resmi CMGSans-Bold 1920x1080
├── markdowns/             <- Dokumentasi arsitektur, doktrin lirik, & panduan teknis
│   ├── RULES.md           <- Standarisasi format lirik panggung
│   ├── GENERATE.md        <- Arsitektur kompilasi on-demand & injeksi ProPresenter
│   ├── GUIDE.md           <- Panduan pengguna & kontribusi gereja
│   └── AGENT.md           <- Manual operasional AI coding agent
├── tools/                 <- Skrip scraper & audit (khusus developer/maintainer)
│   ├── audit_cleanliness.py
│   └── migrate_txt_to_sqlite.py
├── LICENSE                <- Lisensi resmi MIT (@zzdevxx)
└── README.md              <- Panduan pemakaian ini
```

---

## 🛠️ Perintah untuk Developer / Maintainer

Mengekspor seluruh 20.301 lagu kembali menjadi file teks biasa (`.txt`):
```powershell
engine\banklycs.exe export-txt [folder_tujuan]
# Contoh: engine\banklycs.exe export-txt database\txt
```

Mengaudit integritas database kapan saja:
```powershell
python tools\audit_cleanliness.py
```

---

## 📜 Lisensi & Disclaimer

- Source code, engine compiler, dan tooling dilisensikan di bawah **[MIT License](LICENSE)** © 2026 **Andreas Restuawanta Christwara ([@zzdevxx](https://github.com/zzdevxx))**.
- Hak cipta teks lirik dan himne sepenuhnya dimiliki oleh pencipta, label musik, penerbit, atau yayasan buku nyanyian gereja terkait (YAMUGER, BPK Gunung Mulia, Sinode HKBP, CCLI, dll.).
- Repositori ini diperuntukkan sebagai alat bantu pelayanan ibadah nirlaba (*non-commercial ecclesiastical worship presentation tool*).
