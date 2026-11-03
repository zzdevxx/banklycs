import os
import re
import sqlite3
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TXT_DIR = os.path.join(BASE_DIR, "database", "txt")
DB_PATH = os.path.join(BASE_DIR, "database", "banklycs.db")

def determine_category(name):
    u = name.upper()
    if re.search(r'\bKJ\s*\d+', u): return "KJ"
    if re.search(r'\bNKB\s*\d+', u): return "NKB"
    if re.search(r'\bPKJ\s*\d+', u): return "PKJ"
    if re.search(r'\bKK\s*\d+', u): return "KK"
    if re.search(r'\bBE\s*\d+', u): return "BE"
    if re.search(r'\bKLIK\s*\d+', u): return "KLIK"
    if re.search(r'\bNNBT\s*\d+', u): return "NNBT"
    if "KIDUNG JAWA" in u or "PASAMUWAN" in u: return "JAWA"
    if any(k in u for k in ["HILLSONG", "BETHEL", "ELEVATION", "PLANETSHAKERS", "TOMLIN", "REDMAN", "WICKHAM", "GAITHER"]):
        return "EN"
    return "ID"

def main():
    start_time = time.time()
    print("==============================================================================", flush=True)
    print("  MIGRASI 20.301 FILE LIRIK TXT KE SQLITE (banklycs.db)", flush=True)
    print("==============================================================================", flush=True)
    
    for ext in ["", "-wal", "-shm"]:
        p = DB_PATH + ext
        if os.path.exists(p):
            try: os.remove(p)
            except: pass
            
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = OFF;")
    
    # 1. Create Base Songs Table
    cur.execute("""
    CREATE TABLE songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        artist TEXT,
        category TEXT,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX idx_songs_title ON songs(title);")
    cur.execute("CREATE INDEX idx_songs_category ON songs(category);")
    
    # 2. Read TXT files
    files = sorted([f for f in os.listdir(TXT_DIR) if f.endswith(".txt")])
    total = len(files)
    print(f"[1/4] Membaca {total:,} file lirik dari {TXT_DIR}...", flush=True)
    
    records = []
    for fname in files:
        fpath = os.path.join(TXT_DIR, fname)
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        base = fname[:-4]
        title = base
        artist = ""
        if " - " in base:
            parts = base.split(" - ", 1)
            title = parts[0].strip()
            artist = parts[1].strip()
            
        cat = determine_category(base)
        records.append((fname, title, artist, cat, content))
        
    # 3. Bulk insert songs
    print(f"[2/4] Menyimpan {len(records):,} lagu ke tabel songs...", flush=True)
    cur.executemany("""
    INSERT INTO songs (filename, title, artist, category, content)
    VALUES (?, ?, ?, ?, ?);
    """, records)
    conn.commit()
    print(f"      -> Selesai insert songs ({time.time() - start_time:.2f}s)", flush=True)
    
    # 4. Create FTS5 & Rebuild Index
    print("[3/4] Membangun indeks pencarian Full-Text Search (FTS5)...", flush=True)
    cur.execute("""
    CREATE VIRTUAL TABLE songs_fts USING fts5(
        title, artist, category, content,
        content='songs',
        content_rowid='id'
    );
    """)
    
    # Rebuild FTS5 table from content table in one fast batch
    cur.execute("INSERT INTO songs_fts(songs_fts) VALUES('rebuild');")
    conn.commit()
    print(f"      -> Selesai indeks FTS5 ({time.time() - start_time:.2f}s)", flush=True)
    
    # 5. Attach Triggers for future CRUD
    print("[4/4] Mendaftarkan triggers otomatis...", flush=True)
    cur.execute("""
    CREATE TRIGGER songs_ai AFTER INSERT ON songs BEGIN
      INSERT INTO songs_fts(rowid, title, artist, category, content) 
      VALUES (new.id, new.title, new.artist, new.category, new.content);
    END;
    """)
    cur.execute("""
    CREATE TRIGGER songs_ad AFTER DELETE ON songs BEGIN
      INSERT INTO songs_fts(songs_fts, rowid, title, artist, category, content) 
      VALUES('delete', old.id, old.title, old.artist, old.category, old.content);
    END;
    """)
    cur.execute("""
    CREATE TRIGGER songs_au AFTER UPDATE ON songs BEGIN
      INSERT INTO songs_fts(songs_fts, rowid, title, artist, category, content) 
      VALUES('delete', old.id, old.title, old.artist, old.category, old.content);
      INSERT INTO songs_fts(rowid, title, artist, category, content) 
      VALUES (new.id, new.title, new.artist, new.category, new.content);
    END;
    """)
    
    # Checkpoint WAL to main db file
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    cur.execute("PRAGMA optimize;")
    conn.close()
    
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    elapsed = time.time() - start_time
    print(f"\n[SUKSES] Seluruh 20.301 lagu berhasil dimigrasi dalam {elapsed:.2f} detik!", flush=True)
    print(f"  * Lokasi Database : {DB_PATH}", flush=True)
    print(f"  * Ukuran Database : {size_mb:.2f} MB", flush=True)
    print("==============================================================================", flush=True)

if __name__ == "__main__":
    main()
