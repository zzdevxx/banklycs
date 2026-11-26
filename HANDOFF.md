# Banklycs: penutupan audit 26 November 2026

Perbaikan isolasi konfigurasi dan audit software selesai pada cakupan di bawah. Installer GitHub Release `v2.7` tetap sama; perubahan source ini tidak mengganti aset rilis yang sudah terbit.

## Perbaikan yang diuji

Pada Windows, penggantian environment `LOCALAPPDATA` tidak mengalihkan hasil `.NET Environment.GetFolderPath(LocalApplicationData)`. Helper lama belum menjamin pemisahan konfigurasi operator.

Engine dan desktop sekarang memakai resolver bersama `BANKLYCS_APPDATA_DIR`, yang menerima path absolut. Resolver mencakup `config.json`, `inject_state.json`, pembacaan flag desktop, dan profil WebView2. Tanpa override, direktori data pengguna tetap menjadi default.

`/api/status` melaporkan `config_dir`. Ketiga helper di `tools/test_inject_contract.py`, `tools/verify_app_e2e.py`, dan `tools/serve_isolated_ui.py` memeriksa kecocokan direktori konfigurasi dan ProPresenter sementara sebelum melanjutkan. Binary lama ditolak sebelum helper memberikan kendali ke tes mutasi. Helper memulihkan byte `engine/last_port.txt` pada cleanup.

## Bukti verifikasi

- Build engine dan desktop Release lulus dengan 0 warning dan 0 error.
- `python -m unittest tools.test_inject_contract -v`: 6/6 lulus, termasuk regresi konfigurasi dan inject-state terisolasi.
- `python tools/verify_app_e2e.py`: lulus. Chromium memeriksa 11 tab pada lebar 1000, 1280, 1366, dan 1440 px; search, preview, About, Settings, dan alur inject lulus tanpa error console.
- `python -m unittest tools.test_verify_release_sync -v`: 1/1 lulus. Pemeriksaan `tools/verify_release_sync.py` sebelumnya lulus untuk metadata, integritas SQLite, dan kesesuaian portal lokal.
- Native WPF/WebView2 lulus pada development binary hasil build. Harness menjalankan salinan `Banklycs.App.exe` di payload sementara dan terhubung ke WebView2 milik proses itu melalui CDP. Sebelas tab, search, preview, rundown, About, Settings, serta inject satu lagu ke ProPresenter sementara lulus tanpa page error, console error, HTTP error, atau panggilan endpoint terlarang.
- Hash konfigurasi operator dan byte `engine/last_port.txt` tetap sama. Proses native milik harness sudah berhenti, mutex dilepas, dan port 5050 sampai 5055 bebas. Artefak sandbox native dipertahankan sebagai bukti.
- Audit teks README dan tiga helper Python lulus dengan 0 error/0 warning. Scanner tidak mendukung C#; perubahan C# ditinjau dan dikompilasi terpisah.

Bukti lokal berada di `C:\Users\andre\AppData\Local\Temp\opencode`:

- `banklycs-final-audit-20261126/post-fix/`: log suite dan `verified-summary.json`.
- `banklycs-native-final-audit-20261126/RUN_RESULT.md`: hasil native, batas uji, dan lokasi screenshot WebView2.
- `banklycs-config-isolation-final-20261126/parent-final-crosscheck.json`: pencocokan hash source dengan build/tes, konfigurasi operator, screenshot, output sandbox, dan cleanup native.

## Batas hasil dan resume

Native smoke memakai development binary, bukan installer publik. Aktivasi single-instance, pemulihan dari tray, impor oleh aplikasi ProPresenter nyata, instalasi font, dan penerapan update database belum diuji pada audit ini. Warning detach CDP terjadi saat cleanup; proses native dan port sudah diperiksa terpisah setelahnya.

Jangan menyentuh `D:\ANDREAS\LOCAL` atau data ProPresenter pengguna di `C:\Users\andre\OneDrive\Documents\ProPresenter`. Semua pengujian mutasi berikutnya harus tetap memakai sandbox dan handshake kedua direktori. Jangan mengulang pekerjaan audit yang sudah selesai atau mengganti aset `v2.7` tanpa pekerjaan rilis baru yang diminta pemilik.
