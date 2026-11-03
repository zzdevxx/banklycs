import os
import re
import sys
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def get_ppr_dir():
    for base in [os.environ.get("OneDrive"), os.environ.get("USERPROFILE")]:
        if not base: continue
        for doc in ["Documents", "Dokumen"]:
            c = os.path.join(base, doc, "ProPresenter")
            if os.path.isdir(c): return c
    return None

PPR_DIR = get_ppr_dir()

sys.stdout.reconfigure(encoding='utf-8')

TXT_DIR = os.path.join(BASE_DIR, "database", "txt")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "database", "txt")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "TXT")

PRO_DIR = os.path.join(BASE_DIR, "database", "pro")
if not os.path.isdir(PRO_DIR):
    PRO_DIR = os.path.join(BASE_DIR, "engine", "PRO")
if not os.path.isdir(PRO_DIR):
    PRO_DIR = os.path.join(BASE_DIR, "database", "pro")
if not os.path.isdir(PRO_DIR):
    PRO_DIR = os.path.join(BASE_DIR, "engine", "PRO")
if not os.path.isdir(PRO_DIR):
    PRO_DIR = os.path.join(BASE_DIR, "PRO")

LIB_DIR = os.path.join(PPR_DIR, "Libraries", "Banks") if PPR_DIR else ""

print("==============================================================================")
print("  AUDIT KEBERSIHAN & INTEGRITAS MENYELURUH (BANKLYCS)")
print("==============================================================================")

# 1. Check directory file counts
txt_map = {}
for root, _, files in os.walk(TXT_DIR):
    for f in files:
        if f.endswith(".txt"):
            txt_map[f] = os.path.join(root, f)
txt_files = list(txt_map.keys())
pro_files = [f for f in os.listdir(PRO_DIR) if f.endswith(".pro")]
lib_files = [f for f in os.listdir(LIB_DIR) if f.endswith(".pro")] if os.path.exists(LIB_DIR) else []

print(f"\n[1/5] Jumlah File di Setiap Lokasi:")
print(f"  * database (TXT) : {len(txt_files):,} file")
print(f"  * engine/PRO     : {len(pro_files):,} file")
print(f"  * ProPresenter Injected : {len(lib_files):,} file (hanya lagu aktif)")
is_synced = (len(txt_files) == len(pro_files))
print(f"  -> Status Sinkron Database vs Engine Cache : {'100% PERSIS SINKRON' if is_synced else 'TIDAK SINKRON!'}")

# 2. Check 1-to-1 match between TXT and PRO
txt_bases = set(f[:-4].lower() for f in txt_files)
pro_bases = set(f[:-4].lower() for f in pro_files)

missing_in_pro = txt_bases - pro_bases
print(f"\n[2/5] Pemetaan 1-ke-1:")
print(f"  * Hilang di engine/PRO : {len(missing_in_pro)} file")

# 3. Check PRO file sizes (detect corrupted / 0-byte presentations)
zero_pro = [f for f in pro_files if os.path.getsize(os.path.join(PRO_DIR, f)) == 0]
small_pro = [f for f in pro_files if os.path.getsize(os.path.join(PRO_DIR, f)) < 500]
print(f"\n[3/5] Integritas Binary Protobuf ProPresenter (.pro):")
print(f"  * File 0-byte (Corrupted)    : {len(zero_pro)} file")
print(f"  * File mencurigakan (<500B)  : {len(small_pro)} file")

# 4. Check TXT formatting standards
illegal_chars = re.compile(r'[<>:"/\\|?*]')
bad_filenames = []
bad_first_line = []
bad_second_line = []
overflow_slides = []
encoding_issues = []

header_regex = re.compile(r"^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$", re.IGNORECASE)

print(f"\n[4/5] Memeriksa Format Lirik TXT...")
for fname in txt_files:
    # Filename check
    if illegal_chars.search(fname):
        bad_filenames.append(fname)
        
    fpath = txt_map[fname]
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        encoding_issues.append((fname, str(e)))
        continue
        
    lines = [l.strip() for l in content.splitlines()]
    if not lines or lines[0].upper() != "BLANK":
        bad_first_line.append(fname)
    if len(lines) < 2 or not lines[1]:
        bad_second_line.append(fname)
        
    # Check slide lines <= 2
    curr_slide = []
    in_section = False
    for line in lines:
        if header_regex.match(line):
            if len(curr_slide) > 2:
                overflow_slides.append((fname, len(curr_slide)))
                break
            curr_slide = []
            in_section = True
        elif not line:
            if len(curr_slide) > 2:
                overflow_slides.append((fname, len(curr_slide)))
                break
            curr_slide = []
        else:
            if in_section:
                curr_slide.append(line)
    if len(curr_slide) > 2:
        overflow_slides.append((fname, len(curr_slide)))

print(f"  * Nama file bermasalah       : {len(bad_filenames)} file")
print(f"  * Baris 1 bukan BLANK        : {len(bad_first_line)} file")
print(f"  * Baris 2 bukan Judul        : {len(bad_second_line)} file")
print(f"  * Slide > 2 baris teks       : {len(overflow_slides)} file")
print(f"  * Masalah encoding UTF-8     : {len(encoding_issues)} file")

# 5. Workspace cleanliness check (check root for temporary files)
root_dir = BASE_DIR
all_items = os.listdir(root_dir)
print(f"\n[5/5] Kebersihan Root Workspace ({root_dir}):")
for it in sorted(all_items):
    ipath = os.path.join(root_dir, it)
    is_dir = os.path.isdir(ipath)
    size_str = f"({len(os.listdir(ipath))} items)" if is_dir else f"({os.path.getsize(ipath):,} bytes)"
    print(f"  - {'[DIR] ' if is_dir else '[FILE]'} {it.ljust(25)} {size_str}")

print("\n==============================================================================")
all_clean = (is_synced and len(missing_in_pro) == 0 and len(zero_pro) == 0 and 
             len(bad_filenames) == 0 and len(bad_first_line) == 0 and 
             len(bad_second_line) == 0 and len(overflow_slides) == 0 and 
             len(encoding_issues) == 0)
print(f"KESIMPULAN AUDIT: {'SEMUA 100% BERSIH, VALID, & SIAP PAKAI!' if all_clean else 'ADA TEMUAN PERLU DIBERSIHKAN!'}")
print("==============================================================================")
