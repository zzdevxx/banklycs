# 🎶 Banklycs v2 — Native Studio Console (WPF + WebView2)

**Standalone desktop app** untuk ProPresenter 7: 24.520 lagu rohani siap tayang, satu klik inject. Ini generasi kedua Banklycs — window native, tray icon, installer sungguhan (arsitektur setara ProPresenter 7: .NET + WPF + WebView2 + SQLite + Protobuf).

> 📍 **Banklycs v1** (START.vbs + Edge app-mode) tetap tersedia di repo [banklycs-v1](https://github.com/zzdevxx/banklycs-v1).

---

## 🏗️ Arsitektur

```
Banklycs.App.exe  (satu proses, self-contained, zero-dependency)
├── WPF Window (title bar native, tray icon, close-to-tray, single-instance)
├── WebView2 → UI Studio Console (HTML/CSS/JS — identik dengan v1, 100% reuse)
└── Engine C# in-process (StudioServer: HTTP localhost, kompilasi .pro protobuf)
```

- **`desktop/`** — shell WPF + WebView2 (`Banklycs.App`), ikon, script installer Inno Setup
- **`engine/`** — engine C# (.NET 8): HTTP server, katalog SQLite in-memory, kompilasi `.pro` on-demand, auto-inject tema ProPresenter
- **`app/`** — UI Studio Console (dark mode ProPresenter 7 style)
- **`database/banklycs.db`** — master SQLite 24.520 lagu (61 MB, single-file)
- **`tools/fonts/`** — font panggung CMG Sans

## 🚀 Build dari Source

```powershell
# Prasyarat: .NET 8 SDK (Windows)
cd desktop
dotnet publish Banklycs.App.csproj -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
  -p:EnableCompressionInSingleFile=true -o dist/app
```

## 📦 Installer

```powershell
# Prasyarat: Inno Setup 6 (ISCC.exe)
# Payload distaging ke desktop/dist/staging/ (exe + database + app + engine/ThemeTemplate + tools/fonts)
cd desktop\installer
ISCC.exe banklycs.iss
# Hasil: desktop/dist/Banklycs-Setup-<versi>.exe
```

Installer **per-user tanpa UAC** (`%LOCALAPPDATA%\Programs\Banklycs`), shortcut Desktop + Start Menu, uninstaller resmi.

## ✨ Fitur Shell v2

- Window native (bukan browser) dengan ikon BL custom, DPI-aware
- Tray icon + close-to-tray (klik X = minim ke tray; keluar hanya via tray menu)
- Single-instance: klik exe lagi = buka window yang sudah jalan
- Auto-update check ke GitHub Releases (balon notifikasi → halaman unduhan)
- Context menu & DevTools dimatikan; link eksternal buka di browser sistem

## 📜 Lisensi

MIT © 2026 Andreas Restuawanta Christwara ([@zzdevxx](https://github.com/zzdevxx)).
