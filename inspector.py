"""Distribution-agnostic, read-only Linux hardware discovery over SSH.

Primary data sources are Linux system interfaces and common utilities. Optional
privileged tools enrich the result when available, but are never required for a
successful connection. Parser functions are pure and covered by local fixtures.
"""
from __future__ import annotations

import errno
import json
import re
import shlex
import socket
import threading
import time
from pathlib import Path
from typing import Any, Optional

import paramiko

from i18n import t
from paths import get_known_hosts_path

_KNOWN_HOSTS_LOCK = threading.Lock()


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _available(value: Any) -> bool:
    normalized = _clean_string(value).casefold()
    if not normalized or normalized in {"n/a", "na", "none", "unknown", "not available", "not specified", "not set"}:
        return False
    return not any(token in normalized for token in (
        "default string", "to be filled by o.e.m", "to be filled by oem",
        "system serial number", "not applicable",
    ))


def _run_command(
    client: paramiko.SSHClient,
    command: str,
    tolerant: bool = False,
    timeout: int = 12,
    max_output_bytes: int = 8_000_000,
) -> Optional[str]:
    """Run one bounded SSH command without deadlocks or truncated pipe reads."""
    channel = None
    try:
        _stdin, stdout, _stderr = client.exec_command(command, timeout=timeout)
        channel = stdout.channel
        channel.settimeout(min(float(timeout), 1.0))
        output = bytearray()
        errors = bytearray()
        deadline = time.monotonic() + timeout

        while True:
            while channel.recv_ready():
                chunk = channel.recv(32768)
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > max_output_bytes:
                    channel.close()
                    return None

            while channel.recv_stderr_ready():
                chunk = channel.recv_stderr(8192)
                if not chunk:
                    break
                # Stderr is drained to avoid blocking the remote process, but is
                # deliberately not returned: diagnostics may contain paths/identifiers.
                if len(errors) < 65536:
                    errors.extend(chunk[:65536 - len(errors)])

            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            if time.monotonic() >= deadline:
                channel.close()
                return None
            time.sleep(0.01)

        exit_code = channel.recv_exit_status()
        result = output.decode("utf-8", errors="replace").strip()
        if exit_code == 0 or (tolerant and result):
            return result or None
        return None
    except (OSError, EOFError, socket.timeout, TimeoutError, paramiko.SSHException):
        if channel is not None:
            channel.close()
        return None


def _parse_os_release(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        match = re.match(r"^\s*([A-Z0-9_]+)=(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _parse_lscpu(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        parsed[_clean_string(label).casefold()] = _clean_string(value)
    return parsed


def _parse_meminfo(output: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in output.splitlines():
        match = re.match(r"^\s*([A-Za-z_()]+):\s*(\d+)\s*(kB|KB|B)?", line)
        if not match:
            continue
        name, amount, unit = match.groups()
        value = int(amount)
        if unit and unit.casefold() == "kb":
            value *= 1024
        result[name] = value
    return result


def _module_size_label(amount: float, unit: str) -> str:
    # dmidecode reports binary units (a 4096 MB module is 4 GB).
    if unit == "MB" and amount >= 1024:
        return f"{amount / 1024:g} GB"
    return f"{amount:g} {unit}"


def _parse_memory_devices(output: str) -> dict[str, str]:
    blocks = re.split(r"(?m)^\s*Memory Device\s*$", output)
    installed: list[dict[str, Any]] = []
    slots = 0

    def field(block: str, name: str) -> str:
        match = re.search(rf"(?m)^\s*{name}:\s*(.+?)\s*$", block)
        return _clean_string(match.group(1)) if match else ""

    for block in blocks[1:]:
        size_text = field(block, "Size")
        if not size_text:
            continue
        slots += 1
        if size_text.casefold() in {"no module installed", "not installed", "unknown", "not specified"}:
            continue
        number = re.match(r"^([\d.]+)\s*(KB|MB|GB|TB)\b", size_text, re.I)
        if not number:
            continue
        amount, unit = float(number.group(1)), number.group(2).upper()
        size_bytes = amount * {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}[unit]
        speed_match = re.search(r"(?m)^\s*(?:Configured Memory Speed|Configured Clock Speed|Speed):\s*(\d+)\s*(?:MT/s|MHz)", block)
        vendor = " ".join(
            value for value in (field(block, "Manufacturer"), field(block, "Part Number"))
            if _available(value) and not re.fullmatch(r"(?:0x)?[0-9A-F]{4,}", value, re.I)
        )
        installed.append({
            "bytes": int(size_bytes),
            "size": _module_size_label(amount, unit),
            "type": field(block, "Type"),
            "speed": int(speed_match.group(1)) if speed_match else 0,
            "slot": field(block, "Locator") or field(block, "Bank Locator") or f"slot {slots}",
            "vendor": vendor,
        })

    types = []
    for module in installed:
        match = re.search(r"\bDDR[2-5]\b|\bDDR\b|\bLPDDR[2-5]X?\b", module["type"], re.I)
        if match:
            label = match.group(0).upper()
            if label not in types:
                types.append(label)
    speeds = sorted({module["speed"] for module in installed if module["speed"] > 0})
    total = sum(module["bytes"] for module in installed)
    module_lines = []
    for module in installed:
        parts = [module["slot"], f"{module['size']} {module['type']}".strip()]
        if module["speed"]:
            parts.append(f"{module['speed']} MT/s")
        if module["vendor"]:
            parts.append(module["vendor"])
        module_lines.append(" · ".join(parts))
    max_capacity = re.search(r"(?m)^\s*Maximum Capacity:\s*(.+?)\s*$", output)
    return {
        "ram_type": " / ".join(types) if types else "N/A",
        "ram_speed": " / ".join(f"{speed} MT/s" for speed in speeds) if speeds else "N/A",
        "ram_slots": f"{len(installed)} of {slots} populated" if slots else "N/A",
        "ram_modules": "\n".join(module_lines) if module_lines else "N/A",
        "ram_max_capacity": _clean_string(max_capacity.group(1)) if max_capacity else "N/A",
        "ram_module_total_bytes": str(total) if total else "0",
    }


def _format_capacity(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "N/A"
    if size_bytes >= 1000**4:
        value = f"{size_bytes / (1000**4):.2f}".rstrip("0").rstrip(".")
        return f"{value} TB"
    return f"{size_bytes / (1000**3):.0f} GB"


def _parse_lsblk(output: str, hypervisor: str = "") -> list[dict[str, Any]]:
    virtual_host = _clean_string(hypervisor).casefold() not in {"", "none", "n/a", "not available"}
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        # Older util-linux can lack JSON output. lsblk -P emits safely quoted
        # key/value records, which shlex can parse without guessing field order.
        devices = []
        for line in str(output or "").splitlines():
            try:
                fields = {}
                for token in shlex.split(line):
                    if "=" in token:
                        key, value = token.split("=", 1)
                        fields[key.casefold()] = value
                if fields:
                    devices.append(fields)
            except ValueError:
                continue
        if not devices:
            return []
        data = {"blockdevices": devices}
    devices = data.get("blockdevices", []) if isinstance(data, dict) else []
    parsed: list[dict[str, Any]] = []
    for device in devices if isinstance(devices, list) else []:
        if not isinstance(device, dict) or str(device.get("type", "")).casefold() != "disk":
            continue
        name = _clean_string(device.get("name"))
        if not name or name.casefold().startswith(("loop", "ram", "zram")):
            continue
        try:
            size = int(device.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size <= 0:
            continue
        rota = str(device.get("rota", "")).strip().casefold()
        transport = _clean_string(device.get("tran")).casefold()
        model = _clean_string(device.get("model"))
        vendor = _clean_string(device.get("vendor"))
        identity = f"{model} {vendor}".casefold()
        virtual_device = bool(re.fullmatch(r"vd[a-z]+", name.casefold())) or any(
            marker in identity for marker in ("qemu", "vbox", "virtual disk", "vmware", "virtio", "hyper-v")
        )
        if virtual_device or virtual_host:
            kind = "Virtual"
        elif name.casefold().startswith("nvme") or transport == "nvme":
            kind = "NVMe"
        elif rota in {"1", "true", "yes"}:
            kind = "HDD"
        elif rota in {"0", "false", "no"}:
            # The kernel reports a non-rotating device; this does not prove a
            # physical SATA/NVMe SSD (USB flash also qualifies).
            kind = "SSD / flash"
        else:
            kind = "Unknown"
        raw_mountpoints = device.get("mountpoints", device.get("mountpoint", []))
        if isinstance(raw_mountpoints, str):
            mountpoints = [raw_mountpoints] if raw_mountpoints else []
        elif isinstance(raw_mountpoints, list):
            mountpoints = [str(value) for value in raw_mountpoints if value]
        else:
            mountpoints = []
        partitions = []
        for child in device.get("children", []) or []:
            if not isinstance(child, dict):
                continue
            child_name = _clean_string(child.get("name"))
            child_size = child.get("size")
            try:
                child_size = int(child_size or 0)
            except (TypeError, ValueError):
                child_size = 0
            child_mount = child.get("mountpoints", child.get("mountpoint", []))
            if isinstance(child_mount, str):
                child_mountpoints = [child_mount] if child_mount else []
            elif isinstance(child_mount, list):
                child_mountpoints = [str(value) for value in child_mount if value]
            else:
                child_mountpoints = []
            fstype = _clean_string(child.get("fstype")) or "filesystem unknown"
            if child_name:
                partitions.append({
                    "name": child_name,
                    "capacity": _format_capacity(child_size),
                    "filesystem": fstype,
                    "mountpoints": child_mountpoints,
                })
        parsed.append({
            "name": name,
            "kind": kind,
            "classification_basis": "virtual device model/vendor/name" if virtual_device else "detected hypervisor" if virtual_host else "NVMe transport/name" if kind == "NVMe" else "kernel rotational flag" if kind in {"HDD", "SSD / flash"} else "unavailable",
            "size_bytes": size,
            "capacity": _format_capacity(size),
            "model": model or "N/A",
            "transport": transport.upper() if transport else "N/A",
            "removable": str(device.get("rm", "0")).strip().casefold() in {"1", "true", "yes"},
            "filesystem": _clean_string(device.get("fstype")) or "N/A",
            "mountpoints": mountpoints,
            "partitions": partitions,
        })
    return parsed


def _parse_network_interfaces(output: str) -> list[str]:
    adapters: list[str] = []
    for line in output.splitlines():
        match = re.match(r"^\s*\d+:\s+([^:]+):.*?(?:\bstate\s+([A-Z]+))?", line, re.I)
        if not match:
            continue
        name = match.group(1).split("@", 1)[0].strip()
        if not name or name == "lo":
            continue
        state = (match.group(2) or "").upper()
        if not state:
            flags = re.search(r"<([^>]+)>", line)
            state = "UP" if flags and "UP" in flags.group(1).split(",") else "DOWN"
        item = f"{name} ({state.lower()})"
        if item not in adapters:
            adapters.append(item)
    return adapters


def _parse_gpus(output: str) -> list[str]:
    devices: list[str] = []
    pattern = re.compile(r"^(?:[0-9a-fA-F:.]+\s+)?(?:VGA compatible controller|3D controller|Display controller)(?:\s+\[[0-9a-fA-F]{4}\])?:\s*(.+)$", re.I)
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match:
            device = _clean_string(match.group(1))
            if device and device not in devices:
                devices.append(device)
    return devices


def _format_uptime(output: str) -> str:
    try:
        total_seconds = max(0, int(float(output.strip().split()[0])))
    except (ValueError, IndexError, AttributeError):
        return "N/A"
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _format_gib(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "N/A"
    return f"{size_bytes / (1024**3):.1f} GiB"


_PROBE_SCRIPT = r"""
LC_ALL=C
export LC_ALL
printf '%s\n' '__INVENUX_BEGIN_os_release__'
if [ -r /etc/os-release ]; then
  cat /etc/os-release
elif [ -r /etc/lsb-release ]; then
  cat /etc/lsb-release
elif [ -r /etc/redhat-release ]; then
  cat /etc/redhat-release
elif [ -r /etc/debian_version ]; then
  printf 'Debian GNU/Linux '
  cat /etc/debian_version
fi
printf '%s\n' '__INVENUX_END_os_release__'

printf '%s\n' '__INVENUX_BEGIN_hostname__'
hostname 2>/dev/null || uname -n 2>/dev/null || true
printf '%s\n' '__INVENUX_END_hostname__'

printf '%s\n' '__INVENUX_BEGIN_kernel__'
uname -r 2>/dev/null || true
printf '%s\n' '__INVENUX_END_kernel__'

printf '%s\n' '__INVENUX_BEGIN_architecture__'
uname -m 2>/dev/null || true
printf '%s\n' '__INVENUX_END_architecture__'

printf '%s\n' '__INVENUX_BEGIN_lscpu__'
if command -v lscpu >/dev/null 2>&1; then lscpu 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_lscpu__'

printf '%s\n' '__INVENUX_BEGIN_cpuinfo__'
awk -F: '
/^[[:space:]]*(model name|Hardware|Processor)[[:space:]]*:/ {
  key=$1
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
  value=substr($0, index($0, ":")+1)
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
  if (key == "model name" && model == "") model=value
  else if (key == "Hardware" && hardware == "") hardware=value
  else if (key == "Processor" && processor == "") processor=value
}
/^[[:space:]]*processor[[:space:]]*:/ { logical++ }
/^[[:space:]]*(flags|Features)[[:space:]]*:/ {
  if ($0 ~ /(^|[[:space:]])vmx([[:space:]]|$)/) vmx=1
  if ($0 ~ /(^|[[:space:]])svm([[:space:]]|$)/) svm=1
}
END {
  if (model != "") print "Model name: " model
  else if (hardware != "") print "Hardware: " hardware
  else if (processor != "") print "Processor: " processor
  printf "CPU(s): %d\n", logical
  if (vmx) print "Virtualization: VT-x"
  else if (svm) print "Virtualization: AMD-V"
}' /proc/cpuinfo 2>/dev/null
printf '%s\n' '__INVENUX_END_cpuinfo__'

printf '%s\n' '__INVENUX_BEGIN_meminfo__'
cat /proc/meminfo 2>/dev/null || true
printf '%s\n' '__INVENUX_END_meminfo__'

printf '%s\n' '__INVENUX_BEGIN_memory_devices__'
if command -v dmidecode >/dev/null 2>&1; then dmidecode -t memory 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_memory_devices__'

printf '%s\n' '__INVENUX_BEGIN_lsblk__'
if command -v lsblk >/dev/null 2>&1; then
  lsblk -J -b -o NAME,TYPE,SIZE,ROTA,MODEL,VENDOR,TRAN,RM,FSTYPE,MOUNTPOINTS 2>/dev/null ||
    lsblk -J -b -o NAME,TYPE,SIZE,ROTA,MODEL,VENDOR,TRAN,RM,FSTYPE,MOUNTPOINT 2>/dev/null ||
    lsblk -dn -b -P -o NAME,TYPE,SIZE,ROTA,MODEL,VENDOR,TRAN,RM 2>/dev/null ||
    true
fi
printf '%s\n' '__INVENUX_END_lsblk__'

printf '%s\n' '__INVENUX_BEGIN_dmi__'
for n in __DMI_FIELDS__; do
  printf '__DMI__%s=' "$n"
  if [ -r "/sys/class/dmi/id/$n" ]; then
    cat "/sys/class/dmi/id/$n" 2>/dev/null
  elif [ -r "/sys/devices/virtual/dmi/id/$n" ]; then
    cat "/sys/devices/virtual/dmi/id/$n" 2>/dev/null
  else
    printf '\n'
  fi
done
printf '%s\n' '__INVENUX_END_dmi__'

printf '%s\n' '__INVENUX_BEGIN_lspci__'
if command -v lspci >/dev/null 2>&1; then lspci -nn 2>/dev/null || lspci 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_lspci__'

printf '%s\n' '__INVENUX_BEGIN_drm__'
for f in /sys/class/drm/card[0-9]*/device/uevent; do
  if [ -r "$f" ]; then cat "$f" 2>/dev/null || true; fi
done
printf '%s\n' '__INVENUX_END_drm__'

printf '%s\n' '__INVENUX_BEGIN_netlink__'
if command -v ip >/dev/null 2>&1; then ip -o link show 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_netlink__'

printf '%s\n' '__INVENUX_BEGIN_packages__'
if command -v dpkg-query >/dev/null 2>&1; then printf 'dpkg %s\n' "$(dpkg-query -f '.\n' -W 2>/dev/null | wc -l)"; fi
if command -v rpm >/dev/null 2>&1; then printf 'rpm %s\n' "$(rpm -qa 2>/dev/null | wc -l)"; fi
if command -v pacman >/dev/null 2>&1; then printf 'pacman %s\n' "$(pacman -Qq 2>/dev/null | wc -l)"; fi
if command -v apk >/dev/null 2>&1; then printf 'apk %s\n' "$(apk info 2>/dev/null | wc -l)"; fi
printf '%s\n' '__INVENUX_END_packages__'

printf '%s\n' '__INVENUX_BEGIN_session__'
printf 'init=%s\n' "$(cat /proc/1/comm 2>/dev/null)"
ps -eo comm= 2>/dev/null | sort -u
printf '%s\n' '__INVENUX_END_session__'

printf '%s\n' '__INVENUX_BEGIN_displays__'
for s in /sys/class/drm/card*-*/status; do
  [ -r "$s" ] || continue
  [ "$(cat "$s" 2>/dev/null)" = connected ] || continue
  d=${s%/status}
  printf '%s %s\n' "${d##*/}" "$(head -n 1 "$d/modes" 2>/dev/null)"
done
printf '%s\n' '__INVENUX_END_displays__'

printf '%s\n' '__INVENUX_BEGIN_timezone__'
if [ -r /etc/timezone ]; then cat /etc/timezone; else readlink /etc/localtime 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_timezone__'

printf '%s\n' '__INVENUX_BEGIN_rootfs__'
df -P -k / 2>/dev/null | tail -n 1
printf '%s\n' '__INVENUX_END_rootfs__'

printf '%s\n' '__INVENUX_BEGIN_ipv4__'
if command -v ip >/dev/null 2>&1; then ip -o -4 addr show 2>/dev/null || true; fi
printf '%s\n' '__INVENUX_END_ipv4__'

printf '%s\n' '__INVENUX_BEGIN_netdetails__'
for p in /sys/class/net/*; do
  [ -e "$p" ] || continue
  name=$(basename "$p" 2>/dev/null)
  [ "$name" = "lo" ] && continue
  state=$(cat "$p/operstate" 2>/dev/null || true)
  [ -n "$state" ] || state="unknown"
  speed=$(cat "$p/speed" 2>/dev/null || true)
  case "$speed" in *[!0-9]*|'') speed="";; esac
  driver_path=$(readlink -f "$p/device/driver" 2>/dev/null || true)
  driver=""
  if [ -n "$driver_path" ]; then driver=$(basename "$driver_path" 2>/dev/null); fi
  [ "$driver" = "." ] && driver=""
  mac=$(cat "$p/address" 2>/dev/null || true)
  printf '%s|%s|%s|%s|%s\n' "$name" "$state" "$speed" "$driver" "$mac"
done
printf '%s\n' '__INVENUX_END_netdetails__'

printf '%s\n' '__INVENUX_BEGIN_uptime__'
cat /proc/uptime 2>/dev/null || true
printf '%s\n' '__INVENUX_END_uptime__'

printf '%s\n' '__INVENUX_BEGIN_hypervisor__'
if command -v systemd-detect-virt >/dev/null 2>&1; then
  systemd-detect-virt --vm 2>/dev/null || true
fi
printf '%s\n' '__INVENUX_END_hypervisor__'

printf '%s\n' '__INVENUX_BEGIN_virtualization__'
if command -v systemd-detect-virt >/dev/null 2>&1; then
  systemd-detect-virt 2>/dev/null || true
elif command -v virt-what >/dev/null 2>&1; then
  virt-what 2>/dev/null || true
fi
printf '%s\n' '__INVENUX_END_virtualization__'
"""


def _build_probe_command(include_sensitive_identifiers: bool = False) -> str:
    """Build a fixed, read-only POSIX-shell probe; no target data is interpolated."""
    fields = (
        "sys_vendor product_name product_version board_vendor board_name "
        "bios_vendor bios_version bios_date"
    )
    if include_sensitive_identifiers:
        fields += " product_serial"
    return _PROBE_SCRIPT.replace("__DMI_FIELDS__", fields)


def _parse_probe_sections(output: str) -> dict[str, str]:
    """Parse named probe sections; section order is irrelevant."""
    sections: dict[str, str] = {}
    current: Optional[str] = None
    chunks: list[str] = []
    for line in output.splitlines():
        begin = re.fullmatch(r"__INVENUX_BEGIN_([a-z0-9_]+)__", line.strip())
        end = re.fullmatch(r"__INVENUX_END_([a-z0-9_]+)__", line.strip())
        if begin:
            current = begin.group(1)
            chunks = []
        elif end:
            if current == end.group(1):
                sections[current] = "\n".join(chunks).strip()
            current = None
            chunks = []
        elif current:
            chunks.append(line)
    return sections


def _parse_dmi_section(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith("__DMI__") or "=" not in line:
            continue
        key, value = line[len("__DMI__"):].split("=", 1)
        value = _clean_string(value)
        if _available(value):
            values[key] = value
    return values


def _parse_network_details(output: str) -> list[dict[str, str]]:
    adapters: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("|", 4)
        if len(parts) not in {4, 5}:
            continue
        name, state, speed, driver, mac = (_clean_string(value) for value in [*parts, ""][:5])
        if not name or name == "lo":
            continue
        if state.casefold() in {"", "unknown", "notpresent", "not present"}:
            state = "unknown"
        adapter = {"name": name, "state": state, "speed_mbps": "", "driver": driver or "N/A", "mac": mac}
        if speed.isdigit() and int(speed) > 0:
            adapter["speed_mbps"] = speed
        adapters.append(adapter)
    return adapters


_DESKTOP_PROCESSES = {
    "gnome-shell": "GNOME", "plasmashell": "KDE Plasma", "cinnamon": "Cinnamon",
    "mate-session": "MATE", "xfce4-session": "Xfce", "lxqt-session": "LXQt",
    "lxsession": "LXDE", "budgie-panel": "Budgie", "enlightenment": "Enlightenment",
}
_WINDOW_MANAGERS = {
    "openbox": "Openbox", "xfwm4": "Xfwm4", "marco": "Marco", "muffin": "Muffin",
    "kwin_x11": "KWin", "kwin_wayland": "KWin", "mutter": "Mutter", "metacity": "Metacity",
    "compiz": "Compiz", "fluxbox": "Fluxbox", "icewm": "IceWM", "i3": "i3", "sway": "Sway",
}


def _parse_session(output: str) -> dict[str, str]:
    """Infer init, desktop and display server from process names (ps comm)."""
    init = ""
    names = set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("init="):
            init = line[len("init="):]
        elif line:
            names.add(line)
    desktop = next((label for process, label in _DESKTOP_PROCESSES.items() if process in names), "")
    manager = next((label for process, label in _WINDOW_MANAGERS.items() if process in names), "")
    if names & {"Xwayland", "sway", "kwin_wayland"}:
        server = "Wayland"
    elif names & {"Xorg", "X"}:
        server = "X11"
    else:
        server = ""
    session = " + ".join(value for value in (desktop, manager) if value)
    return {
        "init_system": init or "N/A",
        "desktop": session or "N/A",
        "display_server": server or "N/A",
    }


def _parse_packages(output: str) -> str:
    counts = []
    for line in output.splitlines():
        manager, _, count = line.strip().partition(" ")
        if count.isdigit() and int(count) > 0:
            counts.append(f"{int(count)} ({manager})")
    return ", ".join(counts) or "N/A"


def _parse_displays(output: str) -> str:
    displays = []
    for line in output.splitlines():
        connector, _, mode = line.strip().partition(" ")
        if connector:
            connector = re.sub(r"^card\d+-", "", connector)
            displays.append(f"{connector} {mode}".strip())
    return "\n".join(displays) or "N/A"


def _parse_rootfs(output: str) -> str:
    fields = output.split()
    if len(fields) < 5 or not fields[1].isdigit() or not fields[2].isdigit():
        return "N/A"
    total, used = int(fields[1]) * 1024, int(fields[2]) * 1024
    percent = round(100 * used / total) if total else 0
    return f"{_format_capacity(used)} / {_format_capacity(total)} ({percent}%)"


def _parse_ipv4(output: str) -> dict[str, list[str]]:
    addresses: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = re.match(r"^\s*\d+:\s+(\S+)\s+inet\s+(\S+)", line)
        if match and match.group(1) != "lo":
            addresses.setdefault(match.group(1), []).append(match.group(2))
    return addresses


def _count_cpu_list(value: str) -> int:
    """Count Linux CPU-list syntax such as 0-3,8,10-11 without guessing."""
    value = _clean_string(value)
    if not value:
        return 0
    total = 0
    try:
        for item in value.split(","):
            item = item.strip()
            if not item:
                return 0
            if "-" in item:
                first, last = item.split("-", 1)
                low, high = int(first), int(last)
                if low < 0 or high < low:
                    return 0
                total += high - low + 1
            elif item.isdigit():
                total += 1
            else:
                return 0
    except ValueError:
        return 0
    return total

def _collect_linux_hardware(
    client: paramiko.SSHClient,
    include_sensitive_identifiers: bool = False,
    timeout: int = 30,
) -> dict[str, Any]:
    """Collect a normalized Linux hardware snapshot with one SSH round trip.

    The probe is read-only and uses standard OS interfaces first. Optional tools
    enrich the snapshot but do not define whether an endpoint is reachable.
    """
    raw_output = _run_command(
        client,
        _build_probe_command(include_sensitive_identifiers),
        timeout=max(5, timeout),
    ) or ""
    sections = _parse_probe_sections(raw_output)

    os_text = sections.get("os_release", "")
    os_release = _parse_os_release(os_text)
    distro = (
        os_release.get("PRETTY_NAME")
        or os_release.get("DISTRIB_DESCRIPTION")
        or os_release.get("NAME")
        or os_release.get("DISTRIB_ID")
        or ""
    )
    if not distro:
        first_line = next((line.strip() for line in os_text.splitlines() if line.strip()), "")
        distro = first_line if first_line and "=" not in first_line else "N/A"
    if os_release.get("VERSION_ID") and distro == os_release.get("NAME"):
        distro = f"{distro} {os_release['VERSION_ID']}"
    distro = _clean_string(distro) or "N/A"

    hostname = _clean_string(sections.get("hostname", "")) or "N/A"
    kernel = _clean_string(sections.get("kernel", "")) or "N/A"
    architecture = _clean_string(sections.get("architecture", "")) or "N/A"

    lscpu_text = sections.get("lscpu", "")
    cpuinfo_text = sections.get("cpuinfo", "")
    cpu = _parse_lscpu(lscpu_text)
    cpu_fallback = _parse_lscpu(cpuinfo_text)

    cpu_model = (
        cpu.get("model name")
        or cpu.get("model")
        or cpu.get("hardware")
        or cpu.get("processor")
        or cpu_fallback.get("model name")
        or cpu_fallback.get("hardware")
        or cpu_fallback.get("processor")
        or "N/A"
    )
    if not _available(cpu_model):
        cpu_model = "N/A"

    logical_threads = 0
    for key in ("cpu(s)", "on-line cpu(s)"):
        value = cpu.get(key, "")
        if value.isdigit() and int(value) > 0:
            logical_threads = int(value)
            break
    if not logical_threads:
        logical_threads = _count_cpu_list(cpu.get("on-line cpu(s) list", ""))
    if not logical_threads:
        fallback_threads = cpu_fallback.get("cpu(s)", "")
        if fallback_threads.isdigit():
            logical_threads = int(fallback_threads)

    sockets = 0
    if cpu.get("socket(s)", "").isdigit():
        sockets = int(cpu["socket(s)"])
    cores_per_socket = 0
    if cpu.get("core(s) per socket", "").isdigit():
        cores_per_socket = int(cpu["core(s) per socket"])
    physical_cores = sockets * cores_per_socket if sockets and cores_per_socket else 0
    if not physical_cores and cpu.get("core(s)", "").isdigit():
        physical_cores = int(cpu["core(s)"])
    if not physical_cores and cpu_fallback.get("core(s)", "").isdigit():
        physical_cores = int(cpu_fallback["core(s)"])
    # Do not pretend every logical CPU is a distinct physical core. Hyperthreading,
    # containers, CPU affinity, and architecture make that inference incorrect.
    if physical_cores and logical_threads:
        cores_threads = f"{physical_cores}/{logical_threads}"
    elif physical_cores:
        cores_threads = f"{physical_cores}/N/A"
    elif logical_threads:
        cores_threads = f"N/A/{logical_threads}"
    else:
        cores_threads = "N/A"

    frequency = cpu.get("cpu max mhz") or cpu.get("cpu mhz") or "N/A"
    if _available(frequency) and frequency != "N/A":
        try:
            mhz = float(frequency.replace(",", ".").split()[0])
            frequency = f"{mhz / 1000:.2f} GHz" if mhz >= 1000 else f"{mhz:.0f} MHz"
        except (ValueError, IndexError):
            frequency = "N/A"
    virtualization_extension = cpu.get("virtualization") or cpu_fallback.get("virtualization") or "N/A"
    sockets_label = str(sockets) if sockets else "N/A"
    cpu_vendor = cpu.get("vendor id") or cpu_fallback.get("vendor id") or "N/A"
    cpu_family = cpu.get("cpu family") or cpu_fallback.get("cpu family") or "N/A"
    cpu_model_number = cpu.get("model") if cpu.get("model", "").isdigit() else "N/A"
    cpu_stepping = cpu.get("stepping") or cpu_fallback.get("stepping") or "N/A"

    meminfo_text = sections.get("meminfo", "")
    meminfo = _parse_meminfo(meminfo_text)
    total_bytes = meminfo.get("MemTotal", 0)
    available_bytes = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    available_bytes = min(total_bytes, max(0, available_bytes)) if total_bytes else 0
    used_bytes = max(0, total_bytes - available_bytes)
    memory_devices_text = sections.get("memory_devices", "")
    memory_devices = _parse_memory_devices(memory_devices_text)
    ram_type = memory_devices.get("ram_type", "N/A")
    ram = (
        f"{total_bytes / (1024**3):.1f} GiB"
        + (f" {ram_type}" if _available(ram_type) else "")
        if total_bytes else "N/A"
    )

    lsblk_text = sections.get("lsblk", "")
    drives = _parse_lsblk(lsblk_text, sections.get("hypervisor", ""))
    drive_types = list(dict.fromkeys(
        drive["kind"] for drive in drives if drive["kind"] != "Unknown"
    ))
    disk_type = " + ".join(drive_types) if drive_types else "N/A"
    drive_total = sum(drive["size_bytes"] for drive in drives)
    disk_size = _format_capacity(drive_total) if drives else "N/A"
    drive_lines: list[str] = []
    for drive in drives:
        line = (
            f"{drive['name']} · {drive['kind']} · {drive['capacity']} · "
            f"{drive['model']} · transport {drive['transport']}"
        )
        if drive["mountpoints"]:
            line += " · mounted at " + ", ".join(drive["mountpoints"])
        if drive["partitions"]:
            partitions = []
            for partition in drive["partitions"]:
                part = f"{partition['name']} · {partition['capacity']} · {partition['filesystem']}"
                if partition["mountpoints"]:
                    part += " · " + ", ".join(partition["mountpoints"])
                partitions.append(part)
            line += "\n  Partitions: " + " | ".join(partitions)
        drive_lines.append(line)

    dmi = _parse_dmi_section(sections.get("dmi", ""))
    manufacturer = dmi.get("sys_vendor", "N/A")
    model = dmi.get("product_name", "N/A")
    board_vendor = dmi.get("board_vendor", "")
    board_model = dmi.get("board_name", "")
    motherboard = " — ".join(
        value for value in (board_vendor, board_model) if _available(value)
    ) or "N/A"
    bios = " · ".join(
        _clean_string(dmi.get(key, ""))
        for key in ("bios_vendor", "bios_version", "bios_date")
        if _available(dmi.get(key))
    ) or "N/A"
    system_serial = dmi.get("product_serial", "N/A") if include_sensitive_identifiers else "Not collected (opt-in)"

    gpus = _parse_gpus(sections.get("lspci", ""))
    if not gpus:
        vendor_ids = re.findall(r"(?m)^PCI_ID=(.+)$", sections.get("drm", ""))
        gpus = [f"PCI device {value}" for value in dict.fromkeys(vendor_ids)]

    net_details = _parse_network_details(sections.get("netdetails", ""))
    if not net_details:
        net_details = [
            {"name": item.split(" (", 1)[0], "state": item.rsplit("(", 1)[-1].rstrip(")"),
             "speed_mbps": "", "driver": "N/A"}
            for item in _parse_network_interfaces(sections.get("netlink", ""))
        ]
    ipv4 = _parse_ipv4(sections.get("ipv4", ""))
    network_lines = []
    for adapter in net_details:
        components = [adapter["name"], adapter["state"]]
        components.extend(ipv4.get(adapter["name"], []))
        if adapter["speed_mbps"]:
            components.append(f"{adapter['speed_mbps']} Mbps")
        if _available(adapter["driver"]):
            components.append(f"driver {adapter['driver']}")
        if adapter.get("mac") and adapter["mac"] != "00:00:00:00:00:00":
            components.append(f"MAC {adapter['mac']}")
        network_lines.append(" · ".join(components))
    session = _parse_session(sections.get("session", ""))
    timezone = _clean_string(sections.get("timezone", "")).split("zoneinfo/")[-1] or "N/A"
    os_version = (
        os_release.get("VERSION") or os_release.get("VERSION_ID") or os_release.get("DISTRIB_RELEASE") or ""
    )
    codename = (
        os_release.get("VERSION_CODENAME") or os_release.get("UBUNTU_CODENAME")
        or os_release.get("DISTRIB_CODENAME") or ""
    )
    if codename and codename.casefold() not in os_version.casefold():
        os_version = f"{os_version} ({codename})".strip()

    uptime = _format_uptime(sections.get("uptime", ""))
    virtualization = _clean_string(sections.get("virtualization", "")) or "N/A"
    if virtualization.casefold() == "none":
        virtualization = "Not detected (physical host not independently confirmed)"
    elif virtualization.casefold() in {"n/a", "not available"}:
        virtualization = "N/A"

    cpu_source = "lscpu" if _available(cpu.get("model name") or cpu.get("model")) else "/proc/cpuinfo"
    system_source = "SMBIOS sysfs" if dmi else "SMBIOS fields unavailable"
    memory_source = "/proc/meminfo" if total_bytes else "memory statistics unavailable"
    storage_source = "lsblk JSON" if drives else "lsblk unavailable or access restricted"
    source_parts = [
        f"OS: {'/etc/os-release' if os_release else 'release-file fallback'}",
        f"CPU: {cpu_source}",
        f"Memory: {memory_source}",
        f"Storage: {storage_source}",
        f"System/board/firmware: {system_source}",
        f"Graphics: {'lspci/sysfs' if gpus else 'not reported'}",
        f"Network: {'sysfs' if net_details else 'not reported'}",
    ]

    details = {
        "os_name": _clean_string(os_release.get("NAME") or os_release.get("DISTRIB_ID")) or distro,
        "os_version": _clean_string(os_version) or "N/A",
        "os_like": _clean_string(os_release.get("ID_LIKE")) or "N/A",
        "desktop": session["desktop"],
        "display_server": session["display_server"],
        "displays": _parse_displays(sections.get("displays", "")),
        "packages": _parse_packages(sections.get("packages", "")),
        "init_system": session["init_system"],
        "timezone": timezone,
        "root_disk_usage": _parse_rootfs(sections.get("rootfs", "")),
        "hostname": hostname,
        "manufacturer": manufacturer,
        "model": model,
        "architecture": architecture,
        "cpu_vendor": cpu_vendor,
        "cpu_family": cpu_family,
        "cpu_model_number": cpu_model_number,
        "cpu_stepping": cpu_stepping,
        "cpu_sockets": sockets_label,
        "cpu_max_frequency": frequency,
        "cpu_virtualization": virtualization_extension,
        "ram_speed": memory_devices.get("ram_speed", "N/A"),
        "ram_slots": memory_devices.get("ram_slots", "N/A"),
        "ram_modules": memory_devices.get("ram_modules", "N/A"),
        "ram_max_capacity": memory_devices.get("ram_max_capacity", "N/A"),
        "ram_used": _format_gib(used_bytes),
        "ram_available": _format_gib(available_bytes),
        "storage_devices": "\n".join(drive_lines) if drive_lines else "N/A",
        "storage_classification_basis": "Virtual disks are identified by model/vendor/name or a detected hypervisor (including passthrough disks). Otherwise NVMe uses transport/name; HDD vs non-rotating media uses the Linux kernel rotational flag.",
        "gpu": "\n".join(gpus) if gpus else "N/A",
        "network_adapters": "\n".join(network_lines) if network_lines else "N/A",
        "bios": bios,
        "uptime": uptime,
        "virtualization": virtualization,
        "system_serial": system_serial,
        "collection_sources": "; ".join(source_parts),
    }

    required_fields = {
        "Linux distribution": _available(distro),
        "Kernel version": _available(kernel),
        "Machine architecture": _available(architecture),
        "CPU model": _available(cpu_model),
        "CPU topology": bool(physical_cores or logical_threads),
        "Usable RAM total": total_bytes > 0,
        "Storage inventory": bool(drives),
        "System vendor/model": _available(manufacturer) or _available(model),
    }
    missing = [label for label, present in required_fields.items() if not present]
    coverage = round(100 * (len(required_fields) - len(missing)) / len(required_fields))
    details["coverage_percent"] = f"{coverage}%"
    optional_missing = []
    if not _available(motherboard):
        optional_missing.append("motherboard")
    if not _available(memory_devices.get("ram_speed", "")):
        optional_missing.append("DIMM speed")
    if not gpus:
        optional_missing.append("GPU")
    if not net_details:
        optional_missing.append("network adapter detail")
    if missing:
        details["collection_notes"] = "Core data unavailable: " + ", ".join(missing)
    elif optional_missing:
        details["collection_notes"] = "Core inventory collected; optional detail unavailable: " + ", ".join(optional_missing)
    else:
        details["collection_notes"] = "Core inventory collected. Values and device classifications depend on kernel interfaces and tools available on the target."

    return {
        "status": "SUCESSO_PARCIAL" if coverage < 50 else "SUCESSO",
        "placa_mae": motherboard,
        "processador": cpu_model,
        "cores_threads": cores_threads,
        "ram": ram,
        "disk_type": disk_type,
        "disk_size": disk_size,
        "distro": distro,
        "kernel": kernel,
        "hardware_details": details,
    }


_UNREACHABLE_ERRNOS = {errno.EHOSTUNREACH, errno.ENETUNREACH, getattr(errno, "EHOSTDOWN", errno.EHOSTUNREACH)}


def _connection_failure(exc: BaseException, ip: str, timeout: int, port: int = 22) -> Optional[str]:
    """Name the network cause; None when the error is not a connection failure."""
    if isinstance(exc, socket.gaierror):
        return t("hw_dns_failed", ip=ip)
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return t("hw_connection_timeout", timeout=timeout)
    # paramiko wraps refused/unreachable per address; the first error decides.
    if isinstance(exc, paramiko.ssh_exception.NoValidConnectionsError):
        exc = next(iter(exc.errors.values()), exc)
    if isinstance(exc, ConnectionRefusedError) or getattr(exc, "errno", None) == errno.ECONNREFUSED:
        return t("hw_connection_refused", port=port)
    if getattr(exc, "errno", None) in _UNREACHABLE_ERRNOS:
        return t("hw_host_unreachable")
    return None


def _remember_host_key(known_hosts: Path, hostname: str, key: paramiko.PKey) -> None:
    """Append a TOFU key to the shared file.

    The file is re-read under the lock because parallel workers each loaded it
    before connecting; saving a client's stale copy would drop other hosts.
    """
    with _KNOWN_HOSTS_LOCK:
        try:
            stored = paramiko.HostKeys()
            if known_hosts.is_file():
                stored.load(str(known_hosts))
            if not stored.check(hostname, key):
                stored.add(hostname, key.get_name(), key)
                known_hosts.parent.mkdir(parents=True, exist_ok=True)
                stored.save(str(known_hosts))
        except OSError:
            pass


def _new_client(known_hosts: Path, trust_unknown_hosts: bool) -> paramiko.SSHClient:
    """A client that checks host keys against the system file and Invenux's own."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    with _KNOWN_HOSTS_LOCK:
        if known_hosts.is_file():
            try:
                # load_host_keys() would make AutoAddPolicy save this stale
                # copy itself, outside the lock; _remember_host_key() merges.
                client.get_host_keys().load(str(known_hosts))
            except OSError:
                pass
    client.set_missing_host_key_policy(
        paramiko.AutoAddPolicy() if trust_unknown_hosts else paramiko.RejectPolicy()
    )
    return client


def _load_private_key(key_path: Optional[str]) -> Optional[paramiko.PKey]:
    if not key_path:
        return None
    private_key = Path(key_path).expanduser()
    if not private_key.is_file():
        raise FileNotFoundError(str(private_key))
    try:
        return paramiko.PKey.from_path(private_key)
    except (AttributeError, NotImplementedError):
        key_errors = []
        for key_class in (
            getattr(paramiko, "Ed25519Key", None),
            getattr(paramiko, "ECDSAKey", None),
            getattr(paramiko, "RSAKey", None),
            getattr(paramiko, "DSSKey", None),
        ):
            if key_class is None:
                continue
            try:
                return key_class.from_private_key_file(str(private_key))
            except (paramiko.SSHException, ValueError, TypeError) as exc:
                key_errors.append(exc)
        if key_errors:
            raise paramiko.SSHException("Unsupported or unreadable private key") from key_errors[-1]
    return None


def _known_host_name(ip: str, port: int) -> str:
    # known_hosts names a non-default port as [host]:port, as OpenSSH and paramiko do.
    return ip if port == 22 else f"[{ip}]:{port}"


class JumpHostError(Exception):
    """The bastion itself failed; the message is ready for the machine's row."""


class JumpHost:
    """One bastion connection shared by every worker of a collection.

    Each target is reached through a direct-tcpip channel of this transport,
    so a fleet behind the bastion costs one login on it instead of one per
    machine. A failed login is remembered: retrying it per machine would only
    repeat the same error and could lock the account.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        key_path: Optional[str],
        use_agent: bool = False,
        timeout: int = 30,
        trust_unknown_hosts: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.use_agent = use_agent
        self.timeout = timeout
        self.trust_unknown_hosts = trust_unknown_hosts
        self._client: Optional[paramiko.SSHClient] = None
        self._failure: Optional[str] = None
        self._lock = threading.Lock()

    def _connect(self) -> paramiko.SSHClient:
        known_hosts = get_known_hosts_path()
        client = _new_client(known_hosts, self.trust_unknown_hosts)
        try:
            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password or None,
                pkey=_load_private_key(self.key_path),
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
                allow_agent=self.use_agent,
                look_for_keys=False,
            )
        except paramiko.AuthenticationException:
            reason = t("hw_auth_failed")
        except FileNotFoundError:
            reason = t("hw_key_not_found", key_path=self.key_path)
        except paramiko.ssh_exception.BadHostKeyException:
            reason = t("hw_host_key_mismatch", ip=self.host)
        except (paramiko.SSHException, OSError, EOFError, ValueError) as exc:
            reason = _connection_failure(exc, self.host, self.timeout, self.port) or str(exc)
        else:
            if self.trust_unknown_hosts:
                _remember_host_key(
                    known_hosts, _known_host_name(self.host, self.port), client.get_transport().get_remote_server_key()
                )
            return client
        client.close()
        self._failure = t("hw_jump_failed", host=self.host, reason=reason)
        raise JumpHostError(self._failure)

    def open_channel(self, ip: str, port: int, timeout: int) -> paramiko.Channel:
        with self._lock:
            if self._failure:
                raise JumpHostError(self._failure)
            transport = self._client.get_transport() if self._client else None
            if transport is None or not transport.is_active():
                self._client = self._connect()
                transport = self._client.get_transport()
        try:
            return transport.open_channel("direct-tcpip", (ip, port), ("127.0.0.1", 0), timeout=timeout)
        except (paramiko.SSHException, OSError, EOFError) as exc:
            raise JumpHostError(t("hw_jump_unreachable", host=self.host, ip=ip, port=port)) from exc

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None


def get_hardware_info(
    ip: str,
    username: str,
    password: Optional[str],
    key_path: Optional[str],
    timeout: int = 30,
    trust_unknown_hosts: bool = False,
    include_sensitive_identifiers: bool = False,
    port: int = 22,
    use_agent: bool = False,
    jump: Optional[JumpHost] = None,
) -> dict[str, Any]:
    """Connect to one explicitly supplied host and discover Linux hardware read-only."""
    known_hosts = get_known_hosts_path()
    client = _new_client(known_hosts, trust_unknown_hosts)
    try:
        pkey = _load_private_key(key_path)
        sock = None
        if jump is not None:
            try:
                sock = jump.open_channel(ip, port, timeout)
            except JumpHostError as exc:
                return {"status": "FALHA_CONEXAO", "erro": str(exc)}
        client.connect(
            hostname=ip,
            port=port,
            username=username,
            password=password or None,
            pkey=pkey,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            allow_agent=use_agent,
            look_for_keys=False,
            sock=sock,
        )
        if trust_unknown_hosts:
            _remember_host_key(known_hosts, _known_host_name(ip, port), client.get_transport().get_remote_server_key())
        return _collect_linux_hardware(
            client,
            include_sensitive_identifiers=include_sensitive_identifiers,
            timeout=timeout,
        )
    except paramiko.AuthenticationException:
        return {"status": "FALHA_AUTH", "erro": t("hw_auth_failed")}
    except FileNotFoundError:
        return {"status": "FALHA_AUTH", "erro": t("hw_key_not_found", key_path=key_path)}
    except (socket.timeout, socket.gaierror, paramiko.ssh_exception.NoValidConnectionsError, TimeoutError) as exc:
        return {"status": "FALHA_CONEXAO", "erro": _connection_failure(exc, ip, timeout, port) or str(exc)}
    except paramiko.ssh_exception.BadHostKeyException:
        return {"status": "ERRO_CHAVE_HOST", "erro": t("hw_host_key_mismatch", ip=ip)}
    except paramiko.SSHException as exc:
        return {"status": "ERRO_SSH", "erro": t("hw_ssh_error", error=exc)}
    except (OSError, ValueError, TypeError) as exc:
        reason = _connection_failure(exc, ip, timeout, port)
        if reason:
            return {"status": "FALHA_CONEXAO", "erro": reason}
        return {"status": "ERRO_DESCONHECIDO", "erro": t("hw_unknown_error", error=exc)}
    finally:
        client.close()
