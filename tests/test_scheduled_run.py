"""Headless scheduled runs: a snapshot per run and a change file with hardware differences only."""
import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import core
from snapshots import SnapshotStore


class ScheduledRunTests(unittest.TestCase):
    def setUp(self):
        from i18n import get_language, set_language

        previous = get_language()
        set_language("en")
        self.addCleanup(set_language, previous)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.targets = self.root / "targets.csv"
        self.targets.write_text("IP\n192.0.2.10\n192.0.2.11\n", encoding="utf-8")
        self.changes = self.root / "out" / "changes.csv"
        self.store = SnapshotStore(self.root / "snapshots.db")
        self.fleet = {
            "192.0.2.10": {"status": "SUCESSO", "ram": "8.0 GiB", "processador": "CPU A", "kernel": "6.1"},
            "192.0.2.11": {"status": "SUCESSO", "ram": "4.0 GiB", "processador": "CPU B", "kernel": "6.1"},
        }

    def run_scheduled(self):
        original = app.InventoryController

        def make_controller():
            return original(config_path=self.root / "config.json", snapshot_store=self.store)

        def fake_get_hardware_info(**kwargs):
            return {**self.fleet[kwargs["ip"]], "hardware_details": {}}

        with (
            patch("app.setup_logging"),
            patch("app.InventoryController", side_effect=make_controller),
            patch("app.get_reports_dir", return_value=self.root),
            patch.object(core, "get_hardware_info", side_effect=fake_get_hardware_info),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return app.main([
                "--input", str(self.targets), "--user", "inventory", "--key", str(self.targets),
                "--output-format", "CSV", "--report-changes", str(self.changes),
            ])

    def change_rows(self):
        with self.changes.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle, delimiter=";"))

    def test_each_run_saves_a_snapshot_and_reports_only_hardware_changes(self):
        self.assertEqual(self.run_scheduled(), 0)
        self.assertEqual(len(self.store.list_snapshots()), 1)
        self.assertEqual(self.changes.read_bytes(), b"")

        self.assertEqual(self.run_scheduled(), 0)
        self.assertEqual(self.changes.read_bytes(), b"")

        # A memory upgrade on one machine, a kernel update on the other: only the memory is hardware.
        self.fleet["192.0.2.10"]["ram"] = "16.0 GiB"
        self.fleet["192.0.2.11"]["kernel"] = "6.8"
        self.run_scheduled()
        rows = self.change_rows()
        self.assertEqual([(r["IP"], r["Field"], r["Previous value"], r["Current value"]) for r in rows],
                         [("192.0.2.10", "Memory", "8.0 GiB", "16.0 GiB")])

        # A machine that is off has no hardware to compare; that is not a change.
        self.fleet["192.0.2.11"] = {"status": "FALHA_CONEXAO", "erro": "timeout"}
        self.run_scheduled()
        self.assertEqual(self.changes.read_bytes(), b"")
        self.assertEqual(len(self.store.list_snapshots()), 4)


if __name__ == "__main__":
    unittest.main()
