"""Cross-distro hardware parsing tests using anonymized command-output fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from i18n import get_language, set_language
import inspector


class HardwareParserTests(unittest.TestCase):
    def test_os_release_unquotes_values(self):
        parsed = inspector._parse_os_release(
            'NAME="Example Linux"\nID=example\nVERSION_ID="42"\nPRETTY_NAME="Example Linux 42 (Stone)"\n'
        )
        self.assertEqual(parsed["ID"], "example")
        self.assertEqual(parsed["PRETTY_NAME"], "Example Linux 42 (Stone)")

    def test_lscpu_parses_sockets_cores_threads_and_frequency(self):
        parsed = inspector._parse_lscpu(
            "CPU(s):                          16\n"
            "Socket(s):                       2\n"
            "Core(s) per socket:               4\n"
            "Thread(s) per core:                2\n"
            "CPU max MHz:                 4200.0000\n"
        )
        self.assertEqual(parsed["cpu(s)"], "16")
        self.assertEqual(parsed["socket(s)"], "2")
        self.assertEqual(parsed["core(s) per socket"], "4")
        self.assertEqual(parsed["cpu max mhz"], "4200.0000")

    def test_meminfo_uses_byte_units_and_available_memory(self):
        parsed = inspector._parse_meminfo(
            "MemTotal:       16384000 kB\n"
            "MemFree:         1024000 kB\n"
            "MemAvailable:    8192000 kB\n"
        )
        self.assertEqual(parsed["MemTotal"], 16384000 * 1024)
        self.assertEqual(parsed["MemAvailable"], 8192000 * 1024)

    def test_memory_device_parser_counts_every_slot(self):
        array = (
            "Handle 0x0007, DMI type 16, 23 bytes\nPhysical Memory Array\n"
            "\tMaximum Capacity: 32 GB\n\tNumber Of Devices: 2\n\n"
        )
        module = (
            "Handle 0x0008, DMI type 17, 40 bytes\nMemory Device\n\tTotal Width: 64 bits\n"
            "\tSize: 4096 MB\n\tForm Factor: DIMM\n\tLocator: {slot}\n\tBank Locator: BANK 0\n"
            "\tType: DDR4\n\tSpeed: 2400 MT/s\n\tManufacturer: Kingston\n"
            "\tSerial Number: 12345678\n\tPart Number: 99U5701-001.A00G\n"
            "\tConfigured Clock Speed: 2400 MT/s\n\n"
        )
        empty = (
            "Handle 0x000A, DMI type 17, 40 bytes\nMemory Device\n\tSize: No Module Installed\n"
            "\tLocator: ChannelB-DIMM0\n\tType: Unknown\n\tSpeed: Unknown\n"
            "\tManufacturer: Not Specified\n\tPart Number: Not Specified\n\n"
        )
        one = inspector._parse_memory_devices(array + module.format(slot="ChannelA-DIMM0") + empty)
        self.assertEqual(one["ram_slots"], "1 of 2 populated")
        self.assertEqual(one["ram_type"], "DDR4")
        self.assertEqual(one["ram_speed"], "2400 MT/s")
        self.assertEqual(one["ram_max_capacity"], "32 GB")
        self.assertEqual(one["ram_modules"], "ChannelA-DIMM0 · 4 GB DDR4 · 2400 MT/s · Kingston 99U5701-001.A00G")
        self.assertEqual(int(one["ram_module_total_bytes"]), 4 * 1024**3)

        two = inspector._parse_memory_devices(
            array + module.format(slot="ChannelA-DIMM0") + module.format(slot="ChannelB-DIMM0")
        )
        self.assertEqual(two["ram_slots"], "2 of 2 populated")
        self.assertEqual(two["ram_modules"].count("\n"), 1)

    def test_system_details_like_fastfetch(self):
        self.assertEqual(inspector._parse_packages("dpkg 1834\nrpm 0\n"), "1834 (dpkg)")
        self.assertEqual(inspector._parse_displays("card0-HDMI-A-1 1920x1080\n"), "HDMI-A-1 1920x1080")
        self.assertEqual(inspector._parse_rootfs("/dev/sda1 117000000 45000000 66000000 41% /"), "46 GB / 120 GB (38%)")
        session = inspector._parse_session("init=systemd\nXorg\nlxsession\nopenbox\nsshd\n")
        self.assertEqual(session, {"init_system": "systemd", "desktop": "LXDE + Openbox", "display_server": "X11"})
        self.assertEqual(
            inspector._parse_ipv4("2: eth0    inet 10.0.0.8/24 brd 10.0.0.255 scope global eth0\n1: lo    inet 127.0.0.1/8 scope host lo\n"),
            {"eth0": ["10.0.0.8/24"]},
        )

    def test_lsblk_preserves_each_physical_drive_and_detects_medium(self):
        parsed = inspector._parse_lsblk(json.dumps({
            "blockdevices": [
                {"name": "nvme0n1", "type": "disk", "size": 512_000_000_000,
                 "rota": False, "model": "Example NVMe", "tran": "nvme", "rm": False},
                {"name": "sda", "type": "disk", "size": 1_000_000_000_000,
                 "rota": "1", "model": "Archive Drive", "tran": "sata", "rm": "0"},
                {"name": "sda1", "type": "part", "size": 100_000_000_000,
                 "rota": "1", "model": "Archive Drive", "tran": "sata", "rm": "0"},
                {"name": "loop0", "type": "loop", "size": 1_000_000, "rota": 0},
            ]
        }))
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["kind"], "NVMe")
        self.assertEqual(parsed[0]["capacity"], "512 GB")
        self.assertEqual(parsed[1]["kind"], "HDD")
        self.assertEqual(parsed[1]["capacity"], "1 TB")

    def test_lsblk_virtual_and_physical_devices(self):
        fixtures = [
            ("sda", "QEMU HARDDISK", "QEMU", "sata", "Virtual"),
            ("vda", None, None, None, "Virtual"),
            ("vdab", "", "", "virtio", "Virtual"),
            ("sda", "VBOX HARDDISK", "ATA", "sata", "Virtual"),
            ("sda", "Virtual disk", "VMware", "spi", "Virtual"),
            ("sda", "Virtual Disk", "Msft", None, "Virtual"),
            ("sda", "", "VMware", "sas", "Virtual"),
            ("nvme0n1", "VMware Virtual NVMe Disk", "", "nvme", "Virtual"),
            ("nvme0n1", "Example NVMe", "Example", "nvme", "NVMe"),
            ("sda", "Example SSD", "ATA", "sata", "SSD / flash"),
            ("sdb", "Archive Drive", "ATA", "sata", "HDD"),
        ]
        for name, model, vendor, transport, expected in fixtures:
            with self.subTest(name=name, model=model, vendor=vendor):
                device = {"name": name, "type": "disk", "size": 512_000_000_000,
                          "rota": expected == "HDD", "model": model,
                          "vendor": vendor, "tran": transport}
                parsed = inspector._parse_lsblk(json.dumps({"blockdevices": [device]}))
                self.assertEqual(parsed[0]["kind"], expected)

    def test_lsblk_pairs_recognizes_virtual_disks_regardless_of_rotation(self):
        for rota in ("0", "1"):
            with self.subTest(rota=rota):
                parsed = inspector._parse_lsblk(
                    f'NAME="sda" TYPE="disk" SIZE="512000000000" ROTA="{rota}" '
                    'MODEL="Virtual Disk" VENDOR="Msft" TRAN="" RM="0"'
                )
                self.assertEqual(parsed[0]["kind"], "Virtual")

    def test_collector_uses_hypervisor_but_not_container_for_storage(self):
        disk = {"name": "nvme0n1", "type": "disk", "size": 512_000_000_000,
                "rota": 0, "tran": "nvme"}
        for hypervisor, virtualization, expected in (
            ("kvm", "kvm", "Virtual"), ("vmware", "vmware", "Virtual"),
            ("microsoft", "microsoft", "Virtual"), ("none", "docker", "NVMe"),
            ("", "", "NVMe"), ("none", "none", "NVMe"),
        ):
            with self.subTest(hypervisor=hypervisor, virtualization=virtualization):
                sections = {"lsblk": json.dumps({"blockdevices": [disk]}),
                            "hypervisor": hypervisor, "virtualization": virtualization}
                output = "\n".join(
                    f"__INVENUX_BEGIN_{key}__\n{value}\n__INVENUX_END_{key}__"
                    for key, value in sections.items()
                )
                with patch.object(inspector, "_run_command", return_value=output) as probe:
                    details = inspector._collect_linux_hardware(Mock())
                command = probe.call_args.args[1]
                self.assertIn("systemd-detect-virt --vm", command)
                self.assertIn("MODEL,VENDOR,TRAN", command)
                self.assertEqual(details["disk_type"], expected)
                self.assertIn(expected, details["hardware_details"]["storage_devices"])

    def test_network_parser_excludes_loopback_and_macos_colon_suffixes(self):
        parsed = inspector._parse_network_interfaces(
            "2: enp1s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP mode DEFAULT\n"
            "3: wlp2s0: <BROADCAST,MULTICAST> mtu 1500 state DOWN mode DORMANT\n"
            "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 state UNKNOWN mode DEFAULT\n"
        )
        self.assertEqual(parsed, ["enp1s0 (up)", "wlp2s0 (down)"])

    def test_gpu_parser_recognizes_vga_and_3d_adapters(self):
        parsed = inspector._parse_gpus(
            "00:02.0 VGA compatible controller: Example Graphics Inc. Integrated GPU (rev 01)\n"
            "03:00.0 3D controller: Example Compute Ltd. Accelerator\n"
            "05:00.0 Ethernet controller: Example Network Inc. NIC\n"
        )
        self.assertEqual(len(parsed), 2)
        self.assertIn("Integrated GPU", parsed[0])
        self.assertIn("Accelerator", parsed[1])

    def test_cpu_list_counts_single_cpus_as_one(self):
        self.assertEqual(inspector._count_cpu_list("0-3,8,10-11"), 7)
        self.assertEqual(inspector._count_cpu_list("0-3,x"), 0)

    def test_custom_port_is_used_and_named_in_known_hosts(self):
        client = Mock()
        with (
            patch.object(inspector.paramiko, "SSHClient", return_value=client),
            patch.object(inspector, "_collect_linux_hardware", return_value={"status": "SUCESSO"}),
            patch.object(inspector, "_remember_host_key") as remember,
        ):
            inspector.get_hardware_info("10.0.0.9", "reader", "secret", None, timeout=5, trust_unknown_hosts=True, port=2222)
        self.assertEqual(client.connect.call_args.kwargs["port"], 2222)
        self.assertEqual(remember.call_args.args[1], "[10.0.0.9]:2222")

    def test_tofu_keys_from_parallel_workers_are_all_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            known_hosts = Path(tmp) / "known_hosts"
            first, second = inspector.paramiko.ECDSAKey.generate(), inspector.paramiko.ECDSAKey.generate()
            inspector._remember_host_key(known_hosts, "10.0.0.1", first)
            inspector._remember_host_key(known_hosts, "10.0.0.2", second)
            stored = inspector.paramiko.HostKeys(str(known_hosts))
            self.assertTrue(stored.check("10.0.0.1", first))
            self.assertTrue(stored.check("10.0.0.2", second))

    def test_connection_failures_name_the_network_cause(self):
        import errno
        import socket

        def wrapped(code):
            return inspector.paramiko.ssh_exception.NoValidConnectionsError(
                {("10.0.0.9", 22): OSError(code, "synthetic")}
            )

        previous = get_language()
        set_language("pt-br")
        self.addCleanup(set_language, previous)
        self.assertIn("desligada", inspector._connection_failure(wrapped(errno.EHOSTUNREACH), "10.0.0.9", 15))
        self.assertIn("recusada na porta 2222", inspector._connection_failure(wrapped(errno.ECONNREFUSED), "10.0.0.9", 15, 2222))
        self.assertIn("15 s", inspector._connection_failure(socket.timeout(), "10.0.0.9", 15))
        self.assertIsNone(inspector._connection_failure(PermissionError(13, "denied"), "10.0.0.9", 15))

    def test_uptime_format_and_unknown_value(self):
        self.assertEqual(inspector._format_uptime("90061.32 123.00"), "1d 1h 1m")
        self.assertEqual(inspector._format_uptime("not-a-number"), "N/A")

    def test_collector_returns_multi_device_hardware_and_serial_is_opt_in(self):
        section_data = {
            "os_release": 'PRETTY_NAME="Example Linux 42"\nNAME="Example Linux"\n',
            "hostname": "example-host",
            "kernel": "6.8.0-example",
            "architecture": "x86_64",
            "lscpu": (
                "Model name: Example Processor\nCPU(s): 8\nSocket(s): 1\n"
                "Core(s) per socket: 4\nThread(s) per core: 2\nCPU max MHz: 3600.0000\n"
                "Virtualization: VT-x\nVendor ID: GenuineExample\nCPU family: 6\n"
            ),
            "cpuinfo": "Model name: Example Processor\nCPU(s): 8\nVirtualization: VT-x\n",
            "meminfo": "MemTotal: 16384000 kB\nMemAvailable: 8192000 kB\nMemFree: 1000000 kB\n",
            "memory_devices": (
                "Memory Device\n\tSize: 16 GB\n\tType: DDR4\n\tSpeed: 3200 MT/s\n"
            ),
            "lsblk": json.dumps({"blockdevices": [
                {"name": "nvme0n1", "type": "disk", "size": 512_000_000_000, "rota": 0,
                 "model": "Example NVMe", "tran": "nvme", "rm": False, "fstype": None,
                 "mountpoints": [None], "children": [
                     {"name": "nvme0n1p1", "type": "part", "size": 511_000_000_000,
                      "fstype": "ext4", "mountpoints": ["/"]},
                 ]},
                {"name": "sda", "type": "disk", "size": 1_000_000_000_000, "rota": 1,
                 "model": "Example Archive", "tran": "sata", "rm": False, "fstype": None,
                 "mountpoints": [None]},
            ]}),
            "lspci": "00:02.0 VGA compatible controller [0300]: Example GPU [1234:5678]\n",
            "drm": "PCI_ID=1234:5678\n",
            "netlink": "2: enp1s0: <BROADCAST,MULTICAST,UP> mtu 1500 state UP mode DEFAULT\n",
            "netdetails": "enp1s0|up|1000|e1000e|52:54:00:12:34:56\n",
            "ipv4": "2: enp1s0    inet 10.0.0.8/24 brd 10.0.0.255 scope global enp1s0\n",
            "uptime": "90061.32 123.00",
            "virtualization": "kvm",
            "dmi": "",
        }
        dmi_lines = (
            "__DMI__sys_vendor=Example Systems\n"
            "__DMI__product_name=Model A\n"
            "__DMI__product_version=Rev 2\n"
            "__DMI__board_vendor=Example Systems\n"
            "__DMI__board_name=Board A\n"
            "__DMI__bios_vendor=Example Firmware\n"
            "__DMI__bios_version=1.2.3\n"
            "__DMI__bios_date=2026-02-01\n"
        )
        dmi_with_serial = dmi_lines + "__DMI__product_serial=SECRET-SERIAL-123\n"

        def make_probe(include_serial: bool) -> str:
            output = []
            for name, value in section_data.items():
                if name == "dmi":
                    value = dmi_with_serial if include_serial else dmi_lines
                output.append(
                    f"__INVENUX_BEGIN_{name}__\n{value.strip()}\n"
                    f"__INVENUX_END_{name}__"
                )
            return "\n".join(output)

        def fake_command(_client, command, tolerant=False, timeout=12):
            return make_probe("product_serial" in command)

        with patch.object(inspector, "_run_command", side_effect=fake_command) as mocked:
            details = inspector._collect_linux_hardware(Mock(), include_sensitive_identifiers=False)
            details_with_serial = inspector._collect_linux_hardware(Mock(), include_sensitive_identifiers=True)

        self.assertEqual(mocked.call_count, 2)  # One probe / SSH round trip per target.
        self.assertEqual(details["status"], "SUCESSO")
        self.assertEqual(details["distro"], "Example Linux 42")
        self.assertEqual(details["processador"], "Example Processor")
        self.assertEqual(details["cores_threads"], "4/8")
        self.assertEqual(details["disk_type"], "NVMe + HDD")
        self.assertNotIn("physical block devices", details["disk_size"])
        self.assertEqual(details["hardware_details"]["manufacturer"], "Example Systems")
        self.assertEqual(details["hardware_details"]["model"], "Model A")
        self.assertIn("nvme0n1", details["hardware_details"]["storage_devices"])
        self.assertIn("nvme0n1p1", details["hardware_details"]["storage_devices"])
        self.assertIn("ext4 · /", details["hardware_details"]["storage_devices"])
        self.assertIn("sda", details["hardware_details"]["storage_devices"])
        self.assertIn("Example GPU", details["hardware_details"]["gpu"])
        self.assertIn("enp1s0", details["hardware_details"]["network_adapters"])
        self.assertIn("1000 Mbps", details["hardware_details"]["network_adapters"])
        self.assertIn("10.0.0.8/24", details["hardware_details"]["network_adapters"])
        self.assertIn("MAC 52:54:00:12:34:56", details["hardware_details"]["network_adapters"])
        self.assertEqual(details["hardware_details"]["uptime"], "1d 1h 1m")
        self.assertEqual(details["hardware_details"]["virtualization"], "kvm")
        self.assertEqual(details["hardware_details"]["system_serial"], "Not collected (opt-in)")
        self.assertEqual(details_with_serial["hardware_details"]["system_serial"], "SECRET-SERIAL-123")
        self.assertEqual(details["hardware_details"]["coverage_percent"], "100%")


if __name__ == "__main__":
    unittest.main()
