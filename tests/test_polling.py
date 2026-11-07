"""Incremental state delivery and scan completion."""
import json
from pathlib import Path
from queue import Queue
import tempfile
import unittest
from unittest.mock import Mock, patch

import app
from scripts.demo_server import fake_collector, fleet
from snapshots import SnapshotStore


class PollingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.controller = app.InventoryController(
            config_path=self.root / "config.json",
            snapshot_store=SnapshotStore(self.root / "snapshots.db"),
        )

    def test_http_revision_parameter_and_legacy_response(self):
        with patch("app.ThreadingHTTPServer") as server:
            server.return_value.server_address = ("127.0.0.1", 8765)
            app.create_http_server(self.controller)
            handler_class = server.call_args.args[1]
        handler = object.__new__(handler_class)
        handler._check_host = Mock(return_value=True)
        handler._check_token = Mock(return_value=True)
        handler._send_json = Mock()
        for query in ("", "?since=0", "?since=invalid", "?since=-1", "?since="):
            with self.subTest(query=query):
                handler.path = "/api/state" + query
                handler.do_GET()
                response = handler._send_json.call_args
                if query in ("", "?since=0"):
                    self.assertEqual(response.args[0]["reset"], query == "")
                    self.assertEqual(response.args[0]["revision"], 0)
                else:
                    self.assertEqual(response.kwargs["status"], 400)

    def test_empty_cancelled_collection_finishes_without_snapshot(self):
        controller = self.controller
        controller.records = [{"ip": "192.0.2.1", "status": "PENDING"}]
        controller._reset_records()
        controller.scanning = True
        engine = Mock()
        controller.active_engine = engine
        controller.cancel_scan()
        engine.cancel.assert_called_once()
        controller._run_scan_worker(engine, Queue(), "targets.csv")
        state = controller.get_state(controller.revision)
        self.assertFalse(state["scanning"])
        self.assertEqual(state["snapshots"], [])
        self.assertEqual(state["records"], [])

    def test_snapshot_failure_does_not_leave_collection_running(self):
        controller = self.controller
        controller.records = [{"ip": "192.0.2.1", "status": "ONLINE"}]
        controller.scanning = True
        with patch.object(controller.snapshot_store, "save_snapshot", side_effect=OSError("disk full")):
            with self.assertLogs("app", level="WARNING"):
                controller._run_scan_worker(Mock(), Queue(), "targets.csv")
        self.assertFalse(controller.get_state()["scanning"])

    def test_unchanged_poll_reuses_analysis_and_does_not_read_snapshots(self):
        controller = self.controller
        with patch("app.compute_fleet_analytics", wraps=app.compute_fleet_analytics) as analytics:
            initial = controller.get_state()
            controller.scanning = True
            with patch.object(controller.snapshot_store, "list_snapshots") as snapshots:
                delta = controller.get_state(initial["revision"])
                legacy = controller.get_state()
            snapshots.assert_not_called()
            analytics.assert_called_once()
        self.assertEqual(delta["records"], [])
        self.assertNotIn("analytics", delta)
        self.assertNotIn("snapshots", delta)
        self.assertIn("analytics", legacy)
        self.assertIn("snapshots", legacy)

    def test_replacement_resets_stale_and_future_cursors(self):
        controller = self.controller
        initial = controller.get_state()
        targets = self.root / "targets.csv"
        targets.write_text("IP\n192.0.2.1\n")
        loaded = controller.load_targets(str(targets))
        for since in (initial["revision"], loaded["revision"] + 1):
            state = controller.get_state(since)
            self.assertTrue(state["reset"])
            self.assertEqual(state["records"], loaded["records"])
        self.assertEqual(controller.get_state(loaded["revision"])["records"], [])

    def test_3000_machine_backlog_is_delivered_without_loss_under_200kb(self):
        controller = self.controller
        machines = fleet("en", 3000)
        self.assertEqual(len({machine["ip"] for machine in machines}), 3000)
        collect = fake_collector(machines)
        with patch("scripts.demo_server.time.sleep"):
            controller.records = [dict(collect(m["ip"], "", "", ""), ip=m["ip"], status="ONLINE") for m in machines]
        controller.scanning = True
        controller.revision = 3000
        controller.record_revisions = {m["ip"]: i + 1 for i, m in enumerate(machines)}
        since = 0
        received = {}
        sizes = []
        while True:
            state = controller.get_state(since)
            sizes.append(len(json.dumps(state, ensure_ascii=False).encode("utf-8")))
            self.assertLess(sizes[-1], 200_000)
            self.assertFalse(state["reset"])
            received.update((record["ip"], record) for record in state["records"])
            self.assertGreater(state["revision"], since)
            since = state["revision"]
            if not state["more"]:
                break
        self.assertEqual(list(received.values()), controller.records)
        self.assertEqual(since, controller.revision)
        print(f"3000 machines: {len(sizes)} batches, max {max(sizes)} bytes")

    def test_worker_publishes_snapshot_before_finishing_and_keeps_latest_record(self):
        controller = self.controller
        controller.records = [{"ip": "192.0.2.1", "status": "PENDING"}]
        controller._reset_records()
        revision = controller.revision
        controller.scanning = True
        queue = Queue()
        engine = Mock()
        def run():
            for ram in ("4 GiB", "8 GiB"):
                queue.put(("HOST_RESULT", "", {"ip": "192.0.2.1", "status": "ONLINE", "ram": ram}))
        engine.run_inventory = run
        save = controller.snapshot_store.save_snapshot
        def save_while_scanning(*args, **kwargs):
            self.assertTrue(controller.get_state(revision)["scanning"])
            return save(*args, **kwargs)
        with patch.object(controller.snapshot_store, "save_snapshot", side_effect=save_while_scanning):
            controller._run_scan_worker(engine, queue, "targets.csv")
        state = controller.get_state(revision)
        self.assertFalse(state["scanning"])
        self.assertEqual(len(state["records"]), 1)
        self.assertEqual(state["records"][0]["ram"], "8 GiB")
        self.assertEqual(len(state["snapshots"]), 1)
        self.assertEqual(state["analytics"]["online"], 1)


if __name__ == "__main__":
    unittest.main()
