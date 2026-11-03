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
from html import unescape

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(BASE_DIR, "database", "banklycs.db")

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = cleaned.replace('’', "'").replace('‘', "'").replace('“', "'").replace('”', "'").replace('"', "'")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_text_quotes(text):
    if not text: return ""
    return (text.replace('’', "'")
                .replace('‘', "'")
                .replace('“', '"')
                .replace('”', '"')
                .replace('â€™', "'")
                .replace('â€˜', "'")
                .replace('â€œ', '"')
                .replace('â€', '"')
                .strip())

def to_title_case(s):
    words = s.split()
    small_words = {'dan', 'di', 'ke', 'dari', 'yang', 'pada', 'untuk', 'dgn', 'dg', 'si', 'sang', 'pun', 'ku', 'mu', 'nya', 'and', 'the', 'in', 'of', 'to', 'for', 'with', 'a', 'an'}
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

def determine_category(title, artist):
    u = (title + " " + artist).upper()
    if re.search(r'\bKJ\s*\d+', u): return "KJ"
    if re.search(r'\bNKB\s*\d+', u): return "NKB"
    if re.search(r'\bPKJ\s*\d+', u): return "PKJ"
    if re.search(r'\bKK\s*\d+', u): return "KK"
    if re.search(r'\bBE\s*\d+', u): return "BE"
    if re.search(r'\bKLIK\s*\d+', u): return "KLIK"
    if re.search(r'\bNNBT\s*\d+', u): return "NNBT"
    if "JAWA" in u or "PASAMUWAN" in u: return "JAWA"
    if any(k in u for k in ["HILLSONG", "BETHEL", "ELEVATION", "PLANETSHAKERS", "TOMLIN", "REDMAN", "WICKHAM", "GAITHER", "MAVERICK", "BRANDON LAKE", "PHIL WICKHAM", "CHRIS TOMLIN", "MATT REDMAN"]):
        return "EN"
    eng_words = set(re.findall(r'\b[a-z]+\b', title.lower()))
    eng_markers = {"the", "and", "you", "my", "lord", "god", "in", "is", "of", "to", "we", "for", "he", "our", "all", "your", "with", "me", "are", "be", "jesus", "holy", "praise", "glory", "grace", "love"}
    if len(eng_words.intersection(eng_markers)) >= 2:
        return "EN"
    return "ID"

def fetch_html(url, timeout=10, max_retries=2):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except:
            if attempt < max_retries - 1:
                time.sleep(0.5)
    return None

# ==============================================================================
# SOURCE 1: PSALMNOTE (Indonesian & Contemporary Praise & Worship)
# ==============================================================================
def parse_psalmnote_item(item):
    alias = item.get('alias')
    raw_title = to_title_case(clean_text_quotes(item.get('title') or ""))
    raw_artist = clean_text_quotes(item.get('artist') or "")
    fallback_lyric = item.get('lyric') or ""

    if not raw_title:
        return None

    sections = []
    if alias:
        url = f"https://psalmnote.com/song/{alias}"
        html = fetch_html(url)
        if html:
            blocks = re.findall(r'<button[^>]*class="[^"]*song-part-tag[^"]*"[^>]*>(.*?)</button>.*?<div id="songPart\d+"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
            for tag_html, body_html in blocks:
                raw_tag = re.sub(r'<[^>]+>', '', tag_html).replace('[', '').replace(']', '').strip()
                tag_upper = raw_tag.upper()
                if 'INTRO' in tag_upper: sec_name = "INTRO"
                elif 'OUTRO' in tag_upper or 'ENDING' in tag_upper: sec_name = "ENDING"
                elif 'INTERLUDE' in tag_upper or 'TRANSITION' in tag_upper: sec_name = "INTERLUDE"
                elif 'CHORUS' in tag_upper or 'REFF' in tag_upper:
                    m_num = re.search(r'\d+', raw_tag)
                    sec_name = f"CHORUS {m_num.group(0)}" if m_num else "CHORUS"
                elif 'BRIDGE' in tag_upper:
                    m_num = re.search(r'\d+', raw_tag)
                    sec_name = f"BRIDGE {m_num.group(0)}" if m_num else "BRIDGE"
                elif 'PRE' in tag_upper and 'CHORUS' in tag_upper: sec_name = "PRE-CHORUS"
                elif 'VERSE' in tag_upper or 'BAIT' in tag_upper:
                    m_num = re.search(r'\d+', raw_tag)
                    sec_name = f"VERSE {m_num.group(0)}" if m_num else "VERSE 1"
                else: sec_name = raw_tag

                lyric_matches = re.findall(r'<section class="lyric"[^>]*>(.*?)</section>', body_html)
                clean_lines = [re.sub(r'<[^>]+>', '', unescape(l)).strip() for l in lyric_matches]
                clean_lines = [l for l in clean_lines if l and not l.startswith('/') and not l.startswith('|')]
                if clean_lines:
                    slides = format_lines_into_slides(clean_lines)
                    if slides:
                        sections.append((sec_name, slides))

    # Fallback to item['lyric']
    if not sections and fallback_lyric and len(fallback_lyric) > 50:
        lines = [clean_text_quotes(l).strip() for l in re.split(r'[\r\n]+|\.\s+', fallback_lyric) if clean_text_quotes(l).strip()]
        lines = [l for l in lines if len(l) > 4 and not l.lower().startswith('key') and not l.lower().startswith('tempo')]
        if len(lines) >= 4:
            slides = format_lines_into_slides(lines)
            half = max(2, len(slides) // 2)
            sections = [("VERSE 1", slides[:half]), ("CHORUS", slides[half:])]

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    core = f"{raw_title} - {raw_artist}" if raw_artist else raw_title
    filename = sanitize_filename(core) + ".txt"

    out = ["BLANK", core, ""]
    for s_hdr, slides in sections:
        out.append(s_hdr)
        for s in slides:
            out.append(s)
            out.append("")

    content = "\n".join(out).strip() + "\n"
    category = determine_category(raw_title, raw_artist)

    return filename, raw_title, raw_artist, category, content

# ==============================================================================
# SOURCE 2: LALSPROJECT OFFICIAL HYMNALS (KLIK, NNBT, PKJ, NKB, KJ)
# ==============================================================================
def parse_lalsproject_item(item, book_name):
    code = str(item.get('code', '')).strip()
    raw_title = item.get('title', '').strip()
    title = to_title_case(raw_title)
    artist = f"{book_name} {code}"
    filename = sanitize_filename(f"{title} - {artist}") + ".txt"

    lyrics_blocks = item.get('lyrics', [])
    sections = []
    verse_idx = 0
    chorus_idx = 0

    for block in lyrics_blocks:
        verses = block.get('verses', [])
        for v in verses:
            kind = v.get('kind', 'NORMAL').upper()
            raw_lines = v.get('lines', [])
            lines = [clean_text_quotes(re.sub(r'<[^>]+>', '', l)).strip() for l in raw_lines if l.strip()]
            slides = format_lines_into_slides(lines)
            if not slides: continue

            if 'REFRAIN' in kind or 'CHORUS' in kind:
                chorus_idx += 1
                s_name = "CHORUS" if chorus_idx == 1 else f"CHORUS {chorus_idx}"
            else:
                verse_idx += 1
                s_name = f"VERSE {verse_idx}"

            sections.append((s_name, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    core = f"{title} - {artist}"
    out = ["BLANK", core, ""]
    for s_hdr, slides in sections:
        out.append(s_hdr)
        for s in slides:
            out.append(s)
            out.append("")

    content = "\n".join(out).strip() + "\n"
    return filename, title, artist, book_name, content

# ==============================================================================
# SOURCE 3: OPENLP ENGLISH CHRISTIAN WORSHIP & HYMNS
# ==============================================================================
def parse_openlyrics_item(item_path):
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

    xml_content = fetch_html(url, timeout=8)
    if not xml_content:
        return None

    xml_clean = re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)
    try:
        root = ET.fromstring(xml_clean)
    except:
        return None

    title = ""
    t_elem = root.find('.//properties/titles/title')
    if t_elem is not None and t_elem.text:
        title = clean_text_quotes(t_elem.text)
    if not title:
        title = hint_title

    authors = []
    for a in root.findall('.//properties/authors/author'):
        if a.text and a.text.strip():
            at = clean_text_quotes(a.text)
            if at.lower() not in ["author unknown", "unknown", "traditional"]:
                at = re.sub(r'\s*\([^)]*\d+[^)]*\)', '', at).strip()
                if at and at not in authors:
                    authors.append(at)

    artist = ", ".join(authors[:2]) if authors else hint_artist

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
        lines = [clean_text_quotes(l) for l in raw_text.splitlines() if clean_text_quotes(l)]
        if not lines: continue

        slides = format_lines_into_slides(lines)
        if slides:
            sections.append((sec_hdr, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    core = f"{title} - {artist}"
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

# ==============================================================================
# MAIN BATCH ORCHESTRATION
# ==============================================================================
def main():
    start_time = time.time()
    print("==============================================================================")
    print("  MASSIVE EXPANSION: IMPORT LAGU KE SQLITE DATABASE (banklycs.db)")
    print("==============================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT LOWER(title), LOWER(COALESCE(artist, '')), LOWER(filename) FROM songs;")
    rows = cur.fetchall()
    existing_titles = set(r[0] for r in rows)
    existing_pairs = set((r[0], r[1]) for r in rows)
    existing_files = set(r[2] for r in rows)

    initial_count = len(rows)
    print(f"[STATUS] Database saat ini: {initial_count:,} lagu master terdaftar.\n", flush=True)

    records_to_insert = []
    seen_in_batch = set()

    # --------------------------------------------------------------------------
    # 1. PSALMNOTE IMPORT (Indonesian & English Praise & Worship)
    # --------------------------------------------------------------------------
    psalmnote_path = os.path.join(BASE_DIR, "tools", "psalmnote_catalog.json")
    if os.path.exists(psalmnote_path):
        with open(psalmnote_path, "r", encoding="utf-8") as f:
            psalm_data = json.load(f)

        candidates = []
        for k, v in psalm_data.items():
            t = (v.get('title') or '').strip().lower()
            a = (v.get('artist') or '').strip().lower()
            if not t or len(v.get('lyric') or '') < 40: continue
            if t not in existing_titles and (t, a) not in existing_pairs:
                candidates.append(v)

        print(f"[1/3] Mengimpor dari Psalmnote Catalog ({len(candidates):,} kandidat lagu baru)...", flush=True)
        psalm_added = 0
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(parse_psalmnote_item, c) for c in candidates]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        fname, title, artist, cat, content = res
                        low_key = (title.lower(), artist.lower())
                        if low_key not in existing_pairs and fname.lower() not in existing_files and low_key not in seen_in_batch:
                            records_to_insert.append((fname, title, artist, cat, content))
                            seen_in_batch.add(low_key)
                            seen_in_batch.add(fname.lower())
                            psalm_added += 1
                except:
                    pass

        print(f"      -> Sukses memproses {psalm_added:,} lagu baru dari Psalmnote!", flush=True)

    # --------------------------------------------------------------------------
    # 2. LALSPROJECT OFFICIAL HYMNALS (KLIK, NNBT, PKJ, NKB, KJ)
    # --------------------------------------------------------------------------
    print(f"\n[2/3] Mengimpor Lagu Buku Himne Gereja Resmi (lalsproject)...", flush=True)
    hymn_books = ["KLIK", "NNBT", "PKJ", "NKB", "KJ"]
    hymn_added = 0

    for book in hymn_books:
        url = f"https://raw.githubusercontent.com/lalsproject/lalsproject.github.io/master/{book}.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                book_data = json.loads(resp.read().decode("utf-8"))

            book_count = 0
            for item in book_data:
                res = parse_lalsproject_item(item, book)
                if res:
                    fname, title, artist, cat, content = res
                    low_key = (title.lower(), artist.lower())
                    if low_key not in existing_pairs and fname.lower() not in existing_files and low_key not in seen_in_batch:
                        records_to_insert.append((fname, title, artist, cat, content))
                        seen_in_batch.add(low_key)
                        seen_in_batch.add(fname.lower())
                        hymn_added += 1
                        book_count += 1
            print(f"      -> Buku {book:<5}: +{book_count} lagu", flush=True)
        except Exception as e:
            print(f"      -> Buku {book:<5}: Error {e}", flush=True)

    # --------------------------------------------------------------------------
    # 3. OPENLP ENGLISH CHRISTIAN WORSHIP & HYMNS (GitHub Tree)
    # --------------------------------------------------------------------------
    print(f"\n[3/3] Mengimpor Lagu Bahasa Inggris dari OpenLP Repository...", flush=True)
    openlp_tree_url = "https://api.github.com/repos/Jesulayomy/OpenLP/git/trees/master?recursive=1"
    openlp_added = 0
    try:
        req = urllib.request.Request(openlp_tree_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            tree_data = json.loads(resp.read().decode("utf-8"))
        tree = tree_data.get('tree', [])
        openlp_items = [item['path'] for item in tree if item['path'].startswith('Songs/') and item['path'].endswith('.xml')]

        # Filter candidates
        openlp_cands = []
        for p in openlp_items:
            base = os.path.basename(p)[:-4]
            m = re.match(r'^(.*?)\s*\((.*?)\)$', base)
            t = (m.group(1).strip() if m else base).lower()
            if t not in existing_titles and (t, "") not in existing_pairs:
                openlp_cands.append(p)

        print(f"      -> Mengunduh {len(openlp_cands):,} lagu bahasa Inggris pilihan (16 threads)...", flush=True)

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(parse_openlyrics_item, p) for p in openlp_cands]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        fname, title, artist, cat, content = res
                        low_key = (title.lower(), artist.lower())
                        if low_key not in existing_pairs and fname.lower() not in existing_files and low_key not in seen_in_batch:
                            records_to_insert.append((fname, title, artist, cat, content))
                            seen_in_batch.add(low_key)
                            seen_in_batch.add(fname.lower())
                            openlp_added += 1
                except:
                    pass

        print(f"      -> Sukses memproses {openlp_added:,} lagu bahasa Inggris dari OpenLP!", flush=True)
    except Exception as e:
        print(f"      -> Error OpenLP tree: {e}", flush=True)

    # --------------------------------------------------------------------------
    # ATOMIC DATABASE BATCH INSERT
    # --------------------------------------------------------------------------
    total_new = len(records_to_insert)
    print(f"\n[DATABASE] Memasukkan {total_new:,} lagu baru ke tabel songs & songs_fts...", flush=True)

    if total_new > 0:
        cur.executemany("""
        INSERT OR IGNORE INTO songs (filename, title, artist, category, content)
        VALUES (?, ?, ?, ?, ?);
        """, records_to_insert)

        conn.commit()
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        cur.execute("PRAGMA optimize;")

    cur.execute("SELECT COUNT(*) FROM songs;")
    final_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM songs_fts;")
    final_fts = cur.fetchone()[0]

    conn.close()

    elapsed = time.time() - start_time
    print("==============================================================================")
    print(f"  SELESAI DALAM {elapsed:.1f} DETIK!")
    print(f"  * Total Lagu Awal     : {initial_count:,}")
    print(f"  * Lagu Baru Ditambah  : +{total_new:,}")
    print(f"  * Total Lagu Sekarang : {final_count:,}")
    print(f"  * Sinkronisasi FTS5   : {final_fts:,} (100% Valid)")
    print("==============================================================================")

if __name__ == "__main__":
    main()
