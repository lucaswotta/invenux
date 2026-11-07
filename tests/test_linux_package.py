"""packaging/linux/build_deb.sh, built from a stub release folder."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("dpkg-deb") and shutil.which("sh"), "dpkg-deb is not installed")
class DebianPackageTests(unittest.TestCase):
    def test_deb_installs_program_command_menu_entry_and_icon(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            release = tmp / "invenux-1.2.3-linux-x86_64"
            (release / "_internal").mkdir(parents=True)
            (release / "_internal" / "base_library.zip").write_bytes(b"stub")
            program = release / "invenux"
            program.write_text("#!/bin/sh\n", encoding="utf-8")
            program.chmod(0o755)
            shutil.copy(ROOT / "packaging" / "linux" / "invenux.desktop", release)
            shutil.copy(ROOT / "brand" / "icons" / "invenux-256.png", release / "invenux.png")

            subprocess.run(
                ["sh", str(ROOT / "packaging" / "linux" / "build_deb.sh"), str(release), "1.2.3", str(tmp / "out")],
                check=True, capture_output=True,
            )
            deb = tmp / "out" / "invenux_1.2.3_amd64.deb"
            info = subprocess.run(["dpkg-deb", "--info", str(deb)], check=True, capture_output=True, text=True).stdout
            contents = subprocess.run(["dpkg-deb", "--contents", str(deb)], check=True, capture_output=True, text=True).stdout
            subprocess.run(["dpkg-deb", "--extract", str(deb), str(tmp / "root")], check=True)
            desktop = (tmp / "root" / "usr/share/applications/invenux.desktop").read_text(encoding="utf-8")

        self.assertIn("Package: invenux", info)
        self.assertIn("Version: 1.2.3", info)
        self.assertIn("postrm", info)
        self.assertIn("./opt/invenux/invenux", contents)
        self.assertIn("./opt/invenux/_internal/base_library.zip", contents)
        self.assertIn("./usr/bin/invenux -> /opt/invenux/invenux", contents)
        self.assertIn("./usr/share/icons/hicolor/256x256/apps/invenux.png", contents)
        self.assertIn("root/root", contents)
        self.assertIn("Exec=/opt/invenux/invenux\n", desktop)
        self.assertIn("Icon=invenux\n", desktop)

    def test_rejects_a_folder_that_is_not_a_release(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["sh", str(ROOT / "packaging" / "linux" / "build_deb.sh"), directory, "1.0.0", directory],
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an extracted", result.stderr)


if __name__ == "__main__":
    unittest.main()
