"""The probe's memory-slot step, run by a local POSIX shell with stub dmidecode and sudo."""
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import inspector

DMIDECODE_MEMORY = textwrap.dedent("""\
    # dmidecode 3.5
    Handle 0x0011, DMI type 16, 23 bytes
    Physical Memory Array
    \tMaximum Capacity: 32 GB
    \tNumber Of Devices: 2

    Handle 0x0012, DMI type 17, 40 bytes
    Memory Device
    \tSize: 8 GB
    \tLocator: DIMM A1
    \tType: DDR4
    \tSpeed: 2666 MT/s

    Handle 0x0013, DMI type 17, 40 bytes
    Memory Device
    \tSize: No Module Installed
    \tLocator: DIMM B1
    """)

# dmidecode reads the SMBIOS tables only as root; INVENUX_TEST_ROOT stands in for that.
DMIDECODE_STUB = """#!/bin/sh
if [ "$INVENUX_TEST_ROOT" = 1 ]; then cat "$INVENUX_TEST_FIXTURE"; exit 0; fi
echo '# dmidecode 3.5'
echo '/sys/firmware/dmi/tables/smbios_entry_point: Permission denied' >&2
exit 1
"""
# Without -n a real sudo would wait for a password; the stub fails loudly instead.
SUDO_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$INVENUX_TEST_SUDO_LOG"
[ "$1" = -n ] || { echo 'prompted for a password' >&2; exit 99; }
shift
if [ "$INVENUX_TEST_SUDO" = allow ]; then INVENUX_TEST_ROOT=1 exec "$@"; fi
echo 'sudo: a password is required' >&2
exit 1
"""


@unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "needs a POSIX shell")
class SudoMemoryProbeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, body in (("dmidecode", DMIDECODE_STUB), ("sudo", SUDO_STUB)):
            stub = bin_dir / name
            stub.write_text(body, encoding="utf-8")
            stub.chmod(0o755)
        fixture = self.tmp / "memory.txt"
        fixture.write_text(DMIDECODE_MEMORY, encoding="utf-8")
        self.sudo_log = self.tmp / "sudo.log"
        self.env = {
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "INVENUX_TEST_FIXTURE": str(fixture),
            "INVENUX_TEST_SUDO_LOG": str(self.sudo_log),
        }

    def probe(self, **env):
        started = time.monotonic()
        output = subprocess.run(
            ["sh", "-c", inspector._build_probe_command()],
            env={**self.env, **env}, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
        ).stdout
        elapsed = time.monotonic() - started
        with patch.object(inspector, "_run_command", return_value=output):
            details = inspector._collect_linux_hardware(client=None)["hardware_details"]
        sudo_calls = self.sudo_log.read_text().splitlines() if self.sudo_log.exists() else []
        return details, sudo_calls, elapsed

    def test_root_reads_slots_without_sudo(self):
        details, sudo_calls, _elapsed = self.probe(INVENUX_TEST_ROOT="1")
        self.assertEqual(details["ram_slots"], "1 of 2 populated")
        self.assertIn("Memory slots: dmidecode;", details["collection_sources"])
        self.assertEqual(sudo_calls, [])

    def test_passwordless_sudo_reads_slots(self):
        details, sudo_calls, _elapsed = self.probe(INVENUX_TEST_SUDO="allow")
        self.assertEqual(details["ram_slots"], "1 of 2 populated")
        self.assertEqual(details["ram_max_capacity"], "32 GB")
        self.assertIn("Memory slots: sudo -n dmidecode;", details["collection_sources"])
        self.assertEqual(len(sudo_calls), 1)
        self.assertTrue(sudo_calls[0].startswith("-n "), sudo_calls)

    def test_without_sudo_rights_nothing_prompts_and_slots_are_unavailable(self):
        details, sudo_calls, elapsed = self.probe(INVENUX_TEST_SUDO="deny")
        self.assertEqual(details["ram_slots"], "N/A")
        self.assertIn("Memory slots: unavailable", details["collection_sources"])
        self.assertEqual(len(sudo_calls), 1)
        self.assertTrue(sudo_calls[0].startswith("-n "), sudo_calls)
        self.assertLess(elapsed, 30)


if __name__ == "__main__":
    unittest.main()
