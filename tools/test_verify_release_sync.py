from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import verify_release_sync


class VerifyReleaseSyncTests(unittest.TestCase):
    def test_portal_exact_byte_sizes_match_release_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "banklycs.db"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute("CREATE TABLE songs (category TEXT)")
                connection.executemany("INSERT INTO songs VALUES (?)", [("ID",)] * 1000)
                connection.execute("CREATE TABLE payload (data BLOB)")
                connection.execute("INSERT INTO payload VALUES (?)", (b"x" * (1024 * 1024),))
                connection.commit()
            finally:
                connection.close()

            database_size = database_path.stat().st_size
            database_sha256 = hashlib.sha256(database_path.read_bytes()).hexdigest()
            manifest_path = root / "db_manifest.json"
            manifest_path.write_text(json.dumps({"size": database_size, "sha256": database_sha256}), encoding="utf-8")

            csproj_path = root / "Banklycs.App.csproj"
            csproj_path.write_text("<Project><PropertyGroup><Version>2.7.0</Version></PropertyGroup></Project>", encoding="utf-8")
            server_path = root / "StudioServer.cs"
            server_path.write_text('const string AppVersion = "2.7";', encoding="utf-8")
            installer_script_path = root / "banklycs.iss"
            installer_script_path.write_text('#define MyAppVersion "2.7.0"', encoding="utf-8")

            dist_path = root / "dist"
            dist_path.mkdir()
            installer_path = dist_path / "Banklycs-Setup-2.7.0.exe"
            installer_path.write_bytes(b"installer" * 155_556)
            installer_size = installer_path.stat().st_size
            installer_sha256 = hashlib.sha256(installer_path.read_bytes()).hexdigest()

            def format_id(value: int) -> str:
                return f"{value:,}".replace(",", ".")

            portal_path = root / "index.html"
            portal_path.write_text(
                " ".join(
                    (
                        "1.000",
                        f"Ukuran database: {format_id(database_size)} byte",
                        database_sha256,
                        f"Ukuran installer: {format_id(installer_size)} byte",
                        installer_sha256,
                        "Banklycs-Setup-2.7.0.exe",
                    )
                ),
                encoding="utf-8",
            )

            with patch.multiple(
                verify_release_sync,
                DB_PATH=database_path,
                MANIFEST_PATH=manifest_path,
                CSPROJ_PATH=csproj_path,
                SERVER_PATH=server_path,
                ISS_PATH=installer_script_path,
                DIST_DIR=dist_path,
                PORTAL_HTML=portal_path,
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = verify_release_sync.main()

            self.assertEqual(exit_code, 0, output.getvalue())
            self.assertIn("[PASS]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
