"""Regression tests for the macOS utility UI, brand assets, and local API server."""
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from pathlib import Path

import app
from snapshots import SnapshotStore


class DesktopUtilityUITests(unittest.TestCase):
    def test_brand_tokens_use_macos_dark_utility_palette(self):
        self.assertEqual(app.COLORS["bg_window"], "#1C1C1E")
        self.assertEqual(app.COLORS["bg_sidebar"], "#232326")
        self.assertEqual(app.COLORS["bg_card"], "#262629")
        self.assertEqual(app.COLORS["accent_blue"], "#0A84FF")
        self.assertEqual(app.COLORS["status_online"], "#30D158")
        self.assertEqual(app.APP_BRAND, "Invenux")

        theme_path = Path(__file__).resolve().parents[1] / "brand" / "theme.json"
        theme = json.loads(theme_path.read_text(encoding="utf-8"))
        self.assertEqual(theme["palette"]["bg_window"], "#1C1C1E")
        self.assertEqual(theme["palette"]["accent_blue"], "#0A84FF")

    def test_brand_assets_exist_for_every_platform(self):
        root = Path(__file__).resolve().parents[1]
        for size in (16, 32, 64, 128, 256, 512, 1024):
            self.assertTrue((root / "brand" / "icons" / f"invenux-{size}.png").is_file(), size)
        self.assertTrue((root / "brand" / "invenux.ico").is_file())
        self.assertTrue((root / "brand" / "invenux.icns").is_file())
        self.assertIn('rel="icon"', (root / "ui" / "index.html").read_text(encoding="utf-8"))

    def test_ui_html_contains_three_views_popovers_and_100vh_100vw(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("width: 100vw;", html)
        self.assertIn("height: 100vh;", html)
        self.assertIn("Coleta", html)
        self.assertIn("Parque", html)
        self.assertIn("Snapshots", html)
        self.assertNotIn("Parque & Upgrade", html)
        self.assertNotIn("Snapshots & Diff", html)
        self.assertNotIn("Invent-SSH", html)
        self.assertIn('id="popover-ssh"', html)
        self.assertIn('id="popover-targets"', html)
        self.assertIn('id="popover-export"', html)

    def test_interface_catalog_covers_three_languages(self):
        import re

        html = (Path(__file__).resolve().parents[1] / "ui" / "index.html").read_text(encoding="utf-8")
        catalog = json.loads(re.search(r'<script id="i18n-catalog" type="application/json">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(set(catalog), {"pt-br", "en", "es"})
        keys = set(catalog["en"])
        for language, table in catalog.items():
            self.assertEqual(set(table), keys, language)
        used = set(re.findall(r'data-i18n(?:-html|-placeholder|-title|-aria)?="([^"]+)"', html))
        used |= set(re.findall(r'tr\("([a-z][\w.]*)"', html))
        self.assertEqual(used - keys, set())

    def test_inline_handlers_do_not_call_native_element_methods(self):
        # Inline handlers resolve names on the element first; togglePopover() was
        # silently taken by the browser's Popover API and the toolbar stopped opening.
        import re

        html = (Path(__file__).resolve().parents[1] / "ui" / "index.html").read_text(encoding="utf-8")
        called = set(re.findall(r'on\w+="(?:[^"]*?;\s*)?(\w+)\(', html))
        native = {"togglePopover", "showPopover", "hidePopover", "click", "focus", "blur",
                  "remove", "animate", "closest", "matches", "scroll", "select", "submit", "reset"}
        self.assertEqual(called & native, set())
        self.assertIn("togglePanel", called)

    def test_local_http_server_enforces_token_and_loads_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg_path = tmp_path / "config.json"
            db_path = tmp_path / "snapshots.db"
            csv_path = tmp_path / "alvos.csv"
            csv_path.write_text(
                "IP,HOSTNAME,LOCATION\n10.24.8.104,srv-app-sp04,Matriz\n10.24.12.19,pdv-fl04-cx01,Filial 04\n",
                encoding="utf-8",
            )

            controller = app.InventoryController(
                config_path=cfg_path,
                snapshot_store=SnapshotStore(db_path),
            )
            server, url, token = app.create_http_server(controller)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)

            # Root HTML injects session token
            with urllib.request.urlopen(url) as response:
                page = response.read().decode("utf-8")
            self.assertIn(token, page)

            # A foreign Host header (DNS rebinding) never receives the token
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(urllib.request.Request(url, headers={"Host": "attacker.example"}))
            self.assertEqual(ctx.exception.code, 403)

            # Unauthenticated API request is rejected with 403
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url + "api/state")
            self.assertEqual(ctx.exception.code, 403)

            # Authenticated config update keeps password out of disk config
            req_cfg = urllib.request.Request(
                url + "api/config",
                data=json.dumps({
                    "ssh_user": "inv-reader",
                    "ssh_pass": "ephemeral-secret",
                    "max_workers": 24,
                    "ssh_timeout": 12,
                }).encode("utf-8"),
                headers={"X-Invenux-Token": token, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_cfg) as response:
                cfg_payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(cfg_payload["config"]["ssh_user"], "inv-reader")
            self.assertTrue(cfg_payload["config"]["has_password"])
            self.assertNotIn("ssh_pass", cfg_payload["config"])
            saved_disk = cfg_path.read_text(encoding="utf-8")
            self.assertNotIn("ephemeral-secret", saved_disk)

            # /api/open never hands arbitrary files to the desktop opener
            req_open = urllib.request.Request(
                url + "api/open",
                data=json.dumps({"path": str(csv_path)}).encode("utf-8"),
                headers={"X-Invenux-Token": token, "Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_open)
            self.assertEqual(ctx.exception.code, 400)

            # /api/open-link opens only the About sheet's own pages
            def open_link(name):
                return urllib.request.Request(
                    url + "api/open-link",
                    data=json.dumps({"name": name}).encode("utf-8"),
                    headers={"X-Invenux-Token": token, "Content-Type": "application/json"},
                    method="POST",
                )
            with patch("app._open_externally") as opener:
                urllib.request.urlopen(open_link("repo")).read()
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(open_link("https://example.test"))
            opener.assert_called_once_with("https://github.com/lucaswotta/invenux")
            self.assertEqual(ctx.exception.code, 400)

            # Load targets CSV via API
            req_load = urllib.request.Request(
                url + "api/targets/load",
                data=json.dumps({"filepath": str(csv_path)}).encode("utf-8"),
                headers={"X-Invenux-Token": token, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_load) as response:
                state_payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(len(state_payload["records"]), 2)
            self.assertEqual(state_payload["analytics"]["total"], 2)
            self.assertEqual(state_payload["analytics"]["locations_count"], 2)

            # Invalid SSH ports are skipped and named in the status, like rows without an address
            csv_path.write_text("IP,SSH_PORT\n192.0.2.10,2222\n192.0.2.11,99999\n", encoding="utf-8")
            with urllib.request.urlopen(req_load) as response:
                state_payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual([r["ssh_port"] for r in state_payload["records"]], [2222])
            self.assertEqual(state_payload["targets_info"]["invalid_port_rows"], [3])
            self.assertIn("3", state_payload["status_text"].split("·")[-1])


if __name__ == "__main__":
    unittest.main()
