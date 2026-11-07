"""Command-line collection: password from the environment or a prompt, never an argument."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
from snapshots import SnapshotStore


class CommandLinePasswordTests(unittest.TestCase):
    def run_main(self, args, environment):
        created = []
        original = app.InventoryController

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = root / "targets.csv"
            targets.write_text("IP\n10.0.0.1\n", encoding="utf-8")

            def make_controller():
                controller = original(config_path=root / "config.json", snapshot_store=SnapshotStore(root / "s.db"))
                created.append(controller)
                return controller

            with (
                patch.dict(os.environ, environment),
                patch("app.setup_logging"),
                patch("app.InventoryController", side_effect=make_controller),
                patch.object(original, "start_scan", lambda self: self.get_state()),
                patch.object(original, "export_current", lambda self, fmt: root / "report.xlsx"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = app.main(["--input", str(targets), "--user", "inventory", *args])
                env_after = os.environ.get(app.PASSWORD_ENV)
            saved = (root / "config.json").read_text(encoding="utf-8")
        return code, created[0], env_after, saved

    def test_password_comes_from_the_environment_and_is_not_saved(self):
        code, controller, env_after, saved = self.run_main([], {app.PASSWORD_ENV: "s3cret-env"})
        self.assertEqual(code, 0)
        self.assertEqual(controller.config["ssh_pass"], "s3cret-env")
        self.assertIsNone(env_after)
        self.assertNotIn("s3cret-env", saved)

    def test_ask_password_prompts_without_echo(self):
        with patch("app.getpass.getpass", return_value="typed-secret") as prompt:
            code, controller, _env, saved = self.run_main(["--ask-password"], {})
        self.assertEqual(code, 0)
        prompt.assert_called_once()
        self.assertEqual(controller.config["ssh_pass"], "typed-secret")
        self.assertNotIn("typed-secret", saved)

    def test_agent_and_jump_host_options_reach_the_collection(self):
        code, controller, _env, saved = self.run_main(
            ["--agent", "--jump-host", "bastion.example.test", "--jump-port", "2200", "--jump-user", "jumper"], {}
        )
        self.assertEqual(code, 0)
        self.assertTrue(controller.config["ssh_use_agent"])
        self.assertEqual(
            (controller.config["jump_host"], controller.config["jump_port"], controller.config["jump_user"]),
            ("bastion.example.test", 2200, "jumper"),
        )
        self.assertIn("bastion.example.test", saved)

    def test_agent_counts_as_authentication(self):
        from core import Terminal

        targets = [Terminal(ip="192.0.2.10")]
        with self.assertRaises(ValueError):
            app._check_access(targets, {}, "inventory", False)
        app._check_access(targets, {}, "inventory", True)

    def test_there_is_no_password_argument(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            app.main(["--input", "x.csv", "--password", "visible"])


if __name__ == "__main__":
    unittest.main()
