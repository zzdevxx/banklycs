# GUIDE — PANDUAN PENGGUNA, KONTRIBUSI & SCRAPING

> **Proyek**: `banklycs` — Panduan Komprehensif Pengguna & Developer  
> **Terakhir diperbarui**: 2026-11-03

---

## 1. Panduan Cepat untuk Operator Gereja

1. Cukup double-click file **`START.vbs`** di folder root `banklycs` (senyap tanpa jendela terminal).
2. Jendela **Studio Console** akan terbuka di layar laptop.
3. Ketik judul lagu, artis, atau nomor buku himne pada bilah pencarian (contoh: `KJ 392`, `BE 210`, atau `Kuasa DarahMu`). Hasil pencarian muncul seketika (<2 ms).
4. Klik tombol **`+ TAMBAH KE RUNDOWN`** untuk memasukkan lagu ke daftar ibadah minggu ini.
5. Klik tombol **`INJECT KE PROPRESENTER`**.
6. Buka ProPresenter 7 — Playlist ibadah langsung tersedia di sidebar dan siap ditayangkan.

---

## 2. Panduan Kontribusi Lagu Baru

Semua gereja, persekutuan, dan relawan multimedia dipersilakan untuk berkontribusi menambahkan lagu baru atau memperbaiki lirik yang ada.

### A. Prinsip Kontribusi
- **DILARANG MENGGUNAKAN AI/LLM** untuk mengarang lirik lagu. Seluruh lirik harus berasal dari sumber otentik (buku nyanyian, rekaman ibadah resmi, atau situs lirik tepercaya).
- Seluruh kontribusi lagu hanya ditambahkan ke folder [`database/txt/`](../database/txt/) dalam bentuk file `.txt` murni. Jangan menyunting atau mengirim file `.pro` secara manual melalui Pull Request.

### B. Langkah Menambah Lagu
1. Buat file baru di dalam `database/txt/` dengan nama: `Judul Lagu - Nama Artis.txt` (atau `Judul Lagu.txt` jika artis tidak diketahui).
2. Isi file dengan format standar panggung:
   ```text
   BLANK
   Judul Lagu - Nama Artis

   VERSE 1
   Baris pertama bait satu
   Baris kedua bait satu

   CHORUS
   Baris pertama reff
   Baris kedua reff
   ```
3. Pastikan baris lirik berformat *sentence case* (bukan huruf kapital semua) dan maksimal 2 baris per slide.
4. Simpan dengan format encoding **UTF-8** (tanpa BOM).

---

## 3. Panduan Web Scraping & Pipeline Data

Jika Anda adalah developer yang ingin menjalankan scraper atau mengimpor data massal:

### A. Etika & Pencegahan Duplikasi
- **Pengecekan Rekursif**: Skrip scraper wajib memeriksa judul lagu yang sudah ada di `database/txt/` sebelum mengunduh untuk mencegah duplikasi.
- **Sanitisasi Karakter**: Konversi kutip miring (`’`, `‘`, `“`, `”`) menjadi petik ASCII (`'`, `"`). Bersihkan mojibake UTF-8 dan tag HTML.
- **Artis Anonim**: Jika nama artis tidak ditemukan pada halaman sumber, gunakan nama file berupa judul lagu saja. Jangan menggunakan label `- No Name` atau `- Praise & Worship`.

### B. Sumber Data Terpercaya (Whitelist)
| Sumber | Karakteristik Data | Script Parser |
|---|---|---|
| **Psalmnote** (`psalmnote.com`) | Metadata artis & album sangat akurat, format bait/reff rapi | `tools/scrape_psalmnote.py` |
| **Buku Ende HKBP** (`bukuende.hkbp.or.id`) | API resmi HKBP, lirik bahasa Batak Toba otentik | `tools/scrape_buku_ende.py` |
| **LirikLaguKristen.id** | Arsip lagu rohani lawas dan kontemporer Indonesia | `tools/scrape_liriklagukristen.py` |
| **Kidung.com** | Arsip lagu rohani Indonesia klasik | `tools/scrape_kidung_com.py` |
| **Alkitab.mobi / Kidung** | Teks resmi himne YAMUGER (KJ, NKB, PKJ) | `tools/scrape_hymnals.py` |
| **OpenLP / OpenLyrics** | Basis data lirik ibadah global open-source | `tools/import_english_openlp.py` |

### C. Alur Pasca-Scraping Massal
Setelah menjalankan scraper, selalu jalankan audit dan kompilasi:
```powershell
# 1. Rapikan Title Case & duplikat otomatis
python tools/enforce_flat_rules.py --apply

# 2. Verifikasi kebersihan format lirik
python tools/verify_songs.py

# 3. Kompilasi incremental ke cache .pro
powershell -ExecutionPolicy Bypass -File .\engine\Generate.ps1
```
