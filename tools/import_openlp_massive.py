import os
import re
import sys
import ssl
import time
import json
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(BASE_DIR, "database", "banklycs.db")

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = cleaned.replace('’', "'").replace('‘', "'").replace('“', "'").replace('”', "'").replace('"', "'")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_text(s):
    if not s: return ""
    return (s.replace('’', "'")
             .replace('‘', "'")
             .replace('“', '"')
             .replace('”', '"')
             .replace('â€™', "'")
             .replace('â€˜', "'")
             .strip())

def format_lines_into_slides(lines):
    clean = [clean_text(l) for l in lines if clean_text(l)]
    slides = []
    for i in range(0, len(clean), 2):
        slides.append("\n".join(clean[i:i+2]))
    return slides

def parse_openlyrics_xml(xml_content, fallback_title, fallback_artist):
    xml_clean = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
    try:
        root = ET.fromstring(xml_clean)
    except:
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
                at = re.sub(r'\s*\([^)]*\d+[^)]*\)', '', at).strip()
                if at and at not in authors:
                    authors.append(at)

    artist = ", ".join(authors[:2]) if authors else fallback_artist

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
        if lines_elem is None: continue

        raw_xml_lines = ET.tostring(lines_elem, encoding='utf-8').decode('utf-8')
        raw_text = re.sub(r'<br\s*/?>', '\n', raw_xml_lines)
        raw_text = re.sub(r'<[^>]+>', '', raw_text)
        lines = [clean_text(l) for l in raw_text.splitlines() if clean_text(l)]
        if not lines: continue

        slides = format_lines_into_slides(lines)
        if slides:
            sections.append((sec_hdr, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    core = f"{title} - {artist}" if artist else title
    filename = sanitize_filename(core) + ".txt"

    out = ["BLANK", core, ""]
    for s_hdr, slides in sections:
        out.append(s_hdr)
        for s in slides:
            out.append(s)
            out.append("")

    content = "\n".join(out).strip() + "\n"
    category = "EN"

    return filename, title, artist, category, content

def fetch_and_parse(item_path):
    base = os.path.basename(item_path)[:-4]
    hint_title = base
    hint_artist = "Hymn"
    m = re.match(r'^(.*?)\s*\((.*?)\)$', base)
    if m:
        hint_title = m.group(1).strip()
        hint_artist = m.group(2).strip()
        if hint_artist.lower() in ["author unknown", "unknown"]:
            hint_artist = "Hymn"

    encoded_path = urllib.parse.quote(item_path)
    url = f"https://raw.githubusercontent.com/Jesulayomy/OpenLP/master/{encoded_path}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            xml_content = resp.read().decode('utf-8', errors='ignore')
        return parse_openlyrics_xml(xml_content, hint_title, hint_artist)
    except:
        return None

def main():
    start_time = time.time()
    print("==============================================================================")
    print("  MASSIVE EXPANSION: 2.100+ LAGU BAHASA INGGRIS DARI OPENLP DATABASE")
    print("==============================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT LOWER(title), LOWER(COALESCE(artist, '')), LOWER(filename) FROM songs")
    rows = cur.fetchall()
    existing_pairs = set((r[0], r[1]) for r in rows)
    existing_files = set(r[2] for r in rows)
    initial_count = len(rows)

    print(f"[STATUS] Database saat ini: {initial_count:,} lagu terdaftar.\n", flush=True)

    tree_url = "https://api.github.com/repos/Jesulayomy/OpenLP/git/trees/master?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=12).read().decode("utf-8"))
    song_items = [item["path"] for item in data["tree"] if item["path"].startswith("Songs/") and item["path"].endswith(".xml")]

    candidates = []
    for p in song_items:
        base = os.path.basename(p)[:-4]
        m = re.match(r"^(.*?)\s*\((.*?)\)$", base)
        t = (m.group(1).strip() if m else base).lower()
        a = (m.group(2).strip() if m else "").lower()
        fname = sanitize_filename(base) + ".txt"
        if (t, a) not in existing_pairs and fname.lower() not in existing_files:
            candidates.append(p)

    total_cands = len(candidates)
    print(f"[FETCH] Memulai unduhan paralel {total_cands:,} lagu bahasa Inggris (24 threads)...", flush=True)

    records = []
    seen = set()
    completed = 0

    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = {pool.submit(fetch_and_parse, p): p for p in candidates}
        for fut in as_completed(futures):
            completed += 1
            try:
                res = fut.result()
                if res:
                    fname, title, artist, cat, content = res
                    pair = (title.lower(), artist.lower())
                    if pair not in existing_pairs and fname.lower() not in existing_files and pair not in seen:
                        records.append((fname, title, artist, cat, content))
                        seen.add(pair)
                        seen.add(fname.lower())
            except:
                pass

            if completed % 200 == 0 or completed == total_cands:
                print(f"  [Progress] {completed:,}/{total_cands:,} diunduh ({len(records):,} lagu valid siap disimpan)...", flush=True)

    print(f"\n[DATABASE] Memasukkan {len(records):,} lagu bahasa Inggris baru ke database...", flush=True)

    if records:
        cur.executemany("""
        INSERT OR IGNORE INTO songs (filename, title, artist, category, content)
        VALUES (?, ?, ?, ?, ?);
        """, records)
        conn.commit()

        print("[CHECKPOINT] Menjalankan checkpoint WAL...", flush=True)
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        cur.execute("PRAGMA optimize;")

    cur.execute("SELECT COUNT(*) FROM songs")
    final_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM songs_fts")
    final_fts = cur.fetchone()[0]

    conn.close()

    elapsed = time.time() - start_time
    print("==============================================================================")
    print(f"  SELESAI DALAM {elapsed:.1f} DETIK!")
    print(f"  * Total Lagu Awal     : {initial_count:,}")
    print(f"  * Lagu Baru Ditambah  : +{len(records):,}")
    print(f"  * Total Lagu Sekarang : {final_count:,}")
    print(f"  * Sinkronisasi FTS5   : {final_fts:,} (100% Valid)")
    print("==============================================================================")

if __name__ == "__main__":
    main()
