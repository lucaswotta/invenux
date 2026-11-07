"""Regression tests for endpoint loading and scalable collection behavior."""
import csv
import importlib.util
import tempfile
import threading
import time
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import Mock, patch


HAS_ENGINE_DEPS = all(
    importlib.util.find_spec(name) is not None
    for name in ("openpyxl", "paramiko")
)


@unittest.skipUnless(HAS_ENGINE_DEPS, "openpyxl/paramiko are not installed")
class InventoryEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import core
        cls.core = core

    def setUp(self):
        from i18n import get_language, set_language

        previous = get_language()
        set_language("en")
        self.addCleanup(set_language, previous)

    def make_engine(self, **extra):
        config = {
            "max_workers": 3,
            "ssh_timeout": 5,
            "ssh_user": "inventory-reader",
            "ssh_pass": "not-a-real-password",
            "ssh_key_path": "",
        }
        config.update(extra)
        return self.core.InventoryEngine(config, Queue())

    def test_loader_accepts_hostname_and_preserves_all_user_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Hostname", "Asset Tag", "Location", "Owner", "Notes"])
                writer.writerow(["linux-01.example.test", "ASSET-001", "Lab", "Infra", "memory upgrade"])
                writer.writerow(["", "ASSET-002", "Office", "Ops", "missing host"])
                writer.writerow(["linux-02.example.test", "ASSET-003", "Office", "Ops", ""])

            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()

        self.assertEqual([target.ip for target in targets], [
            "linux-01.example.test",
            "linux-02.example.test",
        ])
        self.assertEqual(targets[0].metadata["ASSET_TAG"], "ASSET-001")
        self.assertEqual(targets[0].metadata["LOCATION"], "Lab")
        self.assertEqual(targets[0].metadata["OWNER"], "Infra")
        self.assertEqual(targets[0].metadata["NOTES"], "memory upgrade")
        self.assertEqual(engine.load_summary["rows_without_target"], [3])

    def test_loader_skips_repeated_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text("IP,Location\n10.0.0.1,A\n10.0.0.2,A\n10.0.0.1,B\n,,\n", encoding="utf-8")
            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()
        self.assertEqual([target.ip for target in targets], ["10.0.0.1", "10.0.0.2"])
        self.assertEqual(engine.load_summary["duplicate_rows"], [4])
        self.assertEqual(engine.load_summary["rows_without_target"], [])

    def test_access_columns_stay_out_of_records_and_override_the_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text(
                "IP;Usuário;Senha;Location\n"
                "10.0.0.1;pdv; s3cr3t-row ;Loja 1\n"
                "10.0.0.2;;;Loja 2\n",
                encoding="utf-8",
            )
            engine = self.make_engine(filepath=str(path))
            calls = {}

            def fake_get_hardware_info(**kwargs):
                calls[kwargs["ip"]] = (kwargs["username"], kwargs["password"])
                return {"status": "SUCESSO", "hardware_details": {}}

            with patch.object(self.core, "get_hardware_info", side_effect=fake_get_hardware_info):
                engine.run_inventory()

        self.assertEqual(calls["10.0.0.1"], ("pdv", " s3cr3t-row "))
        self.assertEqual(calls["10.0.0.2"], ("inventory-reader", "not-a-real-password"))
        summary = engine.load_summary
        self.assertEqual(summary["credential_columns"], ["USUÁRIO", "SENHA"])
        self.assertEqual(summary["extra_columns"], ["LOCATION"])
        self.assertEqual((summary["hosts_with_user"], summary["hosts_with_password"]), (1, 1))
        events = []
        while not engine.log_queue.empty():
            events.append(engine.log_queue.get_nowait())
        self.assertTrue(any(event[0] == "HOST_RESULT" for event in events))
        self.assertNotIn("s3cr3t-row", repr(events))

    def test_ssh_port_column_overrides_the_panel_and_lists_invalid_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text(
                "IP,SSH_PORT,LOCATION\n"
                "192.0.2.10,2222,Lab\n"
                "192.0.2.11,,Lab\n"
                "192.0.2.12,70000,Lab\n"
                "192.0.2.13,ssh,Lab\n"
                "192.0.2.14, 2200 ,Lab\n",
                encoding="utf-8",
            )
            engine = self.make_engine(filepath=str(path), ssh_port=22)
            ports = {}

            def fake_get_hardware_info(**kwargs):
                ports[kwargs["ip"]] = kwargs["port"]
                return {"status": "SUCESSO", "hardware_details": {}}

            with patch.object(self.core, "get_hardware_info", side_effect=fake_get_hardware_info):
                engine.run_inventory()

        self.assertEqual(ports, {"192.0.2.10": 2222, "192.0.2.11": 22, "192.0.2.14": 2200})
        summary = engine.load_summary
        self.assertEqual(summary["invalid_port_rows"], [4, 5])
        self.assertEqual((summary["port_column"], summary["hosts_with_port"]), ("SSH_PORT", 2))
        self.assertEqual(summary["extra_columns"], ["LOCATION"])
        by_ip = {terminal.ip: terminal for terminal in engine.terminals}
        self.assertEqual(by_ip["192.0.2.10"].ssh_port, 2222)
        self.assertEqual(by_ip["192.0.2.11"].ssh_port, 22)
        self.assertNotIn("SSH_PORT", by_ip["192.0.2.10"].metadata)

    def test_port_aliases_and_excel_numbers(self):
        self.assertEqual(self.core._parse_port(2222.0), 2222)
        self.assertEqual(self.core._parse_port("22"), 22)
        for invalid in (0, 65536, 22.5, "-1", "2 2", True):
            self.assertIsNone(self.core._parse_port(invalid), invalid)
        for alias in ("PORT", "Porta", "puerto"):
            with self.subTest(alias=alias):
                engine = self.make_engine()
                targets = engine._terminals_from_rows(["IP", alias], [["192.0.2.10", "2022"]])
                self.assertEqual(targets[0].ssh_port, 2022)

    def test_loader_reads_xlsx_and_preserves_typed_metadata(self):
        from openpyxl import Workbook

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["Hostname", "Asset Tag", "Rack", "Location"])
            sheet.append(["linux-03.example.test", 1004, "R12", "Data Hall"])
            sheet.append(["linux-04.example.test", 1005, "R13", None])
            workbook.save(path)
            workbook.close()

            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()

        self.assertEqual([target.ip for target in targets], [
            "linux-03.example.test",
            "linux-04.example.test",
        ])
        self.assertEqual(targets[0].metadata["ASSET_TAG"], 1004)
        self.assertEqual(targets[0].metadata["RACK"], "R12")
        self.assertEqual(targets[0].metadata["LOCATION"], "Data Hall")
        self.assertNotIn("LOCATION", targets[1].metadata)

    def test_loader_sniffs_semicolon_csv_and_utf8_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text(
                "HOST;ASSET_TAG;NOTES\nlinux-05.example.test;ASSET-005;café\n",
                encoding="utf-8-sig",
            )
            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].ip, "linux-05.example.test")
        self.assertEqual(targets[0].metadata["ASSET_TAG"], "ASSET-005")
        self.assertEqual(targets[0].metadata["NOTES"], "café")

    def test_loader_reports_data_beyond_the_named_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text("IP,LOCATION\n192.0.2.14,Lab,unlabelled-value\n", encoding="utf-8")
            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()
            messages = []
            while not engine.log_queue.empty():
                messages.append(engine.log_queue.get_nowait()[1])

        self.assertEqual(targets, [])
        self.assertTrue(any("Row 2" in message for message in messages))

    def test_loader_rejects_columns_that_collide_after_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assets.csv"
            path.write_text("IP,ip,Location\n192.0.2.1,192.0.2.2,Lab\n", encoding="utf-8")
            engine = self.make_engine(filepath=str(path))
            targets = engine._load_from_spreadsheet()
            messages = []
            while not engine.log_queue.empty():
                messages.append(engine.log_queue.get_nowait()[1])

        self.assertEqual(targets, [])
        self.assertTrue(any("unique" in message.lower() for message in messages))

    def test_worker_count_bounds_concurrent_ssh_calls(self):
        engine = self.make_engine(max_workers=3)
        engine.terminals = [self.core.Terminal(ip=f"host-{i}") for i in range(15)]
        lock = threading.Lock()
        active = 0
        highest = 0

        def fake_get_hardware_info(**kwargs):
            nonlocal active, highest
            with lock:
                active += 1
                highest = max(highest, active)
            time.sleep(0.015)
            with lock:
                active -= 1
            return {
                "status": "SUCESSO",
                "placa_mae": "Example Board",
                "processador": "Example CPU",
                "cores_threads": "4/8",
                "ram": "16GB",
                "disk_type": "SSD",
                "disk_size": "512GB",
                "distro": "Ubuntu",
                "kernel": "6.8",
            }

        with patch.object(self.core, "get_hardware_info", side_effect=fake_get_hardware_info):
            results = engine._execute_collection()

        self.assertEqual(len(results), 15)
        self.assertLessEqual(highest, 3)
        self.assertGreaterEqual(highest, 2)
        self.assertTrue(all(result.status == "ONLINE" for result in results))

    def test_circuit_breaker_stops_after_ten_initial_failures(self):
        engine = self.make_engine(max_workers=1)
        engine.terminals = [self.core.Terminal(ip=f"unreachable-{i}") for i in range(25)]

        def fake_get_hardware_info(**kwargs):
            return {"status": "FALHA_CONEXAO", "erro": "connection refused"}

        with patch.object(self.core, "get_hardware_info", side_effect=fake_get_hardware_info):
            results = engine._execute_collection()

        self.assertEqual(len(results), 10)
        self.assertTrue(all(result.status == "OFFLINE" for result in results))
        queued = []
        while not engine.log_queue.empty():
            queued.append(engine.log_queue.get_nowait())
        self.assertTrue(any("first 10 connections failed" in entry[1] for entry in queued))

    def test_run_inventory_reports_partial_results_as_warning(self):
        from i18n import get_language, set_language

        engine = self.make_engine()
        targets = [self.core.Terminal(ip="online"), self.core.Terminal(ip="offline")]
        results = [
            self.core.Terminal(ip="online", status="ONLINE"),
            self.core.Terminal(ip="offline", status="OFFLINE", erro="connection refused"),
        ]
        previous_language = get_language()
        set_language("pt-br")
        try:
            with (
                patch.object(engine, "_load_from_spreadsheet", return_value=targets),
                patch.object(engine, "_execute_collection", return_value=results),
            ):
                engine.run_inventory()
        finally:
            set_language(previous_language)

        events = []
        while not engine.log_queue.empty():
            events.append(engine.log_queue.get_nowait())
        finish = [event for event in events if event[0] == "FINISH"][-1]
        self.assertEqual(finish[2], "WARNING")
        self.assertIn("1 acessíveis, 1 com falha", finish[1])

    def test_run_inventory_does_not_report_empty_input_as_success(self):
        engine = self.make_engine()
        with patch.object(engine, "_load_from_spreadsheet", return_value=[]):
            engine.run_inventory()
        events = []
        while not engine.log_queue.empty():
            events.append(engine.log_queue.get_nowait())
        finish = [event for event in events if event[0] == "FINISH"][-1]
        self.assertEqual(finish[2], "WARNING")
        self.assertTrue(
            any(phrase in finish[1] for phrase in ("Nenhum destino", "No valid targets")),
            finish[1],
        )

    def test_run_inventory_reports_unhandled_failure(self):
        engine = self.make_engine()
        targets = [self.core.Terminal(ip="host-01")]
        with (
            patch.object(engine, "_load_from_spreadsheet", return_value=targets),
            patch.object(engine, "_execute_collection", side_effect=RuntimeError("synthetic failure")),
        ):
            engine.run_inventory()
        events = []
        while not engine.log_queue.empty():
            events.append(engine.log_queue.get_nowait())
        finish = [event for event in events if event[0] == "FINISH"][-1]
        self.assertEqual(finish[2], "ERROR")
        self.assertIn("synthetic failure", finish[1])

    def test_ssh_host_key_policy_is_strict_unless_compatibility_is_enabled(self):
        import inspector

        for trust_unknown_hosts, expected_policy in (
            (False, inspector.paramiko.RejectPolicy),
            (True, inspector.paramiko.AutoAddPolicy),
        ):
            with self.subTest(trust_unknown_hosts=trust_unknown_hosts):
                client = Mock()
                with (
                    patch.object(inspector.paramiko, "SSHClient", return_value=client),
                    patch.object(inspector, "_collect_linux_hardware", return_value={"status": "SUCESSO", "processador": "Example CPU"}),
                    patch.object(inspector, "_remember_host_key"),
                ):
                    result = inspector.get_hardware_info(
                        ip="example.invalid",
                        username="reader",
                        password=None,
                        key_path=None,
                        timeout=1,
                        trust_unknown_hosts=trust_unknown_hosts,
                    )
                policy = client.set_missing_host_key_policy.call_args.args[0]
                self.assertIsInstance(policy, expected_policy)
                self.assertTrue(client.load_system_host_keys.called)
                self.assertTrue(client.close.called)
                self.assertEqual(result["status"], "SUCESSO")

if __name__ == "__main__":
    unittest.main()
