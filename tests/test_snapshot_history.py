"""Comparing any two snapshots, deleting one, and retention after a collection."""
import csv
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from queue import Queue
from unittest.mock import Mock, patch

import app
from reporting import save_snapshot_diff
from snapshots import SnapshotStore


def record(ip, ram):
    return {"ip": ip, "status": "ONLINE", "ram": ram, "processador": "Example CPU"}


class SnapshotHistoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.store = SnapshotStore(self.root / "snapshots.db")
        self.ids = [
            self.store.save_snapshot([record("192.0.2.1", ram)], created_at=f"2026-0{month}-01 10:00:00")["id"]
            for month, ram in ((1, "4 GiB"), (2, "8 GiB"), (3, "8 GiB"), (4, "16 GiB"))
        ]

    def test_any_two_snapshots_compare_and_the_export_names_the_period(self):
        diff = self.store.compute_diff(self.ids[3], self.ids[0])
        self.assertEqual([(c["previous_value"], c["current_value"]) for c in diff["changes"]], [("4 GiB", "16 GiB")])
        with self.assertRaises(ValueError):
            self.store.compute_diff(self.ids[3], 999)
        path = save_snapshot_diff(
            diff["changes"], self.root, self.ids[3], "en", base_snapshot=diff["base_snapshot"], snapshot=diff["snapshot"]
        )
        self.assertEqual(path.name, f"snapshot_diff_{self.ids[0]}_{self.ids[3]}.csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(rows[0]["Previous snapshot"], "2026-01-01 10:00:00")
        self.assertEqual(rows[0]["Current snapshot"], "2026-04-01 10:00:00")

    def test_deleting_a_snapshot_recounts_the_next_one(self):
        self.assertEqual(self.store.delete_snapshots([self.ids[2]]), [self.ids[2]])
        listed = {snap["id"]: snap["changes_count"] for snap in self.store.list_snapshots()}
        self.assertNotIn(self.ids[2], listed)
        # The April snapshot now follows February: 8 GiB -> 16 GiB is still one change.
        self.assertEqual(listed[self.ids[3]], 1)
        self.store.delete_snapshots([self.ids[0]])
        listed = {snap["id"]: snap["changes_count"] for snap in self.store.list_snapshots()}
        self.assertEqual(listed[self.ids[1]], 0)
        self.assertEqual(self.store.delete_snapshots([999]), [])

    def test_retention_by_count_and_by_age_keeps_the_newest(self):
        now = datetime(2026, 4, 20)
        self.assertEqual(self.store.prune(0, 0, now=now), [])
        self.assertEqual(self.store.prune(keep_days=90, now=now), [self.ids[0]])
        self.assertEqual(self.store.prune(keep_last=2, now=now), [self.ids[1]])
        self.assertEqual(self.store.prune(keep_days=1, now=now), [self.ids[2]])
        self.assertEqual([snap["id"] for snap in self.store.list_snapshots()], [self.ids[3]])


class SnapshotControllerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.store = SnapshotStore(self.root / "snapshots.db")
        self.controller = app.InventoryController(config_path=self.root / "config.json", snapshot_store=self.store)

    def finish_collection(self):
        controller = self.controller
        controller.records = [record("192.0.2.1", "8 GiB")]
        controller._reset_records()
        controller.scanning = True
        controller._run_scan_worker(Mock(), Queue(), "targets.csv")

    def test_retention_runs_after_a_collection(self):
        self.controller.update_config({"snapshot_keep_last": 2})
        for _ in range(3):
            self.finish_collection()
        self.assertEqual(len(self.store.list_snapshots()), 2)
        self.assertEqual(len(self.controller.get_state()["snapshots"]), 2)
        saved = json.loads((self.root / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["snapshot_keep_last"], 2)
        self.controller.update_config({"snapshot_keep_days": "x"})
        self.assertEqual(self.controller.config["snapshot_keep_days"], 0)

    def test_http_compare_export_and_delete(self):
        first = self.store.save_snapshot([record("192.0.2.1", "4 GiB")], created_at="2026-01-01 10:00:00")["id"]
        self.store.save_snapshot([record("192.0.2.1", "8 GiB")], created_at="2026-02-01 10:00:00")
        last = self.store.save_snapshot([record("192.0.2.1", "16 GiB")], created_at="2026-03-01 10:00:00")["id"]
        server, url, token = app.create_http_server(self.controller)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def call(path, body=None):
            request = urllib.request.Request(
                url + path, headers={"X-Invenux-Token": token, "Content-Type": "application/json"},
                data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
            )
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read())

        diff = call(f"api/snapshots/{last}/diff?base={first}")
        self.assertEqual(diff["base_snapshot"]["id"], first)
        self.assertEqual(diff["changes"][0]["previous_value"], "4 GiB")
        with patch("app.get_reports_dir", return_value=self.root):
            exported = call(f"api/snapshots/{last}/diff/export", {"base": first})
        self.assertTrue(exported["path"].endswith(f"snapshot_diff_{first}_{last}.csv"))
        state = call(f"api/snapshots/{first}/delete", {})
        self.assertEqual([snap["id"] for snap in state["snapshots"]], [last, last - 1])
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            call(f"api/snapshots/{first}/delete", {})
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
