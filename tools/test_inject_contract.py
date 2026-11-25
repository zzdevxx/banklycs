#!/usr/bin/env python3
"""Integration regression tests for /api/inject naming and inline-content contracts.

Every test starts an engine process with a temporary ProPresenter root and a
temporary LOCALAPPDATA. Operator libraries, playlists, themes, config, and any
service started outside this test are never read or modified.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = ROOT / "desktop" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "banklycs.exe"
PORT_FILE = ROOT / "engine" / "last_port.txt"

CATALOG_SONG = "Ku Berbahagia - KJ 392.txt"
MISSING_SONG = "Sentuh Hatiku - Jason.txt"
CATALOG_VARIANT = "Sentuh Hatiku - Maria Shandi.txt"
CUSTOM_SONG = "Lagu Baru Custom - E2E.txt"
INJECT_HEADERS = {"X-Banklycs-Inject": "1"}


def http_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        with error:
            raw = error.read().decode("utf-8", errors="replace")
        return error.code, json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}


@contextmanager
def isolated_engine() -> Iterator[tuple[str, Path]]:
    if not EXE_PATH.is_file():
        raise RuntimeError(f"Engine binary not found: {EXE_PATH}")

    original_port_bytes = PORT_FILE.read_bytes() if PORT_FILE.is_file() else None
    with tempfile.TemporaryDirectory(prefix="banklycs_contract_") as tmp:
        tmp_root = Path(tmp)
        pro_dir = tmp_root / "ProPresenter"
        (pro_dir / "Libraries" / "Banks").mkdir(parents=True)
        (pro_dir / "Playlists").mkdir(parents=True)
        local_appdata = tmp_root / "LocalAppData"
        local_appdata.mkdir()

        env = os.environ.copy()
        env["BANKLYCS_PROPRESENTER_DIR"] = str(pro_dir)
        env["LOCALAPPDATA"] = str(local_appdata)

        process = subprocess.Popen(
            [str(EXE_PATH), "serve", "--no-browser"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            port = None
            for _ in range(120):
                for candidate in range(5050, 5056):
                    try:
                        code, status = http_json(f"http://127.0.0.1:{candidate}/api/status")
                        if code == 200 and status.get("propresenter_dir") == str(pro_dir):
                            port = candidate
                            break
                    except Exception:
                        pass
                if port is not None:
                    break
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    raise RuntimeError(f"Engine exited early ({process.returncode}):\n{output}")
                time.sleep(0.25)
            if port is None:
                raise RuntimeError("Timed out waiting for an isolated StudioServer")

            yield f"http://127.0.0.1:{port}", pro_dir
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()

    if original_port_bytes is None:
        if PORT_FILE.is_file():
            PORT_FILE.unlink()
    else:
        PORT_FILE.write_bytes(original_port_bytes)


class InjectContractTests(unittest.TestCase):
    def inject(
        self,
        base: str,
        songs: list[str],
        contents: dict[str, str] | None = None,
        name: str = "Contract Test",
        headers: dict[str, str] | None = INJECT_HEADERS,
    ) -> tuple[int, dict]:
        payload: dict = {"name": name, "songs": songs}
        if contents is not None:
            payload["contents"] = contents
        return http_json(f"{base}/api/inject", "POST", payload, headers)

    def test_inline_contents_key_with_txt_suffix_compiles(self) -> None:
        with isolated_engine() as (base, pro_dir):
            code, result = self.inject(
                base,
                [CUSTOM_SONG],
                {CUSTOM_SONG: "VERSE 1\nPuji Tuhan hai jiwaku\n"},
            )
            self.assertEqual(code, 200, result)
            self.assertTrue(result["success"], result)
            self.assertEqual(result["compiled_to_library"], 1, result)
            self.assertEqual(result["missing_in_pro"], [], result)
            target = pro_dir / "Libraries" / "Banks" / "Lagu Baru Custom - E2E.pro"
            self.assertTrue(target.is_file(), f"Missing compiled presentation: {target}")

    def test_exact_catalog_filename_compiles(self) -> None:
        with isolated_engine() as (base, pro_dir):
            code, result = self.inject(base, [CATALOG_SONG])
            self.assertEqual(code, 200, result)
            self.assertEqual(result["compiled_to_library"], 1, result)
            target = pro_dir / "Libraries" / "Banks" / "Ku Berbahagia - KJ 392.pro"
            self.assertTrue(target.is_file(), f"Missing compiled presentation: {target}")

    def test_existing_catalog_variant_compiles(self) -> None:
        with isolated_engine() as (base, pro_dir):
            code, result = self.inject(base, [CATALOG_VARIANT])
            self.assertEqual(code, 200, result)
            self.assertEqual(result["compiled_to_library"], 1, result)

    def test_unknown_song_is_not_fuzzy_matched(self) -> None:
        with isolated_engine() as (base, pro_dir):
            code, result = self.inject(base, [MISSING_SONG])
            self.assertEqual(code, 500, result)
            self.assertEqual(result["compiled_to_library"], 0, result)
            self.assertIn("Sentuh Hatiku - Jason.pro", result["missing_in_pro"], result)
            banks = list((pro_dir / "Libraries" / "Banks").glob("*.pro"))
            self.assertEqual(banks, [], f"Unexpected fuzzy compilation: {banks}")

    def test_precondition_and_traversal_guards_remain_active(self) -> None:
        with isolated_engine() as (base, _):
            code_no_header, _ = self.inject(base, [CATALOG_SONG], headers=None)
            self.assertEqual(code_no_header, 428)

            code_traversal, _ = http_json(
                f"{base}/api/inject",
                "POST",
                {"name": "Guard", "songs": ["..\\..\\evil.txt"]},
                INJECT_HEADERS,
            )
            self.assertEqual(code_traversal, 400)

            encoded = urllib.parse.quote("..%2F..%2Fevil.txt")
            code_encoded, _ = http_json(
                f"{base}/api/inject",
                "POST",
                {"name": "Guard", "songs": [encoded]},
                INJECT_HEADERS,
            )
            self.assertEqual(code_encoded, 400)


if __name__ == "__main__":
    unittest.main()
