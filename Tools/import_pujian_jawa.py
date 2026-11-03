import os
import re
import sys
import json
import urllib.request
import ssl

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
    small_words = {'lan', 'ing', 'mring', 'kang', 'iku', 'iku', 'dening', 'saking', 'ora', 'ora', 'sing'}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small_words:
            out.append(lw)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def main():
    print("==================================================")
    print("IMPORT LAGU PUJIAN ROHANI JAWA")
    print("==================================================")
    url = "https://pujianjawa.blogspot.com/feeds/posts/default?alt=json&max-results=50"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=8).read().decode('utf-8'))
    entries = data.get('feed', {}).get('entry', [])
    
    existing = set(f.lower() for f in os.listdir(TXT_DIR))
    added = 0

    for e in entries:
        raw_title = e.get('title', {}).get('$t', '').strip()
        title = to_title_case(raw_title)
        artist = "Lagu Rohani Jawa"
        filename = sanitize_filename(f"{title} - {artist}") + ".txt"

        if filename.lower() in existing:
            print(f"  [SKIP] Already exists: {filename}")
            continue

        content_html = e.get('content', {}).get('$t', '')
        # Replace <br> and <p> with newline
        clean_text = re.sub(r'<br\s*/?>', '\n', content_html)
        clean_text = re.sub(r'</p>', '\n', clean_text)
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        raw_lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
        # Remove trailing dots like "................"
        lines = []
        for l in raw_lines:
            l = re.sub(r'\.{2,}', '', l).strip()
            l = clean_text_quotes(l)
            if l:
                lines.append(l)

        if len(lines) < 4:
            continue

        # Chunk into slides of max 2 lines
        slides = []
        for i in range(0, len(lines), 2):
            slides.append("\n".join(lines[i:i+2]))

        out = ["BLANK", f"{title} - {artist}", "", "VERSE 1"]
        for s in slides:
            out.append(s)
            out.append("")

        file_content = "\n".join(out).strip() + "\n"
        fpath = os.path.join(TXT_DIR, filename)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(file_content)

        existing.add(filename.lower())
        added += 1
        print(f"  [+] Ditambahkan: {filename}")

    print(f"\nSelesai! Ditambahkan: {added} lagu rohani Jawa baru.")

if __name__ == "__main__":
    main()
