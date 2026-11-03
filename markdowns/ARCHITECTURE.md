# BANKLYCS — ARSITEKTUR SISTEM & DIAGNOSIS PROPRESENTER

> **Tujuan Dokumen**: Penjelasan mendalam mengenai arsitektur teknis Banklycs, alasan di balik keputusan desain folder, diagnosis teknis kenapa ProPresenter 7 mengalami *crash* saat menampung 20.000 lagu, serta bagaimana mekanisme **On-Demand Realtime Injection** bekerja secara aman dan instan.

---

## 1. Diagram Arsitektur Tingkat Tinggi

```
                  ┌───────────────────────────────────────────────┐
                  │                 BANKLYCS                      │
                  │   (Lokal Workspace: D:\ANDREAS\banklycs)     │
                  └───────┬───────────────────────────────┬───────┘
                          │                               │
       ┌──────────────────▼──────────┐        ┌───────────▼──────────────────┐
       │     database/ (20.301 .txt) │        │  engine/PRO/ (20.301 .pro)   │
       │   Single Source of Truth    │        │  Offline Compiled Vault      │
       └──────────────────┬──────────┘        └───────────┬──────────────────┘
                          │                               │
                          ▼                               ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │                Aplikasi Studio Console (app/server.py)             │
       │   - In-Memory RAM Index (Pencarian <2 milidetik)                    │
       │   - Live Slide Inspector (Preview lirik 18px anti-slop)             │
       │   - Rundown Builder (Susun 5–10 lagu ibadah)                        │
       └──────────────────────────────────┬──────────────────────────────────┘
                                          │
                     [ Klik: "INJECT KE PROPRESENTER" ]
                                          │
                                          ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │              On-Demand Realtime Injector Pipeline                   │
       │  1. Salin HANYA 5-10 file .pro terpilih ke folder ProPresenter      │
       │  2. Jalankan engine: ProEngine.exe create-playlist temp.json        │
       │  3. Modifikasi Protobuf binary Playlists/Library ProPresenter 7     │
       └──────────────────────────────────┬──────────────────────────────────┘
                                          │
                                          ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │                   ProPresenter 7 (Instance Aktif)                   │
       │   - Membuka dalam < 1 detik (Tanpa Lag / Tanpa Crash)               │
       │   - Folder Libraries/Banks hanya berisi lagu aktif ibadah           │
       │   - Playlist langsung muncul di sidebar dan siap ditayangkan        │
       └─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Diagnosis Teknis: Mengapa ProPresenter 7 Crash dengan 20.000 Lagu?

Saat proyek ini pertama kali dieksplorasi, menaruh seluruh 20.301 file `.pro` secara langsung ke dalam folder library ProPresenter (`C:\Users\andre\OneDrive\Documents\ProPresenter\Libraries\Banks`) menyebabkan ProPresenter mengalami *freeze* total atau *crash* saat *startup*.

Investigasi pada berkas log ProPresenter (`C:\Users\andre\AppData\Local\RenewedVision\ProPresenter\Logs\Log.log`) mengungkap penyebab dasarnya:

### A. Tabrakan Indeks Lucene.Net (*Indexing Race Condition*)
```text
System.IO.FileNotFoundException: no segments* file found in Lucene.Net.Store.SimpleFSDirectory
```
- ProPresenter menggunakan pustaka mesin pencari berbasis .NET (**Lucene.Net**) untuk mengindeks seluruh file presentasi pada setiap *startup*.
- Mengindeks 20.000 file Protobuf binary secara serempak di direktori OneDrive memicu *file locking* antar-proses. File `write.lock` dan segmen Lucene gagal ditulis karena sinkronisasi OneDrive (*dehydrated file attributes*), sehingga mesin indeks gagal menginisialisasi katalog pencarian.

### B. Overflow Buffer FileSystemWatcher
- ProPresenter memasang pengawas direktori (`FileSystemWatcher`) pada setiap folder Library.
- Windows API membatasi ukuran buffer notifikasi *file system* default (biasanya 8 KB - 64 KB). Ketika 20.000 file dipindai secara massal, buffer mengalami *buffer overflow*, melewatkan sinyal penyegaran file, dan membuat UI menunggu status *file handle* yang terkunci tanpa batas (*infinite wait*).

### C. Deadlock Thread UI (WPF Thread Access Violation)
```text
System.InvalidOperationException: The calling thread cannot access this object because a different thread owns it.
   at System.Windows.Threading.Dispatcher.VerifyAccess()
```
- Selama pemindaian puluhan ribu lagu di *background thread*, ProPresenter mencoba memperbarui visual antarmuka (pohon pustaka / *library tree item*) secara paralel tanpa melewati `Dispatcher.Invoke()`. Hal ini memicu pengecualian *cross-thread access violation* fatal di lapisan Windows Presentation Foundation (WPF).

---

## 3. Solusi Banklycs: On-Demand Realtime Injection

Daripada memaksa ProPresenter menanggung beban 20.000 file sepanjang waktu, Banklycs memisahkan peran secara elegan:

1. **Vault Penyimpanan Terisolasi**:
   - Master teks 20.301 lagu disimpan di `database/`.
   - Seluruh cache binary `.pro` disimpan di `engine/PRO/` di luar jangkauan pengawas ProPresenter.
2. **Pencarian Kilat di RAM (<2 ms)**:
   - Aplikasi ringan berbasis Python (`app/server.py`) membaca seluruh katalog ke memori RAM saat aplikasi dibuka.
   - Menggunakan algoritma *multi-token filtering*, pencarian 20.000 lagu selesai dalam rentang waktu <2 milidetik tanpa membebani sistem operasi.
3. **Penyuntikan On-Demand (Hanya Lagu Terpilih)**:
   - Operator menyusun daftar lagu ibadah (biasanya 5 hingga 10 lagu) di antarmuka web.
   - Saat tombol **`INJECT KE PROPRESENTER`** diklik:
     - Server menyalin hanya 5–10 file `.pro` yang dipilih ke folder `Libraries/Banks/`.
     - `ProEngine.exe create-playlist` membaca struktur file Protobuf ProPresenter (`Playlists/Library`), menyisipkan entri playlist baru beserta UUID-nya, dan menyimpan kembali file binary tersebut.
   - Hasilnya: ProPresenter tetap membuka dalam waktu **1 detik**, menggunakan memori RAM yang minimal, dan tidak pernah mengalami crash.

---

## 4. Format Binary Protobuf ProPresenter 7

File `.pro` di ProPresenter 7 adalah file serialisasi **Google Protocol Buffers** (Protobuf), bukan format teks XML atau JSON. 

Kompiler `engine/ProEngine.exe` dibangun di atas .NET 8 menggunakan *assembly interop* resmi ProPresenter (`Pro.SerializationInterop.dll` dan `Google.Protobuf.dll`):
- **Struktur Slide**: Setiap bait/reff dibungkus dalam `Presentation.Types.Cue` dan `Slide.Types.Element`.
- **Styling Master**: Slide menggunakan templat `CMGSans-Bold`, ukuran font proporsional panggung (fs134), perataan tengah (*center*), dan kanvas 1920x1080.
- **Pewarnaan Grup Otomatis**:
  - `VERSE`: Biru
  - `CHORUS`: Merah
  - `PRE-CHORUS`: Oranye
  - `BRIDGE`: Ungu
  - `INTRO / INTERLUDE`: Hijau
  - `TAG`: Cyan
  - `ENDING / OUTRO`: Kuning kecokelatan
  - `BLANK`: Hitam pekat
