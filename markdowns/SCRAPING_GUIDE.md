# PANDUAN PENGEMBANGAN SCRAPER & PIPELINE DATA

> **Tujuan Dokumen**: Panduan teknis bagi developer yang ingin menambahkan skrip scraper baru atau menjalankan pipeline data massal untuk menambah koleksi lagu rohani di `banklycs`.

---

## 1. Etika & Aturan Scraping

1. **Anti-Duplikasi Ketat**:
   - Skrip scraper wajib memeriksa keberadaan judul lagu dan nama file secara rekursif sebelum mengunduh atau menulis file baru ke `database/`.
   - Gunakan fungsi pembanding: `title.lower().strip()`.
2. **Sanitisasi Teks & Karakter**:
   - Ganti karakter *curly quotes* (`’`, `‘`, `“`, `”`) menjadi ASCII (`'`, `"`).
   - Buang mojibake UTF-8 (`â€™`, `â€œ`, `\u200b`, dll.).
   - Hapus metadata web: tag HTML, iframe video YouTube, chord kunci gitar, dan tautan sosial media.
3. **Penyusunan Slide Standar**:
   - Pisahkan teks menjadi kelompok maksimal 2 baris per slide.
   - Header bagian harus dinormalkan ke uppercase: `VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, `INTRO`, `OUTRO`.
4. **Artis Tak Dikenal**:
   - Jangan pernah menyematkan label `No Name` atau `Praise & Worship`.
   - Jika artis tidak ditemukan dari API/halaman web, jadikan nama file hanya berupa judul saja: `f"{title}.txt"`.

---

## 2. Sumber Data Web Terpercaya (Whitelist)

| Sumber | Karakteristik Data | Script Parser |
|---|---|---|
| **Psalmnote** (`psalmnote.com`) | Metadata artis & album sangat akurat, format bait/reff rapi | `tools/scrape_psalmnote.py` |
| **Buku Ende HKBP** (`bukuende.hkbp.or.id`) | API resmi HKBP, lirik bahasa Batak Toba otentik | `tools/scrape_buku_ende.py` |
| **LirikLaguKristen.id** | Arsip lagu rohani lawas dan kontemporer Indonesia | `tools/scrape_liriklagukristen.py` |
| **Kidung.com** | Arsip lagu rohani Indonesia klasik | `tools/scrape_kidung_com.py` |
| **Alkitab.mobi / Kidung** | Teks resmi himne YAMUGER (KJ, NKB, PKJ) | `tools/scrape_hymnals.py` |
| **OpenLP / OpenLyrics** | Basis data lirik ibadah global open-source | `tools/import_english_openlp.py` |

---

## 3. Alur Kerja Setelah Scraping Massal

Setiap kali skrip scraper selesai dijalankan, wajib melakukan langkah pembersihan dan kompilasi berikut:

```powershell
# 1. Jalankan perapihan dan standardisasi Title Case otomatis
python tools/enforce_flat_rules.py --apply

# 2. Verifikasi kebersihan seluruh file database
python tools/verify_songs.py

# 3. Jalankan kompilasi incremental untuk memperbarui cache .pro
powershell -ExecutionPolicy Bypass -File .\engine\Generate.ps1
```
