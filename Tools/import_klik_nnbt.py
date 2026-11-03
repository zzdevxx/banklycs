import os
import re
import sys
import json
import urllib.request
import ssl

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "TXT")

def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = cleaned.replace('’', "'").replace('‘', "'").replace('“', "'").replace('”', "'").replace('"', "'")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_text_quotes(text):
    return (text.replace('’', "'")
                .replace('‘', "'")
                .replace('“', '"')
                .replace('”', '"')
                .replace('â€™', "'")
                .replace('â€˜', "'")
                .replace('â€œ', '"')
                .replace('â€', '"'))

def to_title_case(s):
    words = s.split()
    small_words = {'dan', 'di', 'ke', 'dari', 'yang', 'pada', 'untuk', 'dgn', 'dg', 'si', 'sang', 'pun', 'ku', 'mu', 'nya'}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small_words:
            out.append(lw)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def format_lines_to_slides(lines):
    slides = []
    clean = []
    for l in lines:
        cl = re.sub(r'<[^>]+>', '', l).strip()
        cl = clean_text_quotes(cl)
        if cl:
            clean.append(cl)
    for i in range(0, len(clean), 2):
        slides.append("\n".join(clean[i:i+2]))
    return slides

def process_book(book_name, url):
    print(f"\n==================================================")
    print(f"IMPORT {book_name} FROM {url}")
    print(f"==================================================")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8'))
    
    existing = set(f.lower() for f in os.listdir(TXT_DIR))
    added = 0
    skipped = 0

    for item in data:
        code = str(item.get('code', '')).strip()
        raw_title = item.get('title', '').strip()
        title = to_title_case(raw_title)
        
        # Artist / Book tag
        artist = f"{book_name} {code}"
        filename = sanitize_filename(f"{title} - {artist}") + ".txt"

        if filename.lower() in existing:
            skipped += 1
            continue

        lyrics_blocks = item.get('lyrics', [])
        sections = []
        verse_idx = 0
        chorus_idx = 0

        for block in lyrics_blocks:
            verses = block.get('verses', [])
            for v in verses:
                kind = v.get('kind', 'NORMAL').upper()
                lines = v.get('lines', [])
                if not lines:
                    continue
                slides = format_lines_to_slides(lines)
                if not slides:
                    continue

                if 'REFRAIN' in kind or 'CHORUS' in kind:
                    chorus_idx += 1
                    s_name = "CHORUS" if chorus_idx == 1 else f"CHORUS {chorus_idx}"
                else:
                    verse_idx += 1
                    s_name = f"VERSE {verse_idx}"

                sections.append((s_name, slides))

        if not sections or sum(len(s[1]) for s in sections) < 2:
            skipped += 1
            continue

        out = ["BLANK", f"{title} - {artist}", ""]
        for s_hdr, slides in sections:
            out.append(s_hdr)
            for s in slides:
                out.append(s)
                out.append("")

        content = "\n".join(out).strip() + "\n"
        fpath = os.path.join(TXT_DIR, filename)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

        existing.add(filename.lower())
        added += 1

    print(f"-> {book_name} Selesai: +{added} lagu baru | Dilewati: {skipped}")
    return added

def main():
    add_klik = process_book("KLIK", "https://raw.githubusercontent.com/lalsproject/lalsproject.github.io/master/KLIK.json")
    add_nnbt = process_book("NNBT", "https://raw.githubusercontent.com/lalsproject/lalsproject.github.io/master/NNBT.json")
    print(f"\nTOTAL DITAMBAHKAN DARI BUKU GEREJA INDONESIA: +{add_klik + add_nnbt} lagu")

if __name__ == "__main__":
    main()
