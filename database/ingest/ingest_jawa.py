#!/usr/bin/env python3
"""Ingest Kidung Pasamuwan Jawi (KPJ) + Kidung Pasamuwan Kristen (KPK)
from the lirik-kpk.blogspot.com Atom feed dumps into banklycs.db.

Feed XML files are fetched beforehand (curl) into %TEMP%/feed_*.xml.
Output: BL lyric format (VERSE n / CHORUS headers, blank-line slide breaks).
Category = JAWA; artist = "KPJ 001" / "KPK 001" (collection + number).
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

ATTRIB_RE = re.compile(r"^\(?\s*kidung pasamuwan", re.I)
JUNK_RE = re.compile(
    r"^(sumber|diposkan|dibaca|label|posting|kirim|bagikan|email|entri|"
    r"langganan|dapatkan|download|unduh|https?://|www\.|share to|"
    r"lirik (kpj|kpk|pujian jawa)|oleh\s)", re.I)
VERSE_RE = re.compile(r"^(\d{1,2})[.\s]+(\S.*)$")
NUM_ONLY_RE = re.compile(r"^\d{1,3}[.\s]*$")
REFF_ALONE_RE = re.compile(r"^reff[\s.:\-]*$", re.I)
REFF_LEAD_RE = re.compile(r"^reff[\s.:\-]*(\S.*)$", re.I)
SPACES_RE = re.compile(r"\s+")


def clean_line(raw: str) -> str:
    s = raw
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ")
    s = html.unescape(s)
    s = SPACES_RE.sub(" ", s).strip()
    # hapus bullet/asterisk sisipan
    s = s.strip("*•·").strip()
    return s


def title_case_jawa(s: str) -> str:
    s = s.strip().rstrip(".,")
    words = s.split()
    out = []
    for w in words:
        out.append(w if len(w) <= 2 and w.islower() or "." in w else w.capitalize())
    return " ".join(out) if out else s


def parse_content(content: str):
    """Return list of (header, [lines]) sections in BL format.

    Marker "\x01REFF\x01" di akhir section berarti chorus diulang di titik itu.
    """
    body = re.sub(r"^<div[^>]*>", "", content.strip())
    body = re.sub(r"</div>\s*$", "", body)
    lines = [clean_line(l) for l in body.split("<br />")]

    sections = []  # [header, lines]
    cur_header, cur_lines = "VERSE 1", []
    reff_pending = False  # marker Reff menunggu dikonfirmasi sebagai repeat

    def flush():
        nonlocal cur_lines
        if cur_lines:
            sections.append([cur_header, list(cur_lines)])
            cur_lines = []

    for ln in lines:
        if not ln:
            continue
        if ATTRIB_RE.match(ln) or JUNK_RE.match(ln):
            continue
        if REFF_ALONE_RE.match(ln):
            flush()
            reff_pending = True
            cur_header = "CHORUS"
            continue
        m = REFF_LEAD_RE.match(ln)
        if m:
            flush()
            reff_pending = True
            cur_header = "CHORUS"
            rest = clean_line(m.group(1))
            if rest and not REFF_ALONE_RE.match(rest):
                cur_lines.append(rest)
            continue
        m = VERSE_RE.match(ln)
        if m and not NUM_ONLY_RE.match(ln):
            num, rest = int(m.group(1)), clean_line(m.group(2))
            if not sections and not cur_lines:
                # baris pertama konten "14. JUDUL" = nomor lagu, bukan verse
                continue
            if cur_header == "CHORUS" and not cur_lines and reff_pending and sections:
                # Reff menyendiri tanpa isi lalu langsung verse = pengulangan
                sections[-1][1].append("\x01REFF\x01")
            flush()
            reff_pending = False
            cur_header = f"VERSE {num}"
            if rest and not REFF_ALONE_RE.match(rest):
                cur_lines.append(rest)
            continue
        cur_lines.append(ln)
    flush()
    return sections


def inline_reffs(sections):
    """Ganti marker repeat + 'Reff' menyendiri di tengah verse dengan isi chorus."""
    chorus = next((s for s in sections if s[0] == "CHORUS" and s[1]), None)
    if not chorus:
        return [[h, [l for l in ls if l != "\x01REFF\x01"]] for h, ls in sections]
    out = []
    for header, lines in sections:
        if header == "CHORUS":
            out.append([header, lines])
            continue
        chunk = []
        for ln in lines:
            if ln == "\x01REFF\x01" or REFF_ALONE_RE.match(ln) or REFF_LEAD_RE.match(ln):
                if chunk:
                    out.append([header, chunk])
                    chunk = []
                out.append(["CHORUS", list(chorus[1])])
            else:
                chunk.append(ln)
        if chunk:
            out.append([header, chunk])
    return out


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def extract(entry_title, content):
    """Return (title, sections) or None if the entry is not a song post."""
    t = entry_title.strip()
    content_flat = clean_line(content)
    m = re.match(r"^KPK\s*(\d+)[.\s]*$", t)
    if m:
        # judul lagu = baris pertama konten (biasanya di <b>); konten utuh
        # diparse terpisah, lalu baris judul dibuang lewat post-pass
        nonempty = [l for l in (clean_line(x) for x in re.split(r"<br\s*/?>", content)) if l]
        if not nonempty:
            return None
        title = title_case_jawa(nonempty[0])
        num = int(m.group(1))
        return (title, num, "KPK", parse_content(content))
    m = re.match(r"^(\d{1,3})[.\s]\s*(.+)$", t)
    if m:
        num = int(m.group(1))
        title = title_case_jawa(m.group(2))
        return (title, num, "KPJ", parse_content(content))
    return None


def to_bl(sections) -> str:
    parts = []
    for header, lines in sections:
        parts.append(header)
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def main():
    dry = "--dry" in sys.argv
    conn = sqlite3.connect(os.path.abspath(DB))
    existing = {}
    for fid, title in conn.execute("SELECT id, title FROM songs"):
        existing.setdefault(norm_title(title), fid)

    entries = []
    for f in sorted(glob.glob(TMP + r"\feed_*.xml")):
        x = open(f, encoding="utf-8").read()
        for e in re.findall(r"<entry>(.*?)</entry>", x, re.S):
            t = re.search(r"<title type='text'>(.*?)</title>", e, re.S)
            c = re.search(r"<content type='html'>(.*?)</content>", e, re.S)
            if t and c:
                entries.append((html.unescape(t.group(1).strip()), html.unescape(c.group(1))))

    parsed, skipped_meta = [], 0
    for t, c in entries:
        r = extract(t, c)
        if r:
            title, num, coll, sections = r
            sections = inline_reffs(sections)
            # buang baris yang isinya sama dengan judul (header blog ikut
            # terbawa di awal konten)
            tkey = norm_title(title)
            def not_title(l):
                stripped = re.sub(r"^\d{1,3}[.\s]*", "", l)
                return norm_title(l) != tkey and norm_title(stripped) != tkey
            sections = [[h, [l for l in ls if not_title(l)]] for h, ls in sections]
            sections = [[h, ls] for h, ls in sections if ls]
            if sections:
                parsed.append((title, num, coll, to_bl(sections)))
        else:
            skipped_meta += 1

    # dedupe dalam batch + vs DB
    seen, fresh, dup_db, dup_batch = set(), [], 0, 0
    for title, num, coll, bl in parsed:
        key = norm_title(title)
        if key in existing:
            dup_db += 1
            continue
        if key in seen:
            dup_batch += 1
            continue
        seen.add(key)
        fresh.append((title, num, coll, bl))

    print(f"entries: {len(entries)} | meta/skip: {skipped_meta} | parsed: {len(parsed)}")
    print(f"fresh: {len(fresh)} | dup-vs-DB: {dup_db} | dup-in-batch: {dup_batch}")
    from collections import Counter
    print("per koleksi:", dict(Counter(c for _, _, c, _ in fresh)))

    if dry:
        for title, num, coll, bl in fresh[:3]:
            print("\n=== SAMPLE:", title, f"({coll} {num}) ===")
            print(bl[:500])
        return

    # hapus entry JAWA lama yang bukan lagu
    conn.execute("DELETE FROM songs WHERE category='JAWA' AND title='Kidung Pasamuwan Jawi'")
    added = 0
    for title, num, coll, bl in fresh:
        artist = f"{coll} {num:03d}"
        fname = f"{title} - {artist}.txt"
        try:
            conn.execute(
                "INSERT INTO songs (filename, title, artist, category, content) VALUES (?,?,?,?,?)",
                (fname, title, artist, "JAWA", bl))
            added += 1
        except sqlite3.IntegrityError:
            # filename bentrok: tambahkan suffix nomor
            fname2 = f"{title} ({coll} {num:03d}b) - {artist}.txt"
            conn.execute(
                "INSERT INTO songs (filename, title, artist, category, content) VALUES (?,?,?,?,?)",
                (fname2, title, artist, "JAWA", bl))
            added += 1
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    jawa = conn.execute("SELECT COUNT(*) FROM songs WHERE category='JAWA'").fetchone()[0]
    print(f"INSERTED: {added} | total DB: {total} | kategori JAWA: {jawa}")


if __name__ == "__main__":
    main()
