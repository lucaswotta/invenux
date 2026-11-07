# Architecture

## Data Flow

```text
CSV / XLSX target list
        |
        v
core.py (normalize columns, preserve metadata, bounded ThreadPoolExecutor)
        |
        +---> inspector.py (single SSH round-trip POSIX probe + TOFU known_hosts)
        |
        v
Terminal records (emitted incrementally via HOST_RESULT events)
        |
        +---> snapshots.py (SQLite persistence, diff calculation, fleet analytics)
        |
        +---> reporting.py (XLSX, CSV, and offline HTML generation)
        |
        v
app.py (InventoryController + local HTTP/JSON server + native WebView/browser shell)
```

## Modules

- `app.py`: `InventoryController`, local `ThreadingHTTPServer` bound to `127.0.0.1` with per-session token verification (`X-Invenux-Token`), CLI runner, and desktop window launcher (`pywebview`, `Gtk 3.0` + `WebKit2`, or browser) and the file dialog (`zenity`/`kdialog` on Linux; the pywebview dialog, then PowerShell or `osascript`, on Windows and macOS). Release packages carry pywebview: WebView2 on Windows, WebKit on macOS and Qt WebEngine (PySide6) on Linux; `scripts/smoke_window.py` checks in CI that each package opens its own window (on Linux, through DevTools, that the UI loads in it).
- `ui/index.html`: Single-page interface with three views (Collection, Fleet, Snapshots), popovers (Targets, SSH, Export), the hardware inspector, the help sheet with the spreadsheet tutorial, and its pt-BR/en/es catalog as an embedded JSON block.
- `core.py`: Streaming `.xlsx`/`.xlsm`/`.csv` target loader, `Terminal` dataclass, bounded worker pool (`max_workers`), consecutive-failure circuit breaker, and event queue emission.
- `inspector.py`: SSH connection lifecycle (password, key file or `ssh-agent`, optional `JumpHost` reached once per collection with one `direct-tcpip` channel per machine) and read-only POSIX shell probe (`_PROBE_SCRIPT`) reading `/etc/os-release`, `uname`, `lscpu`, `/proc/cpuinfo`, `/proc/meminfo`, `dmidecode -t memory` (falling back to `sudo -n`), `lsblk`, `df`, `/sys/class/dmi/id`, `lspci`, `/sys/class/drm`, `/sys/class/net`, `ip`, `ps`, package managers, `/proc/uptime`, and `systemd-detect-virt`.
- `snapshots.py`: `SnapshotStore` backed by `sqlite3` (`snapshots.db`), field-by-field diff engine (`compute_records_diff`), and neutral distribution aggregator (`compute_fleet_analytics`).
- `reporting.py`: Report exporter for `.xlsx`, `.csv`, and `.html`, plus `.xlsx` target template generator (`create_template_workbook`).
- `paths.py`: OS-appropriate user directories for configuration, logs, known hosts, SQLite snapshots, and exported reports.
- `i18n.py`: Messages generated in Python, in `pt-br`, `en` and `es`, and the system-language detection.
- `build.py`: Native `PyInstaller` packaging script.
- `scripts/`: `render_brand.py` (icons, wordmarks, social preview), `demo_server.py` and `capture_media.mjs` (README media from a fictional fleet).
- `brand/`: icon sources (`icon.svg`, `icon-small.svg`), rendered icons, `.ico`, `.icns`, social preview; `packaging/linux/invenux.desktop` and `packaging/linux/install.sh` (per-user install from the release folder) and `packaging/linux/build_deb.sh` (the `.deb` built from the same folder).

## Security Boundaries

- Local API endpoints require the per-process `X-Invenux-Token` header and a `Host` of `127.0.0.1` or `localhost`, which blocks DNS rebinding.
- In browser mode the page pings `/api/ping` every 20 s and the process exits after 180 s without requests.
- SSH passwords exist only in process memory and are stripped from `public_config()` and `config.json`.
- Host keys are checked against system `known_hosts` and `~/.local/share/invenux/known_hosts`. When `trust_unknown_hosts` (TOFU, the default) is enabled, newly discovered host keys are merged into that file under a lock so subsequent key changes trigger `BadHostKeyException`.
- Spreadsheet exports prefix values starting with `=`, `+`, `-`, or `@` with `'` to prevent formula execution.
- HTML exports escape all collected and user-supplied strings.
