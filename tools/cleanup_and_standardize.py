import os
import re
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "TXT")

def clean_song_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = [l.strip() for l in content.splitlines()]
    if not lines:
        return "empty", "Empty file"

    # Line 1 must be BLANK
    # Line 2 must be Title - Artist
    fname = os.path.basename(filepath)
    fname_no_ext = fname[:-4]

    title_line = fname_no_ext
    if len(lines) >= 2 and lines[0].upper() == "BLANK" and lines[1]:
        title_line = lines[1]

    # Delete if filename suggests an article / compilation / ad
    low_fname = fname_no_ext.lower()
    bad_patterns = [
        r'^\d+\+\s+lagu', r'^daftar\s+lagu', r'^\d+\s+lagu\s+rohani',
        r'kumpulan\s+lagu', r'chord\s+kunci', r'kunci\s+gitar',
        r'lirik\s+dan\s+kord', r'album\s+rohani'
    ]
    for bp in bad_patterns:
        if re.search(bp, low_fname):
            return "delete", f"Compilation/article page: {fname}"

    # Standardize headers:
    # REFF, REFFRAIN -> CHORUS
    # BAIT X -> VERSE X
    cleaned_lines = []
    for l in lines[2:]: # after header
        if not l:
            cleaned_lines.append("")
            continue
        up = l.upper()
        if up.startswith("REFF"):
            m = re.search(r'\d+', up)
            cleaned_lines.append(f"CHORUS {m.group(0)}" if m else "CHORUS")
        elif up.startswith("BAIT"):
            m = re.search(r'\d+', up)
            cleaned_lines.append(f"VERSE {m.group(0)}" if m else "VERSE 1")
        elif up in ["CHORUS:", "VERSE:", "BRIDGE:", "ENDING:", "INTRO:", "OUTRO:"]:
            cleaned_lines.append(up.replace(':', ''))
        else:
            cleaned_lines.append(l)

    # Re-structure into valid sections and strictly max 2 lines per slide
    header_regex = re.compile(r"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$", re.IGNORECASE)

    sections = []
    curr_header = "VERSE 1"
    curr_slides = []
    curr_slide_lines = []

    for l in cleaned_lines:
        if header_regex.match(l):
            if curr_slide_lines:
                for i in range(0, len(curr_slide_lines), 2):
                    curr_slides.append("\n".join(curr_slide_lines[i:i+2]))
                curr_slide_lines = []
            if curr_slides:
                sections.append((curr_header, curr_slides))
                curr_slides = []
            curr_header = l.upper()
        elif not l:
            if curr_slide_lines:
                for i in range(0, len(curr_slide_lines), 2):
                    curr_slides.append("\n".join(curr_slide_lines[i:i+2]))
                curr_slide_lines = []
        else:
            curr_slide_lines.append(l)

    if curr_slide_lines:
        for i in range(0, len(curr_slide_lines), 2):
            curr_slides.append("\n".join(curr_slide_lines[i:i+2]))
    if curr_slides:
        sections.append((curr_header, curr_slides))

    # Total slides
    total_slides = sum(len(s[1]) for s in sections)
    if total_slides < 1:
        return "too_short", f"Only {total_slides} slides"

    # Rebuild file strictly conforming to ProPresenter standard
    out = ["BLANK", title_line, ""]
    for s_hdr, slides in sections:
        out.append(s_hdr)
        for s in slides:
            out.append(s)
            out.append("")

    new_content = "\n".join(out).strip() + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return "updated", "OK"

def main():
    files = [f for f in os.listdir(TXT_DIR) if f.endswith(".txt")]
    print(f"Checking & Standardizing {len(files)} files in TXT...")
    
    deleted = 0
    updated = 0
    errors = 0

    for f in files:
        fpath = os.path.join(TXT_DIR, f)
        status, msg = clean_song_file(fpath)
        if status == "delete":
            os.remove(fpath)
            deleted += 1
            print(f"  [DEL] {msg}")
        elif status == "updated":
            updated += 1
        else:
            errors += 1

    remaining = len([f for f in os.listdir(TXT_DIR) if f.endswith(".txt")])
    print(f"\nDone! Updated/Verified: {updated} | Deleted: {deleted} | Skipped/Error: {errors}")
    print(f"Total TXT Files Remaining: {remaining}")

if __name__ == "__main__":
    main()
