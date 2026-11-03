# AGENT — MANUAL OPERASIONAL & STATUS ESTAFET

> **Tujuan Dokumen**: Panduan wajib bagi AI coding agent berikutnya yang bekerja pada repositori `banklycs`.  
> Dokumen ini memuat arsitektur sistem, aturan ketat (*Golden Rules*), alur kerja harian, status terkini, dan *backlog* tugas.

---

## 1. Peta Arsitektur Proyek

```text
banklycs/
├── database/          ← Master database lirik (.txt murni, flat, 20.301 lagu, Single Source of Truth)
├── app/               ← Aplikasi Studio Console GUI (server.py, index.html, style.css, app.js)
├── engine/            ← Compiler C# .NET 8 (ProEngine.exe) & isolasi cache (engine/PRO/*.pro)
├── tools/             ← Skrip scraper web & data pipeline (Python)
├── markdowns/         ← Dokumentasi inti: RULES.md, GENERATE.md, GUIDE.md, AGENT.md
├── START.bat          ← Launcher 1-klik bagi operator gereja
├── README.md          ← Dokumentasi publik bagi pengguna
└── .gitignore         ← Aturan ignore Git (mengabaikan cache engine/PRO/*.pro)
```

---

## 2. Doktrin Utama & Aturan Mutlak (Golden Rules)

### A. Anti-Halusinasi AI (Strict Zero-Tolerance)
- **DILARANG KERAS** mengarang lirik lagu menggunakan LLM. Seluruh lirik wajib murni hasil scraping atau transkripsi dari sumber resmi/rekaman asli.
- Jika artis/pencipta lagu tidak diketahui dari sumber: **gunakan nama file berupa judul saja** (contoh: `Adalah Baik Untuk.txt`), **JANGAN** mengarang nama artis atau menggunakan label `- No Name` atau `- Praise & Worship`.

### B. Aturan File Lirik di `database/`
1. **Format Penamaan**: `Judul Lagu - Artis.txt` atau `Judul Lagu.txt`.
2. **Title Case**: Judul wajib Title Case (contoh: `Kumenang.txt` ✔ / `KUMENANG.txt` ✘).
3. **Buku Himne Resmi**: Gunakan kode buku dan nomor sebagai artis (`KJ 392`, `BE 179`, `NKB 125`, `KK 459`, `PKJ 76`, `KLIK 446`, `NNBT 12`).
4. **Struktur Baku**:
   - Baris 1: `BLANK`
   - Baris 2: Judul lagu (identik persis dengan nama file)
   - Maksimal 2 baris teks per slide (dipisah satu baris kosong).
   - Huruf kapital hanya pada awal baris dan kata ganti ilahi (`Mu`, `Nya`, `Ku`, `Kau`, `Tuhan`, `Allah`).
   - Header bagian uppercase: `VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, `INTRO`, `OUTRO`, `ENDING`, `TAG`, `INTERLUDE`.

### C. Alur Kerja Injektor ProPresenter
1. Master database 20.301 lagu berada di `database/`.
2. Cache file binary ProPresenter 7 (`.pro`) berada di `engine/PRO/`.
3. Folder library ProPresenter aktif (`Libraries/Banks`) **TIDAK BOLEH** diisi 20.000 file sekaligus (memicu crash indeks Lucene dan deadlock thread WPF ProPresenter).
4. Injeksi playlist ibadah dilakukan on-demand melalui `app/server.py` dan `ProEngine.exe create-playlist`.

---

## 3. Perintah Kerja Harian & Pemeliharaan

```powershell
# 1. Menjalankan GUI lokal (Port 5050)
.\START.bat
# Atau manual: python app/server.py 5050

# 2. Menjalankan audit menyeluruh kebersihan file & sync
python tools/audit_cleanliness.py

# 3. Menjalankan verifikasi format lirik
python tools/verify_songs.py

# 4. Menjalankan ringkasan statistik database
python tools/summarize_db.py

# 5. Menjalankan perapihan flat otomatis (dry run & apply)
python tools/enforce_flat_rules.py
python tools/enforce_flat_rules.py --apply
```

---

## 4. Status Estafet Terkini (Handoff State)

| Metrik / Komponen | Status | Keterangan |
|---|---|---|
| **Master Database** | `database/` | **20.301** file `.txt`, flat murni (0 subfolder) |
| **Engine Cache** | `engine/PRO/` | **20.301** file `.pro`, 100% sinkron 1-ke-1 |
| **Aplikasi GUI** | `app/` | Studio Console berjalan stabil (Dark Grey theme, font 18px) |
| **Injeksi Real-Time** | Teruji & Berhasil | Injeksi on-demand berhasil tanpa membebani ProPresenter |
| **ProPresenter 7** | Berjalan Stabil | Startup instan (<1 detik), folder `Libraries/Banks` hanya berisi file aktif |
| **Git Status** | Branch `master` | Bersih (*clean working tree*), remote GitLab & Codeberg terkonfigurasi |

---

## 5. Backlog Tugas Prioritas

1. **Push ke GitLab & Codeberg**:
   - Pastikan repo kosong `banklycs` sudah dibuat di web UI Codeberg (`https://codeberg.org/zzdree/banklycs`).
   - Eksekusi `git push -u origin master` dan `git push -u codeberg master`.
2. **Melanjutkan Scraper yang Terputus**:
   - `tools/scrape_liriklagukristen.py`: Lanjutkan scraping sisa link yang belum ada di database.
   - `tools/scrape_buku_ende.py`: Ambil sisa lagu Buku Ende HKBP (nomor 845 s/d 867) dari API resmi HKBP.
3. **Perapihan Slide Overflow**:
   - Terdapat 369 file yang memiliki slide dengan >2 baris teks. Dapat diproses dengan pemisah slide cerdas pada baris kosong.
4. **Elevation Worship Reattribution**:
   - Terdapat ±37 lagu berbahasa Indonesia yang sebelumnya terlacak dengan nama artis `Elevation Worship` (warisan scraper lama). Lacak komposer aslinya di Psalmnote atau jadikan judul saja.
