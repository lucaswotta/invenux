"""Run Invenux with a fictional fleet for screenshots and recordings.

The real interface, server, exports and snapshot history run in a throwaway home
folder; only the SSH collector is replaced by canned machines on documentation
addresses (192.0.2.0/24). Nothing connects to a network.

    python scripts/demo_server.py --port 8765 --language en

The target spreadsheet is written to <home>/fleet.csv and its path is printed.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LOCATIONS = {
    "en": ("HQ", "Branch 01", "Branch 02", "Warehouse"),
    "pt-br": ("Matriz", "Filial 01", "Filial 02", "Depósito"),
    "es": ("Sede", "Sucursal 01", "Sucursal 02", "Almacén"),
}

PROFILES = [
    {"cpu": "Intel(R) Celeron(R) CPU J1800 @ 2.41GHz", "cores": "2/2", "freq": "2.58 GHz", "board": ("ASUSTeK COMPUTER INC.", "J1800I-C/BR"),
     "ram_gib": 3.8, "dimm": ("DDR3", 1333, "4 GB", "1 of 1 populated"), "disk": ("SSD / flash", 120, "KINGSTON SA400S37120G"),
     "gpu": "Intel Corporation Atom Processor Z36xxx/Z37xxx Series Graphics & Display [8086:0f31]", "os": ("Lubuntu", "18.04.5 LTS (bionic)", "ubuntu debian", "4.15.0-22-generic"),
     "desktop": "LXDE + Openbox"},
    {"cpu": "Intel(R) Core(TM) i3-8100 CPU @ 3.60GHz", "cores": "4/4", "freq": "3.60 GHz", "board": ("Gigabyte Technology Co., Ltd.", "H310M S2P 2.0"),
     "ram_gib": 7.8, "dimm": ("DDR4", 2400, "8 GB", "1 of 2 populated"), "disk": ("SSD / flash", 240, "WDC WDS240G2G0A"),
     "gpu": "Intel Corporation UHD Graphics 630 [8086:3e91]", "os": ("Ubuntu", "22.04.4 LTS (jammy)", "debian", "5.15.0-105-generic"),
     "desktop": "Xfce + Xfwm4"},
    {"cpu": "Intel(R) Pentium(R) Gold G5420 CPU @ 3.80GHz", "cores": "2/4", "freq": "3.80 GHz", "board": ("Gigabyte Technology Co., Ltd.", "H310M S2P 2.0"),
     "ram_gib": 3.8, "dimm": ("DDR4", 2400, "4 GB", "1 of 2 populated"), "disk": ("SSD / flash", 128, "SATA SSD 128GB"),
     "gpu": "Intel Corporation UHD Graphics 610 [8086:3e93]", "os": ("Linux Mint", "21.3 (virginia)", "ubuntu debian", "5.15.0-91-generic"),
     "desktop": "Cinnamon + Muffin"},
    {"cpu": "12th Gen Intel(R) Core(TM) i3-12100", "cores": "4/8", "freq": "4.30 GHz", "board": ("PCWARE", "IPMH610G"),
     "ram_gib": 15.4, "dimm": ("DDR4", 2666, "8 GB", "2 of 2 populated"), "disk": ("NVMe", 256, "KINGSTON SNV2S250G"),
     "gpu": "Intel Corporation Alder Lake-S GT1 [UHD Graphics 730] [8086:4692]", "os": ("Debian GNU/Linux", "12 (bookworm)", "N/A", "6.1.0-21-amd64"),
     "desktop": "GNOME · Wayland"},
    {"cpu": "Intel(R) Xeon(R) E-2234 CPU @ 3.60GHz", "cores": "4/8", "freq": "4.80 GHz", "board": ("Dell Inc.", "0RRGFP"),
     "ram_gib": 31.2, "dimm": ("DDR4", 2666, "16 GB", "2 of 4 populated"), "disk": ("HDD", 2000, "TOSHIBA MG04ACA200E"),
     "gpu": "Matrox Electronics Systems Ltd. Integrated Matrox G200eW3 [102b:0536]", "os": ("Rocky Linux", "9.4 (Blue Onyx)", "rhel centos fedora", "5.14.0-427.el9.x86_64"),
     "desktop": "N/A"},
]


def fleet(language: str, count: int = 24) -> list[dict]:
    """Fictional machines with unique documentation addresses or reserved names."""
    random.seed(7)
    machines = []
    locations = LOCATIONS[language]
    for index in range(count):
        location = locations[0 if index < 6 else 1 if index < 14 else 2 if index < 21 else 3]
        profile = PROFILES[4] if location == locations[0] and index < 2 else PROFILES[index % 4]
        prefix = "srv" if profile is PROFILES[4] else "pos"
        machines.append({
            "ip": f"192.0.2.{10 + index}" if index < 244 else f"host-{index + 1}.example",
            "hostname": f"{prefix}-{index + 1:02d}",
            "location": location,
            "asset": f"AT-{1040 + index}",
            "profile": profile,
            "outcome": "offline" if index in (9, 17, 20) else "auth" if index == 13 else "online",
        })
    return machines


def write_targets(path: Path, machines: list[dict]) -> None:
    lines = ["IP,HOSTNAME,LOCATION,ASSET_TAG"]
    lines += [f"{m['ip']},{m['hostname']},{m['location']},{m['asset']}" for m in machines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fake_collector(machines: list[dict]):
    from i18n import t

    by_ip = {machine["ip"]: machine for machine in machines}

    def get_hardware_info(ip, username, password, key_path, timeout=30, **_options):
        machine = by_ip[ip]
        time.sleep(random.uniform(0.4, 2.6))
        if machine["outcome"] == "offline":
            return {"status": "FALHA_CONEXAO", "erro": t("hw_host_unreachable")}
        if machine["outcome"] == "auth":
            return {"status": "FALHA_AUTH", "erro": t("hw_auth_failed")}
        p = machine["profile"]
        size_gb, model = p["disk"][1], p["disk"][2]
        capacity = f"{size_gb / 1000:g} TB" if size_gb >= 1000 else f"{size_gb} GB"
        ram_type, speed, module, slots = p["dimm"]
        used = round(p["ram_gib"] * random.uniform(0.3, 0.7), 1)
        modules = "\n".join(
            f"DIMM {chr(65 + n)}1 · {module} {ram_type} · {speed} MT/s · Kingston KVR{speed}N19S8/{module.split()[0]}"
            for n in range(int(slots.split()[0]))
        )
        return {
            "status": "SUCESSO",
            "placa_mae": f"{p['board'][0]} — {p['board'][1]}",
            "processador": p["cpu"],
            "cores_threads": p["cores"],
            "ram": f"{p['ram_gib']:.1f} GiB {ram_type}",
            "disk_type": p["disk"][0],
            "disk_size": f"{capacity} total (1 physical block devices)",
            "distro": f"{p['os'][0]} {p['os'][1].split(' (')[0]}",
            "kernel": p["os"][3],
            "hardware_details": {
                "hostname": machine["hostname"],
                "os_name": p["os"][0], "os_version": p["os"][1], "os_like": p["os"][2],
                "desktop": p["desktop"], "display_server": "N/A",
                "displays": "HDMI-A-1 1920x1080" if p["desktop"] != "N/A" else "N/A",
                "packages": f"{random.randint(1400, 2300)} (dpkg)" if "rhel" not in p["os"][2] else f"{random.randint(700, 900)} (rpm)",
                "init_system": "systemd", "timezone": "America/Sao_Paulo",
                "root_disk_usage": f"{round(size_gb * random.uniform(0.2, 0.6))} GB / {size_gb} GB ({random.randint(20, 60)}%)",
                "manufacturer": p["board"][0], "model": p["board"][1], "architecture": "x86_64",
                "bios": "American Megatrends Inc. · F13 · 08/13/2021",
                "cpu_sockets": "1", "cpu_max_frequency": p["freq"], "cpu_virtualization": "VT-x",
                "ram_speed": f"{speed} MT/s", "ram_slots": slots, "ram_modules": modules,
                "ram_max_capacity": "64 GB", "ram_used": f"{used} GiB", "ram_available": f"{p['ram_gib'] - used:.1f} GiB",
                "storage_devices": f"sda · {p['disk'][0]} · {capacity} · {model} · transport SATA\n  Partitions: sda1 · {capacity} · ext4 · /",
                "gpu": p["gpu"],
                "network_adapters": f"enp2s0 · up · {machine['ip']}/24 · 1000 Mbps · driver r8169",
                "uptime": f"{random.randint(0, 20)}d {random.randint(0, 23)}h {random.randint(0, 59)}m",
                "virtualization": "Not detected (physical host not independently confirmed)",
                "system_serial": "Not collected (opt-in)",
                "coverage_percent": "100%",
                "collection_notes": "Core inventory collected. Values and device classifications depend on kernel interfaces and tools available on the target.",
            },
        }

    return get_hardware_info


def shift_clock(modules, clock: str) -> None:
    """Make the app's clock read `clock` (HH:MM) today, so captures do not show the real time."""
    hour, minute = (int(part) for part in clock.split(":"))
    real = datetime.now()
    offset = real.replace(hour=hour, minute=minute, second=0, microsecond=0) - real

    class ShiftedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + offset

    for module in modules:
        module.datetime = ShiftedDateTime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--machines", type=int, default=24)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--language", choices=("en", "pt-br", "es"), default="en")
    parser.add_argument("--home", type=Path, help="Home folder to use (default: a new temporary one).")
    parser.add_argument("--clock", default="10:42", help="Time of day the app should see (HH:MM).")
    args = parser.parse_args()

    home = args.home or Path(tempfile.mkdtemp(prefix="invenux-demo-"))
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(home)
    for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        os.environ.pop(variable, None)
    os.environ["LANG"] = {"en": "en_US.UTF-8", "pt-br": "pt_BR.UTF-8", "es": "es_ES.UTF-8"}[args.language]
    sys.path.insert(0, str(ROOT))

    import app
    import core
    import reporting
    import snapshots

    shift_clock((core, reporting, snapshots), args.clock)
    machines = fleet(args.language, args.machines)
    targets = home / {"en": "fleet.csv", "pt-br": "maquinas.csv", "es": "equipos.csv"}[args.language]
    write_targets(targets, machines)
    core.get_hardware_info = fake_collector(machines)
    print(f"Targets: {targets}", flush=True)
    return app.main(["--no-window", "--port", str(args.port)])


if __name__ == "__main__":
    raise SystemExit(main())
