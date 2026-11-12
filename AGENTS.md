# Banklycs, panduan agen

## Konteks proyek

- Banklycs: engine lirik worship + database untuk ProPresenter 7. Windows-native, zero dependency, offline.
- Satu repository sejak v2.2; rilis lama terarsip di GitHub Releases.
- Database `database/banklycs.db` TIDAK masuk Git (>100 MB). Distribusi lewat release asset + `db_manifest.json`.

## Aturan teks publishing (wajib)

Semua teks publik di repo ini (README, release notes, teks installer `desktop/installer/banklycs.iss`, pesan commit) mengikuti skill `antislop` + `antislop-copywriting`:

1. Zero em dash (`—`). Pakai koma, titik dua, atau kurung.
2. Tanpa emoji di heading.
3. Tanpa superlatif dan klaim yang tidak bisa diverifikasi ("terlengkap", "100% zero-duplicate", "seamless").
4. Setiap angka (jumlah lagu, ukuran file, SHA-256) diambil ulang dari sumber aslinya sebelum dipublikasikan. Sumber kebenaran:
   - Jumlah lagu & kategori: `SELECT category, COUNT(*) FROM songs GROUP BY category` di `database/banklycs.db`
   - Ukuran DB: ukuran file `database/banklycs.db` aktual
   - Ukuran installer: file `desktop/dist/Banklycs-Setup-*.exe`
   - SHA-256 DB: `database/db_manifest.json`
5. Angka performa hanya boleh ditulis setelah diukur lewat command nyata di sesi yang sama.
6. Bahasa Indonesia lugas dan teknis, kalimat aktif, subjek jelas.
7. Sebelum rilis baru: cek ulang angka di `banklycs-download/index.html` (repo terpisah) terhadap sumber di atas, karena angka di sana cepat basi.

## Hal teknis yang sering salah

- Desktop app meng-embed engine via `ProjectReference` ke `engine/ProEngine.csproj`; tidak ada `banklycs.exe` terpisah di installer.
- UUID dokumen `.pro` bersifat permanen: reuse dari file lama, fallback UUIDv5 dari nama file. Jangan kembalikan ke `Guid.NewGuid()`.
- RTF template harus identik dengan output ProPresenter; jangan menulis RTF manual.
- Setelah inject, cek log ProPresenter (`%LOCALAPPDATA%\RenewedVision\ProPresenter\Logs`), bukan cuma byte file.
- Sinkronisasi cloud: `python D:/ANDREAS/agent-memory/tools/sync_cloud.py banklycs` (3 remote sekaligus).
