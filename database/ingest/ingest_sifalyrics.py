#!/usr/bin/env python3
"""Ingest sifalyrics.com song pages (curated popular-artist subset) into banklycs.db.

Input: %TEMP%/sifa_songs/*.html. Output: BL lyric format, category EN only
(non-English lyrics are skipped — Indonesian coverage comes from other sources).
Sections are unlabeled <p> blocks; repeated blocks become CHORUS.
"""
import glob
import html
import os
import re
import sqlite3
import sys
import unicodedata

DB = os.path.join(os.path.dirname(__file__), '..', 'banklycs.db')
TMP = os.environ.get('TEMP', r'C:\Users\andre\AppData\Local\Temp')

EN_WORDS = {'the', 'and', 'you', 'my', 'lord', 'god', 'jesus', 'christ', 'is', 'of', 'in',
            'your', 'we', 'our', 'he', 'his', 'with', 'for', 'to', 'love', 'holy', 'king',
            'heart', 'soul', 'praise', 'worship', 'glory', 'name', 'forever', 'grace',
            'savior', 'spirit', 'heaven', 'faith', 'sing', 'alive'}


def clean(s: str) -> str:
    s = html.unescape(s)
    s = s.replace('\ufffd', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_title(s: str) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    return re.sub(r'[^a-z0-9]', '', s)


def block_key(lines) -> str:
    return norm_title(' '.join(lines))


def parse_song(path: str):
    raw = open(path, 'rb').read()
    try:
        h = raw.decode('utf-8')
    except UnicodeDecodeError:
        h = raw.decode('cp1252', 'replace')
    t = re.search(r'<title>(.*?)</title>', h)
    if not t:
        return None
    tp = clean(t.group(1))  # "Song Title Lyrics - Artist Name"
    m = re.match(r'^(.*?)\s+Lyrics\s+-\s+(.+?)\s*$', tp)
    if not m:
        return None
    title, artist = m.group(1).strip(), m.group(2).strip()

    i = h.find('class="lyrics-text"')
    if i < 0:
        return None
    j = h.find('lyrics-review', i)
    if j < 0:
        j = len(h)
    blob = h[i:j]

    blocks = []
    for pm in re.finditer(r'<p>(.*?)</p>', blob, re.S):
        raw_lines = re.split(r'<br\s*/?>', pm.group(1))
        lines = [clean(re.sub(r'<[^>]+>', ' ', l)) for l in raw_lines]
        lines = [l for l in lines if l]
        if lines:
            blocks.append(lines)
    if not blocks:
        return None

    # bahasa: EN saja
    text = ' '.join(l for b in blocks for l in b).lower()
    tokens = set(re.findall(r"[a-z']+", text))
    if len(tokens & EN_WORDS) < 4:
        return None

    # seksi: blok pertama = VERSE 1; blok identik dengan blok sebelumnya = CHORUS
    sections, seen_keys = [], {}
    verse_no = 0
    for b in blocks:
        k = block_key(b)
        if k in seen_keys and len(k) > 8:
            sections.append(('CHORUS', b))
        else:
            verse_no += 1
            sections.append((f'VERSE {verse_no}', b))
            seen_keys[k] = True

    bl = []
    for header, lines in sections:
        bl.append(header)
        bl.extend(lines)
        bl.append('')
    return title, artist, '\n'.join(bl).strip() + '\n'


def main():
    dry = '--dry' in sys.argv
    conn = sqlite3.connect(os.path.abspath(DB))
    existing = {}
    for fid, title in conn.execute("SELECT id, title FROM songs"):
        existing.setdefault(norm_title(title), fid)

    fresh, dup_db, skipped = [], 0, 0
    seen = set()
    for f in sorted(glob.glob(TMP + r'\sifa_songs\*.html')):
        r = parse_song(f)
        if not r:
            skipped += 1
            continue
        title, artist, bl = r
        key = norm_title(title)
        if key in existing or key in seen:
            dup_db += 1
            continue
        seen.add(key)
        fresh.append((title, artist, bl))

    print(f'fresh: {len(fresh)} | dup-vs-DB: {dup_db} | skip/bukan-EN: {skipped}')
    if dry:
        for title, artist, bl in fresh[:3]:
            print(f'\n=== {title} ({artist}) ===')
            print(bl[:400])
        return

    added = 0
    for title, artist, bl in fresh:
        artist_disp = artist or 'Unknown Artist'
        fname = f'{title} - {artist_disp}.txt'
        try:
            conn.execute(
                'INSERT INTO songs (filename, title, artist, category, content) VALUES (?,?,?,?,?)',
                (fname, title, artist_disp, 'EN', bl))
            added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    total = conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0]
    print(f'INSERTED: {added} | total DB: {total}')


if __name__ == '__main__':
    main()
