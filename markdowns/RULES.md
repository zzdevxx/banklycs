# BANKLYCS — DOKTRIN & ATURAN LIRIK MASTER (RULES)
> **Repo**: `banklycs` (portable — semua tool resolve path relatif)
> **Database lirik**: `database\` — **20.301 lagu, satu folder datar, TANPA subfolder**
> **Cache ProPresenter**: `engine\PRO\` (format binary Protobuf Pro7)
> **Aplikasi GUI**: `app\` (Studio Console UI, Start.bat)
> **Konteks Agent**: baca `markdowns\AGENT_CONTEXT.md` dan `markdowns\HANDOFF.md`
> **Terakhir diperbarui**: 2026-11-03

---

## 1. Tujuan (Goals)
1. Operator **tidak pernah** copy-paste lirik dari browser lagi. Buka `Start.bat`, cari judul di antara 20.000+ lagu dalam 2 ms, klik inject ke ProPresenter.
2. ProPresenter tetap ringan dan cepat terbuka (1 detik) tanpa crash karena library hanya menampung lagu rundown aktif.
3. **Simple**: satu folder `database\` berisi file `.txt`. Tidak ada subfolder yang membingungkan.

---

## 2. Struktur Folder
```
banklycs/
├── database/        ← master lirik .txt (20.301 lagu flat)
├── app/             ← aplikasi Studio Console GUI
├── engine/          ← compiler C# .NET 8 & isolasi cache engine/PRO/
├── tools/           ← scraper & data pipeline (Python)
├── markdowns/       ← panduan doktrin, aturan lirik, & konteks agent
├── Start.bat        ← launcher satu klik
└── README.md        ← panduan umum
```
ProPresenter Library: `C:\Users\ASUS\OneDrive\Dokumen\ProPresenter\Libraries\Banks`
(auto-registered mode MERGE; playlist ibadah aman selama build incremental).

---

## 3. Aturan Wajib File TXT (Golden Rules)

### A. Penamaan File
- **Poin 1 — Format**: `Judul Lagu.txt` atau `Judul Lagu - Artis.txt`.
- **Poin 2 — Judul saja (tanpa artis)** untuk lagu yang **artinya/penyanyinya tidak diketahui** dari sumber (dulu berlabel `No Name`). Contoh: `Adalah Baik Untuk.txt`.
- **Poin 3 — Satu artis saja** bila multi-artis/feat. — ambil artis utama. Contoh: `Build My Life - Pat Barrett.txt`.
- **Poin 4 — Pengecualian sah duo/tim resmi**: `Robert & Lea Sutanto`, `Rivers & Robots`, `All Sons & Daughters`.
- **Poin 5 — Buku himne pakai nomor sebagai "artis"**: `KJ 392`, `BE 179`, `NKB 125`, `KK 459`, `PKJ 76`, `KLIK 446`, `NNBT 12`. Nomor tetap bisa diketik di pencarian ProPresenter.
- **Poin 6 — Title Case, BUKAN kapital semua**: `Kumenang.txt` ✔ / `KUMENANG.txt` ✘.
  - Kata kecil Indonesia (dan, di, ke, untuk, yang...) tetap kecil kecuali kata pertama.
  - Huruf pertama judul wajib kapital. Nama orang/tempat dipertahankan apa adanya dari sumber.
- **Poin 7 — Nama file = baris 2 isi file.** Keduanya harus identik persis (slide BLANK menampilkan judul).
- **Poin 8 — Basename HARMONIS GLOBAL** (folder PRO datar, tidak boleh ada 2 file `.txt` dengan nama sama).

### B. Struktur Isi
```
BLANK
Judul Lagu - Artis        ← identik dengan nama file

VERSE 1
Baris lirik 1
Baris lirik 2

CHORUS
Baris reff 1
Baris reff 2
```
- Baris 1 = `BLANK`, baris 2 = judul, lalu baris kosong.
- **Header bagian (UPPERCASE, recognized engine, case-insensitive)**:
  `BLANK`, `INTRO`, `VERSE`/`VERSE 1..n`, `PRE-CHORUS`, `CHORUS`, `BRIDGE`, `TAG`, `INTERLUDE`, `ENDING`, `OUTRO`.
  - `BAIT` dinormalkan → `VERSE`; `REFF` → `CHORUS`; `PRE CHORUS` → `PRE-CHORUS`.
- **Maksimal 2 baris per slide** (antar slide dipisah satu baris kosong).
- **Baris lirik TIDAK boleh kapital semua** — sentence case (`Ada kuasa dalam darah-Nya` bukan `ADA KUASA DALAM DARAH-NYA`). Header bagian tetap kapital.
- **Kata ganti ilahi**: `Mu`, `Nya`, `Ku`, `Kau` kapital (`diamankan-Nya`, `Berserah Kepada Allahku`).
- **Encoding UTF-8 tanpa BOM**, petik ASCII `'` `"`, tanpa mojibake/zero-width.
- **Dilarang**: placeholder `LYRIC_LINE_n`, teks `Chords and Lyrics`, link URL, lirik karangan AI.

### C. Isi = Sumber Valid, Bukan Halusinasi
- Seluruh lirik hasil **scrape langsung** dari situs (lihat §6) — diverifikasi identik dengan halaman sumber.
- Tidak ada pembuatan lirik oleh LLM. Kalau sumber tidak menyebut penyanyi → **judul saja**, bukan mengarang artis.

---

## 4. Menambah Lagu Baru (3 cara)
1. **Buat manual**: simpan `.txt` mengikuti §3 langsung di `TXT\` → jalankan `Generate.ps1`. Selesai < 1 detik (incremental).
2. **Scraper** (lihat §5): otomatis menulis ke `TXT\` datar, skip yang sudah ada (cek rekursif + judul).
3. **Templat kosong**:
   ```powershell
   # contoh 2 baris per slide, header kapital, tanpa artis jika tidak diketahui
   ```

## 5. Tools & Scripts (folder `Tools\`)
| Script | Fungsi |
|---|---|
| `scrape_psalmnote.py` | Katalog API psalmnote.com (7.095 lagu) → TXT datar, artis asli |
| `scrape_liriklagukristen.py` | Sitemap liriklagukristen.id (±4.800 lagu) → TXT datar; fallback artis `No Name` → nama file jadi judul saja (via enforce rules) |
| `scrape_kidung_com.py`, `scrape_kk.py`, `scrape_buku_ende.py`, `scrape_hymnals.py` | Buku himne (KJ/PKJ/NKB/KK/BE) — pakai penamaan `Judul - KJ 123` |
| `import_english_openlp.py`, `import_klik_nnbt.py`, `import_pujian_jawa.py` | Impor basis data open-source |
| `normalize_unicode.py` | Perbaikan mojibake/karakter aneh (idempoten) |
| `enforce_flat_rules.py` | **Perapi massal**: datar, judul Title Case, hapus duplikat konten, baris2=namafile, buang placeholder. Jalankan dry-run dulu, lalu `--apply` |
| `verify_songs.py`, `verify_titles.py`, `audit_cleanliness.py` | Verifikasi kualitas bank |
| `summarize_db.py` | Ringkasan statistik koleksi |

Setelah scraper massal: jalankan `python Tools\enforce_flat_rules.py` (cek) → `--apply` → `Generate.ps1`.

---

## 6. Sumber Web Terpercaya (untuk validasi & scraping)
**Indonesia:**
1. **Psalmnote** `https://psalmnote.com` — metadata lengkap + struktur VERSE/CHORUS (JPCC, GMS, NDC, Symphony, dll).
2. **LirikLaguKristen.id** `https://liriklagukristen.id` — lagu lawas PD/80-90an & kontemporer.
3. **Kidung.com** `https://kidung.com` — arsip rohani Indonesia.
4. **Alkitab.mobi/kidung** — teks resmi KJ, PKJ, NKB, KK, BE.
5. **Buku Ende HKBP** `https://bukuende.hkbp.or.id` — BE Batak toba.
6. **LALS Project** (GitHub) — JSON buku nyanyian Indonesia.

**Internasional:**
7. **CCLI SongSelect** `https://songselect.ccli.com` — standar emas lirik gereja global.
8. **PraiseCharts** — chord + lirik.
9. **Hymnary.org** — ensiklopedia himne klasik (data komposer abad 16–20).
10. **OpenLP / OpenLyrics DB** (GitHub) — basis data ibadah open-source.

Cara validasi cepat: buka URL sumber, cari lagu, bandingkan baris per baris dengan isi `.txt`.

---

## 7. Kompilasi Engine
```powershell
# INCREMENTAL (default, aman — playlist tidak disentuh)
powershell -ExecutionPolicy Bypass -File .\Generate.ps1

# FULL REBUILD (kosongkan PRO & library Banks; playlist ikut bersih)
powershell -ExecutionPolicy Bypass -File .\Generate.ps1 -Full

# Rebuild binary engine bila source C# diubah
powershell -ExecutionPolicy Bypass -File .\Generate.ps1 -RebuildEngine -Full
```
- Engine memindai `TXT\` rekursif (`SearchOption.AllDirectories`) → tetap benar walau folder datar.
- Incremental pakai cache SHA-256 (`Engine\compile_manifest.json`): file tak berubah → skip; `.pro` yatim (TXT dihapus/rename) → otomatis dibersihkan dari `PRO\` & library.
- Tema master `zz` (`Lyric - Praise`, CMGSans-Bold fs134, 1920x1080; fallback `Engine\ThemeTemplate`).
- Performa: full 20.301 lagu ± 30-60 detik; incremental ± 1-4 detik.
- Error kompilasi per-file dicatat `Engine\last_errors.txt`, tidak menggagalkan batch.
- OneDrive: kalau ProPresenter lambat, set folder `ProPresenter` "Always keep on this device".

## 8. Alur Harian Operator
1. ProPresenter 7 → tab Search → ketik judul (atau nomor `KJ 458`, `BE 234`).
2. Double-click lagu → preview → tayangkan; drag ke playlist untuk rundown.
3. Lagu baru? Taruh `.txt` di `TXT\` → `Generate.ps1` → langsung muncul.

## 9. Riwayat Perapihan (changelog)
- **2026-11-02**: Migrasi label artis `Praise & Worship` (4.600 file) → hapus 2.408 duplikat + rename `No Name`; scrape Psalmnote +5.434 lagu; **FLATTEN total**: 44 subfolder (7.413 file) digabung ke root, 750 duplikat konten dihapus (411 di antaranya No Name yang identik dgn versi berartis), 496 judul ALL-CAPS→Title Case, 3.029 `No Name`→judul saja, placeholder `LYRIC_LINE_n` (30 file) dibuang, baris2 disejajarkan dgn nama file (181 selisih). **Akhir: 20.301 file datar, 0 error.** Backup: `_backup_TXT_20261102.zip` (9,7 MB).
