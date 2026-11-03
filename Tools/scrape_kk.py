import os
import re
import sys
import ssl
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from scrape_hymnals import scrape_song, sanitize_filename

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "TXT")

def to_title_case_clean(title):
    # If all uppercase, convert to Title Case
    if title.isupper():
        words = title.split()
        lowers = {'dan', 'yang', 'di', 'ke', 'dari', 'pada', 'untuk', 'dengan', 'atas', 'si', 'sang'}
        new_words = []
        for i, w in enumerate(words):
            if i > 0 and w.lower() in lowers:
                new_words.append(w.lower())
            else:
                new_words.append(w.capitalize())
        return " ".join(new_words)
    return title

def process_kk_song(num, existing_lower_files):
    res, err = scrape_song("kk", num)
    if err or not res:
        return "error", num, err

    filename_raw, content = res
    # e.g. "MARI, PUJI DIA - KK 1.txt"
    if " - KK " in filename_raw:
        title_part, book_part = filename_raw.rsplit(" - KK ", 1)
        clean_title = to_title_case_clean(title_part)
        filename = f"{clean_title} - KK {book_part}"
    else:
        filename = filename_raw

    filename = filename.replace('’', "'").replace('‘', "'")
    filename = sanitize_filename(filename[:-4]) + ".txt"

    if filename.lower() in existing_lower_files:
        return "skipped", num, "Already exists"

    # Also clean content title line
    lines = content.splitlines()
    if len(lines) >= 2:
        title_line = lines[1]
        if " - KK " in title_line:
            t_part, b_part = title_line.rsplit(" - KK ", 1)
            lines[1] = f"{to_title_case_clean(t_part)} - KK {b_part}"
    
    clean_content = "\n".join(lines).replace('’', "'").replace('‘', "'") + "\n"

    fpath = os.path.join(TXT_DIR, filename)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(clean_content)

    return "added", num, filename

def main():
    existing_lower_files = set(f.lower() for f in os.listdir(TXT_DIR))
    print("==============================================================================")
    print("  SCRAPING KIDUNG KEESAAN (KK 1 s/d 774)")
    print("==============================================================================")
    
    added = 0
    skipped = 0
    error = 0

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(process_kk_song, num, existing_lower_files): num for num in range(1, 775)}
        for fut in as_completed(futures):
            num = futures[fut]
            try:
                status, num, info = fut.result()
                if status == "added":
                    added += 1
                    existing_lower_files.add(info.lower())
                    if added % 50 == 0 or added == 774:
                        print(f"  Progress: +{added} lagu KK baru berhasil ditambahkan...", flush=True)
                elif status == "skipped":
                    skipped += 1
                else:
                    error += 1
            except Exception as e:
                error += 1

    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {added} lagu KK baru | Dilewati: {skipped} | Gagal/Kosong: {error}")
    print("==============================================================================")

if __name__ == "__main__":
    main()
