# AGENT CONTEXT & OPERATIONAL MANUAL — BANKLYCS

> **Tujuan Dokumen**: Panduan wajib bagi AI coding agent yang bekerja pada repositori `banklycs`.  
> Dokumen ini memuat arsitektur sistem, aturan ketat (*Golden Rules*), serta alur kerja agar kualitas kode dan lirik tetap terjaga.

---

## 1. Peta Arsitektur Proyek

```text
banklycs/
├── database/          ← Master database lirik (.txt murni, flat, 20.301 lagu, Single Source of Truth)
├── app/               ← Aplikasi Studio Console GUI (server.py, index.html, style.css, app.js)
├── engine/            ← Compiler C# .NET 8 (ProEngine.exe) & isolasi cache (engine/PRO/)
├── tools/             ← Skrip scraper web & data pipeline (Python)
├── markdowns/         ← Dokumentasi, doktrin sistem, aturan lirik, arsitektur, & panduan kontribusi
├── Start.bat          ← Launcher 1-klik bagi operator gereja
├── README.md          ← Dokumentasi publik bagi pengguna
└── .gitignore         ← Aturan ignore Git (mengabaikan cache PRO/*.pro agar repo ringan)
```

---

## 2. Doktrin Utama & Aturan Mutlak (Golden Rules)

### A. Anti-Halusinasi AI (Strict Zero-Tolerance)
- **DILARANG KERAS** mengarang lirik lagu menggunakan LLM. Seluruh lirik wajib murni hasil scraping atau transkripsi dari sumber resmi/rekaman asli.
- Jika artis/pencipta lagu tidak diketahui dari sumber: **gunakan nama file berupa judul saja** (contoh: `Adalah Baik Untuk.txt`), **JANGAN** mengarang nama artis atau menggunakan label `- No Name` atau `- Praise & Worship`.

### B. Aturan File Lirik di `database/`
1. **Format Penamaan**: `Judul Lagu - Artis.txt` atau `Judul Lagu.txt`.
2. **Title Case**: Judul wajib Title Case (contoh: `Kumenang.txt` ✔ / `KUMENANG.txt` ✘). Kata hubung kecil Indonesia (*dan, di, ke, dari, untuk, yang*) tetap huruf kecil kecuali di awal kalimat.
3. **Buku Himne Resmi**: Gunakan kode buku dan nomor sebagai artis (contoh: `KJ 392`, `BE 179`, `NKB 125`, `KK 459`, `PKJ 76`, `KLIK 446`, `NNBT 12`).
4. **Struktur Isi**:
   ```text
   BLANK
   Judul Lagu - Artis        ← Wajib identik persis dengan nama file

   VERSE 1
   Baris lirik pertama
   Baris lirik kedua

   CHORUS
   Baris reff pertama
   Baris reff kedua
   ```
   - Baris 1: `BLANK`
   - Baris 2: Judul lagu (identik dengan nama file)
   - Maksimal **2 baris teks per slide** (dipisah satu baris kosong).
   - Baris lirik berformat *sentence case* (huruf kapital hanya di awal baris atau kata ganti ilahi: `Mu`, `Nya`, `Ku`, `Kau`, `Tuhan`, `Allah`).
   - Header bagian uppercase: `VERSE`, `CHORUS`, `PRE-CHORUS`, `BRIDGE`, `INTRO`, `OUTRO`, `ENDING`, `TAG`, `INTERLUDE`.

---

### C. Alur Kerja Aplikasi & Injektor ProPresenter
1. Master database 20.301 lagu berada di `database/`.
2. Cache file binary ProPresenter 7 (`.pro`) berada di `engine/PRO/`.
3. Folder library ProPresenter aktif (`Libraries/Banks`) **TIDAK BOLEH** diisi 20.000 file sekaligus (karena memicu crash Lucene index dan deadlock WPF UI ProPresenter).
4. Aplikasi GUI (`app/`) bekerja dengan sistem **On-Demand Realtime Injector**:
   - Operator menyusun rundown playlist (5–10 lagu).
   - Saat klik `INJECT KE PROPRESENTER`, hanya file `.pro` lagu terpilih yang disalin ke `Libraries/Banks/`.
   - Engine mendaftarkan playlist ke file ProPresenter `Playlists/Library`.
   - ProPresenter membuka playlist tersebut secara instan tanpa lag.

---

## 3. Dokumen Terkait di Folder `markdowns/`

- [`RULES.md`](RULES.md): Doktrin lengkap penulisan lirik, penamaan file, dan standarisasi panggung.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): Analisis teknis penyebab crash ProPresenter 7 dan arsitektur On-Demand Realtime Injector.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): Panduan bagi kontributor open-source / gereja lain untuk menambah lagu baru.
- [`SCRAPING_GUIDE.md`](SCRAPING_GUIDE.md): Pedoman pengembangan scraper, whitelist sumber data, dan etika deduplikasi.
- [`HANDOFF.md`](HANDOFF.md): Status serah terima tugas teknis, metrik database terkini, dan backlog.

---

## 4. Perintah Kerja Harian & Pemeliharaan

```powershell
# 1. Menjalankan GUI lokal (Port 5050)
.\Start.bat
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
