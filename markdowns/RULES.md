# RULES — DOKTRIN & STANDAR LIRIK MASTER

> **Proyek**: `banklycs` — Bank Lirik & Injektor Cepat ProPresenter 7  
> **Master Database**: `database/` — **20.301 lagu, SATU folder datar murni, TANPA subfolder**  
> **Engine & Cache**: `engine/PRO/` (file binary Protobuf ProPresenter 7)  
> **Studio Console GUI**: `app/` (Server lokal Python + UI antarmuka web, `START.bat`)  
> **Terakhir diperbarui**: 2026-11-03

---

## 1. Filosofi & Visi Sistem

1. **Operator Sentris**: Operator proyektor gereja **tidak boleh lagi** mencari & *copy-paste* lirik terburu-buru dari Google/browser saat kebaktian berlangsung. Cukup buka `START.bat`, ketik judul/nomor buku, lagu ketemu dalam <2 milidetik, lalu klik `INJECT KE PROPRESENTER`.
2. **ProPresenter Selalu Ringan (<1 detik startup)**: Memasukkan 20.000 file sekaligus ke dalam ProPresenter terbukti menyebabkan *deadlock* thread UI dan tabrakan indeks Lucene. Banklycs menyimpan 20.000 lagu di vault lokal, dan **hanya menyuntikkan (inject) 5–10 lagu rundown aktif** ke ProPresenter.
3. **Penyimpanan Sederhana (Single Source of Truth)**: Folder `database/` berisi file `.txt` murni berformat standar yang dapat dibaca manusia (*human-readable*), ramah Notepad, dan mudah dilacak perubahannya di Git. File `.pro` di `engine/PRO/` hanyalah artefak kompilasi mesin.

---

## 2. Aturan Format & Penamaan File

1. **Format Standar**: `Judul Lagu - Artis.txt` atau `Judul Lagu.txt`.
2. **Tanpa Artis Jika Tidak Diketahui**: Jika artis/pencipta lagu tidak tercantum pada sumber resmi, gunakan nama file berupa judul lagu saja (contoh: `Adalah Baik Untuk.txt`). **DILARANG** menambahkan label rekaan seperti `- No Name`, `- Unknown`, atau `- Praise & Worship`.
3. **Satu Artis Utama**: Jika lagu dinyanyikan secara kolaborasi/fitur (*featuring*), ambil hanya artis utama (contoh: `Build My Life - Pat Barrett.txt`).
4. **Pengecualian Sah Duo/Grup Resmi**: Nama grup yang sah dipertahankan utuh (contoh: `Robert & Lea Sutanto`, `Rivers & Robots`, `All Sons & Daughters`, `GMS Live`, `JPCC Worship`).
5. **Standar Buku Himne Resmi**: Gunakan singkatan buku dan nomor urut sebagai "artis" agar mudah dicari langsung di pencarian:
   - `KJ 392` (Kidung Jemaat)
   - `BE 179` (Buku Ende HKBP)
   - `NKB 125` (Nyanyikanlah Kidung Baru)
   - `KK 459` (Kidung Keesaan)
   - `PKJ 76` (Pelengkap Kidung Jemaat)
   - `KLIK 446` (Kumpulan Lagu Ibadah Kreatif)
   - `NNBT 12` (Nyanyian Baru Bagi Tuhan)
   *(Contoh: `Ku Berbahagia - KJ 392.txt`, `Ro Ma Ho Tu Jesus - BE 179.txt`)*
6. **Title Case**: Judul lagu wajib menggunakan Title Case (contoh: `Kumenang.txt` ✔ / `KUMENANG.txt` ✘).
   - Kata hubung dan preposisi kecil bahasa Indonesia (*dan, di, ke, dari, untuk, yang, pada, demi*) tetap huruf kecil kecuali berada di awal judul.
7. **Kesesuaian Baris Kedua**: Baris kedua dalam isi file **wajib identik persis** dengan nama file tanpa ekstensi `.txt`.
8. **Keunikan Global Datar**: Seluruh nama file dalam `database/` harus unik secara global karena disimpan dalam satu folder datar tanpa subfolder.

---

## 3. Struktur Isi File Lirik

Setiap file `.txt` wajib mengikuti susunan baku berikut:

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

1. **Slide Pembuka (BLANK)**:
   - Baris 1: `BLANK`
   - Baris 2: Judul lagu (persis sama dengan nama file)
   - Baris 3: Kosong (*empty line*)
2. **Maksimal 2 Baris per Slide**:
   - Untuk keterbacaan optimal jemaat di layar proyektor/LED, setiap slide dibatasi maksimal 2 baris teks.
   - Antar slide dipisahkan oleh satu baris kosong.
3. **Header Bagian (UPPERCASE)**:
   - Header bagian yang dikenali oleh engine: `BLANK`, `INTRO`, `VERSE` (atau `VERSE 1..n`), `PRE-CHORUS`, `CHORUS`, `BRIDGE`, `TAG`, `INTERLUDE`, `ENDING`, `OUTRO`.
   - Istilah bahasa Indonesia dinormalkan: `BAIT` → `VERSE`, `REFF` → `CHORUS`.
4. **Sentence Case pada Teks Lirik**:
   - Teks lirik **tidak boleh ditulis huruf kapital semua** (*ALL CAPS*).
   - Huruf kapital hanya digunakan pada awal baris, nama orang, dan kata ganti ilahi (`Mu`, `Nya`, `Ku`, `Kau`, `Tuhan`, `Allah`).
5. **Kebersihan Karakter**:
   - Disimpan dengan format UTF-8 murni (tanpa BOM).
   - Menggunakan tanda petik ASCII standar (`'` dan `"`), bukan petik miring mojibake.
   - Tidak boleh mengandung tautan web (URL), chord musik, atau placeholder generator (`LYRIC_LINE_1`).

---

## 4. Doktrin Nol-Halusinasi (Strict Zero-Hallucination)

- **DILARANG KERAS** menggunakan AI/LLM untuk mengarang atau melengkapi teks lirik lagu.
- Semua lirik wajib bersumber dari data autentik: hasil scraping situs lirik tepercaya, buku himne gereja berlisensi, atau rekaman audio resmi.
- Jika ada bait yang tidak lengkap dari sumber web, cari sumber pembanding resmi atau tinggalkan apa adanya sesuai dokumen aslinya.
