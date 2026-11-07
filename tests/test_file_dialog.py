"""System file dialogs per platform; the commands are checked here, the dialogs need the real systems."""
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

import app

PATTERNS = ["*.xlsx", "*.xlsm", "*.csv"]


def finished(stdout, returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


class FileDialogTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(app, "_webview_window", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def pick(self, platform, result, title='Choose the "machines" sheet'):
        with patch.object(app.sys, "platform", platform), patch("app.subprocess.run", return_value=result) as run:
            chosen = app._pick_local_file(title, PATTERNS)
        return chosen, run

    def test_macos_uses_osascript_with_the_title_as_an_argument(self):
        chosen, run = self.pick("darwin", finished("/Users/ana/Planilhas/máquinas.xlsx\n"))
        self.assertEqual(chosen, "/Users/ana/Planilhas/máquinas.xlsx")
        command = run.call_args.args[0]
        self.assertEqual(command[0], "osascript")
        self.assertEqual(command[-1], 'Choose the "machines" sheet')
        script = " ".join(command[1:-1])
        self.assertNotIn("machines", script)
        self.assertIn('of type {"xlsx", "xlsm", "csv"}', script)

    def test_macos_cancel_returns_nothing(self):
        chosen, _run = self.pick("darwin", finished("", returncode=1))
        self.assertIsNone(chosen)

    def test_windows_uses_a_winforms_dialog_without_quoting_the_title(self):
        chosen, run = self.pick("win32", finished("C:\\Users\\ana\\máquinas.xlsx"))
        self.assertEqual(chosen, "C:\\Users\\ana\\máquinas.xlsx")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["powershell", "-NoProfile"])
        self.assertIn("-STA", command)
        self.assertIn("OpenFileDialog", command[-1])
        self.assertNotIn("machines", command[-1])
        env = run.call_args.kwargs["env"]
        self.assertEqual(env["INVENUX_DIALOG_TITLE"], 'Choose the "machines" sheet')
        self.assertEqual(env["INVENUX_DIALOG_FILTER"], "*.xlsx;*.xlsm;*.csv|*.xlsx;*.xlsm;*.csv|*.*|*.*")
        self.assertEqual(run.call_args.kwargs["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def test_windows_without_powershell_falls_back_to_the_upload(self):
        with patch.object(app.sys, "platform", "win32"), patch("app.subprocess.run", side_effect=FileNotFoundError):
            self.assertIsNone(app._pick_local_file("Title", PATTERNS))

    def test_pywebview_window_dialog_comes_first_on_windows_and_macos(self):
        fake_webview = types.SimpleNamespace(FileDialog=types.SimpleNamespace(OPEN=10))
        window = Mock()
        window.create_file_dialog.return_value = ("C:\\Inventario\\maquinas.xlsx",)
        with patch.dict(sys.modules, {"webview": fake_webview}), patch.object(app, "_webview_window", window):
            chosen, run = self.pick("win32", finished("ignored"))
            self.assertEqual(chosen, "C:\\Inventario\\maquinas.xlsx")
            run.assert_not_called()
            window.create_file_dialog.assert_called_once_with(
                10, file_types=("Spreadsheets (*.xlsx;*.xlsm;*.csv)", "All files (*.*)")
            )
            window.create_file_dialog.return_value = None
            chosen, run = self.pick("darwin", finished("ignored"))
            self.assertIsNone(chosen)
            run.assert_not_called()

    def test_failing_pywebview_dialog_falls_back_to_the_system_command(self):
        window = Mock()
        window.create_file_dialog.side_effect = RuntimeError("no GUI loop")
        with patch.dict(sys.modules, {"webview": types.SimpleNamespace(OPEN_DIALOG=10)}), patch.object(app, "_webview_window", window):
            chosen, run = self.pick("darwin", finished("/Users/ana/a.csv\n"))
        self.assertEqual(chosen, "/Users/ana/a.csv")
        run.assert_called_once()

    def test_linux_keeps_zenity_first(self):
        window = Mock()
        with (
            patch.object(app, "_webview_window", window),
            patch("app.shutil.which", side_effect=lambda name: "/usr/bin/zenity" if name == "zenity" else None),
        ):
            chosen, run = self.pick("linux", finished("/home/ana/maquinas.csv\n"))
        self.assertEqual(chosen, "/home/ana/maquinas.csv")
        self.assertEqual(run.call_args.args[0][0], "zenity")
        window.create_file_dialog.assert_not_called()


if __name__ == "__main__":
    unittest.main()
