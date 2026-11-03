# ProPresenter Lyric Banks 🎵

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
- **Standar Panggung Profesional**:
  - Maksimal **2 baris teks per slide** (mudah dibaca jemaat dan pemusik).
  - Menggunakan tema panggung teruji: Font `CMGSans-Bold`, ukuran font proporsional (fs134), Canvas 1920x1080.
  - Slide pertama otomatis berupa slide **`BLANK`** berlabel judul lagu.
  - Header bagian terstandarisasi (`VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, dll.).
- **Engine Kompilasi Berkecepatan Tinggi (.NET 8)**:
  - Didukung engine kompilasi berbasis C# yang langsung menghasilkan file binary Protobuf `.pro` resmi ProPresenter 7.
  - **Inkremental & Caching SHA-256**: Kompilasi puluhan ribu lagu hanya butuh **1-2 detik** untuk mendeteksi lagu baru/berubah.
  - **Playlist Ibadah Aman**: Mode inkremental tidak akan menghapus atau mereset playlist ibadah aktif Anda.
- **Pencarian Cepat (Zero Confusion)**:
  - Seluruh file berada dalam folder datar (*flat*) tanpa subfolder rumit. Cukup tekan `Ctrl + F` di ProPresenter dan ketik judul lagu atau kode buku (mis. `KJ 458`, `BE 234`).

---

## 🚀 Panduan Memulai Cepat (Quick Start)

### 1. Menggunakan GUI Playlist Builder (Direkomendasikan ⭐)
Cukup **double-click** file:
```
Start-GUI.bat
```
- Aplikasi **Studio Console** akan langsung terbuka di layar laptop Anda (antarmuka dark grey berkecepatan tinggi, anti-lag).
- Cari lagu dari 20.301 database master secara instan (<2 milidetik).
- Tinjau lirik bait per bait pada panel tengah (*live slide inspector*).
- Susun daftar lagu ibadah pada panel kanan, lalu klik tombol **`INJECT KE PROPRESENTER`**.
- Buka ProPresenter 7 — Playlist ibadah langsung tersedia dan ProPresenter terbuka dalam **1 detik tanpa lag maupun crash!**

### 2. Sinkronisasi Manual Engine (CLI)
Jika ingin mengompilasi ulang database `.pro`:
```powershell
powershell -ExecutionPolicy Bypass -File .\Generate.ps1
```

---

## ✍️ Cara Menambah Lagu Baru

Anda bisa menambahkan lagu karya gereja lokal atau aransemen baru dengan mudah:

1. Buat file teks baru di dalam folder [`TXT\`](TXT/) dengan format:
   - `Judul Lagu - Artis.txt` (Contoh: `Ku Hidup Bagi-Mu - JPCC Worship.txt`)
   - Atau `Judul Lagu.txt` jika artis/pencipta tidak diketahui.
2. Isi file mengikuti struktur baku:
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
3. Simpan file, lalu jalankan `.\Generate.ps1`. Lagu langsung otomatis muncul di ProPresenter dalam hitungan detik.

---

## 📂 Struktur Repositori

```
propresenter-lyricbanks/
├── TXT/                 # Master file lirik (.txt murni, flat, 20.300+ file)
├── PRO/                 # Output binary ProPresenter 7 (.pro)
├── Engine/              # ProEngine (.NET 8 C# compiler, source code, & cache)
├── Tools/               # Utility Python (Scraper, Validator, Enforcer rules)
├── Generate.ps1         # Script runner utama satu klik
├── Generate.md          # Doktrin lengkap & Golden Rules teknis format lirik
├── HANDOFF.md           # Log catatan pengembangan & checklist rilis
└── README.md            # Dokumentasi panduan umum
```

---

## 🤝 Kontribusi & Standar Kualitas (Golden Rules)

Kami sangat menyambut kontribusi penambahan lagu baru dari komunitas gereja! Harap perhatikan beberapa aturan utama:
1. **Dilarang Halusinasi AI**: Semua lirik harus bersumber dari sumber resmi atau rekaman ibadah yang valid.
2. **Title Case**: Judul lagu wajib Title Case (bukan ALL-CAPS).
3. **Maksimal 2 Baris per Slide**: Pisahkan bait yang panjang dengan baris kosong agar nyaman ditayangkan di proyektor panggung.
4. **Sentence Case pada Lirik**: Huruf kapital hanya di awal baris atau kata ganti ilahi (`-Nya`, `Tuhan`, `Kau`, `Allah`).

---

## ⚖️ Lisensi & Disclaimer

- Tooling, script generator, dan engine compiler dilisensikan di bawah **MIT License**.
- Hak cipta lirik dan lagu sepenuhnya dimiliki oleh pencipta, label musik, penerbit, atau yayasan buku nyanyian gereja terkait (YAMUGER, BPK Gunung Mulia, Sinode HKBP, CCLI, dll.).
- Repositori ini diperuntukkan sebagai alat bantu pelayanan ibadah nirlaba (*non-commercial church ministry presentation tool*).
