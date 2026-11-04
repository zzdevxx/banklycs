import os
import sys
import sqlite3
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(BASE_DIR, "database", "banklycs.db")

if not os.path.exists(DB_PATH):
    print(f"[FATAL] Database not found: {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
cur = conn.cursor()

header_regex = re.compile(
    r"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$",
    re.IGNORECASE
)

cur.execute("SELECT id, filename, content FROM songs ORDER BY id;")
rows = cur.fetchall()

empty_content = []
bad_first_line = []
overflow_slides = []
line2_mismatch = []

for sid, fname, content in rows:
    if not content or not content.strip():
        empty_content.append(fname)
        continue
    lines = [l.strip() for l in content.splitlines()]
    if not lines or lines[0].upper() != "BLANK":
        bad_first_line.append(fname)

    base_name = fname[:-4] if fname.endswith(".txt") else fname
    if len(lines) >= 2 and lines[1] != base_name:
        line2_mismatch.append((fname, lines[1]))

    curr_slide = []
    for line in lines:
        if header_regex.match(line) or not line:
            if len(curr_slide) > 2:
                overflow_slides.append(fname)
                break
            curr_slide = []
        else:
            curr_slide.append(line)
    if len(curr_slide) > 2:
        overflow_slides.append(fname)

print("==============================================================================")
print(f"VERIFY SONGS AUDIT (TOTAL: {len(rows):,} SONGS IN SQLITE)")
print("==============================================================================")
print(f"  * Empty content           : {len(empty_content)}")
print(f"  * Bad first line != BLANK : {len(bad_first_line)}")
print(f"  * Line 2 != filename base : {len(line2_mismatch)}")
print(f"  * Overflow slides (>2 lines): {len(overflow_slides)}")

if not empty_content and not bad_first_line and not line2_mismatch and not overflow_slides:
    print("  -> STATUS: 100% MEMENUHI GOLDEN RULES PANGGUNG!")
else:
    print("  -> STATUS: Terdapat pelanggaran format.")

conn.close()
