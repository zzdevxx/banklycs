#!/usr/bin/env python3
"""Integration regressions for inject contracts and local-data isolation.

Each test starts an engine with temporary ProPresenter and Banklycs data paths.
The helper checks the reported paths before yielding, so no test can send a
mutation request to an engine that is not isolated. Operator config files are
checked by SHA-256 only and must remain unchanged.
"""
from __future__ import annotations

import hashlib
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
OPERATOR_CONFIG_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
) / "Banklycs"


def operator_config_hashes() -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for filename in ("config.json", "inject_state.json"):
        path = OPERATOR_CONFIG_DIR / filename
        hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return hashes


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
def isolated_engine() -> Iterator[tuple[str, Path, Path]]:
    if not EXE_PATH.is_file():
        raise RuntimeError(f"Engine binary not found: {EXE_PATH}")

    original_port_bytes = PORT_FILE.read_bytes() if PORT_FILE.is_file() else None
    try:
        with tempfile.TemporaryDirectory(prefix="banklycs_contract_") as tmp:
            tmp_root = Path(tmp)
            pro_dir = tmp_root / "ProPresenter"
            (pro_dir / "Libraries" / "Banks").mkdir(parents=True)
            (pro_dir / "Playlists").mkdir(parents=True)
            local_appdata = tmp_root / "LocalAppData"
            config_dir = local_appdata / "Banklycs"
            config_dir.mkdir(parents=True)

            env = os.environ.copy()
            env["BANKLYCS_PROPRESENTER_DIR"] = str(pro_dir)
            env["LOCALAPPDATA"] = str(local_appdata)
            env["BANKLYCS_APPDATA_DIR"] = str(config_dir)

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
                                if status.get("config_dir") != str(config_dir):
                                    raise RuntimeError(
                                        "StudioServer does not support isolated app data: "
                                        f"config_dir={status.get('config_dir')!r}, expected {str(config_dir)!r}; "
                                        "refusing to run mutation tests"
                                    )
                                port = candidate
                                break
                        except urllib.error.URLError:
                            pass
                    if port is not None:
                        break
                    if process.poll() is not None:
                        output = process.stdout.read() if process.stdout else ""
                        raise RuntimeError(f"Engine exited early ({process.returncode}):\n{output}")
                    time.sleep(0.25)
                if port is None:
                    raise RuntimeError("Timed out waiting for an isolated StudioServer")

                yield f"http://127.0.0.1:{port}", pro_dir, config_dir
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()
    finally:
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

    def test_settings_and_inject_state_stay_in_sandbox(self) -> None:
        operator_hashes_before = operator_config_hashes()
        try:
            with isolated_engine() as (base, _pro_dir, config_dir):
                settings_code, settings_result = http_json(
                    f"{base}/api/settings",
                    "POST",
                    {"app_auto_check": False, "db_auto_check": False, "protect_user_edits": True},
                )
                self.assertEqual(settings_code, 200, settings_result)

                inject_code, inject_result = self.inject(base, [CATALOG_VARIANT])
                self.assertEqual(inject_code, 200, inject_result)

                config_path = config_dir / "config.json"
                inject_state_path = config_dir / "inject_state.json"
                self.assertTrue(config_path.is_file(), f"Settings were not saved under {config_dir}")
                self.assertTrue(inject_state_path.is_file(), f"Inject state was not saved under {config_dir}")
                self.assertTrue(config_path.resolve().is_relative_to(config_dir.resolve()))
                self.assertTrue(inject_state_path.resolve().is_relative_to(config_dir.resolve()))
        finally:
            self.assertEqual(operator_config_hashes(), operator_hashes_before)

    def test_inline_contents_key_with_txt_suffix_compiles(self) -> None:
        with isolated_engine() as (base, pro_dir, _config_dir):
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
        with isolated_engine() as (base, pro_dir, _config_dir):
            code, result = self.inject(base, [CATALOG_SONG])
            self.assertEqual(code, 200, result)
            self.assertEqual(result["compiled_to_library"], 1, result)
            target = pro_dir / "Libraries" / "Banks" / "Ku Berbahagia - KJ 392.pro"
            self.assertTrue(target.is_file(), f"Missing compiled presentation: {target}")

    def test_existing_catalog_variant_compiles(self) -> None:
        with isolated_engine() as (base, pro_dir, _config_dir):
            code, result = self.inject(base, [CATALOG_VARIANT])
            self.assertEqual(code, 200, result)
            self.assertEqual(result["compiled_to_library"], 1, result)

    def test_unknown_song_is_not_fuzzy_matched(self) -> None:
        with isolated_engine() as (base, pro_dir, _config_dir):
            code, result = self.inject(base, [MISSING_SONG])
            self.assertEqual(code, 500, result)
            self.assertEqual(result["compiled_to_library"], 0, result)
            self.assertIn("Sentuh Hatiku - Jason.pro", result["missing_in_pro"], result)
            banks = list((pro_dir / "Libraries" / "Banks").glob("*.pro"))
            self.assertEqual(banks, [], f"Unexpected fuzzy compilation: {banks}")

    def test_precondition_and_traversal_guards_remain_active(self) -> None:
        with isolated_engine() as (base, _pro_dir, _config_dir):
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
