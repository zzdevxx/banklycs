import os
import re
import sys
import ssl
import time
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

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
    return text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('â€™', "'").replace('â€˜', "'")

def fetch_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except:
        return None

def fetch_html(url, timeout=12, max_retries=3):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.0 + attempt * 1.5)
            else:
                return None
    return None

def format_lines_into_slides(lines):
    clean = [clean_text_quotes(l).strip() for l in lines if clean_text_quotes(l).strip()]
    slides = []
    for i in range(0, len(clean), 2):
        chunk = clean[i:i+2]
        slides.append("\n".join(chunk))
    return slides

def parse_song_from_page(alias, item_info):
    url = f"https://psalmnote.com/song/{alias}"
    html = fetch_html(url)
    
    raw_title = item_info.get('title') or ""
    raw_artist = item_info.get('artist') or ""
    fallback_lyric = item_info.get('lyric') or ""

    if html:
        # Title from H1 if available
        m_title = re.search(r'<h1 class="songviewer-h1"[^>]*>\s*(.*?)\s*<', html, re.DOTALL)
        if m_title:
            raw_title = unescape(m_title.group(1)).strip()

        # Artist
        m_artist = re.search(r'<a\s+[^>]*href="/artist/[^"]*"[^>]*>(.*?)</a>', html)
        if m_artist:
            raw_artist = unescape(m_artist.group(1)).strip()

        # Extract structured parts: <button ... song-part-tag ...> ... </button> ... <div id="songPartX"> ... </div>
        blocks = re.findall(r'<button[^>]*class="[^"]*song-part-tag[^"]*"[^>]*>(.*?)</button>.*?<div id="songPart\d+"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
        
        sections = []
        for tag_html, body_html in blocks:
            raw_tag = re.sub(r'<[^>]+>', '', tag_html).replace('[', '').replace(']', '').strip()
            tag_upper = raw_tag.upper()
            if 'INTRO' in tag_upper:
                sec_name = "INTRO"
            elif 'OUTRO' in tag_upper or 'ENDING' in tag_upper:
                sec_name = "ENDING"
            elif 'INTERLUDE' in tag_upper or 'TRANSITION' in tag_upper:
                sec_name = "INTERLUDE"
            elif 'CHORUS' in tag_upper or 'REFF' in tag_upper:
                m_num = re.search(r'\d+', raw_tag)
                sec_name = f"CHORUS {m_num.group(0)}" if m_num else "CHORUS"
            elif 'BRIDGE' in tag_upper:
                m_num = re.search(r'\d+', raw_tag)
                sec_name = f"BRIDGE {m_num.group(0)}" if m_num else "BRIDGE"
            elif 'PRE' in tag_upper and 'CHORUS' in tag_upper:
                sec_name = "PRE-CHORUS"
            elif 'VERSE' in tag_upper or 'BAIT' in tag_upper:
                m_num = re.search(r'\d+', raw_tag)
                sec_name = f"VERSE {m_num.group(0)}" if m_num else "VERSE 1"
            else:
                sec_name = raw_tag

            # Find lyric lines
            lyric_matches = re.findall(r'<section class="lyric"[^>]*>(.*?)</section>', body_html)
            clean_lines = [re.sub(r'<[^>]+>', '', unescape(l)).strip() for l in lyric_matches]
            clean_lines = [l for l in clean_lines if l and not l.startswith('/') and not l.startswith('|')]
            
            if clean_lines:
                slides = format_lines_into_slides(clean_lines)
                if slides:
                    sections.append((sec_name, slides))

        if sections:
            return raw_title, raw_artist, sections

    # Fallback to item_info['lyric'] if structured HTML not parsed
    if fallback_lyric and len(fallback_lyric) > 50:
        lines = []
        for l in re.split(r'\. |\n', fallback_lyric):
            l = re.sub(r'\b[A-G](#|b)?\b', '', l) # remove chords
            l = re.sub(r'[/\\|0-9\.]', '', l).strip()
            if len(l) > 5 and not l.lower().startswith('key') and not l.lower().startswith('change'):
                lines.append(l)
        if len(lines) >= 4:
            slides = format_lines_into_slides(lines)
            return raw_title, raw_artist, [("VERSE 1", slides[:len(slides)//2]), ("CHORUS", slides[len(slides)//2:])]

    return raw_title, raw_artist, None

def process_single_psalmnote(item, existing_lower_files):
    alias = item.get('alias')
    if not alias:
        return "skipped", "No alias"

    title, artist, sections = parse_song_from_page(alias, item)
    if not sections:
        return "error", f"No sections: {alias}"

    # Clean title
    title = clean_text_quotes(title)
    # Strip leading track numbers like "01. " or "12. "
    title = re.sub(r'^\d+[\.\-\s]+', '', title).strip()
    artist = clean_text_quotes(artist).strip()

    if not title or (not artist and not sections):
        return "error", "Missing title"
    if not artist:
        artist = ""

    fname_core = f"{title} - {artist}" if artist else title
    filename = sanitize_filename(fname_core) + ".txt"
    if filename.lower() in existing_lower_files:
        return "skipped", filename

    header = f"{title} - {artist}" if artist else title
    out_lines = ["BLANK", header, ""]
    for sec_name, slides in sections:
        out_lines.append(sec_name)
        for s in slides:
            out_lines.append(s)
            out_lines.append("")

    content = "\n".join(out_lines).strip() + "\n"
    if len(content) < 80:
        return "error", "Content too short"

    fpath = os.path.join(TXT_DIR, filename)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

    return "added", filename

CACHE_FILE = os.path.join(BASE_DIR, "Tools", "psalmnote_catalog.json")

def main():
    print("==============================================================================")
    print("  PSALMNOTE SCRAPER (TARGET: MENEMBUS > 10.000 LAGU)")
    print("==============================================================================")

    all_songs = {}
    if os.path.exists(CACHE_FILE):
        print(f"[1/3] Memuat katalog dari cache {CACHE_FILE}...", flush=True)
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                all_songs = json.load(f)
            print(f"  -> {len(all_songs)} lagu dimuat dari cache.", flush=True)
        except Exception as e:
            print(f"  -> Gagal baca cache: {e}, melakukan discovery ulang...")

    if not all_songs:
        letters = 'abcdefghijklmnopqrstuvwxyz'
        prefixes = [c1 + c2 for c1 in letters for c2 in letters]
        prefixes.extend(list(letters))
        prefixes.extend([str(i) for i in range(10)])

        print(f"[1/3] Menjalankan API Discovery dengan {len(prefixes)} query prefixes...", flush=True)
        with ThreadPoolExecutor(max_workers=10) as pool:
            future_to_pref = {pool.submit(fetch_json, f"https://psalmnote.com/api/song/autocomplete?searchString={p}"): p for p in prefixes}
            for fut in as_completed(future_to_pref):
                res = fut.result()
                if res and isinstance(res, list):
                    for item in res:
                        alias = item.get('alias')
                        if alias and alias not in all_songs:
                            all_songs[alias] = item

        print(f"  -> Total lagu unik ditemukan di katalog Psalmnote: {len(all_songs)} lagu.", flush=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_songs, f, ensure_ascii=False)
        print(f"  -> Tersimpan di cache {CACHE_FILE}.", flush=True)

    # 2. Filter against existing files (REKURSIF - folder TXT datar tapi aman utk warisan)
    existing_lower_files = set()
    existing_titles = set()
    for dirpath, _dn, filenames in os.walk(TXT_DIR):
        for fn in filenames:
            if fn.lower().endswith('.txt'):
                existing_lower_files.add(fn.lower())
                stem = os.path.splitext(fn)[0]
                existing_titles.add(stem.split(' - ', 1)[0].strip().lower())
                existing_titles.add(stem.lower())
    print(f"[2/3] Memfilter lagu yang belum ada di database lokal ({len(existing_lower_files)} lagu saat ini)...", flush=True)
    
    songs_to_fetch = []
    for alias, item in all_songs.items():
        title = clean_text_quotes(item.get('title') or "")
        title = re.sub(r'^\d+[\.\-\s]+', '', title).strip()
        artist = clean_text_quotes(item.get('artist') or "").strip()
        fname_core = f"{title} - {artist}" if artist else title
        fname = sanitize_filename(fname_core) + ".txt"
        if fname.lower() not in existing_lower_files:
            songs_to_fetch.append(item)

    print(f"  -> Lagu baru yang siap di-scrape: {len(songs_to_fetch)} lagu.", flush=True)

    # 3. Parallel scraping
    print(f"\n[3/3] Mulai mengunduh & memformat {len(songs_to_fetch)} lagu dari Psalmnote...", flush=True)
    added = 0
    skipped = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process_single_psalmnote, it, existing_lower_files): it for it in songs_to_fetch}
        for fut in as_completed(futures):
            try:
                status, info = fut.result()
                if status == "added":
                    added += 1
                    existing_lower_files.add(info.lower())
                    if added % 50 == 0 or added == len(songs_to_fetch):
                        total_now = len(existing_lower_files)
                        print(f"  [Progress] +{added} lagu baru berhasil ditambahkan (Total Database: {total_now} lagu)...", flush=True)
                elif status == "skipped":
                    skipped += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1

    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {added} lagu baru | Dilewati: {skipped} | Gagal: {errors}")
    print(f"Total Database Saat Ini: {len(os.listdir(TXT_DIR))} lagu")
    print("==============================================================================")

if __name__ == "__main__":
    main()
