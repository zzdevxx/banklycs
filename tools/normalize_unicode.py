"""
Normalize Unicode tipografi pada seluruh TXT (idempoten, aman di-run ulang).

Yang dilakukan:
 1. Perbaiki mojibake cp1252->UTF-8 (contoh: 'â€™' menjadi apostrof kurly)
 2. Petik kurly -> ASCII (penyair/pencetak lidah memakai ' untuk elisi: 'Ku, 'kau)
 3. Dash & elipsis -> ASCII
 4. Spasi khusus (NBSP, thin space, ZWSP/ZWJ, BOM, soft hyphen) dinormalkan/dihapus
 5. Karakter asing (Cyrillic, Georgian, Hangul, CJK, dll) DIBIARKAN lalu dilaporkan
    ke report agar bisa direview manual (jangan auto-hapus: bisa jadi lagu asing asli)
"""
import os
import re
import unicodedata
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TXT_DIR = os.path.join(BASE_DIR, "database")
if not os.path.isdir(TXT_DIR):
    TXT_DIR = os.path.join(BASE_DIR, "TXT")
REPORT = os.path.join(BASE_DIR, "Tools", "_report_unicode.txt")

# ==== Peta normalisasi sederhana ====
SIMPLE_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201A": ",", "\u201B": "'",   # petik satu
    "\u201C": '"', "\u201D": '"', "\u201E": '"', "\u201F": '"',   # petik dua
    "\u00AB": '"', "\u00BB": '"', "\u2039": "'", "\u203A": "'",
    "\u02BC": "'", "\u02B9": "'", "\u2032": "'",                  # modifier apostrof
    "\u02DC": "~", "\u02C6": "^",                                 # tilde/kapit -> ASCII
    "\u2013": "-", "\u2014": "-", "\u2011": "-", "\u00AD": "",     # dash + soft hyphen
    "\u2026": "...",
    "\u00A0": " ", "\u2000": " ", "\u2001": " ", "\u2002": " ", "\u2003": " ",
    "\u2004": " ", "\u2005": " ", "\u2006": " ", "\u2007": " ", "\u2008": " ",
    "\u2009": " ", "\u200A": " ", "\u202F": " ", "\u205F": " ", "\u3000": " ",
    "\u200B": "", "\u200C": "", "\u200D": "", "\uFEFF": "", "\u200E": "", "\u200F": "",
    "\u00A6": "-", "\u00B7": "*",                                  # broken bar -> dash (artefak), middot -> *
}

LATIN_ACCENTS = {
    "\u00C0": "A", "\u00C1": "A", "\u00C2": "A", "\u00C3": "A", "\u00C4": "A", "\u00C5": "A",
    "\u00E0": "a", "\u00E1": "a", "\u00E2": "a", "\u00E3": "a", "\u00E4": "a", "\u00E5": "a",
    "\u00C8": "E", "\u00C9": "E", "\u00CA": "E", "\u00CB": "E",
    "\u00E8": "e", "\u00E9": "e", "\u00EA": "e", "\u00EB": "e",
    "\u00CC": "I", "\u00CD": "I", "\u00CE": "I", "\u00CF": "I",
    "\u00EC": "i", "\u00ED": "i", "\u00EE": "i", "\u00EF": "i",
    "\u00D2": "O", "\u00D3": "O", "\u00D4": "O", "\u00D5": "O", "\u00D6": "O", "\u00D8": "O",
    "\u00F2": "o", "\u00F3": "o", "\u00F4": "o", "\u00F5": "o", "\u00F6": "o", "\u00F8": "o",
    "\u00D9": "U", "\u00DA": "U", "\u00DB": "U", "\u00DC": "U",
    "\u00F9": "u", "\u00FA": "u", "\u00FB": "u", "\u00FC": "u",
    "\u00DD": "Y", "\u00FD": "y", "\u00FF": "y",
    "\u00C7": "C", "\u00E7": "c", "\u00D1": "N", "\u00F1": "n",
    "\u0130": "I", "\u0131": "i",                     # İ ı (transliterasi)
    "\u0152": "OE", "\u0153": "oe", "\u0142": "l", "\u0141": "L",
    "\u0105": "a", "\u0119": "e", "\u0117": "e", "\u016B": "u",
    "\u0107": "c", "\u010D": "c", "\u0161": "s", "\u0160": "S", "\u015F": "s",
    "\u017A": "z", "\u017C": "z", "\u017E": "z", "\u011F": "g", "\u0130 ": "",
    "\u0113": "e", "\u0101": "a", "\u01CE": "a", "\u01D0": "i", "\u01D2": "O",
    "\u01D4": "u", "\u015B": "s", "\u015D": "s", "\u011B": "e",
    "\u025B": "e", "\u0259": "e", "\u0254": "o",
    "\u03B5": "e",                                    # epsilon kecil (sering typo)
    "\u20AC": "E",                                    # euro -> dihapus lewat jalur mojibake umumnya
}

FOREIGN_RANGES = [
    (0x0400, 0x04FF, "Cyrillic"), (0x0500, 0x052F, "Cyrillic-Sup"),
    (0x10A0, 0x10FF, "Georgian"), (0x0530, 0x058F, "Armenian"),
    (0x0600, 0x06FF, "Arabic"), (0x0900, 0x097F, "Devanagari"),
    (0x1100, 0x11FF, "Hangul-Jamo"), (0xAC00, 0xD7AF, "Hangul"),
    (0x3040, 0x30FF, "Kana"), (0x4E00, 0x9FFF, "CJK"), (0x3400, 0x4DBF, "CJK-ext"),
    (0xFF00, 0xFFEF, "Half/Full-width"),
]

def is_foreign(ch):
    cp = ord(ch)
    for lo, hi, name in FOREIGN_RANGES:
        if lo <= cp <= hi:
            return name
    return None

# Set karakter yang bisa dihasilkan byte kelanjutan cp1252 (80-BF)
_C1252 = ("[\u0080-\u00A1\u00A2\u00A3\u00A4\u00A5\u00A6\u00A7\u00A8\u00A9\u00AA\u00AB\u00AC\u00AD"
          "\u00AE\u00AF\u00B0\u00B1\u00B2\u00B3\u00B4\u00B5\u00B6\u00B7\u00B8\u00B9\u00BA\u00BB\u00BC\u00BD\u00BE\u00BF"
          "\u20AC\u201A\u0192\u201E\u2026\u2020\u2021\u02C6\u2030\u0160\u2039\u0152\u017D\u2018\u2019\u201C\u201D"
          "\u2022\u2013\u2014\u02DC\u2122\u0161\u203A\u0153\u0178\u017E]")
MOJIBAKE_MARK = re.compile("\u00E2" + _C1252 + _C1252 + "|\u00C3" + _C1252 + "|\u00C2" + _C1252)

def fix_mojibake(s):
    """Perbaiki sekuens mojibake UTF-8->cp1252 yang paling umum (â€™, â€, Ã©, dll).
    Konservatif: hanya sub pada sekuens yang berhasil di-round-trip."""
    count = 0
    def _repl(m):
        nonlocal count
        for enc in ("cp1252", "latin-1"):
            try:
                fixed = m.group(0).encode(enc).decode("utf-8")
                count += 1
                return fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return m.group(0)
    result = MOJIBAKE_MARK.sub(_repl, s)
    return result, count

def normalize_text(text):
    stats = Counter()
    foreign = Counter()
    text, n_moji = fix_mojibake(text)
    if n_moji:
        stats["mojibake"] += n_moji
    out_chars = []
    for ch in text:
        if ch in SIMPLE_MAP:
            rep = SIMPLE_MAP[ch]
            out_chars.append(rep)
            if rep:
                stats["mapped"] += 1
            else:
                stats["removed"] += 1
            continue
        if ch in LATIN_ACCENTS:
            out_chars.append(LATIN_ACCENTS[ch])
            stats["mapped"] += 1
            continue
        fn = is_foreign(ch)
        if fn:
            foreign[fn] += len(ch)
            out_chars.append(ch)
            continue
        # sisa non-ASCII lain (nota musik ♩ ♭ →, simbol): biarkan, tapi laporkan
        if ord(ch) > 126:
            foreign[f"Other:{unicodedata.name(ch, 'U+%04X')}"[:40]] += 1
            out_chars.append(ch)
            continue
        out_chars.append(ch)
    result = "".join(out_chars)
    result, n2 = fix_mojibake(result)
    if n2:
        stats["mojibake"] += n2
    # rapikan spasi berlebih di akhir baris
    lines = [ln.rstrip() for ln in result.split("\n")]
    result = "\n".join(lines)
    return result, stats, foreign

def main():
    # recursive scan
    file_paths = []
    for root, _, fs in os.walk(TXT_DIR):
        for f in fs:
            if f.endswith(".txt"):
                file_paths.append(os.path.join(root, f))
    files = [os.path.basename(p) for p in file_paths]
    changed = 0
    mojibake_files = []
    foreign_files = []
    report_lines = []
    for fname in sorted(files):
        fpath = os.path.join(TXT_DIR, fname)
        with open(fpath, "r", encoding="utf-8-sig") as f:
            original = f.read()
        try:
            norm, stats, foreign = normalize_text(original)
        except Exception as e:
            report_lines.append(f"ERROR-READ  {fname}: {e}")
            continue
        if norm != original:
            with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                f.write(norm)
            changed += 1
            if stats["mojibake"]:
                mojibake_files.append(fname)
        if foreign:
            foreign_files.append((fname, dict(foreign)))
    with open(REPORT, "w", encoding="utf-8") as r:
        r.write("=" * 70 + "\n")
        r.write(f"LAPORAN NORMALISASI UNICODE — {len(files)} file dicek\n")
        r.write("=" * 70 + "\n")
        r.write(f"File diubah                : {changed}\n")
        r.write(f"File mojibake diperbaiki   : {len(mojibake_files)}\n")
        r.write(f"File masih ada karakter asing (PERLU REVIEW MANUAL):\n")
        for fname, fcnt in foreign_files:
            r.write(f"  - {fname}  {fcnt}\n")
        if report_lines:
            r.write("\nERROR:\n")
            r.writelines(l + "\n" for l in report_lines)
    print(f"Selesai. {changed} file dinormalkan, {len(foreign_files)} file masih ada karakter asing.")
    print(f"Report: {REPORT}")

if __name__ == "__main__":
    main()
