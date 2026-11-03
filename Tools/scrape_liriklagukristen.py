import os
import re
import sys
import ssl
import time
import urllib.request
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
    return (text.replace('’', "'")
                .replace('‘', "'")
                .replace('“', '"')
                .replace('”', '"')
                .replace('â€™', "'")
                .replace('â€˜', "'")
                .replace('â€œ', '"')
                .replace('â€', '"'))

def fetch_url(url, timeout=12, max_retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(0.5 + attempt * 0.5)
            else:
                return None
    return None

def parse_song_page(html):
    if not html:
        return None
    lyrics_match = re.search(r'<div class="lyrics">(.*?)</div>\s*</article>', html, re.DOTALL)
    if not lyrics_match:
        return None
    raw_lyrics_html = lyrics_match.group(1)
    if "lyrics-empty" in raw_lyrics_html or "Lirik untuk lagu ini belum tersedia" in raw_lyrics_html:
        return None

    # Title from H1
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html)
    if not h1:
        return None
    raw_title = unescape(h1.group(1)).strip()
    raw_title = clean_text_quotes(raw_title)
    # Strip numbered prefixes like "1. ", "01. "
    raw_title = re.sub(r'^\d+[\.\-\s]+', '', raw_title).strip()

    title = raw_title
    artist = ""

    # Check if artist embedded in title
    if " - " in title:
        parts = title.split(" - ", 1)
        title = parts[0].strip()
        artist = parts[1].strip()

    # Look inside raw_lyrics_html for explicit artist mentions
    meta_m = re.search(r'(?:Penyanyi|Artist|Dipopulerkan oleh|Vokal|Ciptaan|Cipt\.)\s*[:\-]\s*([^\n<]+)', raw_lyrics_html, re.IGNORECASE)
    if meta_m and not artist:
        cand_artist = unescape(meta_m.group(1)).strip()
        cand_artist = clean_text_quotes(cand_artist)
        if 2 <= len(cand_artist) <= 50 and not any(k in cand_artist.lower() for k in ["http", "www", "youtube"]):
            artist = cand_artist

    # Clean the lyrics HTML:
    cleaned_html = re.sub(r'<div class="yt-facade".*?</div>', '', raw_lyrics_html, flags=re.DOTALL)
    cleaned_html = re.sub(r'<(script|iframe|style|button)[^>]*>.*?</\1>', '', cleaned_html, flags=re.DOTALL)
    cleaned_html = re.sub(r'<p>\s*(?:Penyanyi|Artist|Dipopulerkan oleh|Vokal|Ciptaan|Cipt\.|Chord|Intro|Outro\s*:)[^\n<]*</p>', '', cleaned_html, flags=re.IGNORECASE)
    cleaned_html = re.sub(r'<p>\s*https?://[^\s<]+\s*</p>', '', cleaned_html)

    # Extract paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', cleaned_html, re.DOTALL)
    if not paragraphs:
        paragraphs = cleaned_html.split('<br><br>')

    sections = []
    verse_count = 0

    for p in paragraphs:
        p_text = re.sub(r'<br\s*/?>', '\n', p)
        p_text = re.sub(r'<[^>]+>', '', p_text)
        p_text = unescape(p_text).strip()
        p_text = clean_text_quotes(p_text)
        
        raw_lines = [l.strip() for l in p_text.splitlines() if l.strip()]
        if not raw_lines:
            continue

        first_line = raw_lines[0].upper()
        sec_header = None
        start_idx = 0

        if any(first_line.startswith(k) for k in ["VERSE", "BAIT", "CHORUS", "REFF", "BRIDGE", "PRE-CHORUS", "ENDING", "OUTRO"]):
            sec_header = raw_lines[0].replace(':', '').strip().upper()
            start_idx = 1
        elif "CHORUS" in first_line or "REFF" in first_line:
            sec_header = "CHORUS"
            start_idx = 1
        elif "BRIDGE" in first_line:
            sec_header = "BRIDGE"
            start_idx = 1

        body_lines = raw_lines[start_idx:]
        body_lines = [l for l in body_lines if not l.startswith("http") and not l.lower().startswith("chord") and len(l) > 1]
        if not body_lines:
            continue

        if not sec_header:
            verse_count += 1
            sec_header = f"VERSE {verse_count}"

        # Group lines into 2 per slide
        slides = []
        for i in range(0, len(body_lines), 2):
            chunk = body_lines[i:i+2]
            slides.append("\n".join(chunk))

        if slides:
            sections.append((sec_header, slides))

    if not sections or sum(len(s[1]) for s in sections) < 2:
        return None

    return title, artist, sections

def process_single_song_url(url, existing_lower_files):
    html = fetch_url(url)
    res = parse_song_page(html)
    if not res:
        return "skipped", "Empty or invalid lyrics"

    title, artist, sections = res
    # Aturan bank: artis tidak diketahui -> nama file = judul saja.
    core = f"{title} - {artist}" if artist else title
    filename = sanitize_filename(core) + ".txt"

    if filename.lower() in existing_lower_files:
        return "skipped", filename

    out_lines = ["BLANK", core, ""]
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

def collect_existing_files(root):
    """Kumpulkan SEMUA nama file .txt secara rekursif (root + subfolder) -> cegah duplikat."""
    names = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".txt"):
                names.add(fn.lower())
    return names

def collect_existing_titles(root):
    """Kumpulkan judul lagu (bagian sebelum ' - ') secara rekursif -> cegah duplikat judul."""
    titles = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".txt"):
                stem = os.path.splitext(fn)[0]
                if " - " in stem:
                    titles.add(stem.split(" - ", 1)[0].strip().lower())
    return titles

def main():
    print("==============================================================================")
    print("  LIRIKLAGUKRISTEN.ID SCRAPER (TARGET: MENEMBUS > 10.000 LAGU)")
    print("==============================================================================")

    # 1. Fetch sitemap URLs
    sitemap_url = "https://liriklagukristen.id/sitemap-0.xml"
    print(f"[1/3] Mengambil sitemap dari {sitemap_url}...", flush=True)
    xml = fetch_url(sitemap_url)
    if not xml:
        print("[ERROR] Gagal mengunduh sitemap!")
        return

    urls = re.findall(r'<loc>([^<]+)</loc>', xml)
    song_urls = [u for u in urls if not u.endswith('.id/') and not '/page/' in u and not '/category/' in u and not '/tag/' in u]
    print(f"  -> Ditemukan {len(song_urls)} link lagu.", flush=True)

    # 2. Existing database (REKURSIF: root + seluruh subfolder, by nama file & judul)
    existing_lower_files = collect_existing_files(TXT_DIR)
    existing_titles = collect_existing_titles(TXT_DIR)
    current_count = len(existing_lower_files)
    print(f"[2/3] Database lokal saat ini: {current_count} lagu (semua folder).", flush=True)

    # Filter URL yang judulnya sudah ada di database
    def url_title(url):
        slug = url.rstrip('/').split('/')[-1]
        t = unescape(slug).replace('-', ' ').strip().lower()
        return re.sub(r'^\d+[\.\-\s]+', '', t)

    song_urls = [u for u in song_urls if url_title(u) not in existing_titles]
    print(f"  -> Sisa URL yang belum ada judulnya di database: {len(song_urls)}", flush=True)

    # 3. Parallel scraping
    print(f"\n[3/3] Mulai mengunduh dan menyaring lagu secara paralel (12 workers)...", flush=True)
    added = 0
    skipped = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(process_single_song_url, u, existing_lower_files): u for u in song_urls}
        for fut in as_completed(futures):
            try:
                status, info = fut.result()
                if status == "added":
                    added += 1
                    existing_lower_files.add(info.lower())
                    total_now = len(existing_lower_files)
                    if added % 50 == 0:
                        print(f"  [Progress] +{added} lagu baru berhasil ditambahkan (Total Database: {total_now} lagu)...", flush=True)
                elif status == "skipped":
                    skipped += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1

    final_count = len(collect_existing_files(TXT_DIR))
    print("\n==============================================================================")
    print(f"SELESAI! Ditambahkan: {added} lagu baru | Dilewati: {skipped} | Gagal: {errors}")
    print(f"Total Database Saat Ini: {final_count} lagu (semua folder)")
    print("==============================================================================")

if __name__ == "__main__":
    main()
