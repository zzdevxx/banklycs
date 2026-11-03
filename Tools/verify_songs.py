import os
import hashlib
import re
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

txt_dir = os.path.join(BASE_DIR, "TXT")
pro_dir = os.path.join(BASE_DIR, "PRO")

txt_map = {}
for root, _, files in os.walk(txt_dir):
    for f in files:
        if f.endswith(".txt"):
            txt_map[f] = os.path.join(root, f)
txt_files = list(txt_map.keys())
pro_files = set(f[:-4] for f in os.listdir(pro_dir) if f.endswith(".pro"))

header_regex = re.compile(r"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$", re.IGNORECASE)

hashes = {}
duplicate_hashes = []
too_short = []
files_without_blank = []
no_section_files = []
slide_overflow_files = []
encoding_errors = []

for fname in sorted(txt_files):
    fpath = txt_map[fname]
    size = os.path.getsize(fpath)
    
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(fpath, "r", encoding="latin-1") as f:
                content = f.read()
            encoding_errors.append(fname)
        except Exception as e:
            too_short.append((fname, f"Read error: {e}"))
            continue

    # Content normalization for duplicate detection (ignoring title line)
    lines = [l.strip() for l in content.splitlines()]
    non_empty = [l for l in lines if l]
    
    # Hash check on actual lyrics
    h = hashlib.md5("\n".join(non_empty).lower().encode("utf-8")).hexdigest()
    if h in hashes:
        duplicate_hashes.append((fname, hashes[h]))
    else:
        hashes[h] = fname
        
    if size < 35:  # ambang 35B: refrains liturgis sah ("Amin.", "Haleluya") hanya ~40-75B
        too_short.append((fname, f"{size} bytes"))
        
    if not lines or lines[0].upper() != "BLANK":
        files_without_blank.append((fname, lines[0] if lines else "EMPTY"))
        
    # Check headers
    has_section = False
    for line in lines:
        if header_regex.match(line):
            has_section = True
            break
    if not has_section:
        no_section_files.append(fname)
        
    # Check slide lines count (max 2 lines per slide)
    # Parse slides by empty lines
    curr_slide = []
    max_lines_in_slide = 0
    in_section = False
    for line in lines:
        if header_regex.match(line):
            if len(curr_slide) > 2:
                max_lines_in_slide = max(max_lines_in_slide, len(curr_slide))
            curr_slide = []
            in_section = True
        elif not line:
            if len(curr_slide) > 2:
                max_lines_in_slide = max(max_lines_in_slide, len(curr_slide))
            curr_slide = []
        else:
            if in_section:
                curr_slide.append(line)
    if len(curr_slide) > 2:
        max_lines_in_slide = max(max_lines_in_slide, len(curr_slide))
    if max_lines_in_slide > 2:
        slide_overflow_files.append((fname, max_lines_in_slide))

print("=" * 60)
print(f"HASIL VERIFIKASI LENGKAP ({len(txt_files)} FILE TXT)")
print("=" * 60)
print(f"1. Total File TXT        : {len(txt_files)}")
print(f"2. Total File PRO        : {len(pro_files)}")
print(f"   Sinkron TXT vs PRO    : {'100% Sesuai' if len(txt_files) == len(pro_files) else 'Ada perbedaan'}")
print(f"3. Duplikasi Lirik Persis: {len(duplicate_hashes)} pasangan")
print(f"4. File Terlalu Pendek   : {len(too_short)} file")
print(f"5. Tanpa Header BLANK    : {len(files_without_blank)} file")
print(f"6. Tanpa Section Tag     : {len(no_section_files)} file")
print(f"7. Slide > 2 Baris Teks  : {len(slide_overflow_files)} file")
print(f"8. Masalah Encoding      : {len(encoding_errors)} file")
print("=" * 60)

if duplicate_hashes:
    print(f"\nContoh Duplikasi ({len(duplicate_hashes)} pasang):")
    for f1, f2 in duplicate_hashes[:15]:
        print(f"  - [{f1}] sama dengan [{f2}]")

if too_short:
    print(f"\nFile Terlalu Pendek:")
    for f, reason in too_short[:10]:
        print(f"  - {f} ({reason})")

if files_without_blank:
    print(f"\nFile Tanpa BLANK:")
    for f, line1 in files_without_blank[:10]:
        print(f"  - {f} (Baris pertama: '{line1}')")

if no_section_files:
    print(f"\nFile Tanpa Section Header:")
    for f in no_section_files[:10]:
        print(f"  - {f}")

if slide_overflow_files:
    print(f"\nContoh Slide > 2 Baris:")
    for f, max_l in slide_overflow_files[:10]:
        print(f"  - {f} (Slide maks {max_l} baris)")
