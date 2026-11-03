# GENERATE — KOMPILER ENGINE & INJEKTOR PROPRESENTER

> **Proyek**: `banklycs` — Arsitektur Kompilasi & Injeksi Cepat ProPresenter 7  
> **Lokasi Engine**: `engine/ProEngine.exe` (C# .NET 8, Google Protobuf)  
> **Script Batch**: `engine/Generate.ps1`  
> **Cache Binary**: `engine/PRO/`  
> **Terakhir diperbarui**: 2026-11-03

---

## 1. Diagram Alur Data & Injeksi

```
┌─────────────────────────┐          ┌─────────────────────────┐
│ database/ (20.301 .txt) │          │ engine/PRO/ (20.301.pro)│
│ Single Source of Truth  │          │ Vault Binary Protobuf   │
└────────────┬────────────┘          └────────────┬────────────┘
             │                                    │
             ▼                                    ▼
┌──────────────────────────────────────────────────────────────┐
│            Studio Console GUI (app/server.py)                │
│ - RAM Search Catalog (<2 milidetik)                          │
│ - Rundown Builder (Pilih 5–10 lagu ibadah)                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
            [ Klik: "INJECT KE PROPRESENTER" ]
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│            Pipeline On-Demand Realtime Injection             │
│ 1. Salin HANYA 5-10 file .pro terpilih ke Libraries/Banks/   │
│ 2. Panggil: ProEngine.exe create-playlist temp.json          │
│ 3. Update binary Playlists/Library ProPresenter              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                ProPresenter 7 (Instance Aktif)               │
│ - Startup Instan (<1 detik, Tanpa Crash)                     │
│ - Playlist Ibadah langsung muncul & siap tayang              │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Diagnosis Teknis: Kenapa ProPresenter Crash dengan 20.000 Lagu?

Ketika 20.301 file `.pro` diletakkan sekaligus di dalam folder library ProPresenter (`OneDrive\Documents\ProPresenter\Libraries\Banks`), ProPresenter mengalami *freeze* total atau *crash* saat *startup*. Berdasarkan audit log resmi ProPresenter (`AppData\Local\RenewedVision\ProPresenter\Logs\Log.log`), ditemukan 3 penyebab utama:

### A. Tabrakan Mesin Indeks Lucene.Net (*Indexing Race Condition*)
```text
System.IO.FileNotFoundException: no segments* file found in Lucene.Net.Store.SimpleFSDirectory
```
ProPresenter menggunakan **Lucene.Net** untuk mengindeks seluruh file perpustakaan saat *startup*. Mengindeks 20.000 file Protobuf binary secara bersamaan di folder sinkronisasi OneDrive memicu tabrakan *file locking*. File `write.lock` gagal ditulis, menyebabkan seluruh subsistem pencarian ProPresenter macet total.

### B. Overflow Buffer FileSystemWatcher
Windows API membatasi buffer notifikasi pengawas berkas default (8 KB – 64 KB). Saat 20.000 file dipantau sekaligus, sistem mengalami *buffer overflow*, melewatkan sinyal penyegaran file, dan membuat UI menunggu status *file handle* yang terkunci tanpa batas (*infinite wait*).

### C. Deadlock Thread Visual UI (WPF Cross-Thread Violation)
```text
System.InvalidOperationException: The calling thread cannot access this object because a different thread owns it.
   at System.Windows.Threading.Dispatcher.VerifyAccess()
```
Pemindaian puluhan ribu lagu di latar belakang memicu thread pekerja memperbarui hierarki visual WPF (*tree view*) tanpa sinkronisasi `Dispatcher.Invoke()`, menyebabkan *crash* fatal seketika.

---

## 3. Solusi Banklycs: On-Demand Realtime Injection

Banklycs memecahkan masalah ini dengan memisahkan penyimpanan masif dari eksekusi:
1. **20.000 Lagu Tersimpan di Vault Lokal**: Seluruh database teks tersimpan di `database/` dan seluruh cache binary di `engine/PRO/`. ProPresenter sama sekali tidak dibebani oleh berkas-berkas ini.
2. **Pencarian Kilat di RAM (<2 ms)**: Server Python membaca seluruh katalog ke memori saat aplikasi dijalankan, memungkinkan pencarian seketika tanpa I/O disk berat.
3. **Penyuntikan Terarah (Hanya Lagu Aktif)**:
   - Saat operator menyusun rundown (5–10 lagu) dan menekan tombol injeksi, hanya file `.pro` lagu tersebut yang disalin ke `Libraries/Banks/`.
   - Engine mendaftarkan daftar lagu tersebut ke dalam file Protobuf `Playlists/Library`.
   - ProPresenter membuka playlist dalam **1 detik** dengan konsumsi memori sangat hemat.

---

## 4. Format Binary Protobuf ProPresenter 7

File `.pro` di ProPresenter 7 adalah file serialisasi **Google Protocol Buffers** (Protobuf).  
Engine dikompilasi menggunakan C# .NET 8 dan *assembly interop* resmi ProPresenter (`Pro.SerializationInterop.dll` & `Google.Protobuf.dll`):

- **Master Theme**: Font `CMGSans-Bold`, ukuran font proporsional panggung (fs134), perataan tengah (*center*), kanvas 1920x1080.
- **Pewarnaan Grup Otomatis**:
  - `VERSE`: Biru
  - `CHORUS`: Merah
  - `PRE-CHORUS`: Oranye
  - `BRIDGE`: Ungu
  - `INTRO / INTERLUDE`: Hijau
  - `TAG`: Cyan
  - `ENDING / OUTRO`: Kuning kecokelatan
  - `BLANK`: Hitam pekat

---

## 5. Menjalankan Batch Compiler (`Generate.ps1`)

Jika Anda menambahkan ratusan lagu baru ke `database/` dan ingin mengompilasi ulang seluruh cache `.pro`:

```powershell
# Mode Incremental (Default — hanya mengompilasi file baru/berubah, ~1-3 detik)
powershell -ExecutionPolicy Bypass -File .\engine\Generate.ps1

# Mode Rebuild Penuh (Menghapus dan mengompilasi ulang seluruh 20.000 lagu, ~30 detik)
powershell -ExecutionPolicy Bypass -File .\engine\Generate.ps1 -Full
```
