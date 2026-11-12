# Banklycs Scraper

Tools pengayaan katalog lagu: discover → fetch → parse → dedupe.

## Subcommands

### `check-proxy`
Validasi daftar proxy terhadap domain target, tulis yang hidup saja.

```bash
python scraper.py check-proxy D:/ANDREAS/codebuddy-autoinject/data/np-https.txt \
    --out alive.txt --concurrency 60 --timeout 8
```

Catatan: proxy publik gratis tinggal hidupnya ~3–5%. Untuk 60 ribu proxy,
siapkan waktu ±30–60 menit dengan concurrency 300.

### `discover`
Kumpulkan URL halaman lagu dari sebuah sumber.

```bash
python scraper.py discover sifalyrics --out urls.txt
python scraper.py discover lirikrohani --out urls.txt
```

### `fetch`
Unduh halaman lagu. Resume otomatis (file yang sudah ada > --min-size dilewati).
Keep-alive session per worker. Proxy opsional dengan rotasi per worker.
Throttle global saat kena 429/503.

```bash
# tanpa proxy (untuk situs yang ramah)
python scraper.py fetch --urls urls.txt --out sifa_songs --workers 8

# dengan proxy (untuk situs yang throttle per-IP)
python scraper.py fetch --urls urls.txt --out sifa_songs \
    --proxy alive.txt --workers 200 --timeout 12
```

Tips throttle: kalau rate TURUN saat workers dinaikkan, situs sedang
throttle per-IP — turunkan workers, atau pakai proxy. Proxy publik lambat
(±5–18 dtk/request) tapi bisa diparalel ratusan worker.

### `parse`
Konversi HTML tersimpan → format BL → insert `database/banklycs.db`.
Deteksi bahasa otomatis (ID/EN), dedupe vs DB + dalam batch.

```bash
python scraper.py parse sifalyrics --dir sifa_songs --dry   # laporan saja
python scraper.py parse sifalyrics --dir sifa_songs          # insert
```

### `dedupe`
Hapus duplikat (judul sama + isi identik/≥90% mirip), simpan versi terlengkap.

```bash
python scraper.py dedupe --dry
python scraper.py dedupe
```

## Menambah sumber baru

Buat class di `adapters.py` dengan tiga method:

```python
class SumberBaru:
    @staticmethod
    def discover(out): ...          # tulis URL lagu ke file

    @staticmethod
    def parse_song(path): ...       # HTML -> (title, artist, category, bl) | None

    @staticmethod
    def run(html_dir, dry=False, source_name='...'): ...
```

Daftarkan di dict `ADAPTERS`. Format BL: header `VERSE n` / `CHORUS` /
`PRE-CHORUS` / `BRIDGE` dst, baris lirik, baris kosong sebagai pemisah slide.

## Pelajaran lapangan

- **Zombie process**: script Python yang di-abort/timeout di Windows bisa
  tetap hidup makan CPU — cek `tasklist | grep python` sebelum menyalahkan
  situs atau jaringan.
- **Throttle dinamis**: sifalyrics menahan IP agresif (~200 req/menit
  langsung hang). Proxy rotasi mengatasinya; ukuran pool > jumlah worker.
- **Ukuran file DB bisa tetap** walau isi bertambah (SQLite reuse free
  pages) — verifikasi pakai `COUNT(*)` + sha256, bukan ukuran file.
