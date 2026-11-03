import os
import re
import sys
import ssl
import time
import urllib.request
import urllib.parse
from html import unescape

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "TXT")

def sanitize_filename(name):
    # Windows forbidden characters: < > : " / \ | ? *
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def format_verse_lines(raw_lines):
    """Formats raw lines of a verse into slides of at most 2 lines each."""
    lines = []
    for l in raw_lines:
        l = l.strip()
        if not l:
            continue
        # If line is extremely long, try to split at comma or semicolon
        if len(l) > 65 and ',' in l:
            parts = [p.strip() for p in l.split(',') if p.strip()]
            if len(parts) == 2 and len(parts[0]) > 15 and len(parts[1]) > 15:
                lines.append(parts[0] + ',')
                lines.append(parts[1])
                continue
        lines.append(l)

    # Chunk into slides of max 2 lines
    slides = []
    for i in range(0, len(lines), 2):
        chunk = lines[i:i+2]
        slides.append("\n".join(chunk))
    return slides

def scrape_song(book, number):
    url = f"https://alkitab.mobi/kidung/{book.lower()}/{number}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None, f"HTTP Error: {e}"

    # Extract Title: <p class="paragraphtitle"><strong>KJ 1 - Haleluya, Pujilah</strong></p>
    title_m = re.search(r'<p class="paragraphtitle">\s*<strong>([^<]+)</strong>', html)
    if not title_m:
        title_m = re.search(r'<strong>\s*([A-Z]{2,4}\s+\d+\s*-[^<]+)</strong>', html)
    if not title_m:
        return None, "Title not found"

    full_title_raw = unescape(title_m.group(1)).strip()
    # e.g. "KJ 2 - Suci, Suci, Suci" or "PKJ 1 - Abadi Kasih..."
    # We want format: "Suci, Suci, Suci - KJ 2"
    m_split = re.match(r'^([A-Z]{2,4}\s+\d+[a-z]?)\s*-\s*(.+)$', full_title_raw)
    if m_split:
        book_id = m_split.group(1).strip()
        song_title = m_split.group(2).strip().strip('.')
    else:
        book_id = f"{book.upper()} {number}"
        song_title = full_title_raw

    # Extract Verses
    # Format:
    # <p><i><strong>1</strong>.</i>&nbsp; Line 1<br>Line 2...</p>
    p_matches = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)
    sections = []
    
    verse_idx = 1
    for p in p_matches:
        # Check if this paragraph contains a verse number: <i><strong>(\d+)</strong>.</i>
        v_num_m = re.search(r'<i><strong>(\d+)</strong>\.?</i>', p)
        # Check if refrein
        is_refrein = 'refrein' in p.lower() or 'ref.' in p.lower()
        
        # Clean tags
        clean_p = re.sub(r'<i><strong>.*?</strong>\.?</i>', '', p)
        clean_p = re.sub(r'<small>.*?</small>', '', clean_p)
        clean_p = unescape(clean_p)
        
        # Split by <br> or newline
        raw_lines = [re.sub(r'<[^>]+>', '', l).strip() for l in re.split(r'<br\s*/?>|\n', clean_p)]
        raw_lines = [l for l in raw_lines if l and not l.startswith('Play') and not l.startswith('http')]
        
        if not raw_lines:
            continue
            
        if v_num_m:
            sec_name = f"VERSE {v_num_m.group(1)}"
        elif is_refrein:
            sec_name = "CHORUS"
        else:
            sec_name = f"VERSE {verse_idx}"
            verse_idx += 1
            
        slides = format_verse_lines(raw_lines)
        if slides:
            sections.append((sec_name, slides))

    if not sections:
        return None, "No verse sections found"

    # Assemble formatted lyric text
    filename_base = f"{song_title} - {book_id}"
    filename_clean = sanitize_filename(filename_base) + ".txt"

    out_lines = ["BLANK", f"{song_title} - {book_id}", ""]
    for sec_name, slides in sections:
        out_lines.append(sec_name)
        for s in slides:
            out_lines.append(s)
            out_lines.append("") # blank line between slides

    content = "\n".join(out_lines).strip() + "\n"
    return (filename_clean, content), None

def main():
    books_config = [
        ("kj", 1, 478),
        ("nkb", 1, 230),
        ("pkj", 1, 288)
    ]
    
    existing_files = set(f.lower() for f in os.listdir(TXT_DIR))
    
    total_added = 0
    total_skipped = 0
    total_errors = 0

    print("==============================================================================")
    print("  SCRAPING HYMNAL RESMI GEREJA (KJ, NKB, PKJ)")
    print("==============================================================================")

    for book, start_num, end_num in books_config:
        print(f"\n[START] Memproses Buku {book.upper()} ({start_num} s/d {end_num})...")
        for num in range(start_num, end_num + 1):
            # Check if this book & number already exists in TXT_DIR
            pattern = rf'{book.lower()}\s+{num}\b'
            already_have = any(re.search(pattern, f) for f in existing_files)
            if already_have:
                total_skipped += 1
                continue

            result, err = scrape_song(book, num)
            if err:
                # Some numbers might not exist (e.g. gap numbers)
                total_errors += 1
                continue

            filename, content = result
            fpath = os.path.join(TXT_DIR, filename)
            
            # Double check if exact filename exists
            if os.path.exists(fpath):
                total_skipped += 1
                continue

            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)

            existing_files.add(filename.lower())
            total_added += 1
            print(f"  [+] ({book.upper()} {num:03d}) Ditambahkan: {filename}")
            
            # Gentle delay to respect server
            time.sleep(0.08)

    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {total_added} lagu baru | Dilewati (sudah ada): {total_skipped} | Error/Lewat: {total_errors}")
    print("==============================================================================")

if __name__ == "__main__":
    main()
