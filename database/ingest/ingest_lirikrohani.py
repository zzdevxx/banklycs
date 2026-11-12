#!/usr/bin/env python3
"""Ingest lirikrohani.com song pages into banklycs.db.

Input: %TEMP%/lr_songs/*.html (fetched beforehand).
Output: BL lyric format. Category ID/EN via stopword detection.
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

LABEL_MAP = {
    'verse': 'VERSE', 'chorus': 'CHORUS', 'reff': 'CHORUS', 'ref': 'CHORUS',
    'pre chorus': 'PRE-CHORUS', 'pre-chorus': 'PRE-CHORUS', 'prechorus': 'PRE-CHORUS',
    'bridge': 'BRIDGE', 'tag': 'TAG', 'ending': 'ENDING', 'outro': 'OUTRO',
    'intro': 'INTRO', 'interlude': 'INTERLUDE', 'vamp': 'VAMP',
}

ID_WORDS = {'yang', 'dan', 'di', 'ku', 'mu', 'nya', 'tuhan', 'yesus', 'kristus', 'allah',
            'dalam', 'bagi', 'dengan', 'akan', 'pada', 'untuk', 'dari', ' tidak', 'sudah',
            'aku', 'kami', 'kita', 'engkau', 'hatiku', 'jiwaku', 'hidupku', 'sgala',
            'bapa', 'roh', 'kudus', 'puji', 'pujian', 'sembah', 'penyembahan', 'surga',
            'dosaku', 'kasih', 'ampuni', 'slamat', 'selamat', 'besar', 'mulia', 'suci'}
EN_WORDS = {'the', 'and', 'you', 'my', 'lord', 'god', 'jesus', 'christ', 'is', 'of', 'in',
            'your', 'we', 'our', 'he', 'his', 'with', 'for', 'to', 'love', 'holy', 'king',
            'heart', 'soul', 'praise', 'worship', 'glory', 'name', 'forever', 'grace'}


def clean(s: str) -> str:
    s = html.unescape(s)
    s = s.replace('\ufffd', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_title(s: str) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    return re.sub(r'[^a-z0-9]', '', s)


def parse_song(path: str):
    raw = open(path, 'rb').read()
    try:
        h = raw.decode('utf-8')
    except UnicodeDecodeError:
        h = raw.decode('cp1252', 'replace')
    t = re.search(r'<title>(.*?)</title>', h)
    if not t:
        return None
    title_page = clean(t.group(1))  # "Lirik X (Artist) | Lirik Rohani"
    m = re.match(r'^Lirik\s+(.*?)\s*(?:\(([^)]*)\))?\s*\|\s*Lirik Rohani\s*$', title_page)
    title = m.group(1).strip() if m else title_page.split('|')[0].replace('Lirik', '', 1).strip()
    artist = ''
    m2 = re.search(r'Penyanyi</dt>\s*<dd[^>]*>\s*(.*?)\s*</dd>', h, re.S)
    if m2:
        artist = clean(m2.group(1))
    if not artist and m and m.group(2):
        artist = m.group(2).strip()

    sections = []
    verse_no = 0
    for sec in re.finditer(r'<section([^>]*)>(.*?)</section>', h, re.S):
        attrs, body = sec.group(1), sec.group(2)
        lines = [clean(x) for x in re.findall(r'<p>(.*?)</p>', body, re.S)]
        lines = [l for l in lines if l]
        if not lines:
            continue
        lm = re.search(r'<p class="label">([^<]*)</p>', body)
        if lm:
            label = clean(lm.group(1)).lower()
            words = label.split()
            base = ' '.join(w for w in words if not w.isdigit())
            num = next((w for w in words if w.isdigit()), '')
            header = LABEL_MAP.get(base)
            if not header:
                continue
            if num:
                header = f'{header} {int(num)}'
        elif 'class="reff"' in attrs or 'reff' in attrs:
            header = 'CHORUS'
        else:
            # himne liturgis: section tanpa label = satu bait
            verse_no += 1
            header = f'VERSE {verse_no}'
        sections.append((header, lines))

    if not sections or not title:
        return None

    # bahasa
    text = ' '.join(l for _, ls in sections for l in ls).lower()
    tokens = set(re.findall(r"[a-z']+", text))
    id_score = len(tokens & ID_WORDS)
    en_score = len(tokens & EN_WORDS)
    lang = 'EN' if en_score > id_score else 'ID'

    bl = []
    for header, lines in sections:
        bl.append(header)
        bl.extend(lines)
        bl.append('')
    return title, artist, lang, '\n'.join(bl).strip() + '\n'


def main():
    dry = '--dry' in sys.argv
    conn = sqlite3.connect(os.path.abspath(DB))
    existing = {}
    for fid, title in conn.execute("SELECT id, title FROM songs"):
        existing.setdefault(norm_title(title), fid)

    fresh, dup_db, bad = [], 0, 0
    seen = set()
    for f in sorted(glob.glob(TMP + r'\lr_songs\*.html')):
        r = parse_song(f)
        if not r:
            bad += 1
            continue
        title, artist, lang, bl = r
        key = norm_title(title)
        if key in existing or key in seen:
            dup_db += 1
            continue
        seen.add(key)
        fresh.append((title, artist, lang, bl))

    from collections import Counter
    print(f'parsed: {len(fresh) + dup_db + bad} | fresh: {len(fresh)} | dup-vs-DB: {dup_db} | gagal: {bad}')
    print('bahasa:', dict(Counter(l for _, _, l, _ in fresh)))

    if dry:
        for title, artist, lang, bl in fresh[:3]:
            print(f'\n=== {title} ({artist}) [{lang}] ===')
            print(bl[:400])
        return

    added = 0
    for title, artist, lang, bl in fresh:
        artist_disp = artist or 'Lirik Rohani'
        fname = f'{title} - {artist_disp}.txt'
        try:
            conn.execute(
                'INSERT INTO songs (filename, title, artist, category, content) VALUES (?,?,?,?,?)',
                (fname, title, artist_disp, lang, bl))
            added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    total = conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0]
    print(f'INSERTED: {added} | total DB: {total}')


if __name__ == '__main__':
    main()
