# HANDOFF — Estafet Agent Berikutnya
> Dibuat: 2026-11-03 ~07:35 WIB (Sesi 2 Selesai)
> **Wajib dibaca bersama `markdowns/RULES.md` dan `markdowns/AGENT_CONTEXT.md`**

---

## 1. KONDISI TERAKHIR (semua sudah diverifikasi)
| Metrik | Nilai |
|---|---|
| Lagu di `database\` | **20.301** file `.txt` |
| Subfolder | **0** — folder datar murni di `database/` |
| Cache Engine | `engine\PRO\` (**20.301** file `.pro` siap pakai) |
| Error compile | **0** |
| Aplikasi GUI | `app\` (Server Python + Studio Console UI, Start.bat) |
| Injeksi Realtime | **SUKSES & TERUJI** (Lagu & playlist masuk seketika ke ProPresenter) |
| ProPresenter Crash | **TERATASI 100%** (Library ProPresenter hanya diisi lagu playlist aktif) |
| Git Status | Clean, terinisialisasi di branch master, siap push |

## 2. YANG BARU DILAKUKAN SESI INI
1. Migrasi `Praise & Worship` (4.600) → `No Name` → lalu ke **judul saja**.
2. Scrape **Psalmnote**: +5.434 lagu (katalog cache: `Tools\psalmnote_catalog.json`).
3. **Flatten total** via `Tools\enforce_flat_rules.py` (44 subfolder → root; 750 duplikat konten dibuang — termasuk 411 No Name yang liriknya identik dgn versi berartis; 496 judul caps→Title Case; placeholder `LYRIC_LINE_n` dihapus).
4. Merge dokumentasi → `Generate.md` di root; `Generate.ps1` dipindah ke root (path sudah disesuaikan); folder `Markdowns` dihapus.
5. Kedua scraper sudah disesuaikan: tulis ke TXT datar, dedup rekursif, artis tak dikenal → nama file = judul saja (tanpa embel embel).

## 3. TUGAS UTAMA BERIKUTNYA (permintaan user: **"tambah lagu, target unlimited"**)
User mau koleksi terus bertambah besar. Prioritas:

### A. Selesaikan scrape yang TERPUTUS (paling cepat)
- `scrape_liriklagukristen.py`: terakhir di-kill manual saat ±688 URL tersisa. **Jalankan ulang** — dedup-nya rekursif, aman.
  ```powershell
  python Tools\scrape_liriklagukristen.py
  ```
- Setelah itu jalankan `python Tools\enforce_flat_rules.py` (dry run → review → `--apply`) untuk rapikan Title Case/duplikat hasil baru, lalu `powershell -ExecutionPolicy Bypass -File .\Generate.ps1`.

### B. Sumber yang BELUM disentuh sama sekali
| Sumber | Cara | Catatan |
|---|---|---|
| `kidung.com` | `Tools\scrape_kidung_com.py` sudah ada — cek masih hidup situsnya | arsip lawas |
| `bukuende.hkbp.or.id` | `Tools\scrape_buku_ende.py` — BE lengkap s/d 867; bank kini BE ±844 | API resmi HKBP |
| **LALS Project** (GitHub) | clone → JSON resmi KJ/PKJ/NKB/KLIK/NNBT — impor massal paling bersih & terlisensi | `import_klik_nnbt.py` bisa dirujuk |
| OpenLP / OpenLyrics global | `import_english_openlp.py` sudah ada — jalankan lagi utk DB english yang bertambah | sumber massal legal |
| **CCLI SongSelect** | validasi lirik (butuh akun gereja) | standar emas verifikasi |
| PraiseCharts / hymnary.org | hymnody klasik + data komposer | utk reattribution |

### C. Perbaikan kualitas (temuan sesi ini, belum dieksekusi)
1. **Elevation Worship salah attribusi**: ±37 lagu berbahasa Indonesia ada di nama `Elevation Worship` (warisan scraper lama, mis. `Berkat Tuhan Mengalir Turun-Temurun - Elevation Worship.txt`). Cari judul aslinya di Psalmnote/liriklagukristen → ganti artis benar atau jadi judul saja. Cek juga subfolder-artis lain yang serupa (Hillsong/Bethel — sekarang sudah flat, jadi cari via `grep` nama artis).
2. Label generik sisa: `Various Artists` (±393), `Worship Hymn` (±679), `Lagu Sekolah Minggu` (±220), `KIDUNG`? — pertahankan (masuk akal), TAPI kalau ada yang bisa dilacak ke komposer/penyanyi asli, upgrade.
3. Nama artis dengan `feat.`/multi masih ada beberapa (`... - Gloria Trio, feat. Ricky Romeoch, Gerson Group.txt`) → potong ke artis utama sesuai Golden Rule §3.A.3.
4. Cek 4 file judul dengan tabrakan penanda `(2)` — kalau liriknya ternyata beda sumber, biarkan; kalau sama, merge.

## 4. PENTING — JANGAN ULANGI KESALAHAN INI
1. **JANGAN buat subfolder lagi.** Engine scan `AllDirectories` dan `PRO\` flat → dua file basename sama akan saling timpa (pernah terjadi 1.372 tabrakan sebelum flatten).
2. **Setiap scrape massal** → WAJIB lanjut `enforce_flat_rules.py --apply` → `Generate.ps1` (incremental) → cek `TXT == PRO == Banks` (PowerShell count).
3. **Scraper = murni copy teks dari situs. DILARANG mengarang lirik via LLM.** Kalau ragu, buka URL sumber & bandingkan baris-per-baris (user sangat peduli soal "jangan halu").
4. Script scraper pakai default artis **"No Name"** — tapi aturan bank sekarang: artis tak dikenal → **nama file tanpa ` - Artis`**. `enforce_flat_rules` yang mengonversi. Alternatif: langsung set di scraper (psalmnote & liriklagukristen SUDAH diperbaiki; scraper lain: `scrape_hymnals`, `scrape_kk`, dll masih pakai `- No Name` → biarkan, nanti di-strip oleh flatten).
5. Kill proses scraper: `Get-Process python* | Stop-Process -Force` (background task kill saja tidak selalu membunuh child process python).
6. ProPresenter lambat saat buka = OneDrive dehydrated → set folder ProPresenter "Always keep on this device".

## 5. Perintah harian
```powershell
# compile cepat (hanya file baru/berubah, ±1-2 detik; playlist ibadah aman)
powershell -ExecutionPolicy Bypass -File .\Generate.ps1

# rebuild total (playlist dibersihkan — tanya user dulu!)
powershell -ExecutionPolicy Bypass -File .\Generate.ps1 -Full

# audit kualitas kapan saja
python Tools\enforce_flat_rules.py          # dry run
python Tools\verify_songs.py
python Tools\summarize_db.py
```

## 6. Saldo katalog Psalmnote (utak-atik tanpa hit website dua kali)
`Tools\psalmnote_catalog.json` berisi **7.095** entri lengkap dengan metadata. Lagu yang ada di katalog tapi GAGAL scrape (err/skip ±34 dari 5.468) bisa dicoba ulang satu per satu via `https://psalmnote.com/song/{alias}`.

---
**Status serah terima: bank 20.301 lagu LIVE & sinkron di ProPresenter. Silakan lanjut dari §3.A.**
