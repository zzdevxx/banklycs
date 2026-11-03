# PANDUAN KONTRIBUSI (CONTRIBUTING GUIDE)

Terima kasih telah berminat untuk berkontribusi pada **Banklycs**!  
Proyek ini dibangun secara nirlaba untuk membantu pelayanan multimedia gereja dan persekutuan agar memiliki akses lirik lagu yang bersih, akurat, dan siap tayang di panggung ibadah.

---

## 1. Prinsip Utama Kontribusi

### A. Nol Halusinasi AI (Strict Zero-Hallucination)
- **DILARANG MENGGUNAKAN AI/LLM** untuk mengarang atau melengkapi teks lirik lagu.
- Semua lirik lagu yang ditambahkan wajib berasal dari sumber autentik: buku nyanyian resmi gereja, transkripsi rekaman ibadah resmi, atau situs lirik tepercaya.

### B. Single Source of Truth (`database/`)
- Seluruh kontribusi lagu hanya ditambahkan ke folder [`database/`](../database/) dalam bentuk file `.txt` murni.
- Jangan menyunting atau mengirimkan file `.pro` secara manual melalui Pull Request. Cache `.pro` akan dikompilasi secara otomatis oleh engine.

---

## 2. Cara Menambahkan Lagu Baru

1. **Buat File Baru di `database/`**:
   - Penamaan file: `Judul Lagu - Nama Artis.txt`
   - Jika artis tidak diketahui: `Judul Lagu.txt` (JANGAN gunakan nama `- No Name` atau `- Unknown`).
   - Gunakan format **Title Case** pada nama file (contoh: `Darah-Mu Yesus - JPCC Worship.txt`).

2. **Format Isi File**:
   Pastikan file mengikuti susunan baku berikut:
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

   **Ketentuan Wajib**:
   - Baris 1: `BLANK`
   - Baris 2: Judul lagu (harus sama persis dengan nama file).
   - Maksimal **2 baris teks per slide** (dipisah satu baris kosong).
   - Huruf kapital hanya pada awal kalimat, nama orang, dan kata ganti ilahi (`Mu`, `Nya`, `Ku`, `Kau`, `Tuhan`, `Allah`). Jangan menulis lirik dalam huruf kapital semua (*ALL CAPS*).
   - Simpan dengan encoding **UTF-8** (tanpa BOM).

---

## 3. Menjalankan Verifikasi Sebelum Mengirimkan PR

Sebelum mengajukan *Merge Request* atau *Pull Request*, jalankan skrip audit lokal untuk memastikan tidak ada kesalahan format:

```powershell
# 1. Audit kebersihan database
python tools/audit_cleanliness.py

# 2. Verifikasi aturan format lirik
python tools/verify_songs.py
```

Jika hasil audit menunjukkan `0 file bermasalah`, kontribusi Anda siap untuk di-*commit* dan diajukan.

---

## 4. Standar Pesan Commit (Git Conventions)

Gunakan format [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(db): add 10 songs from Symphony Worship Album 2026`
- `fix(lyrics): correct typo on chorus in Darah-Mu Yesus`
- `docs: update contributing instructions in markdowns`
- `refactor(app): optimize memory search filtering`
