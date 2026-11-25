#!/usr/bin/env python3
"""End-to-end automated integration and Playwright UI suite for Banklycs Studio Console."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = ROOT / "desktop" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "banklycs.exe"


def http_json(url: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        return err.code, json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}


def main() -> int:
    if not EXE_PATH.is_file():
        print(f"[FAIL] Engine binary not found: {EXE_PATH}")
        return 1

    local_cfg_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Banklycs"
    saved_backups: dict[Path, bytes] = {}
    for name in ("config.json", "inject_state.json"):
        p = local_cfg_dir / name
        if p.is_file():
            saved_backups[p] = p.read_bytes()

    with tempfile.TemporaryDirectory(prefix="banklycs_e2e_pro7_") as tmp_dir:
        tmp_pro = Path(tmp_dir) / "ProPresenter"
        (tmp_pro / "Libraries" / "Banks").mkdir(parents=True, exist_ok=True)
        (tmp_pro / "Playlists").mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["BANKLYCS_PROPRESENTER_DIR"] = str(tmp_pro)

        proc = subprocess.Popen(
            [str(EXE_PATH), "serve"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        port = None
        try:
            t0 = time.time()
            for _ in range(80):
                for cand in range(5050, 5056):
                    try:
                        code, st = http_json(f"http://127.0.0.1:{cand}/api/status")
                        if code == 200 and st.get("propresenter_dir") == str(tmp_pro):
                            port = cand
                            break
                    except Exception:
                        pass
                if port:
                    break
                if proc.poll() is not None:
                    raise RuntimeError(f"Engine exited early: {proc.returncode}\n{proc.stdout.read()}\n{proc.stderr.read()}")
                time.sleep(0.25)

            if not port:
                raise RuntimeError("Timed out waiting for StudioServer /api/status")

            base = f"http://127.0.0.1:{port}"
            print(f"[OK] Engine listening on {base} in {time.time() - t0:.2f}s (sandboxed ProPresenter dir)")

            # 1. Status & category counts parity
            _, status = http_json(f"{base}/api/status")
            assert status["total_songs"] == 54204, f"Expected 54204 songs, got {status['total_songs']}"
            assert status["app_version"] == "2.7", f"Expected app_version 2.7, got {status['app_version']}"

            expected_cats = {
                "EN": 34979, "ID": 14679, "KJ": 998, "BE": 844, "KK": 758,
                "JAWA": 752, "KLIK": 433, "PKJ": 378, "NKB": 338, "NNBT": 45,
            }
            cat_sum = 0
            for cat, expected_n in expected_cats.items():
                code, d = http_json(f"{base}/api/songs?category={cat}")
                assert code == 200 and d["total_matched"] == expected_n, f"{cat}: {d['total_matched']} != {expected_n}"
                cat_sum += d["total_matched"]
            assert cat_sum == 54204
            print("[OK] Verified all 10 categories sum to 54,204 songs")

            # 2. Search & lyrics special characters
            for q in ("kasih", "KJ 392", "Tuhan Pasti Sanggup", "'Kau Tetap", '" Gusti'):
                code, res = http_json(f"{base}/api/songs?q={urllib.parse.quote(q)}")
                assert code == 200 and res["total_matched"] >= 1, f"Search failed for {q}"
                fn = res["songs"][0]["filename"]
                lcode, ldata = http_json(f"{base}/api/lyrics?file={urllib.parse.quote(fn)}")
                assert lcode == 200 and ldata.get("raw"), f"Lyrics missing for {fn}"
            code400, _ = http_json(f"{base}/api/lyrics")
            assert code400 == 400
            code404, _ = http_json(f"{base}/api/lyrics?file=NonExistent_12345.txt")
            assert code404 == 404
            print("[OK] Search, special-char quotes/ampersands, and /api/lyrics error codes verified")

            # 3. Settings & Theme selection persistence
            code, themes = http_json(f"{base}/api/themes")
            assert code == 200 and themes.get("propresenter_dir") == str(tmp_pro)
            code, sel = http_json(f"{base}/api/themes/select", "POST", {"slide_name": "Lyric - Worship"})
            assert code == 200 and sel["active_theme"] == "Lyric - Worship"
            code, sel = http_json(f"{base}/api/themes/select", "POST", {"slide_name": "Lyric - Praise"})
            assert code == 200 and sel["active_theme"] == "Lyric - Praise"
            code, set_res = http_json(
                f"{base}/api/settings",
                "POST",
                {"app_auto_check": True, "db_auto_check": True, "protect_user_edits": True},
            )
            assert code == 200 and set_res["success"] is True
            print("[OK] Theme selection and /api/settings roundtrip verified")

            # 4. Security guards (428 missing header, 400 traversal)
            c428, _ = http_json(f"{base}/api/inject", "POST", {"playlist": "T", "songs": ["Sentuh Hatiku - Jason.txt"]})
            assert c428 == 428, f"Expected 428 without header, got {c428}"
            c400, _ = http_json(
                f"{base}/api/inject",
                "POST",
                {"playlist": "T", "songs": ["..\\..\\evil.txt"]},
                {"X-Banklycs-Inject": "1"},
            )
            assert c400 == 400, f"Expected 400 traversal, got {c400}"

            # 5. Protobuf Inject + Protect User Edits + Delete Playlist + Clean Banks
            inj_headers = {"X-Banklycs-Inject": "1"}
            c200, inj = http_json(
                f"{base}/api/inject",
                "POST",
                {
                    "playlist": "E2E Ibadah Test",
                    "songs": ["Sentuh Hatiku - Jason.txt", "Ku Berbahagia - KJ 392.txt", "Lagu Baru Custom - E2E.txt"],
                    "contents": {"Lagu Baru Custom - E2E.txt": "VERSE 1\nPuji Tuhan hai jiwaku\nSelalu bersyukur\n"},
                    "styles": {"Sentuh Hatiku - Jason.txt": "worship"},
                },
                inj_headers,
            )
            assert c200 == 200 and inj["success"] is True and inj["compiled_count"] == 3, f"Inject unexpected: {inj}"
            banks_dir = tmp_pro / "Libraries" / "Banks"
            target_pro = banks_dir / "Sentuh Hatiku - Jason.pro"
            assert target_pro.is_file() and target_pro.stat().st_size > 200
            assert (banks_dir / "Ku Berbahagia - KJ 392.pro").is_file()
            assert (banks_dir / "Lagu Baru Custom - E2E.pro").is_file()
            assert (tmp_pro / "Playlists" / "Library").is_file()

            # Simulate operator editing Sentuh Hatiku inside ProPresenter 7
            edited_bytes = target_pro.read_bytes() + b"\x00USER_EDIT"
            target_pro.write_bytes(edited_bytes)
            c200, inj2 = http_json(
                f"{base}/api/inject",
                "POST",
                {"playlist": "E2E Ibadah Test", "songs": ["Sentuh Hatiku - Jason.txt"]},
                inj_headers,
            )
            assert c200 == 200 and "Sentuh Hatiku - Jason.pro" in (inj2.get("skipped_modified") or [])
            assert target_pro.read_bytes() == edited_bytes, "User-edited .pro was overwritten!"

            c200, del_res = http_json(f"{base}/api/playlist/delete", "POST", {"name": "E2E Ibadah Test"}, inj_headers)
            assert c200 == 200 and del_res["success"] is True
            c404, _ = http_json(f"{base}/api/playlist/delete", "POST", {"name": "E2E Ibadah Test"}, inj_headers)
            assert c404 == 404

            c200, cln = http_json(f"{base}/api/banks/clean", "POST", {}, inj_headers)
            assert c200 == 200 and len(list(banks_dir.glob("*.pro"))) == 0
            print("[OK] Protobuf inject, Protect User Edits, Playlist Delete, and Clean Banks verified")

            # 6. Playwright UI E2E across laptop widths
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                for w, h in [(1000, 760), (1280, 800), (1366, 768), (1440, 900)]:
                    page = browser.new_page(viewport={"width": w, "height": h})
                    errs = []
                    bad_http = []
                    page.on("pageerror", lambda e: errs.append(f"PAGEERROR:{e}"))
                    page.on("console", lambda m: errs.append(f"CONSOLE:{m.text}") if m.type == "error" else None)
                    page.on("response", lambda r: bad_http.append(f"{r.status} {r.url}") if r.status >= 400 and "favicon" not in r.url else None)

                    page.goto(base, wait_until="networkidle")
                    page.wait_for_timeout(500)

                    # Click ALL 11 category tabs without overlap/interception
                    tabs = page.locator(".pro-tab")
                    assert tabs.count() == 11, f"Expected 11 tabs, got {tabs.count()}"
                    for idx in range(tabs.count()):
                        tabs.nth(idx).click(timeout=3000)

                    # Back to All & search
                    page.click("#tab-ALL")
                    page.fill("#search-input", "Sentuh Hatiku")
                    page.wait_for_timeout(250)
                    options = page.locator("#song-list [role='option']")
                    assert options.count() >= 1
                    options.first.click()
                    page.wait_for_timeout(300)
                    assert len(page.locator("#inspector-content").inner_html()) > 100

                    if w == 1280:
                        page.click("#add-to-rundown-btn")
                        page.wait_for_timeout(200)
                        assert page.locator("#rundown-count").inner_text().strip() == "1"

                        # Inject via UI button
                        page.click("#inject-btn")
                        page.wait_for_timeout(1200)
                        modal_title = page.locator("#modal-title").inner_text()
                        assert "Selesai" in modal_title or "Berhasil" in modal_title or "ProPresenter" in modal_title, modal_title
                        page.click("#modal-ok-btn")
                        page.wait_for_timeout(200)

                        # Open About & Settings modals
                        page.click("#about-btn")
                        page.wait_for_timeout(200)
                        img_ok = page.evaluate("() => { const i = document.querySelector('.about-photo'); return i && i.complete && i.naturalWidth > 0; }")
                        assert img_ok, "About author.jpg failed to load"
                        page.click("#about-ok-btn")

                        page.click("#settings-btn")
                        page.wait_for_timeout(250)
                        assert page.locator("#settings-pro-path").inner_text().strip() == str(tmp_pro)
                        page.click("#settings-cancel-btn")

                    has_em = page.evaluate("() => document.body.innerText.includes('\\u2014')")
                    assert not has_em, f"Found forbidden em-dash in UI at {w}px"
                    assert not errs, f"JS/Console errors at {w}px: {errs}"
                    assert not bad_http, f"HTTP >=400 at {w}px: {bad_http}"
                    page.close()
                browser.close()
            print("[OK] Playwright UI & all 11 toolbar tabs passed at 1000/1280/1366/1440px with 0 console errors")
            return 0
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
            for p in list(saved_backups):
                p.write_bytes(saved_backups[p])
            for name in ("config.json", "inject_state.json"):
                target = local_cfg_dir / name
                if target not in saved_backups and target.is_file():
                    target.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
