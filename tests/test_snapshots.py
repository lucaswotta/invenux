"""Unit tests for local snapshot storage, neutral diffs, and fleet analytics."""
import tempfile
import unittest
from pathlib import Path

from snapshots import SnapshotStore, compute_fleet_analytics, compute_records_diff


class SnapshotAndAnalyticsTests(unittest.TestCase):
    def test_virtual_storage_has_its_own_bucket_and_is_not_flash(self):
        records = [{"status": "ONLINE", "disk_type": kind}
                   for kind in ("Virtual", "Virtual + SSD / flash", "NVMe", "SSD / flash", "HDD")]
        records.append({"status": "OFFLINE", "disk_type": "Virtual"})
        analytics = compute_fleet_analytics(records)
        self.assertEqual(analytics["virtual_count"], 2)
        self.assertEqual(analytics["flash_pct"], 40.0)
        self.assertEqual(analytics["locations"][0]["flash"], 2)
        self.assertEqual(analytics["locations"][0]["virtual"], 2)
        distribution = {item["label"]: item for item in analytics["storage_distribution"]}
        self.assertEqual(distribution["Virtual"]["count"], 2)
        self.assertEqual(distribution["Virtual"]["percent"], 40.0)
        self.assertEqual(sum(item["count"] for item in distribution.values()), 5)

    def test_compute_fleet_analytics_is_neutral_and_groups_by_location(self):
        records = [
            {
                "ip": "10.0.0.1",
                "status": "ONLINE",
                "ram": "8.0 GiB DDR4",
                "disk_type": "NVMe",
                "distro": "Debian GNU/Linux 12",
                "metadata": {"LOCATION": "Matriz · SP"},
            },
            {
                "ip": "10.0.0.2",
                "status": "ONLINE",
                "ram": "4.0 GiB DDR3",
                "disk_type": "HDD",
                "distro": "Ubuntu 22.04 LTS",
                "metadata": {"LOCATION": "Filial 04"},
            },
            {
                "ip": "10.0.0.3",
                "status": "OFFLINE",
                "ram": "N/A",
                "disk_type": "N/A",
                "distro": "N/A",
                "metadata": {"LOCATION": "Filial 04"},
            },
        ]
        analytics = compute_fleet_analytics(records)
        self.assertEqual(analytics["total"], 3)
        self.assertEqual(analytics["online"], 2)
        self.assertEqual(analytics["offline"], 1)
        self.assertEqual(analytics["availability_pct"], 66.7)
        self.assertEqual(analytics["nvme_count"], 1)
        self.assertEqual(analytics["hdd_count"], 1)
        self.assertEqual(analytics["flash_pct"], 50.0)
        self.assertEqual(analytics["avg_ram_gb"], 6.0)
        self.assertEqual(len(analytics["locations"]), 2)
        filial = next(item for item in analytics["locations"] if item["location"] == "Filial 04")
        self.assertEqual(filial["total"], 2)
        self.assertEqual(filial["online"], 1)
        self.assertEqual(filial["hdd"], 1)
        self.assertEqual(filial["ram_le_4"], 1)

    def test_snapshot_store_persists_runs_and_computes_field_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp) / "snapshots.db")
            run_1 = [
                {
                    "ip": "10.24.08.12",
                    "status": "ONLINE",
                    "processador": "Intel Core i3-10100T",
                    "ram": "4.0 GiB DDR4",
                    "disk_type": "HDD",
                    "disk_size": "500 GB total (1 physical block devices)",
                    "distro": "Ubuntu 22.04 LTS",
                    "hardware_details": {"hostname": "pdv-fl02-cx04"},
                }
            ]
            run_2 = [
                {
                    "ip": "10.24.08.12",
                    "status": "ONLINE",
                    "processador": "Intel Core i3-10100T",
                    "ram": "8.0 GiB DDR4",
                    "disk_type": "NVMe",
                    "disk_size": "256 GB total (1 physical block devices)",
                    "distro": "Ubuntu 22.04 LTS",
                    "hardware_details": {"hostname": "pdv-fl02-cx04"},
                }
            ]
            meta_1 = store.save_snapshot(run_1, source_name="lote-1.xlsx", duration_seconds=4.2)
            meta_2 = store.save_snapshot(run_2, source_name="lote-1.xlsx", duration_seconds=3.8)

            self.assertEqual(meta_1["changes_count"], 0)
            self.assertEqual(meta_2["changes_count"], 3)

            listed = store.list_snapshots()
            self.assertEqual([item["id"] for item in listed], [meta_2["id"], meta_1["id"]])

            diff = store.compute_diff(meta_2["id"])
            self.assertEqual(diff["base_snapshot"]["id"], meta_1["id"])
            fields = {change["field"]: (change["previous_value"], change["current_value"]) for change in diff["changes"]}
            self.assertEqual(fields["Memória RAM"], ("4.0 GiB DDR4", "8.0 GiB DDR4"))
            self.assertEqual(fields["Tipo de Armazenamento"], ("HDD", "NVMe"))

    def test_disk_size_from_older_versions_is_not_a_change(self):
        before = {"ip": "10.0.0.9", "status": "ONLINE", "disk_size": "128 GB total (1 physical block devices)"}
        after = {"ip": "10.0.0.9", "status": "ONLINE", "disk_size": "128 GB"}
        self.assertEqual(compute_records_diff([after], [before]), [])

    def test_compute_records_diff_ignores_unchanged_hosts(self):
        record = {"ip": "10.0.0.9", "status": "ONLINE", "ram": "16 GiB"}
        self.assertEqual(compute_records_diff([record], [dict(record)]), [])


if __name__ == "__main__":
    unittest.main()
