import os
import re
import sys
import json
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    small_words = {'do', 'di', 'tu', 'na', 'i', 'ni', 'asa', 'ai', 'au', 'ho', 'ro', 'pe', 'sai', 'lao', 'da', 'ma', 'sian'}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small_words:
            out.append(lw)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def format_lines_into_slides(lines):
    clean = []
    for l in lines:
        cl = clean_text_quotes(l).strip()
        if cl:
            clean.append(cl)
    slides = []
    for i in range(0, len(clean), 2):
        slides.append("\n".join(clean[i:i+2]))
    return slides

def process_single_song(item, existing_files):
    num = str(item.get('nomorLagu', '')).strip()
    raw_title = item.get('judul', '').strip()
    title = to_title_case(raw_title)
    artist = f"BE {num}"

    filename = sanitize_filename(f"{title} - {artist}") + ".txt"
    if filename.lower() in existing_files:
        return "skipped", filename, "Already exists"

    url = f"https://api.hkbp.or.id/api/v1/buku-ende/songs/{num}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=8).read().decode('utf-8'))
    except Exception as e:
        return "error", filename, f"Fetch error: {e}"

    lirik = data.get('lirik', [])
    if not lirik:
        return "error", filename, "No lyrics"

    sections = []
    v_idx = 0
    c_idx = 0

    for block in lirik:
        b_type = str(block.get('type', 'verse')).lower()
        lines = block.get('lines', [])
        if not lines:
            continue

        slides = format_lines_into_slides(lines)
        if not slides:
            continue

        if 'chorus' in b_type or 'refrain' in b_type:
            c_idx += 1
            s_name = "CHORUS" if c_idx == 1 else f"CHORUS {c_idx}"
        else:
            v_idx += 1
            s_name = f"VERSE {v_idx}"

        sections.append((s_name, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return "error", filename, "Too short"

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

    return "added", filename, "OK"

def main():
    print("==============================================================================")
    print("  OFFICIAL HKBP BUKU ENDE SCRAPER (BE 1 - 867)")
    print("==============================================================================")

    url = "https://api.hkbp.or.id/api/v1/buku-ende/songs"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        songs = json.loads(urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8'))
    except Exception as e:
        print(f"[ERROR] Gagal memuat indeks lagu: {e}")
        return

    print(f"Total lagu ditemukan di katalog resmi HKBP: {len(songs)} lagu.")
    existing_files = set(f.lower() for f in os.listdir(TXT_DIR))
    print(f"Database saat ini: {len(existing_files)} lagu.")

    added_count = 0
    skipped_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(process_single_song, it, existing_files): it for it in songs}
        for fut in as_completed(futures):
            try:
                status, fname, msg = fut.result()
                if status == "added":
                    added_count += 1
                    existing_files.add(fname.lower())
                    if added_count % 100 == 0 or added_count == len(songs):
                        total_now = len(existing_files)
                        print(f"  [Progress] +{added_count} lagu Buku Ende ditambahkan (Total Database: {total_now} lagu)...", flush=True)
                elif status == "skipped":
                    skipped_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

    final_count = len(os.listdir(TXT_DIR))
    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {added_count} lagu Buku Ende | Dilewati: {skipped_count} | Gagal: {error_count}")
    print(f"Total Database Saat Ini: {final_count} lagu")
    print("==============================================================================")

if __name__ == "__main__":
    main()
