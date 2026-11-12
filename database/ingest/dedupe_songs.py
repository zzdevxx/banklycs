#!/usr/bin/env python3
"""Deduplicate banklycs.db songs.

Same normalized title + near-identical content = duplicate. The better copy
survives: more lyric lines wins, ties broken by chorus presence then lowest id.
"""
import difflib
import os
import re
import sqlite3
import sys
import unicodedata

DB = os.path.join(os.path.dirname(__file__), '..', 'banklycs.db')
HEADER_RE = re.compile(r'^(VERSE|CHORUS|BRIDGE|TAG|INTRO|OUTRO|BLANK)[^\n]*\n?', re.M)


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    return re.sub(r'[^a-z0-9]', '', s)


def body_sig(content: str) -> str:
    body = HEADER_RE.sub('', content)
    return re.sub(r'\s+', '', body.lower())


def quality(content: str):
    lines = [l for l in content.split('\n') if l.strip() and not HEADER_RE.match(l)]
    return (len(lines), bool(re.search(r'^CHORUS', content, re.M)), -1)


def main():
    dry = '--dry' in sys.argv
    conn = sqlite3.connect(os.path.abspath(DB))
    groups = {}
    for row in conn.execute("SELECT id, title, artist, category, content FROM songs"):
        groups.setdefault(norm(row[1]), []).append(row)

    to_delete = []
    removed_lines = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # kelompokkan per kemiripan isi (hash penuh dulu, lalu fuzzy)
        clusters = []
        for m in members:
            sig = body_sig(m[4])
            placed = False
            for cl in clusters:
                ref = cl[0]
                if sig == ref[5] or difflib.SequenceMatcher(None, sig, ref[5]).ratio() > 0.9:
                    cl.append(m + (sig,))
                    placed = True
                    break
            if not placed:
                clusters.append([m + (sig,)])
        for cl in clusters:
            if len(cl) < 2:
                continue
            best = max(cl, key=lambda m: (quality(m[4]), -m[0]))
            for m in cl:
                if m[0] != best[0]:
                    to_delete.append((m[0], m[1], m[2], best[1], best[2]))

    print(f"duplikat dihapus: {len(to_delete)}")
    for fid, title, artist, keep_title, keep_artist in to_delete[:10]:
        print(f"  - [{fid}] {title[:38]} ({artist})  <= keep {keep_title[:30]} ({keep_artist})")
    if dry:
        return
    for fid, *_ in to_delete:
        conn.execute("DELETE FROM songs WHERE id=?", (fid,))
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    print(f"total DB sekarang: {total}")


if __name__ == "__main__":
    main()
