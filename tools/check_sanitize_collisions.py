"""Report catalog filenames that the engine's SanitizeDiskFileName would rewrite.

A rewrite means the SQLite lookup key and the ProPresenter Banks filename diverge,
which used to surface as spurious `missing_in_pro` entries after INJECT.
Read-only diagnostic; run from the repo root: python tools/check_sanitize_collisions.py
"""

import sqlite3
import sys

DB = "database/banklycs.db"
DROPPED = '"?:*<>'
REPLACED = ":/\\|"


def sanitize(name: str) -> str:
    out = []
    for ch in name:
        if ch in DROPPED:
            continue
        out.append(" - " if ch in REPLACED else ch)
    return " ".join("".join(out).split()).strip("- ")


def main() -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = [r[0] for r in conn.execute("select filename from songs")]
    conn.close()

    rewritten = [f for f in rows if sanitize(f[:-4]) + ".txt" != f]
    print(f"total songs: {len(rows)}")
    print(f"filenames rewritten by sanitize: {len(rewritten)}")
    for f in rewritten[:20]:
        print(f"  {f!r} -> {sanitize(f[:-4]) + '.txt'!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())