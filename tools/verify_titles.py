import os
import sqlite3
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(BASE_DIR, "database", "banklycs.db")

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
cur = conn.cursor()

cur.execute("SELECT id, filename, title, artist, category FROM songs;")
rows = cur.fetchall()

titles = defaultdict(list)
artists = defaultdict(list)
no_artist_count = 0

for sid, fname, title, artist, cat in rows:
    clean_title = (title or "").strip()
    clean_artist = (artist or "").strip()
    titles[clean_title.lower()].append((clean_title, clean_artist or "NO_ARTIST"))
    if clean_artist:
        artists[clean_artist].append(clean_title)
    else:
        no_artist_count += 1

same_title_diff_artist = {k: v for k, v in titles.items() if len(v) > 1}
print("==============================================================================")
print(f"VERIFY TITLES & ARTISTS AUDIT (TOTAL: {len(rows):,} SONGS)")
print("==============================================================================")
print(f"Total Unique Titles                     : {len(titles):,}")
print(f"Lagu tanpa artis terdaftar (Title Only) : {no_artist_count:,}")
print(f"Judul sama dengan musisi/versi berbeda : {len(same_title_diff_artist):,}")
print(f"Total Artis/Buku Terdaftar              : {len(artists):,}")

print("\nContoh 8 Judul dengan Versi Terbanyak:")
for t, versions in sorted(same_title_diff_artist.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
    print(f"\n  Judul: '{versions[0][0]}' ({len(versions)} versi):")
    for _, art in versions[:6]:
        print(f"    - {art}")

conn.close()
