# Changelog

Notable changes to Invenux (called Invent-SSH up to 0.5.0) are recorded here.

## [1.0.0] — 2026-11-07

### Added

- ssh-agent and jump host: **Use the keys in ssh-agent** logs in with the agent's keys, and a bastion (host, port, user) is opened once per collection with one forwarded channel per machine. Host keys are checked, and remembered, for the bastion and for each machine. Command line: `--agent`, `--jump-host`, `--jump-port`, `--jump-user` (#32).
- SSH port per machine: an `SSH_PORT` column (also `PORT`, `PORTA`, `PUERTO`) overrides the panel port for its row; the port used shows in the details and the reports, and rows with a port outside 1 to 65535 are skipped and listed (#31).
- Snapshots: **Compare with** takes any other snapshot as the base, the CSV export carries both dates, a snapshot can be deleted, and a retention (last N snapshots or last N days) runs after each collection and keeps the newest (#34).
- `--report-changes FILE` writes the hardware changes since the previous snapshot after a command-line collection; the file is empty when nothing changed, for cron, systemd timers and Task Scheduler (#35).
- Memory slots for non-root users: when plain `dmidecode` shows no devices, the probe tries `sudo -n dmidecode -t memory`, which never prompts. `dmidecode` is also found in `/usr/sbin` and `/sbin` (#33).
- Native file dialog on Windows and macOS (pywebview, then PowerShell or `osascript`), so Choose spreadsheet keeps the original path instead of an uploaded copy (#36). Not run on Windows or macOS yet (#38).
- `invenux_<version>_amd64.deb` next to the Linux `.tar.xz`, installed in `/opt/invenux` with the `invenux` command and a menu entry (#37). The release job and an `apt` install were not run yet (#38).

### Changed

- During a scan the interface asks only for the records that changed (#29).

### Fixed

- Keyboard and screen reader: rows take focus and move with the arrow keys, sheets trap focus and give it back, the status banner is a live region, icon-only controls have labels in the three languages, text and button colors reach 4.5:1 in both themes, and the toolbar wraps below 680 px (#30).
- Pressing Enter in the spreadsheet path field reloads the same path, so an edited spreadsheet can be read again (#30).
- After a page reload the SSH password was erased when starting a collection, which failed with a missing-password error; it is now sent only when the field was edited (#30).
- Virtual disks are classified as Virtual (#28).
- `LICENSE` is the English MIT text, so GitHub detects it; the Portuguese text is in `LICENSE.pt-BR.md` (#27).

## [0.9.2] — 2026-10-20

### Added

- About and settings, opened from the sidebar footer or the app name: language, theme, version and updates, and what Invenux is built with. Language and theme use segmented controls; the old selects lost their open menu whenever the screen refreshed.
- Command-line collections take the SSH password from `INVENUX_SSH_PASSWORD` or `--ask-password` (prompted without echo). There is no password option, so it never shows in the process list or shell history; the variable is removed from the environment once read (#12).

### Changed

- Light theme buttons use a soft shadow instead of a dark edge, and an open toolbar menu no longer gets a blue ring.
- The search field spans the width of the details column below it, with a gray fill in the light theme.
- The Collected column left the table: every machine of a run shares the same minute. The details pane and the reports keep the date and time.

### Fixed

- Storage capacity read "128 GB total (1 physical block devices)" in every language. It is now the capacity alone; the disks stay listed in the machine details. Snapshot comparisons ignore the old wording, so the first collection after updating does not mark every machine as changed.
- The log no longer ends each line with " | value=N/A" or records two paramiko lines per connection.

## [0.9.1] — 2026-10-20

### Fixed

- Programs started by the Linux package inherited its library path: the in-app update stopped in `install.sh` (`gtk-update-icon-cache`: `libmount.so.1: version MOUNT_2_40 not found`), and the file picker (`zenity`, `kdialog`) and Open folder (`xdg-open`) could fail the same way. They now run with the system libraries. On Windows, the new `.exe` started by an update runs as a program of its own.

## [0.9.0] — 2026-10-20

Versions 0.8.0 to 0.8.2 were published for a few hours on 2026-10-20 and are folded into this release.

### Added

- The version shows in the sidebar and in the help sheet. On startup Invenux asks the GitHub releases API whether a newer version exists; the help sheet turns this off. "Update to X" downloads the package for this system and checks it against `SHA256SUMS`: a Linux package installed with `install.sh` is replaced in place, Windows opens the new `.exe` and macOS shows the downloaded `.zip`.
- Light theme. The sidebar offers System, Light and Dark; System follows the operating system.
- Release packages open their own window instead of a browser tab: WebView2 on Windows, WebKit on macOS and a bundled Qt WebEngine on Linux. Closing the window stops the program.
- `install.sh` in the Linux package installs the program, menu entry and icon for the current user; `--uninstall` removes them.
- Optional `USER` and `PASSWORD` columns in the target spreadsheet for machines whose SSH access differs from the SSH panel; empty cells use the panel. Passwords stay in the collector's memory and never reach the table, reports, snapshots or logs, and dropped spreadsheets are copied with owner-only permissions.
- CI opens every package and checks it shows its own window; the Linux package built on Ubuntu 22.04 is also opened on Ubuntu 24.04, and macOS Intel is built on every push.

### Changed

- The Linux package is a folder compressed as `.tar.xz` (about 140 MB, because of Qt WebEngine) and the macOS app is no longer a single self-extracting executable, so both start without unpacking to a temporary folder.
- README screenshots and GIFs show the page clock at the same fixed time as the demo data.

### Fixed

- The Linux package uses the system's `libstdc++`, `libgcc_s`, `libgbm` and GLib. Copies from the Ubuntu 22.04 build machine kept Mesa's EGL from loading on newer systems such as Debian 13, and the window aborted.
- The macOS Intel package closed right after opening: `cryptography` 49 and later have no Intel wheel, and a source build linked Homebrew's OpenSSL. The Intel build pins `cryptography` below 49. The 0.7.0 Intel package had the same defect and was removed from that release.
- The first-run screen, tutorial and help sheet still said "Invent-SSH".
- The Linux menu entry matched the window class with the wrong case (`Invenux` instead of `invenux`) and declared two main categories.

## [0.7.0] — 2026-10-20

### Added

- SSH port setting in the SSH panel (22 by default) and `--ssh-port` on the command line. Host keys for other ports are stored as `[host]:port`, the OpenSSH convention.
- Release packages built by CI for every version tag: Linux x86_64 (`.tar.gz` with the menu entry and icon), Windows x86_64 (`.exe`) and macOS (`.zip` with the app, Apple Silicon and Intel), with `SHA256SUMS`.

### Changed

- "Connection refused" names the port that was tried and suggests SSH may be on another port.

## [0.6.0] — 2026-10-20

### Added

- Interface, reports, template and messages in Portuguese (Brazil), English and Spanish, following the system language until one is chosen.
- Animated tutorial showing how the spreadsheet is read, in the first-run screen and the help sheet; the template gains a how-to sheet.
- New icon set (PNG 16 to 1024, Windows `.ico`, macOS `.icns`, page favicon), a Linux `.desktop` entry, README wordmarks and the GitHub social preview, rendered from `brand/` by `scripts/render_brand.py`.
- `scripts/demo_server.py` and `scripts/capture_media.mjs` regenerate the README screenshots and GIFs from a fictional fleet.

- First-run guide in three steps, a `Como usar` sheet with the spreadsheet format, collected data, status meanings and folders, and `Abrir pasta`/`Abrir` buttons after exports.
- Drag and drop of the target spreadsheet onto the window.
- System details in the inspector and reports: OS version and codename, desktop and display server, connected displays, package count, init, time zone, root filesystem usage, IPv4 and MAC per adapter.
- Every memory slot with locator, size, type, speed and part number, total slots and maximum capacity.
- Collection time per machine in the table and the inspector.
- Responsive layout down to 600 px wide; the window minimum is 720x520 and it opens maximized on smaller screens.
- Excel export with the logo, indicator cards, storage/memory/distribution/location tables with data bars, grouped and colored inventory columns, real dates and numeric coverage.
- After loading targets, the app lists rows without an address and repeated addresses, and opens the SSH panel when access is missing.

### Changed

- Renamed from Invent-SSH to Invenux. The old `invent-ssh` data and settings folders are copied to the new ones on first run.
- Reports and the template go to `Invenux` in the localized Documents folder (`~/Documentos/Invenux` on pt-BR Linux).
- Unsupported system languages fall back to English instead of Portuguese.
- Offline hosts state the cause: connection refused, no answer on the network, time limit, or DNS failure, instead of "Timeout" for all.
- The inspector shows only the diagnosis for hosts that were not collected.

### Fixed

- Alvos, SSH and Exportar did not open in browsers with the Popover API: the inline `togglePopover()` call resolved to the native element method.
- The probe parser dropped sections whose name has a digit (`ipv4`).
- A repeated address in the spreadsheet left one row in `PENDING` after the scan.
- The log claimed a report was saved after each scan and recorded every host's full record.

## [0.5.0] — 2026-10-20

### Changed

- Replaced the Tk desktop UI with a local web interface (`ui/index.html`) served by `app.py` on `127.0.0.1` and shown in `pywebview`, GTK WebKit2 or the default browser.
- Replaced the mascot with a geometric mark and a dark macOS-style palette.
- Reports are written only through Exportar or the CLI; a scan no longer saves an XLSX by itself.
- SSH host keys use TOFU by default: unknown keys are stored in the app `known_hosts` and a changed key is rejected.

### Added

- SQLite snapshot history with field-by-field comparison and CSV export of the changes.
- Fleet view with storage, memory and distribution breakdowns per location.

### Fixed

- XLSX export failed without Pillow (`ImportError`) because of the embedded logo.
- Parallel workers overwrote each other's TOFU entries in `known_hosts`.
- CPU lists such as `0-3,8` counted a single CPU as its index.
- The local server accepted any `Host` header, so a DNS-rebinding page could read the session token.
- In browser mode the server kept running after the tab closed; it now stops after 180 s without requests.
- SQLite connections were never closed.

## [0.4.0] — 2026-10-19

### Changed

- Repositioned the application around public, company-neutral Linux hardware inventory.
- Introduced a custom penguin mark, dark navy desktop shell, yellow primary actions, persistent side navigation, maximized-by-default and resizable windows, and responsive home cards.
- Removed the mandatory database integration and company-specific input/output paths.
- Accepted generic target-column aliases and preserved arbitrary asset metadata from input spreadsheets.
- Split report generation into a dedicated module.

### Added

- Rebranded XLSX reports with embedded product mark, an executive overview, native filters, and a custom midnight-navy/signal-yellow palette.
- Self-contained HTML reports with embedded logo, localized status badges/footer, summary metrics, search, and status filtering.
- CSV formula-injection mitigation and HTML escaping tests.
- Strict SSH host-key validation by default with an explicit, warned compatibility option.
- Bounded in-flight scheduling for large target lists.
- Product vision, architecture, security, contribution, and localized README documentation.

- Added OS-locale fallback on first launch while preserving an explicitly saved language preference.
- Added Linux system-detail collection for CPU topology, RAM availability/modules, each disk and partition, GPU, NIC details, firmware, uptime, virtualization, and collection provenance.
- Reduced per-machine discovery to one bounded read-only SSH command and made core-field coverage honest about missing facts.
- Documented the actual Linux collection sources and the limits of each hardware classification.
- Added native package builds and CI artifacts for Windows, macOS and Linux, alongside a cross-platform test matrix.
