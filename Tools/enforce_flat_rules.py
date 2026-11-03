# -*- coding: utf-8 -*-
"""
FLATTEN + CLEAN master bank lirik ProPresenter (TXT).
  python flatten.py           -> DRY RUN (tidak mengubah file apa pun)
  python flatten.py --apply   -> eksekusi

Aturan:
 1. Satu folder datar: TXT\\*.txt, TIDAK ada subfolder.
 2. Artis No Name -> nama file jadi judul saja (tanpa " - Artis").
 3. Judul ALL-CAPS -> Title Case ("KUMENANG" -> "Kumenang").
 4. Baris lirik ALL-CAPS -> sentence case. Header bagian TETAP UPPERCASE.
 5. Kata ganti ilahi Mu/Nya/Ku/Kau tidak boleh huruf kecil di awal kata.
 6. Sampah scraper (baris LYRIC_LINE_n) dibuang.
 7. Baris 2 file = persis nama file (judul slide BLANK).
 8. Duplikat konten identik -> sisakan satu.
"""
import os, re, sys, hashlib, collections, json

sys.stdout.reconfigure(encoding='utf-8')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "TXT"))
APPLY = "--apply" in sys.argv

ILLEGAL = re.compile(r'[<>:"/\\|?*]')
CODE_RE = re.compile(r'^(KJ|BCK|PKJ|NKB|KK|BE|KLIK|NNBT|NTH|KBO|KJE|MNC|MMS|FKI|GNVRI|GKY|GBI)\s*\d+', re.I)
PLACEHOLDER = re.compile(r'^LYRIC_LINE_?\d+$', re.I)
PRE  = r"(?<=[\s.,!?;:'\"-])"
POST = r"(?=[\s.,!?;:'\"-]|$)"

SMALL = {"dan","di","ke","dari","untuk","dalam","pada","akan","itu","ini","yang","atau","tapi","namun",
         "a","an","the","of","and","to","in","my","me","it","is","as","be","with","our","your","his"}

HDR_CANON = {"BAIT":"VERSE","REFF":"CHORUS","REF":"CHORUS","PRE CHORUS":"PRE-CHORUS",
             "PRECHORUS":"PRE-CHORUS","CHORUS":"CHORUS","VERSE":"VERSE","BRIDGE":"BRIDGE",
             "TAG":"TAG","INTRO":"INTRO","OUTRO":"OUTRO","ENDING":"ENDING","INTERLUDE":"INTERLUDE",
             "REFRAIN":"REFRAIN","BLANK":"BLANK","SOLO":"INTERLUDE","INSTRUMENTAL":"INTERLUDE"}

def letters(s): return [c for c in s if c.isalpha()]

def is_allcaps(s):
    L = letters(s)
    return len(L) >= 3 and sum(1 for c in L if c.isupper()) / len(L) >= 0.85

def is_allsmall(s):
    L = letters(s)
    return len(L) >= 3 and sum(1 for c in L if c.islower()) / len(L) >= 0.95

def norm_quotes(s):
    for a, b in (('\u2019', "'"), ('\u2018', "'"), ('\u201c', '"'), ('\u201d', '"'),
                 ('\u2013', '-'), ('\u2014', '-'), ('\u00a0', ' '),
                 ('\u200b', ''), ('\u200c', ''), ('\u200d', ''), ('\u00ad', '')):
        s = s.replace(a, b)
    return s

def divine(s):
    s = re.sub(PRE + "mu"  + POST, "Mu",  s)
    s = re.sub(PRE + "nya" + POST, "Nya", s)
    s = re.sub(r"-mu\b", "-Mu", s, flags=re.I)
    s = re.sub(r"-nya\b", "-Nya", s, flags=re.I)
    s = re.sub(r"^'ku\b", "'Ku", s, flags=re.I)
    s = re.sub(r"^'kau\b", "'Kau", s, flags=re.I)
    return s

def header_norm(t):
    u = norm_quotes(t).upper().rstrip(':').strip()
    u = re.sub(r'^PRE[\s-]*CHORUS', 'PRE-CHORUS', u)
    m = re.match(r'^(.*?)[\s]+(\d+)$', u)
    base, num = (m.group(1).strip(), m.group(2)) if m else (u.strip(), None)
    base = HDR_CANON.get(base, base)
    if base not in ("BLANK","VERSE","CHORUS","BRIDGE","PRE-CHORUS","TAG","INTRO",
                    "OUTRO","ENDING","INTERLUDE","REFRAIN"):
        return None
    return base + ((" " + num) if num else "")

def looks_header(t):
    return header_norm(t) is not None

def title_case(s):
    out = []
    for i, w in enumerate(s.split(' ')):
        lw = w.lower()
        if not letters(w) or re.match(r'^[\d.,!?:;]+$', w):
            out.append(w); continue
        if CODE_RE.match(w.upper()):
            out.append(lw.upper()); continue
        if lw.startswith("'"):
            out.append("'" + lw[1:].capitalize() if len(lw) > 1 else lw); continue
        out.append((lw[0].upper() + lw[1:]) if (i == 0 or lw not in SMALL) else lw)
    return divine(' '.join(out))

# Hanya NAMA DIRI (orang, tempat, Allah, organisasi) yang dipaksa kapital.
# Kata biasa (kebangkitan, kemenangan, dll) sengaja TIDAK dimasukkan supaya
# tidak ikut dikapitalkan di tengah kalimat.
PROPER = {
    "tuhan":"Tuhan","yesus":"Yesus","kristus":"Kristus","allah":"Allah","bapa":"Bapa",
    "roh":"Roh","kudus":"Kudus","tritunggal":"Tritunggal","khalik":"Khalik",
    "penebus":"Penebus","penolong":"Penolong","gembala":"Gembala","mesias":"Mesias",
    "kristo":"Kristo","adonai":"Adonai","allahku":"Allahku","tuhanku":"Tuhanku",
    "sorga":"Sorga","surga":"Surga","sion":"Sion","yerusalem":"Yerusalem","yerikho":"Yerikho",
    "golgota":"Golgota","kalvari":"Kalvari","eden":"Eden","sinai":"Sinai",
    "yordan":"Yordan","galilea":"Galilea","betlehem":"Betlehem","betania":"Betania",
    "samaria":"Samaria","israel":"Israel","yakub":"Yakub","abraham":"Abraham",
    "daud":"Daud","salomo":"Salomo","elija":"Elia","eliah":"Elia","musa":"Musa",
    "harun":"Harun","yosua":"Yosua","paulus":"Paulus","petrus":"Petrus",
    "yohanes":"Yohanes","matius":"Matius","markus":"Markus","lukas":"Lukas",
    "maria":"Maria","nazaaret":"Nazaaret","karmel":"Karmel","nazaret":"Nazaret",
    "hkbp":"HKBP","gki":"GKI","gmim":"GMIM","pgi":"PGI","yamuger":"YAMUGER",
    "gms":"GMS","ifgf":"IFGF","ndc":"NDC","ccli":"CCLI","hillsong":"Hillsong",
}

BIGRAMS = [("roh kudus","Roh Kudus"),("tuhan yesus","Tuhan Yesus"),
           ("yesus kristus","Yesus Kristus"),("bapa sorgawi","Bapa Sorgawi"),
           ("bapa surga","Bapa Surga"),("anak domba","Anak Domba"),
           ("anak allah","Anak Allah"),("anak manusia","Anak Manusia"),
           ("kota daud","Kota Daud"),("kota david","Kota Daud")]

def restore_proper(s):
    for a, b in BIGRAMS:
        s = re.sub(r'(?i)\b' + re.escape(a) + r'\b', b, s)
    def rep(m):
        w = m.group(0)
        return PROPER.get(w.lower(), w)
    return re.sub(r"[A-Za-z][A-Za-z'\-]*", rep, s)

def sentence_case(s):
    parts = re.split(r'([,;:.!?])', s)
    res, cap = [], True
    for p in parts:
        if p is None: continue
        if re.match(r'^[,;:.!?]$', p):
            res.append(p); cap = True; continue
        if p == '':
            res.append(p); continue
        low = p.lower()
        if cap and letters(low):
            low = low[0].upper() + low[1:]
            cap = False
        res.append(low)
    out = ''.join(res)
    out = restore_proper(out)
    if out: out = out[0].upper() + out[1:]
    return divine(out)

def clean_name(s):
    s = ILLEGAL.sub('', norm_quotes(s))
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*-\s*', ' - ', s)
    return s.strip(' .')[:180]

def body_key(lines):
    txt = ' '.join(l.strip().lower() for i, l in enumerate(lines)
                   if l.strip() and i >= 2 and not looks_header(l) and not PLACEHOLDER.match(l.strip()))
    txt = re.sub(r'[^a-z0-9]', '', txt)
    return hashlib.md5(txt.encode('utf-8', 'ignore')).hexdigest() if len(txt) > 20 else ''

# ------------------------------------------------------------------ load
src = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if not f.lower().endswith('.txt'): continue
        p = os.path.join(dp, f)
        try:
            raw = open(p, 'r', encoding='utf-8-sig', errors='replace').read()
        except Exception as e:
            print("READ FAIL", p, e); continue
        rel = os.path.relpath(dp, ROOT)
        src.append({'path': p, 'folder': '' if rel == '.' else rel,
                    'name': os.path.splitext(f)[0],
                    'lines': raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')})
print(f"Loaded {len(src)} file")

# ------------------------------------------------------------------ parse nama
for s in src:
    stem = s['name']
    while True:
        m = re.search(r'\s+-\s+(No Name|Praise\s+(?:&|&amp;)\s+Worship)$', stem, re.I)
        if not m: break
        stem = stem[:m.start()].strip()

    if ' - ' in stem:
        title, artist = stem.split(' - ', 1)
        title, artist = title.strip(), artist.strip()
        no_name = False
    else:
        title, artist = stem.strip(), ''
        no_name = True

    s['hymnal']   = bool(CODE_RE.match(artist))
    s['no_name']  = no_name
    s['t_was_caps'] = is_allcaps(title)
    s['a_was_small'] = is_allsmall(artist) and not s['hymnal']

    s['title']  = clean_name(title_case(title)  if s['t_was_caps']  else title)
    s['artist'] = clean_name(title_case(artist) if s['a_was_small'] else artist)
    s['stem']   = s['title'] if no_name else clean_name(f"{s['title']} - {s['artist']}")
    s['key']    = body_key(s['lines'])

# ------------------------------------------------------------------ dedupe by nama
groups = collections.defaultdict(list)
for s in src:
    groups[s['stem'].lower()].append(s)

for stem_l, g in groups.items():
    if len(g) == 1:
        g[0]['final'] = g[0]['stem']; g[0]['drop'] = False
        continue
    g.sort(key=lambda x: (0 if x['no_name'] else 1, len(' '.join(x['lines']))), reverse=True)
    keys = {x['key'] for x in g if x['key']}
    if len(keys) <= 1:
        for i, x in enumerate(g):
            x['final'] = x['stem']; x['drop'] = (i > 0)
    else:
        for i, x in enumerate(g):
            x['final'] = x['stem'] if i == 0 else clean_name(f"{x['stem']} ({i+1})")
            x['drop'] = False

# ------- dedupe LINTAS nama, khusus entri No Name (konservatif) -------
# Kalau lirik identik dengan file berartis -> file No Name dibuang.
by_key = collections.defaultdict(list)
for s in src:
    if s.get('drop') or not s['key']: continue
    by_key[s['key']].append(s)
cross = 0
for k, g in by_key.items():
    if len(g) < 2: continue
    named = [x for x in g if not x['no_name']]
    nn    = [x for x in g if x['no_name']]
    if named and nn:
        for x in nn:
            x['drop'] = True; cross += 1
print(f"Dedupe lintas-nama (No Name = kembaran lagu berartis): {cross}")

used = set()
for s in src:
    if s.get('drop'): continue
    base, n = s['final'], 1
    while base.lower() in used:
        n += 1
        base = clean_name(f"{s['final']} ({n})")
    s['final'] = base
    used.add(base.lower())

kept    = [x for x in src if not x.get('drop')]
dropped = [x for x in src if x.get('drop')]

# ------------------------------------------------------------------ rebuild isi
def rebuild(s):
    lines = s['lines']
    out, dirty = [], False
    out.append('BLANK')
    if len(lines) < 2 or lines[1].strip() != s['final']:
        dirty = True
    out.append(s['final'])
    for i in range(2, len(lines)):
        raw = lines[i]
        t = norm_quotes(raw).strip()
        if PLACEHOLDER.match(t):
            dirty = True; continue
        if not t:
            if out and out[-1] != '': out.append('')
            continue
        h = header_norm(t)
        if h is not None:
            if h != t: dirty = True
            out.append(h)
            continue
        new = sentence_case(t) if is_allcaps(t) else divine(t)
        if new != t: dirty = True
        out.append(new)
    txt = '\n'.join(out).rstrip() + '\n'
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    orig_norm = re.sub(r'\r\n?', '\n', '\n'.join(lines)).rstrip() + '\n'
    content_changed = (txt != orig_norm) or dirty
    return txt, content_changed

for s in kept:
    s['content'], s['changed'] = rebuild(s)

# ------------------------------------------------------------------ report
name_changed = sum(1 for x in kept if x['name'] != x['final'])
print(f"\nTOTAL awal          : {len(src)}")
print(f"TOTAL akhir         : {len(kept)}  (duplikat dihapus: {len(dropped)})")
print(f"  keluar subfolder  : {sum(1 for x in kept if x['folder'])}")
print(f"  nama file berubah : {name_changed}")
print(f"    judul caps->TC  : {sum(1 for x in kept if x['t_was_caps'])}")
print(f"    artis caps->TC  : {sum(1 for x in kept if x['a_was_small'])}")
print(f"    NoName->judul   : {sum(1 for x in kept if x['no_name'])}")
print(f"  isi file berubah  : {sum(1 for x in kept if x['changed'])}")

print("\n--- CONTOH PERUBAHAN NAMA ---")
for x in [y for y in kept if y['name'] != y['final']][:16]:
    print(f"  {x['name']}\n      -> {x['final']}")

print("\n--- CONTOH ISI BARU (judul dulu ALL-CAPS) ---")
for x in [y for y in kept if y['t_was_caps']][:3]:
    for l in x['content'].splitlines()[:10]:
        print("   |", l)
    print()

print("--- CONTOH DIHAPUS ---")
for x in dropped[:8]:
    print(f"  {os.path.relpath(x['path'], ROOT)}")

if not APPLY:
    print("\n===== DRY RUN: TIDAK ADA FILE YANG DIAGUBAH =====")
    sys.exit(0)

# ------------------------------------------------------------------ apply
tmp = os.path.join(ROOT, '_stage')
os.makedirs(tmp, exist_ok=True)
plan = []
for x in kept:
    tp = os.path.join(tmp, hashlib.md5(x['path'].encode('utf-8')).hexdigest())
    with open(tp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(x['content'])
    plan.append((x['final'], tp, x['path']))

err = 0
for x in src:
    try: os.remove(x['path'])
    except Exception as e: err += 1; print("DEL FAIL", x['path'], e)

for stem, tp, orig in plan:
    dest = os.path.join(ROOT, stem + '.txt')
    if os.path.exists(dest):
        dest = os.path.join(ROOT, clean_name(stem + ' ~' + hashlib.md5(orig.encode()).hexdigest()[:6]) + '.txt')
    try: os.replace(tp, dest)
    except Exception as e: err += 1; print("MOV FAIL", stem, e)

for dp, dn, fn in os.walk(ROOT, topdown=False):
    if dp == ROOT: continue
    try:
        if not os.listdir(dp): os.rmdir(dp)
    except Exception: pass
try: os.rmdir(tmp)
except Exception: pass

n = len([x for x in os.listdir(ROOT) if x.lower().endswith('.txt')])
print(f"\nAPPLIED. File akhir: {n}. Error: {err}")
leftover = [d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))]
print(f"Subfolder tersisa: {leftover}")
