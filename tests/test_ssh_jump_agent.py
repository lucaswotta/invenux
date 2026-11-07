"""ssh-agent and jump host collections against in-process SSH servers on 127.0.0.1."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import patch

import paramiko

import core
import inspector
from ssh_test_server import FakeSSHServer

# Reserved name (RFC 6761): the operator's computer cannot resolve it, only the bastion's routes can.
INTERNAL = "db.internal.test"


class JumpHostAndAgentTests(unittest.TestCase):
    def setUp(self):
        from i18n import get_language, set_language

        previous = get_language()
        set_language("en")
        self.addCleanup(set_language, previous)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        home = patch.dict(os.environ, {"HOME": str(self.tmp)})
        home.start()
        self.addCleanup(home.stop)
        self.known_hosts = self.tmp / "known_hosts"
        patcher = patch.object(inspector, "get_known_hosts_path", return_value=self.known_hosts)
        patcher.start()
        self.addCleanup(patcher.stop)

    def collect(self, rows, **config):
        path = self.tmp / "targets.csv"
        path.write_text("IP\n" + "".join(f"{row}\n" for row in rows), encoding="utf-8")
        settings = {
            "filepath": str(path), "max_workers": 4, "ssh_timeout": 5, "ssh_user": "reader",
            "ssh_pass": "test-only", "ssh_key_path": "", "trust_unknown_hosts": True,
        }
        settings.update(config)
        engine = core.InventoryEngine(settings, Queue())
        engine.run_inventory()
        return {terminal.ip: terminal for terminal in engine.terminals}

    def bastion_for(self, *targets, **options):
        routes = {(f"{index}.{INTERNAL}", 22): ("127.0.0.1", target.port) for index, target in enumerate(targets)}
        return FakeSSHServer({"jumper": "test-only"}, forwarding=True, routes=routes, **options)

    def test_collection_reaches_machines_routed_only_by_the_bastion(self):
        with FakeSSHServer({"reader": "test-only"}) as first, FakeSSHServer({"reader": "test-only"}) as second:
            with self.bastion_for(first, second) as bastion:
                results = self.collect(
                    [f"0.{INTERNAL}", f"1.{INTERNAL}"],
                    jump_host="127.0.0.1", jump_port=bastion.port, jump_user="jumper",
                )
            direct = self.collect([f"0.{INTERNAL}"])

        self.assertEqual({ip: r.status for ip, r in results.items()}, {f"0.{INTERNAL}": "ONLINE", f"1.{INTERNAL}": "ONLINE"})
        self.assertEqual(sorted(bastion.forwarded), [(f"0.{INTERNAL}", 22), (f"1.{INTERNAL}", 22)])
        # One login on the bastion serves the whole collection.
        self.assertEqual(bastion.connections, 1)
        self.assertEqual(bastion.logins, [("jumper", "password")])
        self.assertEqual((first.logins, second.logins), ([("reader", "password")], [("reader", "password")]))
        self.assertEqual(direct[f"0.{INTERNAL}"].status, "OFFLINE")

    def test_bastion_failure_is_reported_on_each_machine_once(self):
        with FakeSSHServer({"reader": "test-only"}) as target, self.bastion_for(target) as bastion:
            results = self.collect([f"0.{INTERNAL}"], jump_host="127.0.0.1", jump_port=bastion.port, jump_user="intruder")
        self.assertEqual(results[f"0.{INTERNAL}"].status, "OFFLINE")
        self.assertIn("Jump host 127.0.0.1", results[f"0.{INTERNAL}"].erro)
        self.assertIn("authentication", results[f"0.{INTERNAL}"].erro.lower())
        self.assertEqual(target.connections, 0)

    def test_host_keys_are_checked_on_the_bastion_and_on_each_target(self):
        with FakeSSHServer({"reader": "test-only"}) as target, self.bastion_for(target) as bastion:
            jump = {"jump_host": "127.0.0.1", "jump_port": bastion.port, "jump_user": "jumper"}
            name = f"0.{INTERNAL}"

            unknown_bastion = self.collect([name], trust_unknown_hosts=False, **jump)[name]
            self.assertEqual(unknown_bastion.status, "OFFLINE")
            self.assertIn("Jump host", unknown_bastion.erro)
            self.assertEqual(target.connections, 0)

            stored = paramiko.HostKeys()
            stored.add(f"[127.0.0.1]:{bastion.port}", bastion.key.get_name(), bastion.key)
            stored.save(str(self.known_hosts))
            unknown_target = self.collect([name], trust_unknown_hosts=False, **jump)[name]
            self.assertEqual(unknown_target.status, "ERRO_SSH")
            self.assertEqual(target.logins, [])

            self.known_hosts.unlink()
            trusted = self.collect([name], **jump)[name]
            self.assertEqual(trusted.status, "ONLINE")
            remembered = paramiko.HostKeys(str(self.known_hosts))
            self.assertIsNotNone(remembered.lookup(f"[127.0.0.1]:{bastion.port}"))
            self.assertIsNotNone(remembered.lookup(name))

    @unittest.skipUnless(shutil.which("ssh-agent") and shutil.which("ssh-add"), "OpenSSH agent tools are not installed")
    def test_keys_loaded_in_ssh_agent_authenticate_without_key_or_password(self):
        key = paramiko.RSAKey.generate(2048)
        key_file = self.tmp / "agent_key"
        key.write_private_key_file(str(key_file))
        os.chmod(key_file, 0o600)
        socket_path = self.tmp / "agent.sock"
        agent = subprocess.Popen(["ssh-agent", "-D", "-a", str(socket_path)], stdout=subprocess.DEVNULL)
        self.addCleanup(agent.wait)
        self.addCleanup(agent.terminate)
        for _ in range(50):
            if socket_path.exists():
                break
            time.sleep(0.05)
        environment = {**os.environ, "SSH_AUTH_SOCK": str(socket_path)}
        subprocess.run(["ssh-add", str(key_file)], env=environment, check=True, capture_output=True)
        key_file.unlink()

        with patch.dict(os.environ, {"SSH_AUTH_SOCK": str(socket_path)}):
            with FakeSSHServer(authorized_keys=(key,)) as server:
                with_agent = self.collect(["127.0.0.1"], ssh_pass="", ssh_use_agent=True, ssh_port=server.port)["127.0.0.1"]
                without_agent = self.collect(["127.0.0.1"], ssh_pass="", ssh_use_agent=False, ssh_port=server.port)["127.0.0.1"]
                logins = list(server.logins)
        self.assertNotEqual(without_agent.status, "ONLINE")
        self.assertEqual(logins, [("reader", "publickey")])
        self.assertEqual(with_agent.status, "ONLINE")


if __name__ == "__main__":
    unittest.main()
