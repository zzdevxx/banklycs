#!/usr/bin/env python3
"""Launch Banklycs Studio Console with isolated ProPresenter and config roots.

Use this when a human or Playwright needs a live Studio Console URL without
touching the operator's libraries, playlists, themes, or app settings. The
script owns only the engine process it starts; it never stops another service.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = ROOT / "desktop" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "banklycs.exe"
PORT_FILE = ROOT / "engine" / "last_port.txt"


def fetch_status(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=3) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None
    return None


def wait_for_engine(pro_dir: Path, first_port: int, last_port: int, timeout_s: float) -> tuple[int, dict] | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for port in range(first_port, last_port + 1):
            status = fetch_status(port)
            if status is not None and status.get("propresenter_dir") == str(pro_dir):
                return port, status
        time.sleep(0.25)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-port", type=int, default=5050)
    parser.add_argument("--last-port", type=int, default=5055)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary ProPresenter/config tree after shutdown")
    args = parser.parse_args()

    if not EXE_PATH.is_file():
        print(f"[FAIL] Engine binary not found: {EXE_PATH}", file=sys.stderr)
        return 1
    if args.first_port < 1 or args.last_port < args.first_port:
        print("[FAIL] Invalid port range", file=sys.stderr)
        return 1

    temp_root = Path(tempfile.mkdtemp(prefix="banklycs_ui_"))
    pro_dir = temp_root / "ProPresenter"
    (pro_dir / "Libraries" / "Banks").mkdir(parents=True)
    (pro_dir / "Playlists").mkdir(parents=True)
    local_appdata = temp_root / "LocalAppData"
    local_appdata.mkdir()
    engine_log = temp_root / "engine.log"

    saved_port_bytes = PORT_FILE.read_bytes() if PORT_FILE.is_file() else None
    env = os.environ.copy()
    env["BANKLYCS_PROPRESENTER_DIR"] = str(pro_dir)
    env["LOCALAPPDATA"] = str(local_appdata)

    with engine_log.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            [str(EXE_PATH), "serve", "--no-browser"],
            cwd=str(ROOT),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
        try:
            found = wait_for_engine(pro_dir, args.first_port, args.last_port, args.timeout)
            if found is None:
                print(f"[FAIL] Engine did not become ready; log: {engine_log}", file=sys.stderr)
                return 1

            port, status = found
            info = {
                "url": f"http://127.0.0.1:{port}",
                "pid": process.pid,
                "proPresenterDir": str(pro_dir),
                "localAppData": str(local_appdata),
                "engineLog": str(engine_log),
                "catalogSongs": status.get("total_songs"),
                "appVersion": status.get("app_version"),
            }
            print(json.dumps(info, indent=2), flush=True)
            print("owned_process=this script only; press Ctrl+C to stop it.", flush=True)
            while process.poll() is None:
                time.sleep(1)
            print(f"[WARN] Engine exited with code {process.returncode}; log: {engine_log}", file=sys.stderr)
            return process.returncode or 0
        except KeyboardInterrupt:
            print("\n[INFO] Stopping owned engine process.", file=sys.stderr)
            return 130
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if saved_port_bytes is None:
                if PORT_FILE.is_file():
                    PORT_FILE.unlink()
            else:
                PORT_FILE.write_bytes(saved_port_bytes)
            if args.keep_temp:
                print(f"[INFO] Temporary session kept at {temp_root}", file=sys.stderr)
            else:
                shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
