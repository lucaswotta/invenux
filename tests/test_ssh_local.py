"""End-to-end collections against in-process SSH servers on 127.0.0.1."""
import os
import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import patch

import core
import inspector
from ssh_test_server import FakeSSHServer


class LocalSSHTests(unittest.TestCase):
    def setUp(self):
        from i18n import get_language, set_language

        previous = get_language()
        set_language("en")
        self.addCleanup(set_language, previous)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        # Keep the user's own known_hosts files out of the test.
        home = patch.dict(os.environ, {"HOME": str(self.tmp)})
        home.start()
        self.addCleanup(home.stop)
        known_hosts = patch.object(inspector, "get_known_hosts_path", return_value=self.tmp / "known_hosts")
        known_hosts.start()
        self.addCleanup(known_hosts.stop)

    def collect(self, spreadsheet: str, **config):
        path = self.tmp / "targets.csv"
        path.write_text(spreadsheet, encoding="utf-8")
        settings = {
            "filepath": str(path), "max_workers": 2, "ssh_timeout": 5, "ssh_user": "reader",
            "ssh_pass": "test-only", "ssh_key_path": "", "trust_unknown_hosts": True,
        }
        settings.update(config)
        engine = core.InventoryEngine(settings, Queue())
        engine.run_inventory()
        return {terminal.ip: terminal for terminal in engine.terminals}

    def test_row_port_reaches_its_server_and_the_rest_use_the_panel_port(self):
        with FakeSSHServer({"reader": "test-only"}) as panel, FakeSSHServer({"reader": "test-only"}) as row:
            # Two names for the loopback address make two distinct machines.
            results = self.collect(
                f"IP,SSH_PORT\n127.0.0.1,{row.port}\nlocalhost,\n",
                ssh_port=panel.port,
            )
        self.assertEqual(results["127.0.0.1"].status, "ONLINE")
        self.assertEqual(results["localhost"].status, "ONLINE")
        self.assertEqual(results["127.0.0.1"].ssh_port, row.port)
        self.assertEqual(results["localhost"].ssh_port, panel.port)
        self.assertEqual((row.connections, panel.connections), (1, 1))
        self.assertEqual(results["127.0.0.1"].kernel, "6.1.0-test")


if __name__ == "__main__":
    unittest.main()
