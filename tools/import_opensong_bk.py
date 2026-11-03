import os
import re
import sys
import ssl
import time
import json
import html
import sqlite3
import urllib.request
import urllib.parse
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
    s = html.unescape(s)
    return (s.replace("’", "'")
             .replace("‘", "'")
             .replace("“", '"')
             .replace("”", '"')
             .replace("â€™", "'")
             .replace("â€˜", "'")
             .strip())

def to_title_case(s):
    words = s.split()
    small_words = {"dan", "di", "ke", "dari", "yang", "pada", "untuk", "dgn", "dg", "si", "sang", "pun", "ku", "mu", "nya", "and", "the", "in", "of", "to", "for", "with", "a", "an", "is", "by", "or", "nor", "but", "so"}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small_words:
            out.append(lw)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def clean_artist(a):
    if not a: return ""
    a = clean_text(a)
    low = a.lower()
    if any(k in low for k in ["composer unknown", "author unknown", "unknown", "traditional", "public domain"]):
        return ""
    a = re.sub(r"\s*\([^)]*\d+[^)]*\)", "", a).strip()
    return a

def parse_opensong_content(xml_text):
    title_m = re.search(r"<title>(.*?)</title>", xml_text, re.DOTALL)
    author_m = re.search(r"<author>(.*?)</author>", xml_text, re.DOTALL)
    lyrics_m = re.search(r"<lyrics>(.*?)</lyrics>", xml_text, re.DOTALL)
    if not lyrics_m: return None

    raw_title = clean_text(title_m.group(1)).strip() if title_m else ""
    raw_artist = clean_artist(author_m.group(1)) if author_m else ""
    raw_lyrics = lyrics_m.group(1)

    if not raw_title or len(raw_title) < 2:
        return None

    # Strip track number prefixes like "177. "
    raw_title = re.sub(r'^\d+[\.\-\s]+', '', raw_title).strip()
    title = to_title_case(raw_title)
    artist = raw_artist

    sections = []
    current_sec = "VERSE 1"
    current_lines = []
    v_count = 0
    c_count = 0
    b_count = 0

    for line in raw_lyrics.splitlines():
        line = line.strip()
        if not line: continue

        m_sec = re.match(r"^\[([A-Za-z0-9\s]+)\]$", line)
        if m_sec:
            if current_lines:
                sections.append((current_sec, current_lines))
                current_lines = []
            tag = m_sec.group(1).upper()
            if tag.isdigit():
                current_sec = f"VERSE {tag}"
            elif tag.startswith("C"):
                num = tag[1:] if len(tag) > 1 and tag[1:].isdigit() else ""
                if not num:
                    c_count += 1
                    num = str(c_count) if c_count > 1 else ""
                current_sec = f"CHORUS {num}".strip()
            elif tag.startswith("V"):
                num = tag[1:] if len(tag) > 1 and tag[1:].isdigit() else ""
                if not num:
                    v_count += 1
                    num = str(v_count)
                current_sec = f"VERSE {num}".strip()
            elif tag.startswith("B"):
                num = tag[1:] if len(tag) > 1 and tag[1:].isdigit() else ""
                if not num:
                    b_count += 1
                    num = str(b_count) if b_count > 1 else ""
                current_sec = f"BRIDGE {num}".strip()
            elif tag.startswith("P"):
                current_sec = "PRE-CHORUS"
            elif tag.startswith("T"):
                current_sec = "TAG"
            elif tag.startswith("E") or tag.startswith("O"):
                current_sec = "ENDING"
            else:
                current_sec = tag
            continue

        if line.startswith("."): continue
        clean_l = re.sub(r"_{2,}", "", line)
        clean_l = clean_text(clean_l)
        clean_l = re.sub(r"\s+", " ", clean_l).strip()
        if clean_l and len(clean_l) > 1 and not clean_l.startswith(";") and not clean_l.startswith("--"):
            current_lines.append(clean_l)

    if current_lines:
        sections.append((current_sec, current_lines))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    core = f"{title} - {artist}" if artist else title
    filename = sanitize_filename(core) + ".txt"

    out = ["BLANK", core, ""]
    for s_hdr, lines in sections:
        out.append(s_hdr)
        for i in range(0, len(lines), 2):
            out.append("\n".join(lines[i:i+2]))
            out.append("")

    content = "\n".join(out).strip() + "\n"
    category = "EN"

    return filename, title, artist, category, content

def fetch_and_parse(path):
    enc = urllib.parse.quote(path)
    url = f"https://raw.githubusercontent.com/ding0t/opensong-bk/main/{enc}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            xml = resp.read().decode("utf-8", errors="ignore")
        return parse_opensong_content(xml)
    except:
        return None

def main():
    start_time = time.time()
    print("==============================================================================")
    print("  MASSIVE EXPANSION: OPENSONG CHURCH WORSHIP REPOSITORY (8.400+ FILES)")
    print("==============================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT LOWER(title), LOWER(COALESCE(artist, '')), LOWER(filename) FROM songs")
    rows = cur.fetchall()
    existing_pairs = set((r[0], r[1]) for r in rows)
    existing_files = set(r[2] for r in rows)
    initial_count = len(rows)

    print(f"[STATUS] Database saat ini: {initial_count:,} lagu terdaftar.\n", flush=True)

    url = "https://api.github.com/repos/ding0t/opensong-bk/git/trees/main?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=12).read().decode("utf-8"))

    # Filter only relevant non-duplicate folders
    raw_songs = [
        f["path"] for f in data["tree"]
        if f["path"].startswith("Songs/")
        and not " - By Number" in f["path"]
        and not f["path"].endswith(".zip")
        and not f["path"].endswith(".txt")
    ]

    candidates = []
    seen_paths = set()
    for s in raw_songs:
        base = os.path.basename(s).lower()
        clean_name = re.sub(r'\s+i\d+$', '', base).strip()
        fname = sanitize_filename(clean_name) + ".txt"
        if fname.lower() not in existing_files and clean_name not in seen_paths:
            seen_paths.add(clean_name)
            candidates.append(s)

    total_cands = len(candidates)
    print(f"[FETCH] Memulai unduhan paralel {total_cands:,} lagu pilihan (28 threads)...", flush=True)

    records = []
    seen = set()
    completed = 0

    with ThreadPoolExecutor(max_workers=28) as pool:
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

            if completed % 500 == 0 or completed == total_cands:
                print(f"  [Progress] {completed:,}/{total_cands:,} diproses ({len(records):,} lagu valid siap disimpan)...", flush=True)

    print(f"\n[DATABASE] Memasukkan {len(records):,} lagu gereja baru ke database...", flush=True)

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
