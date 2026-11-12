# Banklycs v2.6

Aplikasi desktop native untuk ProPresenter 7: 54.204 lagu rohani siap tayang, satu klik inject. Window native, tray icon, installer sungguhan. Arsitekturnya setara ProPresenter 7: .NET 8 + WPF + WebView2 + SQLite + Protobuf.

> Satu repository sejak v2.2. Semua versi terarsip di [Releases](https://github.com/zzdevxx/banklycs/releases): v1.0 (legacy START.vbs + Edge), v2.0, v2.1, dst. Development berlanjut di sini.

## Arsitektur

```
Banklycs.App.exe  (satu proses, self-contained, zero-dependency)
├── WPF Window (title bar native, tray icon, close-to-tray, single-instance)
├── WebView2 → UI Studio Console (HTML/CSS/JS, identik dengan v1)
└── Engine C# in-process (StudioServer: HTTP localhost, kompilasi .pro protobuf)
```

- `desktop/`: shell WPF + WebView2 (`Banklycs.App`), ikon, script installer Inno Setup
- `engine/`: engine C# (.NET 8): HTTP server, katalog SQLite in-memory, kompilasi `.pro` on-demand, auto-inject tema ProPresenter
- `app/`: UI Studio Console (dark mode ProPresenter 7 style)
- `database/banklycs.db`: master SQLite 54.204 lagu (106 MB, single-file)
- `tools/fonts/`: font panggung CMG Sans

## Build dari Source

```powershell
# Prasyarat: .NET 8 SDK (Windows)
cd desktop
dotnet publish Banklycs.App.csproj -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
  -p:EnableCompressionInSingleFile=true -o dist/app
```

## Installer

```powershell
# Prasyarat: Inno Setup 6 (ISCC.exe)
# Payload distaging ke desktop/dist/staging/ (exe + database + app + engine/ThemeTemplate + tools/fonts)
cd desktop\installer
ISCC.exe banklycs.iss
# Hasil: desktop/dist/Banklycs-Setup-<versi>.exe
```

Installer per-user tanpa UAC (`%LOCALAPPDATA%\Programs\Banklycs`), shortcut Desktop + Start Menu, uninstaller resmi.

## Fitur Shell v2

- Window native (bukan browser) dengan ikon BL custom, DPI-aware
- Tray icon + close-to-tray (klik X = minim ke tray; keluar hanya via tray menu)
- Single-instance: klik exe lagi = buka window yang sudah jalan
- Auto-update check ke GitHub Releases (balon notifikasi → halaman unduhan)
- Context menu & DevTools dimatikan; link eksternal buka di browser sistem

## Sistem Pembaruan (v2.1+)

Dua jalur pembaruan terpisah, keduanya bisa dimatikan/dinyalakan di Settings:

| Jalur | Versi | Sumber | Mekanisme |
|---|---|---|---|
| Aplikasi | `v2.0`, `v2.1`, ... (+0.1) | GitHub Releases `banklycs` | Notifikasi tray + tombol *Periksa Sekarang* di Settings |
| Database | timestamp UTC (mis. `2026-11-12T14:55:47Z`) | `database/db_manifest.json` di repo master | Unduh + verifikasi SHA-256 + swap atomik + reload katalog, tanpa restart |

- Database murni dari maintainer: tidak dapat diedit dari aplikasi. Perbaikan/custom lagu dilakukan langsung di ProPresenter 7.
- Proteksi Editan ProPresenter (default ON): file `.pro` yang sudah disunting operator di ProPresenter tidak akan ditimpa saat inject ulang; lagu yang dilewati tetap masuk playlist dan dilaporkan di dialog inject.
- UUID dokumen bersifat permanen: re-inject memakai ulang UUID dari file lama, atau UUIDv5 deterministik dari nama lagu. Playlist ProPresenter tidak putus walau library dikompilasi ulang.
- Alur update database untuk maintainer: perbarui `banklycs.db` → perbarui `db_manifest.json` → commit + attach DB ke release dengan nama `database_<YYYY-MM-DD_HH-MM-SS>.db` (stamp UTC, identik dengan field `version`) → klien mendeteksi otomatis. Field `version` tetap ISO UTC agar kompatibel dengan parser engine.

## Lisensi

MIT © 2026 Andreas Restuawanta Christwara ([@zzdevxx](https://github.com/zzdevxx)).
