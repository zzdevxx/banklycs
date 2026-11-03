import os
import re
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

txt_dir = os.path.join(BASE_DIR, "TXT")
files = [f[:-4] for root, _, files in os.walk(txt_dir) for f in files if f.endswith(".txt")]

categories = {
    "Kidung Jemaat (KJ)": 0,
    "Nyanyikanlah Kidung Baru (NKB)": 0,
    "Pelengkap Kidung Jemaat (PKJ)": 0,
    "Kidung Keesaan (KK)": 0,
    "Kumpulan Lagu Ibadah Kreatif (KLIK)": 0,
    "Nyanyian Baru Bagi Tuhan (NNBT)": 0,
    "Buku Ende HKBP (BE)": 0,
    "Lagu Rohani Bahasa Jawa (Kidung Jawa)": 0,
    "English Christian Worship & Classic Hymns": 0,
    "Indonesian Contemporary Praise & Worship": 0
}

artists = []

english_keywords = ["hymn", "worship", "redman", "tomlin", "hillsong", "bethel", "planetshakers", "watts", "wesley", "crosby", "newton", "luther", "dykes", "choir"]

for name in files:
    if " - " in name:
        parts = name.split(" - ", 1)
        artist = parts[1].strip()
        artists.append(artist)
        low_name = name.lower()
        low_artist = artist.lower()

        if artist.startswith("KJ ") or " - kj " in low_name:
            categories["Kidung Jemaat (KJ)"] += 1
        elif artist.startswith("NKB ") or " - nkb " in low_name:
            categories["Nyanyikanlah Kidung Baru (NKB)"] += 1
        elif artist.startswith("PKJ ") or " - pkj " in low_name:
            categories["Pelengkap Kidung Jemaat (PKJ)"] += 1
        elif artist.startswith("KK ") or " - kk " in low_name:
            categories["Kidung Keesaan (KK)"] += 1
        elif artist.startswith("KLIK "):
            categories["Kumpulan Lagu Ibadah Kreatif (KLIK)"] += 1
        elif artist.startswith("NNBT "):
            categories["Nyanyian Baru Bagi Tuhan (NNBT)"] += 1
        elif artist.startswith("BE "):
            categories["Buku Ende HKBP (BE)"] += 1
        elif "jawa" in low_artist or "jawi" in low_artist or any(w in low_name for w in ["ndherek", "nderek", "gusti", "matur nuwun", "kula ndedonga", "kawula aturaken", "ingutusa kula"]):
            categories["Lagu Rohani Bahasa Jawa (Kidung Jawa)"] += 1
        elif any(k in low_artist for k in ["worship / hymn", "epic choir", "redman", "tomlin", "baloche", "groves", "camp", "schultz", "parris", "fellingham", "kenoly"]) or any(w in low_name for w in [" - john", " - charles", " - william", " - isaac", " - david", " - martin", " - paul", " - george"]):
            categories["English Christian Worship & Classic Hymns"] += 1
        else:
            # check if title is english words
            title = parts[0]
            words = set(re.findall(r'\b[a-z]+\b', title.lower()))
            eng_markers = {"the", "and", "you", "my", "lord", "god", "in", "is", "of", "to", "we", "for", "he", "our", "all", "your", "with", "me", "are", "be"}
            if len(words.intersection(eng_markers)) >= 2:
                categories["English Christian Worship & Classic Hymns"] += 1
            else:
                categories["Indonesian Contemporary Praise & Worship"] += 1
    else:
        categories["Indonesian Contemporary Praise & Worship"] += 1

print("==============================================================================")
print(f"DATABASE COMPOSITION BREAKDOWN (TOTAL: {len(files):,} SONGS)")
print("==============================================================================")
for k, v in categories.items():
    pct = (v / len(files)) * 100
    print(f"  * {k.ljust(45)}: {v:>6,} lagu ({pct:>5.1f}%)")

print("\nTOP 25 ARTISTS / COMPOSERS / WORSHIP TEAMS:")
for artist, count in Counter(artists).most_common(25):
    if not any(artist.startswith(b) for b in ["KJ ", "NKB ", "PKJ ", "KK ", "KLIK ", "NNBT ", "BE "]):
        print(f"  - {artist.ljust(40)}: {count} lagu")
