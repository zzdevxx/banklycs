# HANDOFF — ESTAFET STATUS PROYEK BANKLYCS

> **Tanggal Status**: 2026-11-03  
> **Workspace**: `D:\ANDREAS\banklycs`  
> **Git Branch**: `master`  
> **Remotes**: `origin` (GitLab: `zzdree/banklycs`), `codeberg` (Codeberg: `zzdree/banklycs`)  
> *(Catatan: Belum di-push ke GitHub sesuai arahan user).*

---

## 1. Kondisi Terverifikasi Terakhir

| Komponen | Status | Keterangan |
|---|---|---|
| **Master Database** | `database/` | **20.301** file `.txt`, flat murni (0 subfolder) |
| **Engine Cache** | `engine/PRO/` | **20.301** file `.pro`, 100% sinkron 1-ke-1 dengan database |
| **Aplikasi GUI** | `app/` | Python HTTPServer + Vanilla HTML/CSS/JS (WCAG AAA dark grey studio theme) |
| **Injeksi Real-Time** | Teruji & Berhasil | Injeksi on-demand berhasil tanpa membebani ProPresenter |
| **ProPresenter 7** | Berjalan Stabil | Startup instan (<1 detik), folder `Libraries/Banks` hanya berisi file aktif |
| **Dokumentasi** | `markdowns/` | Lengkap: `RULES`, `ARCHITECTURE`, `CONTRIBUTING`, `SCRAPING_GUIDE`, `AGENT_CONTEXT`, `HANDOFF` |
| **Tooling Scripts** | `tools/` | Seluruh 17 script Python telah dimutakhirkan ke path `database/` & `engine/PRO/` |

---

## 2. Struktur Repositori Terkini

```text
banklycs/
├── database/        ← Master lirik teks murni (.txt, 20.301 lagu flat, Single Source of Truth)
├── app/             ← Aplikasi Studio Console GUI (server.py, index.html, style.css, app.js)
├── engine/          ← Compiler C# .NET 8 (ProEngine.exe) & isolasi cache .pro (engine/PRO/)
├── tools/           ← Skrip scraper web & data pipeline (Python)
├── markdowns/       ← Dokumentasi, doktrin sistem, arsitektur, & panduan kontribusi
├── Start.bat        ← Launcher satu klik untuk operator gereja
├── README.md        ← Panduan umum pengguna
└── .gitignore       ← Mengabaikan cache PRO/*.pro dan artefak build
```

---

## 3. Tugas Prioritas Berikutnya (Backlog)

1. **Push ke GitLab & Codeberg**:
   - Pastikan repositori kosong `banklycs` sudah dibuat di web UI Codeberg (`https://codeberg.org/zzdree/banklycs`).
   - Eksekusi `git push -u origin master` dan `git push -u codeberg master`.
2. **Melanjutkan Scraper yang Terputus**:
   - `tools/scrape_liriklagukristen.py`: Lanjutkan scraping sisa link yang belum ada di database.
   - `tools/scrape_buku_ende.py`: Ambil sisa lagu Buku Ende HKBP (nomor 845 s/d 867) dari API resmi HKBP.
3. **Perapihan Slide Overflow**:
   - Berdasarkan hasil audit `verify_songs.py`, ada 369 file yang memiliki slide dengan >2 baris teks. Dapat diproses dengan pemisah slide cerdas pada baris kosong.
4. **Elevation Worship Reattribution**:
   - Terdapat ±37 lagu berbahasa Indonesia yang sebelumnya terlacak dengan nama artis `Elevation Worship` (warisan scraper lama). Lacak komposer aslinya di Psalmnote atau jadikan judul saja.
