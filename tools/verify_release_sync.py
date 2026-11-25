#!/usr/bin/env python3
"""Verify release parity between banklycs (DB, manifest, app, installer) and banklycs-download."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "banklycs.db"
MANIFEST_PATH = ROOT / "database" / "db_manifest.json"
CSPROJ_PATH = ROOT / "desktop" / "Banklycs.App.csproj"
SERVER_PATH = ROOT / "engine" / "StudioServer.cs"
ISS_PATH = ROOT / "desktop" / "installer" / "banklycs.iss"
DIST_DIR = ROOT / "desktop" / "dist"
PORTAL_HTML = ROOT.parent / "banklycs-download" / "index.html"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []

    if not DB_PATH.exists():
        print(f"[FAIL] Missing database: {DB_PATH}")
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        total_songs = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        cats = dict(conn.execute("SELECT category, COUNT(*) FROM songs GROUP BY category ORDER BY COUNT(*) DESC").fetchall())
    finally:
        conn.close()

    if integrity != "ok":
        errors.append(f"SQLite integrity_check failed: {integrity}")

    db_bytes = DB_PATH.stat().st_size
    db_sha256 = sha256_file(DB_PATH)
    db_mib = round(db_bytes / (1024 * 1024))

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("size") != db_bytes:
        errors.append(f"db_manifest.json size {manifest.get('size')} != actual {db_bytes}")
    if manifest.get("sha256") != db_sha256:
        errors.append(f"db_manifest.json sha256 {manifest.get('sha256')} != actual {db_sha256}")

    csproj_text = CSPROJ_PATH.read_text(encoding="utf-8")
    server_text = SERVER_PATH.read_text(encoding="utf-8")
    iss_text = ISS_PATH.read_text(encoding="utf-8")

    m_csproj = re.search(r"<Version>([^<]+)</Version>", csproj_text)
    m_server = re.search(r'AppVersion\s*=\s*"([^"]+)"', server_text)
    m_iss = re.search(r'#define\s+MyAppVersion\s+"([^"]+)"', iss_text)

    v_csproj = m_csproj.group(1) if m_csproj else ""
    v_server = m_server.group(1) if m_server else ""
    v_iss = m_iss.group(1) if m_iss else ""

    if not (v_csproj and v_iss and v_csproj == v_iss):
        errors.append(f"Version mismatch: csproj={v_csproj} vs iss={v_iss}")
    if not v_csproj.startswith(v_server):
        errors.append(f"Version mismatch: csproj={v_csproj} vs StudioServer AppVersion={v_server}")

    installer_path = DIST_DIR / f"Banklycs-Setup-{v_csproj}.exe"
    installer_mb = None
    if installer_path.exists():
        installer_mb = round(installer_path.stat().st_size / 1_000_000)

    print(f"Database      : {total_songs:,} songs ({db_bytes:,} B / {db_mib} MiB), integrity={integrity}")
    print(f"Categories    : {cats}")
    print(f"Manifest      : version={manifest.get('version')}, sha256={db_sha256[:16]}...")
    print(f"App Version   : csproj={v_csproj}, server={v_server}, iss={v_iss}")
    if installer_mb is not None:
        print(f"Installer     : {installer_path.name} ({installer_path.stat().st_size:,} B / ~{installer_mb} MB)")

    if PORTAL_HTML.exists():
        html = PORTAL_HTML.read_text(encoding="utf-8")
        formatted_total = f"{total_songs:,}".replace(",", ".")
        if formatted_total not in html:
            errors.append(f"banklycs-download/index.html missing formatted song count {formatted_total}")
        if ".NET 8" in html:
            errors.append("banklycs-download/index.html still references .NET 8")
        if "banklycs.exe" in html:
            errors.append("banklycs-download/index.html still references obsolete banklycs.exe")
        if f"{db_mib} MB" not in html:
            errors.append(f"banklycs-download/index.html missing DB size {db_mib} MB")
        if f"Banklycs-Setup-{v_csproj}.exe" not in html:
            errors.append(f"banklycs-download/index.html missing installer filename Banklycs-Setup-{v_csproj}.exe")
        if installer_mb is not None and f"{installer_mb} MB" not in html:
            errors.append(f"banklycs-download/index.html missing installer size {installer_mb} MB")
        print(f"Portal Check  : inspected {PORTAL_HTML}")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return 1

    print("[PASS] All banklycs <-> banklycs-download release metrics are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
