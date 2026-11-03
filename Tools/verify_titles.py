import os
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

txt_dir = os.path.join(BASE_DIR, "TXT")
files = [f[:-4] for root, _, files in os.walk(txt_dir) for f in files if f.endswith(".txt")]

titles = defaultdict(list)
artists = defaultdict(list)
no_artist_count = 0

for f in files:
    if " - " in f:
        title, artist = f.split(" - ", 1)
        titles[title.strip().lower()].append((title.strip(), artist.strip()))
        artists[artist.strip()].append(title.strip())
    else:
        no_artist_count += 1
        titles[f.strip().lower()].append((f.strip(), "NO_ARTIST"))

same_title_diff_artist = {k: v for k, v in titles.items() if len(v) > 1}
print(f"Total Unique Titles                     : {len(titles)}")
print(f"File tanpa pemisah artist (' - ')       : {no_artist_count}")
print(f"Judul sama dengan musisi/versi berbeda : {len(same_title_diff_artist)}")
print(f"Total Artis/Buku Terdaftar              : {len(artists)}")

print("\nContoh 12 Judul dengan Versi Terbanyak:")
for t, versions in sorted(same_title_diff_artist.items(), key=lambda x: len(x[1]), reverse=True)[:12]:
    print(f"\n  Judul: '{versions[0][0]}' ({len(versions)} versi):")
    for _, art in versions:
        print(f"    - {art}")

print("\nTop 15 Kategori/Penyanyi dengan Lagu Terbanyak:")
for art, songlist in sorted(artists.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
    print(f"  - {art}: {len(songlist)} lagu")
