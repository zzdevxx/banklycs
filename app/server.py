# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import subprocess
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Set root paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
DATABASE_DIR = os.path.join(PROJECT_ROOT, "database", "txt") if os.path.isdir(os.path.join(PROJECT_ROOT, "database", "txt")) else os.path.join(PROJECT_ROOT, "database")
PRO_DIR = os.path.join(PROJECT_ROOT, "database", "pro") if os.path.isdir(os.path.join(PROJECT_ROOT, "database", "pro")) else os.path.join(PROJECT_ROOT, "engine", "PRO")
ENGINE_EXE = os.path.join(PROJECT_ROOT, "engine", "banklycs.exe")

# Resolve ProPresenter directory
def get_propresenter_dir():
    # 1. Check OneDrive Documents
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        for doc_name in ["Documents", "Dokumen"]:
            cand = os.path.join(onedrive, doc_name, "ProPresenter")
            if os.path.isdir(cand):
                return cand
    # 2. Check User Documents
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        for doc_name in ["Documents", "Dokumen"]:
            cand = os.path.join(userprofile, doc_name, "ProPresenter")
            if os.path.isdir(cand):
                return cand
    return None

PROPRESENTER_DIR = get_propresenter_dir()

# Catalog in RAM for ultra-fast instant search
CATALOG = []

def determine_category(name):
    upper = name.upper()
    if re.search(r'\bKJ\s*\d+', upper): return "KJ"
    if re.search(r'\bNKB\s*\d+', upper): return "NKB"
    if re.search(r'\bPKJ\s*\d+', upper): return "PKJ"
    if re.search(r'\bKK\s*\d+', upper): return "KK"
    if re.search(r'\bBE\s*\d+', upper): return "BE"
    if re.search(r'\bKLIK\s*\d+', upper): return "KLIK"
    if re.search(r'\bNNBT\s*\d+', upper): return "NNBT"
    if "KIDUNG JAWA" in upper or "PASAMUWAN" in upper: return "JAWA"
    if any(k in upper for k in ["HILLSONG", "BETHEL", "ELEVATION", "PLANETSHAKERS", "TOMLIN", "REDMAN", "WICKHAM", "GAITHER"]):
        return "EN"
    return "ID"

def load_catalog():
    global CATALOG
    print(f"[CATALOG] Memindai folder database: {DATABASE_DIR}...")
    if not os.path.isdir(DATABASE_DIR):
        print(f"[ERROR] Folder database tidak ditemukan: {DATABASE_DIR}")
        return

    items = []
    for f in os.listdir(DATABASE_DIR):
        if not f.endswith(".txt"):
            continue
        base = f[:-4]
        artist = ""
        title = base
        if " - " in base:
            parts = base.split(" - ", 1)
            title = parts[0].strip()
            artist = parts[1].strip()

        cat = determine_category(base)
        items.append({
            "filename": f,
            "pro": f"{base}.pro",
            "title": title,
            "artist": artist,
            "category": cat,
            "search_index": f"{title} {artist} {base}".lower()
        })

    # Sort alphabetically by title
    items.sort(key=lambda x: x["title"].lower())
    CATALOG = items
    print(f"[CATALOG] Sukses memuat {len(CATALOG):,} lagu ke RAM!")

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json({
                "total_songs": len(CATALOG),
                "propresenter_dir": PROPRESENTER_DIR,
                "project_root": PROJECT_ROOT
            })
            return

        if path == "/api/songs":
            query_params = parse_qs(parsed.query)
            q = query_params.get("q", [""])[0].strip().lower()
            cat = query_params.get("category", ["ALL"])[0].strip().upper()
            limit = int(query_params.get("limit", [100])[0])

            results = []
            for item in CATALOG:
                if cat != "ALL" and item["category"] != cat:
                    continue
                if q:
                    # Match all tokens
                    tokens = q.split()
                    if not all(tok in item["search_index"] for tok in tokens):
                        continue
                results.append({
                    "filename": item["filename"],
                    "pro": item["pro"],
                    "title": item["title"],
                    "artist": item["artist"],
                    "category": item["category"]
                })
                if len(results) >= limit:
                    break

            self.send_json({
                "count": len(results),
                "songs": results
            })
            return

        if path == "/api/lyrics":
            query_params = parse_qs(parsed.query)
            filename = query_params.get("file", [""])[0].strip()
            file_path = os.path.join(DATABASE_DIR, filename)

            if not os.path.isfile(file_path):
                self.send_json({"error": "File tidak ditemukan"}, status=404)
                return

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                # Parse into groups and slides
                lines = content.splitlines()
                groups = []
                cur_group = {"header": "HEADER", "slides": []}
                cur_slide = []

                header_pattern = re.compile(r'^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$', re.I)

                for line in lines:
                    line_str = line.strip()
                    if not line_str:
                        if cur_slide:
                            cur_group["slides"].append(cur_slide)
                            cur_slide = []
                        continue

                    if header_pattern.match(line_str):
                        if cur_slide:
                            cur_group["slides"].append(cur_slide)
                            cur_slide = []
                        if cur_group["slides"]:
                            groups.append(cur_group)
                        cur_group = {"header": line_str.upper(), "slides": []}
                    else:
                        cur_slide.append(line_str)

                if cur_slide:
                    cur_group["slides"].append(cur_slide)
                if cur_group["slides"]:
                    groups.append(cur_group)

                self.send_json({
                    "filename": filename,
                    "title": filename[:-4],
                    "groups": groups,
                    "raw": content
                })
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # Serve static files from GUI_DIR
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/inject":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                playlist_name = data.get("name", "Ibadah Hari Minggu").strip()
                song_files = data.get("songs", [])

                if not song_files:
                    self.send_json({"error": "Daftar lagu kosong"}, status=400)
                    return

                if not PROPRESENTER_DIR:
                    self.send_json({"error": "Folder ProPresenter tidak ditemukan di sistem"}, status=500)
                    return

                # Target ProPresenter Banks library folder
                lib_banks = os.path.join(PROPRESENTER_DIR, "Libraries", "Banks")
                os.makedirs(lib_banks, exist_ok=True)

                # 1. Copy only the selected .pro files to ProPresenter Library Banks
                copied_count = 0
                missing_files = []
                for s in song_files:
                    pro_name = s if s.endswith(".pro") else f"{s}.pro"
                    src_file = os.path.join(PRO_DIR, pro_name)
                    dst_file = os.path.join(lib_banks, pro_name)

                    if os.path.isfile(src_file):
                        # Copy only if not exists or size differs
                        try:
                            import shutil
                            shutil.copy2(src_file, dst_file)
                            copied_count += 1
                        except Exception as copy_err:
                            print(f"[WARN] Gagal menyalin {src_file}: {copy_err}")
                    else:
                        missing_files.append(pro_name)

                # 2. Call ProEngine to create the playlist in ProPresenter
                req_json = {
                    "name": playlist_name,
                    "songs": song_files,
                    "workspace": PROJECT_ROOT
                }

                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
                    tmp_path = tmp.name
                    json.dump(req_json, tmp, ensure_ascii=False)

                try:
                    cmd = [ENGINE_EXE, "create-playlist", tmp_path]
                    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    output_msg = proc.stdout.strip()
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

                self.send_json({
                    "success": True,
                    "playlist": playlist_name,
                    "songs_count": len(song_files),
                    "copied_to_library": copied_count,
                    "missing_in_pro": missing_files,
                    "engine_output": output_msg
                })

            except subprocess.CalledProcessError as err:
                self.send_json({
                    "error": f"Engine gagal membuat playlist: {err.stderr or err.stdout}"
                }, status=500)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        self.send_json({"error": "Endpoint tidak ditemukan"}, status=404)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

def run_server(port=5050):
    load_catalog()
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, AppHandler)
    except OSError:
        # Fallback to port 5051 if 5050 is busy
        port = 5051
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, AppHandler)

    print("==============================================================================")
    print(f"  PROPRESENTER LYRICBANKS - PLAYLIST BUILDER GUI")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"  ProPresenter Dir: {PROPRESENTER_DIR}")
    print("==============================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Server dimatikan.")
        httpd.server_close()

if __name__ == "__main__":
    port = 5050
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
