import os
import re
import sys
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "TXT")

def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = cleaned.replace('’', "'").replace('‘', "'").replace('“', "'").replace('”', "'").replace('"', "'")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_text(s):
    if not s:
        return ""
    return (s.replace('’', "'")
             .replace('‘', "'")
             .replace('“', '"')
             .replace('”', '"')
             .replace('â€™', "'")
             .replace('â€˜', "'")
             .strip())

def parse_openlyrics_xml(xml_content, fallback_title, fallback_artist):
    xml_clean = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
    try:
        root = ET.fromstring(xml_clean)
    except Exception:
        return None

    # Title
    title = ""
    t_elem = root.find('.//properties/titles/title')
    if t_elem is not None and t_elem.text:
        title = clean_text(t_elem.text)
    if not title:
        title = fallback_title

    # Authors
    authors = []
    for a in root.findall('.//properties/authors/author'):
        if a.text and a.text.strip():
            at = clean_text(a.text)
            if at.lower() not in ["author unknown", "unknown", "traditional"]:
                # strip year ranges like (1823-1876)
                at = re.sub(r'\s*\([^)]*\d+[^)]*\)', '', at).strip()
                if at and at not in authors:
                    authors.append(at)

    if authors:
        artist = ", ".join(authors[:2])
    else:
        artist = fallback_artist

    # Lyrics
    sections = []
    v_idx = 0
    c_idx = 0
    b_idx = 0

    verses = root.findall('.//lyrics/verse')
    for verse in verses:
        name = verse.attrib.get('name', '').lower()
        if name.startswith('c'):
            c_idx += 1
            sec_hdr = "CHORUS" if c_idx == 1 else f"CHORUS {c_idx}"
        elif name.startswith('b'):
            b_idx += 1
            sec_hdr = "BRIDGE" if b_idx == 1 else f"BRIDGE {b_idx}"
        elif name.startswith('p'):
            sec_hdr = "PRE-CHORUS"
        elif name.startswith('e') or name.startswith('o'):
            sec_hdr = "ENDING"
        elif name.startswith('i'):
            sec_hdr = "INTRO"
        elif name.startswith('t'):
            sec_hdr = "TAG"
        else:
            v_idx += 1
            sec_hdr = f"VERSE {v_idx}"

        lines_elem = verse.find('lines')
        if lines_elem is None:
            continue

        raw_xml_lines = ET.tostring(lines_elem, encoding='utf-8').decode('utf-8')
        raw_text = re.sub(r'<br\s*/?>', '\n', raw_xml_lines)
        raw_text = re.sub(r'<[^>]+>', '', raw_text)
        
        lines = [clean_text(l) for l in raw_text.splitlines() if clean_text(l)]
        if not lines:
            continue

        slides = []
        for i in range(0, len(lines), 2):
            slides.append("\n".join(lines[i:i+2]))

        if slides:
            sections.append((sec_hdr, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    return title, artist, sections

def fetch_and_process_song(item_path, existing_files):
    # Parse title & artist hint from filename: "Title (Artist).xml"
    base = os.path.basename(item_path)[:-4] # strip .xml
    hint_title = base
    hint_artist = "Worship / Hymn"
    m = re.match(r'^(.*?)\s*\((.*?)\)$', base)
    if m:
        hint_title = m.group(1).strip()
        hint_artist = m.group(2).strip()
        if hint_artist.lower() in ["author unknown", "unknown"]:
            hint_artist = "Worship / Hymn"

    encoded_path = urllib.parse.quote(item_path)
    url = f"https://raw.githubusercontent.com/Jesulayomy/OpenLP/master/{encoded_path}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        xml_content = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')
    except Exception:
        return "error", item_path, "Download failed"

    res = parse_openlyrics_xml(xml_content, hint_title, hint_artist)
    if not res:
        return "skipped", item_path, "No valid sections"

    title, artist, sections = res
    filename = sanitize_filename(f"{title} - {artist}") + ".txt"

    if filename.lower() in existing_files:
        return "skipped", filename, "Already exists"

    out = ["BLANK", f"{title} - {artist}", ""]
    for s_hdr, slides in sections:
        out.append(s_hdr)
        for s in slides:
            out.append(s)
            out.append("")

    content = "\n".join(out).strip() + "\n"
    if len(content) < 80:
        return "error", filename, "Too short"

    fpath = os.path.join(TXT_DIR, filename)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

    return "added", filename, "OK"

def main():
    print("==============================================================================")
    print("  OPENLP ENGLISH CHRISTIAN WORSHIP & HYMN IMPORTER")
    print("==============================================================================")

    tree_url = "https://api.github.com/repos/Jesulayomy/OpenLP/git/trees/master?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=12).read().decode('utf-8'))
        tree = data.get('tree', [])
        song_items = [item['path'] for item in tree if item['path'].startswith('Songs/') and item['path'].endswith('.xml')]
    except Exception as e:
        print(f"[ERROR] Gagal memuat daftar lagu dari GitHub: {e}")
        return

    print(f"Total Lagu Bahasa Inggris ditemukan di katalog OpenLP: {len(song_items)} lagu.", flush=True)

    existing_files = set(f.lower() for f in os.listdir(TXT_DIR))
    print(f"Database saat ini: {len(existing_files)} lagu.", flush=True)

    added_count = 0
    skipped_count = 0
    error_count = 0

    print("\nMulai mengunduh & mengimpor lagu bahasa Inggris secara paralel (16 workers)...", flush=True)

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(fetch_and_process_song, p, existing_files): p for p in song_items}
        for fut in as_completed(futures):
            try:
                status, fname, msg = fut.result()
                if status == "added":
                    added_count += 1
                    existing_files.add(fname.lower())
                    if added_count % 100 == 0 or added_count == len(song_items):
                        total_now = len(existing_files)
                        print(f"  [Progress] +{added_count} lagu bahasa Inggris ditambahkan (Total Database: {total_now} lagu)...", flush=True)
                elif status == "skipped":
                    skipped_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

    final_count = len(os.listdir(TXT_DIR))
    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {added_count} lagu bahasa Inggris | Dilewati: {skipped_count} | Gagal: {error_count}")
    print(f"Total Database Saat Ini: {final_count} lagu")
    print("==============================================================================")

if __name__ == "__main__":
    main()
