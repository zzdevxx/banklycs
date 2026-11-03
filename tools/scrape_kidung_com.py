import os
import re
import sys
import ssl
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from kidung_parser import parse_kidung_content, clean_song_title_and_artist, sanitize_filename

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "TXT")

def fetch_url(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.read().decode("cp1252", errors="ignore")
    except Exception as e:
        return None

def get_page_song_links(page_num):
    url = f"https://www.kidung.com/page/{page_num}/" if page_num > 1 else "https://www.kidung.com/"
    html = fetch_url(url)
    if not html:
        return []
    # Find all h2.entry-title
    articles = re.findall(r'<h2 class="entry-title"[^>]*><a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', html)
    results = []
    for href, raw_title in articles:
        title, artist = clean_song_title_and_artist(raw_title)
        if title and artist:
            results.append((href, title, artist))
    return results

def process_single_song(item, existing_lower_files):
    href, title, artist = item
    fname_base = f"{title} - {artist}"
    fname_clean = sanitize_filename(fname_base) + ".txt"
    
    if fname_clean.lower() in existing_lower_files:
        return "skipped", fname_clean, "Already exists"
        
    html = fetch_url(href)
    if not html:
        return "error", fname_clean, "Failed to load page"
        
    content_m = re.search(r'<div class="entry-content"[^>]*>(.*?)(?:<div class="sharedaddy|<div class="post-meta|<footer|$)', html, re.DOTALL)
    if not content_m:
        return "error", fname_clean, "No entry-content"
        
    raw_content = content_m.group(1)
    sections = parse_kidung_content(raw_content)
    if not sections:
        return "error", fname_clean, "No parsed sections"
        
    out_lines = ["BLANK", f"{title} - {artist}", ""]
    for sec_name, slides in sections:
        out_lines.append(sec_name)
        for s in slides:
            out_lines.append(s)
            out_lines.append("")
            
    content = "\n".join(out_lines).strip() + "\n"
    if len(content) < 100:
        return "error", fname_clean, "Content too short"
        
    fpath = os.path.join(TXT_DIR, fname_clean)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return "added", fname_clean, "OK"

def scrape_kidung_range(start_page=1, end_page=50, max_workers=10):
    existing_lower_files = set(f.lower() for f in os.listdir(TXT_DIR))
    print(f"[KIDUNG.COM] Mengambil daftar lagu dari halaman {start_page} s/d {end_page}...", flush=True)
    
    all_items = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_page = {pool.submit(get_page_song_links, p): p for p in range(start_page, end_page + 1)}
        for fut in as_completed(future_to_page):
            p = future_to_page[fut]
            try:
                links = fut.result()
                all_items.extend(links)
            except Exception as e:
                print(f"  [WARN] Gagal baca page {p}: {e}")
                
    print(f"[KIDUNG.COM] Ditemukan {len(all_items)} lagu potensial dari halaman {start_page}-{end_page}.", flush=True)
    
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_song = {pool.submit(process_single_song, it, existing_lower_files): it for it in all_items}
        for fut in as_completed(future_to_song):
            try:
                status, fname, msg = fut.result()
                if status == "added":
                    added_count += 1
                    existing_lower_files.add(fname.lower())
                    print(f"  [+] Ditambahkan: {fname}", flush=True)
                elif status == "skipped":
                    skipped_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                
    print(f"\n[KIDUNG.COM] Halaman {start_page}-{end_page} Selesai: +{added_count} lagu baru | Dilewati: {skipped_count} | Gagal: {error_count}", flush=True)
    return added_count

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    scrape_kidung_range(start, end)
