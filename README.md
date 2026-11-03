# Banklycs 🎵

> **Koleksi 20.300+ Lagu Rohani & Himne Siap Tayang untuk ProPresenter 7.**  
> Dirancang khusus untuk tim multimedia gereja, operator proyektor, dan worship leader agar **tidak perlu lagi mencari & *copy-paste* lirik dari browser saat ibadah.**

---

## 🌟 Fitur Utama

- **20.300+ Lagu Terkurasi & Siap Tayang**:
  - **Praise & Worship Indonesia (14.500+ lagu)**: GMS Live, JPCC Worship, Symphony Worship, NDC Worship, Bethel, Sari Simorangkir, Franky Sihombing, dll.
  - **English Contemporary & Classic Hymns (2.500+ lagu)**: Hillsong Worship, Elevation Worship, Bethel Music, Planetshakers, Chris Tomlin, dll.
  - **Buku Nyanyian & Himne Klasik Lengkap**:
    - **KJ** (Kidung Jemaat) — 506 lagu
    - **NKB** (Nyanyikanlah Kidung Baru) — 269 lagu
    - **PKJ** (Pelengkap Kidung Jemaat) — 319 lagu
    - **KK** (Kidung Keesaan) — 755 lagu
    - **KLIK** (Kumpulan Lagu Ibadah Kreatif) — 471 lagu
    - **BE** (Buku Ende HKBP Batak) — 832 lagu
    - **NNBT** (Nyanyian Baru Bagi Tuhan) — 44 lagu
    - **Kidung Pasamuwan Jawi** — 36 lagu
- **Studio Console GUI (Anti-Lag & Anti-Crash)**:
  - Antarmuka *dark mode* berkecepatan tinggi tanpa dependensi rumit.
  - Pencarian lirik super cepat (<2 milidetik) untuk 20.000+ lagu.
  - Tinjauan lirik langsung (*live slide inspector*) dengan ukuran font 18px yang jelas dan terbaca.
  - Penyusun rundown ibadah dengan fitur **1-Klik Inject ke ProPresenter**.
- **Standar Panggung Profesional**:
  - Maksimal **2 baris teks per slide** (mudah dibaca jemaat dan pemusik).
  - Menggunakan tema panggung teruji: Font `CMGSans-Bold`, ukuran font proporsional (fs134), Canvas 1920x1080.
  - Slide pertama otomatis berupa slide **`BLANK`** berlabel judul lagu.
  - Header bagian terstandarisasi (`VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, dll.).

---

## 🚀 Panduan Memulai Cepat (Quick Start)

### Syarat Sistem
- **Windows 10 / 11**
- **ProPresenter 7**
- **Python 3.10+**

### Cara Menjalankan Aplikasi
Cukup **double-click** file:
```
START.vbs   (Rekomendasi untuk Operator — 100% senyap tanpa jendela terminal hitam)
```
*(Atau gunakan `START.bat` jika ingin menjalankan melalui terminal).*

1. Aplikasi **Studio Console** akan langsung terbuka di layar laptop Anda.
2. Ketik judul lagu / artis / nomor buku (misal `KJ 392`, `BE 210`, atau `Darah-Mu Yesus`).
3. Klik tombol `+ TAMBAH KE RUNDOWN` untuk menyusun lagu ibadah minggu ini.
4. Klik tombol **`INJECT KE PROPRESENTER`**.
5. Buka ProPresenter 7 — Playlist ibadah langsung tersedia dan ProPresenter terbuka dalam **1 detik tanpa lag maupun crash!**

---

## 📂 Struktur Repositori Bersih

```text
banklycs/
│
├── 📂 database/             ← SATU-SATUNYA tempat lirik master (.txt ramah Notepad & Git)
│   ├── Darah-Mu Yesus - JPCC Worship.txt
│   ├── KJ 392 - 'Ku Berbahagia.txt
│   └── ... (20.301 lagu master)
│
├── 📂 app/                  ← Antarmuka GUI Studio Console (server + web UI)
│   ├── server.py
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── 📂 engine/               ← Compiler C# .NET 8 & internal cache ProPresenter
│   ├── ProEngine.exe
│   ├── Src/
│   └── PRO/                 ← Cache file presentasi binary (.pro) terisolasi
│
├── 📂 tools/                ← Skrip scraper & audit (khusus developer/kontributor)
│   ├── scrape_psalmnote.py
│   ├── scrape_buku_ende.py
│   └── ...
│
├── 📂 markdowns/            ← Dokumentasi arsitektur, doktrin lirik, & panduan kontribusi
│   ├── RULES.md             ← Aturan wajib format lirik & penamaan
│   ├── GENERATE.md          ← Arsitektur engine kompilasi & injeksi ProPresenter
│   ├── GUIDE.md             ← Panduan pengguna, kontribusi gereja, & web scraping
│   └── AGENT.md             ← Konteks wajib untuk AI coding agent & status estafet
│
├── 🚀 START.vbs             ← Launcher 1-klik senyap untuk operator (tanpa jendela CMD)
├── ⚙️ START.bat             ← Launcher via command prompt
└── 📄 README.md             ← Panduan pemakaian ini
```

---

## ✍️ Cara Menambah Lagu Baru

Cukup buat file teks baru di dalam folder [`database/`](database/):
1. Format nama file: `Judul Lagu - Artis.txt` (atau `Judul Lagu.txt` jika artis tidak diketahui).
2. Format isi file:
   ```text
   BLANK
   Judul Lagu - Artis

   VERSE 1
   Baris lirik pertama
   Baris lirik kedua

   CHORUS
   Baris reff pertama
   Baris reff kedua
   ```
3. Begitu file disimpan, lagu langsung otomatis terindeks di pencarian GUI Banklycs.

Untuk panduan format lengkap, silakan baca [markdowns/RULES.md](markdowns/RULES.md) dan [markdowns/GUIDE.md](markdowns/GUIDE.md).

---

## 📚 Dokumentasi Teknis

Dokumentasi lengkap tersimpan rapi di dalam folder [`markdowns/`](markdowns/):
- 📖 [RULES.md](markdowns/RULES.md) — Doktrin & standarisasi format lirik panggung.
- ⚡ [GENERATE.md](markdowns/GENERATE.md) — Arsitektur teknis kompilasi C# & injektor realtime ProPresenter.
- 🤝 [GUIDE.md](markdowns/GUIDE.md) — Panduan pemakaian, kontribusi gereja, & web scraping.
- 🤖 [AGENT.md](markdowns/AGENT.md) — Manual operasional AI agent, checklist pengerjaan, & status estafet.

---

## ⚖️ Lisensi & Disclaimer

- Tooling, script generator, dan engine compiler dilisensikan di bawah **MIT License**.
- Hak cipta lirik dan lagu sepenuhnya dimiliki oleh pencipta, label musik, penerbit, atau yayasan buku nyanyian gereja terkait (YAMUGER, BPK Gunung Mulia, Sinode HKBP, CCLI, dll.).
- Repositori ini diperuntukkan sebagai alat bantu pelayanan ibadah nirlaba (*non-commercial church ministry presentation tool*).
