<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/media/wordmark-dark.png">
  <img src="docs/media/wordmark-light.png" alt="Invenux" height="84">
</picture>

<br>
<br>

**Linux hardware inventory over SSH, from a spreadsheet of machines.**

Agentless and read-only: nothing is installed or written on the machines.

<br>

<a href="https://github.com/lucaswotta/invenux/stargazers"><img src="https://img.shields.io/github/stars/lucaswotta/invenux?style=flat-square&logo=github&labelColor=1C1C1E&color=0A84FF" alt="GitHub stars"></a>
<a href="https://github.com/lucaswotta/invenux/releases/latest"><img src="https://img.shields.io/github/v/release/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="Latest release"></a>
<a href="https://github.com/lucaswotta/invenux/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/lucaswotta/invenux/quality.yml?branch=main&style=flat-square&label=CI&labelColor=1C1C1E&color=0A84FF" alt="CI"></a>
<a href="https://github.com/lucaswotta/invenux/commits/main"><img src="https://img.shields.io/github/last-commit/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="Last commit"></a>
<a href="LICENSE"><img src="https://img.shields.io/github/license/lucaswotta/invenux?style=flat-square&labelColor=1C1C1E&color=0A84FF" alt="MIT license"></a>
<img src="https://img.shields.io/badge/python-3.11%2B-0A84FF?style=flat-square&labelColor=1C1C1E&logo=python&logoColor=white" alt="Python 3.11+">
<img src="https://img.shields.io/badge/runs%20on-Linux%20%C2%B7%20Windows%20%C2%B7%20macOS-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Runs on Linux, Windows and macOS">
<img src="https://img.shields.io/badge/UI-EN%20%C2%B7%20PT--BR%20%C2%B7%20ES-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Interface in English, Portuguese and Spanish">
<img src="https://img.shields.io/badge/telemetry-none-0A84FF?style=flat-square&labelColor=1C1C1E" alt="No telemetry">
<a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-0A84FF?style=flat-square&labelColor=1C1C1E" alt="Pull requests welcome"></a>

<br>

[Download](https://github.com/lucaswotta/invenux/releases/latest) ·
[Features](#features) ·
[Install](#install) ·
[How to use](#how-to-use) ·
[The spreadsheet](#the-spreadsheet) ·
[FAQ](#faq) ·
[Contribute](CONTRIBUTING.md) ·
[Português](README.pt-BR.md) ·
[Español](README.es.md)

<br>

<img src="docs/media/demo-en.gif" width="900" alt="Loading a spreadsheet of 24 machines, entering SSH access, collecting, opening one machine's details, the fleet view and the Excel export">

</div>

## Why Invenux

- **One spreadsheet in, one inventory out.** List the machines with their IP addresses, enter SSH access, press start. Each machine shows up with processor, memory slots, disks, motherboard, BIOS, graphics, network and operating system.
- **Nothing to install on the machines.** One SSH connection runs one read-only script per machine. No agent, no daemon, no file written on the target.
- **It tells you why a machine failed.** Powered off, SSH port closed, time limit, unknown name, wrong password or a changed host key, each with its own message.
- **Reports people actually open.** Excel with a summary sheet and grouped columns, a searchable offline HTML page, and CSV.
- **History without a database server.** Every collection is saved locally and compared field by field with the previous one, so a swapped disk or a memory upgrade stands out.

## Features

| Area | What you get |
| --- | --- |
| **Collection** | Up to 128 parallel SSH connections on any SSH port (22 by default), password, private key or the keys in `ssh-agent`, an optional jump host (bastion), trust on first use for host keys, cancel at any time. |
| **System** | Distribution, version and codename, kernel, architecture, hostname, desktop and display server, displays, package count, init, time zone, uptime, root disk usage. |
| **Hardware** | Manufacturer and model, motherboard, BIOS, processor with cores, threads and frequency, every memory slot (size, type, speed, part number) and the board's maximum, every disk and partition, graphics, network adapters with IPv4 and MAC. |
| **Fleet view** | Storage types, memory capacity and Linux distributions across the online machines, and a breakdown by location. |
| **Snapshots** | Local history of every collection with a field-by-field comparison against the previous one or any other (**Compare with**), exportable to CSV with both dates. Delete a snapshot (asks first) or set a retention in About and settings (keep the last N, or the last N days; applied after each collection, the newest is always kept). |
| **Exports** | Excel (summary with data bars, inventory grouped by subject), interactive HTML that works offline, CSV with formula injection neutralized. |
| **Interface** | English, Portuguese (Brazil) and Spanish, following the system language; built-in guide with an animated tutorial; resizable down to 720 × 520. |
| **Desktop** | Native window on Linux, Windows and macOS (pywebview or GTK), or your browser; packaged builds for the three systems; an About and settings sheet (sidebar footer or the app name) with language, light or dark theme, the version and a one-click update to a newer release. |

<div align="center">

<img src="docs/media/hero-en.png" width="900" alt="Collection view: 24 machines with status, address, hostname, location, processor, memory, storage and system, and the details of one machine on the right">

</div>

<table>
  <tr>
    <td width="50%"><img src="docs/media/fleet-en.png" alt="Fleet view with storage, memory and distribution breakdowns and a table by location"></td>
    <td width="50%"><img src="docs/media/excel-en.png" alt="Excel export summary sheet with indicator cards and tables with data bars"></td>
  </tr>
  <tr>
    <td align="center">Fleet view</td>
    <td align="center">Excel export</td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/media/onboarding-en.png" alt="First run: three steps and an animated tutorial showing how the spreadsheet is read"></td>
    <td width="50%"><img src="docs/media/help-en.png" alt="How to use sheet with the tutorial, steps, folders and spreadsheet columns"></td>
  </tr>
  <tr>
    <td align="center">First run</td>
    <td align="center">Built-in guide</td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/media/light-en.png" alt="Fleet view in the light theme"></td>
    <td width="50%"><img src="docs/media/narrow-en.png" alt="Collection view in a 760 px wide window, with the details below the table"></td>
  </tr>
  <tr>
    <td align="center">Light theme</td>
    <td align="center">Narrow window</td>
  </tr>
</table>

## Install

### Download

Get the file for your system from the [latest release](https://github.com/lucaswotta/invenux/releases/latest):

| System | File | How to start |
| --- | --- | --- |
| Windows 10/11 (x86_64) | `invenux-<version>-windows-x86_64.exe` | Run it. SmartScreen warns about an unsigned program: **More info**, then **Run anyway**. |
| macOS (Apple Silicon or Intel) | `invenux-<version>-macos-arm64.zip` or `-macos-x86_64.zip` | Unzip and open `Invenux.app`. The first time, right-click it and choose **Open**, because the app is not notarized. |
| Linux (x86_64, glibc 2.35 or newer) | `invenux-<version>-linux-x86_64.tar.xz` | Extract and run `./install.sh` to add it to the application menu, or run `./invenux` from the folder. |

The packages are not code-signed; `SHA256SUMS` in the release lists the checksums. Each one opens its own window: WebView2 on Windows (part of Windows 10 and 11), WebKit on macOS and a bundled Qt WebEngine on Linux, which is why the Linux download is about 135 MB.

### From source

**Requirements:** Python 3.11 or newer, and Linux machines reachable over SSH (port 22 by default, configurable).

```sh
git clone https://github.com/lucaswotta/invenux.git
cd invenux
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python3 -m pip install -r requirements.txt
python3 app.py
```

The window uses [pywebview](https://pywebview.flowrl.com/) when it is installed, then GTK WebKit2 on Linux (`python3-gi` and `gir1.2-webkit2-4.1` on Debian and Ubuntu, available to a venv created with `--system-site-packages`), and otherwise opens the interface in your default browser. In the browser the program stops about 3 minutes after the tab is closed.

**Native package.** `python build.py` creates the package for the system you run it on (PyInstaller is not a cross-compiler): one `.exe` on Windows, a folder on Linux and an app bundle on macOS. Pushing a `v*` tag builds the Linux, Windows and macOS packages in CI and publishes them as a GitHub release.

```sh
python3 -m pip install -r requirements-build.txt
python3 build.py                   # dist/invenux-v0.9.2
```

On Linux, `./install.sh` in the extracted release folder copies the program to `~/.local/lib/invenux`, links `~/.local/bin/invenux` and adds the menu entry and icon, without sudo. `./install.sh --uninstall` removes them and keeps history and reports.

## How to use

1. **Targets:** choose the machine spreadsheet, drag it onto the window, or paste its path. No spreadsheet yet? **Get the template**.
2. **SSH:** enter the user, the port (22 unless your machines use another one) and a password, a private key or **Use the keys in ssh-agent**. The password stays in memory only. Machines reachable only through a bastion: fill **Jump host** (host, port and user; an empty user means the SSH user). Invenux logs in to the bastion once per collection, with the same password, key or agent, and opens one forwarded channel per machine; host keys are checked on the bastion and on every machine.
3. **Start collection:** follow each machine in the table and click a row for its details.
4. **Export:** Excel, HTML or CSV, saved in the `Invenux` folder inside your Documents folder, with **Open** and **Open folder** right after.

`How to use` in the toolbar has the animated tutorial, the spreadsheet format, what each status means and buttons to open the report, history and log folders.

**Command line.** Collect and export without the interface. Use `--key`, or a password from the `INVENUX_SSH_PASSWORD` environment variable or `--ask-password` (asked without echo); there is no password option, so it never shows in the process list or shell history:

```sh
python3 app.py --input machines.xlsx --user inventory --key ~/.ssh/id_ed25519 --ssh-port 22 --output-format XLSX
python3 app.py --input machines.xlsx --user inventory --ask-password
python3 app.py --input machines.xlsx --user inventory --agent --jump-host bastion.example.com --jump-user admin
```

### Scheduled collections

`--report-changes FILE` makes a command-line run also write the hardware changes (processor, memory, storage, motherboard) against the previous snapshot, for machines that were online in both runs. Status, system and kernel changes are left out, and the file is empty (0 bytes) when nothing changed, so a scheduler can act only when it has content. Every run saves a snapshot that shows up in the Snapshots view. Use a key, since there is nobody to type a password; the examples use the Linux install (`~/.local/bin/invenux`), and `python3 /path/to/invenux/app.py` works the same from source.

cron (every Monday at 07:00, mail the changes when there are any):

```sh
0 7 * * 1 $HOME/.local/bin/invenux --input $HOME/inventory/machines.xlsx --user inventory --key $HOME/.ssh/id_ed25519 --report-changes $HOME/inventory/changes.csv && [ -s $HOME/inventory/changes.csv ] && mail -s "Hardware changes" admin@example.com < $HOME/inventory/changes.csv
```

systemd timer (`~/.config/systemd/user/invenux.service` and `invenux.timer`, then `systemctl --user enable --now invenux.timer`):

```ini
# invenux.service
[Service]
Type=oneshot
ExecStart=%h/.local/bin/invenux --input %h/inventory/machines.xlsx --user inventory --key %h/.ssh/id_ed25519 --report-changes %h/inventory/changes.csv

# invenux.timer
[Timer]
OnCalendar=Mon 07:00
Persistent=true

[Install]
WantedBy=timers.target
```

Windows Task Scheduler (PowerShell, every Monday at 07:00):

```powershell
$action = New-ScheduledTaskAction -Execute "C:\Tools\invenux.exe" -Argument '--input C:\Inventory\machines.xlsx --user inventory --key C:\Users\me\.ssh\id_ed25519 --report-changes C:\Inventory\changes.csv'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 7am
Register-ScheduledTask -TaskName "Invenux inventory" -Action $action -Trigger $trigger
```

## The spreadsheet

`.xlsx`, `.xlsm` or `.csv` (comma or semicolon). The first row is the header and every following row is a machine.

| Column | Required | Use |
| --- | --- | --- |
| `IP` | Yes | Address or name of the machine. `HOST`, `HOSTNAME`, `ADDRESS`, `IP_ADDRESS`, `ENDPOINT` or `TARGET` also work. |
| `LOCATION` | No | Site or room; groups the fleet view and the reports. `SITE`, `LOCAL`, `UNIDADE`, `FILIAL`, `SETOR`, `UBICACION`, `SEDE` and `SUCURSAL` also work. |
| `USER` | No | SSH user for that machine when it differs from the SSH panel. `USERNAME`, `SSH_USER`, `LOGIN` and `USUARIO` also work. |
| `PASSWORD` | No | SSH password for that machine, for fleets where passwords differ; normally the password goes in the SSH panel. `PASS`, `SENHA` and `CONTRASENA` also work. Empty cells use the panel. Invenux keeps it in memory only and never writes it to the table, reports, snapshots or logs, but the file holds it as plain text. |
| Any other | No | Copied as is to the table and every report, for example `ASSET_TAG`, `OWNER` or `NOTES`. |

Rows without an address and repeated addresses are skipped and listed after loading. The template (**Get the template**) comes with two example rows and a sheet explaining each column, in the interface language.

## What is collected

One SSH connection per machine runs a single POSIX shell script that reads:

| Source | Fields |
| --- | --- |
| `/etc/os-release`, `uname`, `/proc/1/comm`, `ps` | Distribution, version, kernel, architecture, hostname, init, desktop and display server |
| `lscpu`, `/proc/cpuinfo` | Processor model, sockets, cores, threads, maximum frequency, virtualization extension |
| `/proc/meminfo`, `dmidecode -t memory` | Total, used and available memory; every slot with size, type, speed and part number |
| `lsblk`, `df` | Every disk and partition, type (NVMe, SSD or HDD), capacity, root usage |
| `/sys/class/dmi/id` | Manufacturer, model, motherboard, BIOS |
| `lspci`, `/sys/class/drm` | Graphics adapters and connected displays |
| `/sys/class/net`, `ip` | Network adapters, link speed, driver, IPv4, MAC |
| `dpkg`, `rpm`, `pacman`, `apk`, `/etc/timezone` | Installed packages, time zone |

Memory slots need root (`dmidecode`). A user that is not root gets them when sudo lets it run `dmidecode` without a password (for example `inventory ALL=(root) NOPASSWD: /usr/sbin/dmidecode` in `/etc/sudoers.d/`): the probe then runs `sudo -n dmidecode -t memory`, which never asks for a password and fails at once without that rule. Without either, the slot fields show as unavailable and everything else is still collected. `Collection sources` in the reports says whether the slots came from `dmidecode`, `sudo -n dmidecode` or were unavailable. That sudo attempt is logged by sudo on the machine like any other, and a user missing from sudoers may trigger sudo's notice to the administrator. The serial number is not collected unless `include_sensitive_identifiers` is enabled in the configuration file.

## Where files are kept

| | Linux | Windows | macOS |
| --- | --- | --- | --- |
| Reports and template | `~/Documents/Invenux` (localized, for example `~/Documentos/Invenux`) | `Documents\Invenux` | `~/Documents/Invenux` |
| History (`snapshots.db`), host keys (`known_hosts`), logs | `~/.local/share/invenux` | `%LOCALAPPDATA%\Invenux` | `~/Library/Application Support/Invenux` |
| Settings (`config.json`) | `~/.config/invenux` | `%APPDATA%\Invenux` | `~/Library/Application Support/Invenux` |

Folders from the old name (`invent-ssh`) are copied over on the first run.

## Security and privacy

- The interface is served on `127.0.0.1` only, with a per-run token and a check of the `Host` header against DNS rebinding.
- The SSH password is never written to disk.
- Host keys use trust on first use by default: a new key is stored, a changed key is rejected. Turn it off in the SSH panel to accept only keys already known.
- Spreadsheet exports neutralize values that start like a formula; the HTML report escapes every collected value.
- No telemetry. Besides SSH to the machines you list, the only request is a read of the latest release from the GitHub API on startup (`api.github.com/repos/lucaswotta/invenux/releases/latest`); turn it off in About and settings. Updates are checked against the release's `SHA256SUMS` before they are opened or installed.

Report vulnerabilities privately, see [SECURITY.md](SECURITY.md).

## FAQ

**Does it change anything on the machines?**
No. The script only reads files and runs read-only commands. It writes nothing, not even to `/tmp`.

**Why do all my machines show a single memory module?**
Check the **Slots** line in the machine details: it shows how many slots are populated out of how many the board has, with each module listed. If it says unavailable, the SSH user is not root and has no passwordless sudo rule for `dmidecode`, see [What is collected](#what-is-collected).

**A machine shows as Offline, but it is on.**
The row says why. "Did not answer on the network" means no reply at all within about 3 seconds (often powered off or a wrong address); "Connection refused on port N" means it is on but SSH is stopped, blocked or listening on another port (set it in the SSH panel); "No answer within N s" means a firewall or a slow link, so raise the timeout in the SSH panel.

**Is there an installer?**
Not yet: Windows gets one `.exe`, macOS an app bundle and Linux a folder with `install.sh`. See [Download](#download).

**Can it inventory Windows or macOS machines?**
No. The targets must be Linux with SSH. The program itself runs on Linux, Windows and macOS.

**Which port does it use?**
22 by default. Change it in the SSH panel, or with `--ssh-port` on the command line; every machine in a collection uses the same port.

**Can I run it without the interface?**
Yes, see the command line above. It needs a private key.

## Limitations

- Targets must be Linux with SSH, and all machines in a collection share one SSH port.
- Memory slot details need root or passwordless sudo for `dmidecode` on the target.
- Storage type identifies virtual disks by model/vendor/name or a detected hypervisor. Hypervisor detection also classifies passthrough disks as Virtual. Other disks use NVMe transport/name and the kernel's rotational flag; non-rotating media includes USB flash.
- The command line accepts a private key only, not a password.

## Roadmap

Planned work and known problems are tracked as [issues](https://github.com/lucaswotta/invenux/issues): signed installers, SSH agent and jump host, per-machine SSH port, scheduled collections with a change report, comparing any two snapshots and accessibility. Comments and pull requests on any of them are welcome.

## Contributing

Pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers setup, tests, how to add a language and how the screenshots and GIFs in this README are regenerated from a fictional fleet (`scripts/demo_server.py`, `scripts/capture_media.mjs`).

If Invenux saves you a walk to every machine, starring the repository helps other people find it.

## License

[MIT](LICENSE) © Lucas Motta
