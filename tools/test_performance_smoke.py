"""Regression tests for selecting the active Frigate SQLite database."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import performance_smoke as smoke


@unittest.skipUnless(sys.platform.startswith("linux"), "Uses Docker's procfs layout")
class TestDatabaseCheck(unittest.TestCase):
    def test_ignores_damaged_legacy_database_and_rejects_it_as_inactive(self):
        with tempfile.TemporaryDirectory() as temp:
            active = Path(temp) / "database" / "frigate.db"
            legacy = Path(temp) / "config" / "frigate.db"
            active.parent.mkdir()
            legacy.parent.mkdir()
            legacy.write_bytes(b"corrupt legacy database")

            def run_probe(command, **kwargs):
                self.assertEqual(command[:3], ["docker", "exec", "classic"])
                return subprocess.run(
                    [sys.executable, *command[4:]],
                    check=True,
                    capture_output=True,
                    **kwargs,
                ).stdout

            configured = {"database": {"path": str(active)}}
            with (
                closing(sqlite3.connect(active)) as db,
                patch.object(
                    smoke, "fetch", return_value=(json.dumps(configured), {}, 0)
                ),
                patch.object(smoke.subprocess, "check_output", side_effect=run_probe),
            ):
                db.execute("CREATE TABLE event (id TEXT)")
                result = smoke.check_database("http://localhost", "classic")
                self.assertEqual(result, {"database": str(active), "quick_check": "ok"})

                configured["database"]["path"] = str(legacy)
                with (
                    patch.object(
                        smoke, "fetch", return_value=(json.dumps(configured), {}, 0)
                    ),
                    self.assertRaises(subprocess.CalledProcessError) as expected,
                ):
                    smoke.check_database("http://localhost", "classic")
                self.assertIn(
                    "Configured database is not open", expected.exception.stderr
                )
