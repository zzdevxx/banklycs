#!/usr/bin/env python3
"""Adapter sumber lagu untuk Banklycs Scraper.

Tiap adapter menyediakan:
  discover(out)       -> tulis daftar URL halaman lagu ke file
  run(dir, dry, ...)  -> parse HTML di folder -> BL format -> insert DB

Adapter tersedia:
  sifalyrics     sifalyrics.com (sitemap per tahun, lirik <p> blok)
  lirikrohani    lirikrohani.com (index abjad, section berlabel)
  blogger-kpk    feed Blogger lirik-kpk.blogspot.com (KPJ/KPK Jawa)
"""
import glob
import html
import os
import re
import sqlite3
import sys
import unicodedata
import urllib.request
import concurrent.futures as cf

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'banklycs.db')
TMP = os.environ.get('TEMP', r'C:\Users\andre\AppData\Local\Temp')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) BanklycsCatalog/1.0'

# ------------------------------------------------------------------- util
HEADER_RE = re.compile(r'^(VERSE|CHORUS|BRIDGE|TAG|INTRO|OUTRO|BLANK)[^\n]*\n?', re.M)
EN_WORDS = {'the', 'and', 'you', 'my', 'lord', 'god', 'jesus', 'christ', 'is', 'of', 'in',
            'your', 'we', 'our', 'he', 'his', 'with', 'for', 'to', 'love', 'holy', 'king',
            'heart', 'soul', 'praise', 'worship', 'glory', 'name', 'forever', 'grace',
            'savior', 'spirit', 'heaven', 'faith', 'sing', 'alive'}
ID_WORDS = {'yang', 'dan', 'di', 'ku', 'mu', 'nya', 'tuhan', 'yesus', 'kristus', 'allah',
            'dalam', 'bagi', 'dengan', 'akan', 'pada', 'untuk', 'dari', 'tidak', 'sudah',
            'aku', 'kami', 'kita', 'engkau', 'hatiku', 'jiwaku', 'hidupku', 'sgala',
            'bapa', 'roh', 'kudus', 'puji', 'pujian', 'sembah', 'penyembahan', 'surga',
            'dosaku', 'kasih', 'ampuni', 'slamat', 'selamat', 'besar', 'mulia', 'suci'}


def clean(s: str) -> str:
    s = html.unescape(s)
    s = s.replace('\ufffd', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_title(s: str) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    return re.sub(r'[^a-z0-9]', '', s)


def detect_lang(text: str) -> str:
    tokens = set(re.findall(r"[a-z']+", text.lower()))
    return 'EN' if len(tokens & EN_WORDS) >= len(tokens & ID_WORDS) else 'ID'


def read_html(path: str) -> str:
    raw = open(path, 'rb').read()
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1252', 'replace')


def insert_songs(rows, dry=False):
    """rows: list of (title, artist, category, bl). Dedupe vs DB + dalam batch."""
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    existing = {}
    for fid, title in conn.execute('SELECT id, title FROM songs'):
        existing.setdefault(norm_title(title), fid)
    fresh, dup = [], 0
    seen = set()
    for title, artist, cat, bl in rows:
        key = norm_title(title)
        if key in existing or key in seen:
            dup += 1
            continue
        seen.add(key)
        fresh.append((title, artist, cat, bl))
    print(f'fresh: {len(fresh)} | dup-vs-DB/batch: {dup}')
    if dry:
        for r in fresh[:3]:
            print(f'\n=== {r[0]} ({r[1]}) [{r[2]}] ===')
            print(r[3][:400])
        return
    added = 0
    for title, artist, cat, bl in fresh:
        artist_disp = artist or 'Unknown Artist'
        try:
            conn.execute(
                'INSERT INTO songs (filename, title, artist, category, content) VALUES (?,?,?,?,?)',
                (f'{title} - {artist_disp}.txt', title, artist_disp, cat, bl))
            added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    total = conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0]
    print(f'INSERTED: {added} | total DB: {total}')


# --------------------------------------------------------- sifalyrics.com
class Sifalyrics:
    SITEMAP_YEARS = list(range(2026, 2009, -1))

    @staticmethod
    def discover(out):
        urls = set()
        for y in Sifalyrics.SITEMAP_YEARS:
            req = urllib.request.Request(f'https://sifalyrics.com/sitemap/{y}',
                                         headers={'User-Agent': UA})
            try:
                x = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
                urls.update(re.findall(r'<loc>(https://sifalyrics\.com/[^<]+-lyrics)</loc>', x))
                print(f'  {y}: {len(urls)} total', file=sys.stderr)
            except Exception as e:
                print(f'  {y}: gagal {e}', file=sys.stderr)
        open(out, 'w').write('\n'.join(sorted(urls)))
        print(f'{len(urls)} URL ditulis ke {out}')

    @staticmethod
    def run(html_dir, dry=False, source_name='sifalyrics'):
        rows, skipped = [], 0
        for f in sorted(glob.glob(os.path.join(html_dir, '*.html'))):
            r = Sifalyrics.parse_song(f)
            if r:
                rows.append(r)
            else:
                skipped += 1
        print(f'parsed: {len(rows)} | skip/bukan-EN: {skipped}')
        insert_songs(rows, dry=dry)

    @staticmethod
    def parse_song(path):
        h = read_html(path)
        t = re.search(r'<title>(.*?)</title>', h)
        if not t:
            return None
        m = re.match(r'^(.*?)\s+Lyrics\s+-\s+(.+?)\s*$', clean(t.group(1)))
        if not m:
            return None
        title, artist = m.group(1).strip(), m.group(2).strip()
        i = h.find('class="lyrics-text"')
        if i < 0:
            return None
        j = h.find('lyrics-review', i)
        blob = h[i:j if j > 0 else len(h)]
        blocks = []
        for pm in re.finditer(r'<p>(.*?)</p>', blob, re.S):
            lines = [clean(re.sub(r'<[^>]+>', ' ', l))
                     for l in re.split(r'<br\s*/?>', pm.group(1))]
            lines = [l for l in lines if l]
            if lines:
                blocks.append(lines)
        if not blocks:
            return None
        text = ' '.join(l for b in blocks for l in b)
        if detect_lang(text) != 'EN':
            return None
        sections, seen_keys, verse_no = [], set(), 0
        for b in blocks:
            k = norm_title(' '.join(b))
            if k in seen_keys and len(k) > 8:
                sections.append(('CHORUS', b))
            else:
                verse_no += 1
                sections.append((f'VERSE {verse_no}', b))
                seen_keys.add(k)
        bl = []
        for header, lines in sections:
            bl.append(header)
            bl.extend(lines)
            bl.append('')
        return title, artist, 'EN', '\n'.join(bl).strip() + '\n'


# -------------------------------------------------------- lirikrohani.com
class LirikRohani:
    BASE = 'https://lirikrohani.com'
    LABEL_MAP = {
        'verse': 'VERSE', 'chorus': 'CHORUS', 'reff': 'CHORUS', 'ref': 'CHORUS',
        'pre chorus': 'PRE-CHORUS', 'pre-chorus': 'PRE-CHORUS', 'prechorus': 'PRE-CHORUS',
        'bridge': 'BRIDGE', 'tag': 'TAG', 'ending': 'ENDING', 'outro': 'OUTRO',
        'intro': 'INTRO', 'interlude': 'INTERLUDE',
    }

    @staticmethod
    def discover(out):
        letters = list('abcdefghijklmnopqrstuvwxyz0123456789')
        tasks = [(l, p) for l in letters for p in range(1, 12)]
        urls = set()

        def fetch(lp):
            letter, page = lp
            u = f'{LirikRohani.BASE}/abjad/{letter}' + (f'?page={page}' if page > 1 else '')
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            try:
                h = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'replace')
                return re.findall(r'href="(/lagu/[^"]+)"', h)
            except Exception:
                return []

        with cf.ThreadPoolExecutor(8) as ex:
            for res in ex.map(fetch, tasks):
                urls.update(res)
        full = [LirikRohani.BASE + u for u in sorted(urls)]
        open(out, 'w').write('\n'.join(full))
        print(f'{len(full)} URL ditulis ke {out}')

    @staticmethod
    def run(html_dir, dry=False, source_name='lirikrohani'):
        rows, bad = [], 0
        for f in sorted(glob.glob(os.path.join(html_dir, '*.html'))):
            r = LirikRohani.parse_song(f)
            if r:
                rows.append(r)
            else:
                bad += 1
        print(f'parsed: {len(rows)} | gagal: {bad}')
        insert_songs(rows, dry=dry)

    @staticmethod
    def parse_song(path):
        h = read_html(path)
        t = re.search(r'<title>(.*?)</title>', h)
        if not t:
            return None
        tp = clean(t.group(1))
        m = re.match(r'^Lirik\s+(.*?)\s*(?:\(([^)]*)\))?\s*\|\s*Lirik Rohani\s*$', tp)
        if not m:
            return None
        title = m.group(1).strip()
        m2 = re.search(r'Penyanyi</dt>\s*<dd[^>]*>\s*(.*?)\s*</dd>', h, re.S)
        artist = clean(m2.group(1)) if m2 else (m.group(2) or '').strip()

        sections, verse_no = [], 0
        for sec in re.finditer(r'<section([^>]*)>(.*?)</section>', h, re.S):
            attrs, body = sec.group(1), sec.group(2)
            lines = [clean(x) for x in re.findall(r'<p>(.*?)</p>', body, re.S)]
            lines = [l for l in lines if l]
            if not lines:
                continue
            lm = re.search(r'<p class="label">([^<]*)</p>', body)
            if lm:
                words = clean(lm.group(1)).lower().split()
                base = ' '.join(w for w in words if not w.isdigit())
                num = next((w for w in words if w.isdigit()), '')
                header = LirikRohani.LABEL_MAP.get(base)
                if not header:
                    continue
                if num:
                    header = f'{header} {int(num)}'
            elif 'reff' in attrs:
                header = 'CHORUS'
            else:
                verse_no += 1
                header = f'VERSE {verse_no}'
            sections.append((header, lines))
        if not sections or not title:
            return None
        lang = detect_lang(' '.join(l for _, ls in sections for l in ls))
        bl = []
        for header, lines in sections:
            bl.append(header)
            bl.extend(lines)
            bl.append('')
        return title, artist, lang, '\n'.join(bl).strip() + '\n'


# ------------------------------------------------- blogger (KPJ/KPK Jawa)
class BloggerKpk:
    FEED = 'https://lirik-kpk.blogspot.com/feeds/posts/default'
    ATTRIB_RE = re.compile(r'^\(?\s*kidung pasamuwan', re.I)
    JUNK_RE = re.compile(
        r'^(sumber|diposkan|dibaca|label|posting|kirim|bagikan|email|entri|'
        r'langganan|dapatkan|download|unduh|https?://|www\.|share to|'
        r'lirik (kpj|kpk|pujian jawa)|oleh\s)', re.I)
    VERSE_RE = re.compile(r'^(\d{1,2})[.\s]+(\S.*)$')
    NUM_ONLY_RE = re.compile(r'^\d{1,3}[.\s]*$')
    REFF_ALONE_RE = re.compile(r'^reff[\s.:\-]*$', re.I)
    REFF_LEAD_RE = re.compile(r'^reff[\s.:\-]*(\S.*)$', re.I)

    @staticmethod
    def discover(out):
        urls, titles = [], []
        start = 1
        while True:
            u = f'{BloggerKpk.FEED}?max-results=100&start-index={start}'
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            try:
                x = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
            except Exception:
                break
            entries = re.findall(r'<entry>(.*?)</entry>', x, re.S)
            if not entries:
                break
            titles.extend(entries)
            start += 100
            time.sleep(0.5)
        # tulis judul entry (fetch feed sudah sekaligus konten; fetch per-entry
        # tidak diperlukan — parser membaca dump feed langsung)
        open(out, 'w').write(f'# feed entries: {len(titles)} (gunakan parse langsung)')
        print(f'{len(titles)} entri feed terbaca; konten feed disimpan otomatis saat parse')

    @staticmethod
    def run(html_dir=None, dry=False, source_name='blogger-kpk'):
        """Feed Blogger di-fetch langsung (tiap entry berisi konten penuh)."""
        entries = []
        start = 1
        while True:
            u = f'{BloggerKpk.FEED}?max-results=100&start-index={start}'
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            try:
                x = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
            except Exception:
                break
            found = re.findall(r'<entry>(.*?)</entry>', x, re.S)
            if not found:
                break
            entries.extend(found)
            start += 100
        print(f'entri feed: {len(entries)}')
        rows = []
        for e in entries:
            t = re.search(r"<title type='text'>(.*?)</title>", e, re.S)
            c = re.search(r"<content type='html'>(.*?)</content>", e, re.S)
            if not (t and c):
                continue
            r = BloggerKpk.extract(html.unescape(t.group(1).strip()),
                                   html.unescape(c.group(1)))
            if r:
                rows.append(r)
        insert_songs(rows, dry=dry)

    @staticmethod
    def extract(entry_title, content):
        t = entry_title.strip()
        m = re.match(r'^KPK\s*(\d+)[.\s]*$', t)
        if m:
            nonempty = [l for l in (clean(x) for x in re.split(r'<br\s*/?>', content)) if l]
            if not nonempty:
                return None
            title = nonempty[0].strip().rstrip('.,').title()
            sections = BloggerKpk.parse_content(content)
        else:
            m2 = re.match(r'^(\d{1,3})[.\s]\s*(.+)$', t)
            if not m2:
                return None
            title = m2.group(2).strip().rstrip('.,').title()
            sections = BloggerKpk.parse_content(content)
        sections = BloggerKpk.inline_reffs(sections)
        tkey = norm_title(title)

        def not_title(l):
            stripped = re.sub(r'^\d{1,3}[.\s]*', '', l)
            return norm_title(l) != tkey and norm_title(stripped) != tkey

        sections = [[h, [l for l in ls if not_title(l) and l != '\x01REFF\x01']]
                    for h, ls in sections]
        sections = [[h, ls] for h, ls in sections if ls]
        if not sections:
            return None
        bl = []
        for header, lines in sections:
            bl.append(header)
            bl.extend(lines)
            bl.append('')
        num = (m or re.match(r'^(\d{1,3})[.\s]', t)).group(1)
        coll = 'KPK' if m else 'KPJ'
        return title, f'{coll} {int(num):03d}', 'JAWA', '\n'.join(bl).strip() + '\n'

    @staticmethod
    def parse_content(content):
        body = re.sub(r'^<div[^>]*>', '', content.strip())
        body = re.sub(r'</div>\s*$', '', body)
        lines = [clean(l) for l in body.split('<br />')]
        sections, cur_header, cur_lines = [], 'VERSE 1', []
        reff_pending = False

        def flush():
            nonlocal cur_lines
            if cur_lines:
                sections.append([cur_header, list(cur_lines)])
                cur_lines = []

        for ln in lines:
            if not ln or BloggerKpk.ATTRIB_RE.match(ln) or BloggerKpk.JUNK_RE.match(ln):
                continue
            if BloggerKpk.REFF_ALONE_RE.match(ln):
                flush()
                reff_pending = True
                cur_header = 'CHORUS'
                continue
            m = BloggerKpk.REFF_LEAD_RE.match(ln)
            if m:
                flush()
                reff_pending = True
                cur_header = 'CHORUS'
                rest = clean(m.group(1))
                if rest and not BloggerKpk.REFF_ALONE_RE.match(rest):
                    cur_lines.append(rest)
                continue
            m = BloggerKpk.VERSE_RE.match(ln)
            if m and not BloggerKpk.NUM_ONLY_RE.match(ln):
                num, rest = int(m.group(1)), clean(m.group(2))
                if not sections and not cur_lines:
                    continue  # baris "14. JUDUL" = nomor lagu
                if cur_header == 'CHORUS' and not cur_lines and reff_pending and sections:
                    sections[-1][1].append('\x01REFF\x01')
                flush()
                reff_pending = False
                cur_header = f'VERSE {num}'
                if rest and not BloggerKpk.REFF_ALONE_RE.match(rest):
                    cur_lines.append(rest)
                continue
            cur_lines.append(ln)
        flush()
        return sections

    @staticmethod
    def inline_reffs(sections):
        chorus = next((s for s in sections if s[0] == 'CHORUS' and s[1]), None)
        if not chorus:
            return [[h, [l for l in ls if l != '\x01REFF\x01']] for h, ls in sections]
        out = []
        for header, lines in sections:
            if header == 'CHORUS':
                out.append([header, lines])
                continue
            chunk = []
            for ln in lines:
                if (ln == '\x01REFF\x01' or BloggerKpk.REFF_ALONE_RE.match(ln)
                        or BloggerKpk.REFF_LEAD_RE.match(ln)):
                    if chunk:
                        out.append([header, chunk])
                        chunk = []
                    out.append(['CHORUS', list(chorus[1])])
                else:
                    chunk.append(ln)
            if chunk:
                out.append([header, chunk])
        return out


ADAPTERS = {
    'sifalyrics': Sifalyrics,
    'lirikrohani': LirikRohani,
    'blogger-kpk': BloggerKpk,
}
