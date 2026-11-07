"""Local SQLite snapshot storage, neutral diffing, and fleet distribution analytics."""
from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from paths import get_snapshots_db_path

_LEGACY_DISK_SIZE = re.compile(r" total \(\d+ physical block devices\)$")

DIFF_FIELDS: tuple[tuple[str, str], ...] = (
    ("status", "Status"),
    ("processador", "Processador"),
    ("ram", "Memória RAM"),
    ("disk_type", "Tipo de Armazenamento"),
    ("disk_size", "Armazenamento"),
    ("placa_mae", "Placa-mãe"),
    ("distro", "Sistema Operacional"),
    ("kernel", "Kernel"),
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat(sep=" ", timespec="seconds")
        except TypeError:
            return value.isoformat()
    text = " ".join(str(value).strip().split())
    return "" if text.casefold() in {"n/a", "na", "none", "nan"} else text


def _extract_hostname(record: Mapping[str, Any]) -> str:
    details = record.get("hardware_details") or {}
    if isinstance(details, Mapping):
        detected = _clean(details.get("hostname"))
        if detected:
            return detected
    meta = record.get("metadata") or {}
    if isinstance(meta, Mapping):
        for key in ("HOSTNAME", "HOST", "NAME", "NOME"):
            candidate = _clean(meta.get(key))
            if candidate:
                return candidate
    return _clean(record.get("ip")) or "—"


def _extract_location(record: Mapping[str, Any]) -> str:
    meta = record.get("metadata") or {}
    if isinstance(meta, Mapping):
        for key in ("LOCATION", "SITE", "LOCAL", "LOCALIZACAO", "LOCALIZAÇÃO", "UNIDADE", "FILIAL", "DEPARTMENT",
                    "SETOR", "UBICACION", "UBICACIÓN", "SEDE", "SUCURSAL"):
            candidate = _clean(meta.get(key))
            if candidate:
                return candidate
    return "Geral"


def _parse_ram_gb(ram_text: str) -> float:
    text = _clean(ram_text)
    if not text:
        return 0.0
    match = re.search(r"([\d.,]+)\s*(GiB|GB|MiB|MB|TiB|TB)", text, re.I)
    if not match:
        return 0.0
    try:
        amount = float(match.group(1).replace(",", "."))
    except ValueError:
        return 0.0
    unit = match.group(2).upper()
    if unit in {"TIB", "TB"}:
        return amount * 1024.0
    if unit in {"MIB", "MB"}:
        return amount / 1024.0
    return amount


def _classify_storage(disk_type: str) -> str:
    upper = _clean(disk_type).upper()
    if not upper:
        return "Unknown"
    if "VIRTUAL" in upper:
        return "Virtual"
    if "NVME" in upper:
        return "NVMe"
    if "SSD" in upper or "FLASH" in upper:
        return "SSD"
    if "HDD" in upper:
        return "HDD"
    return "Other"


def compute_records_diff(
    previous_records: Sequence[Mapping[str, Any]],
    current_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Compute neutral field-by-field changes between two snapshots keyed by IP."""
    prev_by_ip: dict[str, Mapping[str, Any]] = {}
    for rec in previous_records:
        ip = _clean(rec.get("ip"))
        if ip:
            prev_by_ip[ip] = rec

    changes: list[dict[str, str]] = []
    for curr in current_records:
        ip = _clean(curr.get("ip"))
        if not ip or ip not in prev_by_ip:
            continue
        prev = prev_by_ip[ip]
        hostname = _extract_hostname(curr)
        for field_key, field_label in DIFF_FIELDS:
            before = _clean(prev.get(field_key)) or "—"
            after = _clean(curr.get(field_key)) or "—"
            if field_key == "disk_size":
                # Up to 0.9.1 the capacity carried a device count; compare the capacity only.
                before = _LEGACY_DISK_SIZE.sub("", before)
                after = _LEGACY_DISK_SIZE.sub("", after)
            if before != after:
                changes.append({
                    "ip": ip,
                    "hostname": hostname,
                    "field": field_label,
                    "field_key": field_key,
                    "previous_value": before,
                    "current_value": after,
                })
    return changes


def compute_fleet_analytics(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute neutral hardware distribution metrics and location breakdown."""
    total = len(records)
    online_records = [r for r in records if str(r.get("status", "")).upper() == "ONLINE"]
    online = len(online_records)
    offline = sum(str(r.get("status", "")).upper() == "OFFLINE" for r in records)
    other_errors = total - online - offline
    availability_pct = round((online / total) * 100, 1) if total else 0.0

    nvme_count = 0
    ssd_count = 0
    hdd_count = 0
    virtual_count = 0
    ram_values: list[float] = []
    ram_le_4 = 0
    ram_8 = 0
    ram_16_plus = 0
    distro_counts: dict[str, int] = {}
    locations_map: dict[str, dict[str, Any]] = {}

    for rec in records:
        loc = _extract_location(rec)
        bucket = locations_map.setdefault(loc, {
            "location": loc,
            "total": 0,
            "online": 0,
            "flash": 0,
            "hdd": 0,
            "virtual": 0,
            "ram_le_4": 0,
            "ram_8_plus": 0,
        })
        bucket["total"] += 1
        is_online = str(rec.get("status", "")).upper() == "ONLINE"
        if not is_online:
            continue

        bucket["online"] += 1
        storage_kind = _classify_storage(str(rec.get("disk_type", "")))
        if storage_kind == "Virtual":
            virtual_count += 1
            bucket["virtual"] += 1
        elif storage_kind == "NVMe":
            nvme_count += 1
            bucket["flash"] += 1
        elif storage_kind == "SSD":
            ssd_count += 1
            bucket["flash"] += 1
        elif storage_kind == "HDD":
            hdd_count += 1
            bucket["hdd"] += 1

        ram_gb = _parse_ram_gb(str(rec.get("ram", "")))
        if ram_gb > 0:
            ram_values.append(ram_gb)
            if ram_gb <= 4.5:
                ram_le_4 += 1
                bucket["ram_le_4"] += 1
            elif ram_gb <= 12.0:
                ram_8 += 1
                bucket["ram_8_plus"] += 1
            else:
                ram_16_plus += 1
                bucket["ram_8_plus"] += 1

        distro = _clean(rec.get("distro")) or "Não identificado"
        distro_counts[distro] = distro_counts.get(distro, 0) + 1

    storage_total = nvme_count + ssd_count + hdd_count + virtual_count
    flash_pct = round(((nvme_count + ssd_count) / storage_total) * 100, 1) if storage_total else 0.0
    avg_ram_gb = round(sum(ram_values) / len(ram_values), 1) if ram_values else 0.0

    def _pct(count: int, denom: int) -> float:
        return round((count / denom) * 100, 1) if denom else 0.0

    ram_denom = len(ram_values)
    sorted_distros = sorted(distro_counts.items(), key=lambda item: (-item[1], item[0]))[:4]
    distro_distribution = [
        {"label": name, "count": count, "percent": _pct(count, online)}
        for name, count in sorted_distros
    ]

    locations_list = sorted(
        locations_map.values(),
        key=lambda item: (-item["total"], item["location"]),
    )

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "errors": other_errors,
        "availability_pct": availability_pct,
        "locations_count": len(locations_map),
        "flash_pct": flash_pct,
        "nvme_count": nvme_count,
        "ssd_count": ssd_count,
        "hdd_count": hdd_count,
        "virtual_count": virtual_count,
        "avg_ram_gb": avg_ram_gb,
        "storage_distribution": [
            {"label": "Virtual", "count": virtual_count, "percent": _pct(virtual_count, storage_total), "tone": "green"},
            {"label": "NVMe", "count": nvme_count, "percent": _pct(nvme_count, storage_total), "tone": "blue"},
            {"label": "SSD SATA / Flash", "count": ssd_count, "percent": _pct(ssd_count, storage_total), "tone": "teal"},
            {"label": "HDD Mecânico", "count": hdd_count, "percent": _pct(hdd_count, storage_total), "tone": "purple"},
        ],
        "ram_distribution": [
            {"label": "Até 4 GB", "count": ram_le_4, "percent": _pct(ram_le_4, ram_denom), "tone": "teal"},
            {"label": "8 GB", "count": ram_8, "percent": _pct(ram_8, ram_denom), "tone": "blue"},
            {"label": "16 GB ou superior", "count": ram_16_plus, "percent": _pct(ram_16_plus, ram_denom), "tone": "green"},
        ],
        "distro_distribution": distro_distribution,
        "locations": locations_list,
    }


class SnapshotStore:
    """SQLite persistence for local inventory runs and historical comparisons."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else get_snapshots_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # sqlite3's own context manager commits but never closes the connection.
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    total_hosts INTEGER NOT NULL,
                    online_hosts INTEGER NOT NULL,
                    offline_hosts INTEGER NOT NULL,
                    error_hosts INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    changes_count INTEGER NOT NULL DEFAULT 0,
                    records_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_snapshot(
        self,
        records: Sequence[Mapping[str, Any]],
        source_name: str = "Coleta manual",
        duration_seconds: float = 0.0,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        normalized = [self._serialize_record(r) for r in records]
        total = len(normalized)
        online = sum(str(r.get("status", "")).upper() == "ONLINE" for r in normalized)
        offline = sum(str(r.get("status", "")).upper() == "OFFLINE" for r in normalized)
        errors = total - online - offline
        timestamp = created_at or datetime.now().isoformat(sep=" ", timespec="seconds")

        with self._connect() as conn:
            prev_row = conn.execute(
                "SELECT records_json FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            changes_count = 0
            if prev_row is not None:
                try:
                    prev_records = json.loads(prev_row["records_json"])
                    changes_count = len(compute_records_diff(prev_records, normalized))
                except (json.JSONDecodeError, TypeError):
                    changes_count = 0

            cursor = conn.execute(
                """
                INSERT INTO snapshots (
                    created_at, source_name, total_hosts, online_hosts,
                    offline_hosts, error_hosts, duration_seconds,
                    changes_count, records_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    source_name,
                    total,
                    online,
                    offline,
                    errors,
                    round(float(duration_seconds), 2),
                    changes_count,
                    json.dumps(normalized, ensure_ascii=False),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            conn.commit()

        return {
            "id": snapshot_id,
            "created_at": timestamp,
            "source_name": source_name,
            "total_hosts": total,
            "online_hosts": online,
            "offline_hosts": offline,
            "error_hosts": errors,
            "duration_seconds": round(float(duration_seconds), 2),
            "changes_count": changes_count,
        }

    def list_snapshots(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, source_name, total_hosts, online_hosts,
                       offline_hosts, error_hosts, duration_seconds, changes_count
                FROM snapshots
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_snapshot(self, snapshot_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE id = ?",
                (int(snapshot_id),),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        try:
            data["records"] = json.loads(data.pop("records_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            data["records"] = []
        return data

    def delete_snapshots(self, snapshot_ids: Sequence[int]) -> list[int]:
        """Delete snapshots; the next survivor's change count is redone against its new predecessor."""
        ids = sorted({int(value) for value in snapshot_ids})
        if not ids:
            return []
        with self._connect() as conn:
            marks = ",".join("?" * len(ids))
            deleted = [row["id"] for row in conn.execute(f"SELECT id FROM snapshots WHERE id IN ({marks})", ids)]
            if not deleted:
                return []
            conn.execute(f"DELETE FROM snapshots WHERE id IN ({marks})", ids)
            followers = {
                row["id"]
                for deleted_id in deleted
                for row in conn.execute("SELECT id FROM snapshots WHERE id > ? ORDER BY id LIMIT 1", (deleted_id,))
            }
            for follower in sorted(followers):
                current = conn.execute("SELECT records_json FROM snapshots WHERE id = ?", (follower,)).fetchone()
                previous = conn.execute(
                    "SELECT records_json FROM snapshots WHERE id < ? ORDER BY id DESC LIMIT 1", (follower,)
                ).fetchone()
                count = 0
                if previous is not None:
                    try:
                        count = len(compute_records_diff(json.loads(previous["records_json"]), json.loads(current["records_json"])))
                    except (json.JSONDecodeError, TypeError):
                        count = 0
                conn.execute("UPDATE snapshots SET changes_count = ? WHERE id = ?", (count, follower))
        return deleted

    def prune(self, keep_last: int = 0, keep_days: int = 0, now: datetime | None = None) -> list[int]:
        """Apply retention: a snapshot goes when it is beyond the newest keep_last or older than
        keep_days; 0 turns a rule off. The newest snapshot always stays, so a long pause between
        collections never empties the history.
        """
        keep_last = max(0, int(keep_last or 0))
        keep_days = max(0, int(keep_days or 0))
        if not keep_last and not keep_days:
            return []
        with self._connect() as conn:
            rows = conn.execute("SELECT id, created_at FROM snapshots ORDER BY id DESC").fetchall()
        cutoff = (now or datetime.now()) - timedelta(days=keep_days) if keep_days else None
        doomed = []
        for position, row in enumerate(rows):
            if position == 0:
                continue
            too_many = bool(keep_last) and position >= keep_last
            try:
                too_old = cutoff is not None and datetime.fromisoformat(row["created_at"]) < cutoff
            except ValueError:
                too_old = False
            if too_many or too_old:
                doomed.append(row["id"])
        return self.delete_snapshots(doomed)

    def compute_diff(self, snapshot_id: int, base_snapshot_id: int | None = None) -> dict[str, Any]:
        current = self.get_snapshot(snapshot_id)
        if current is None:
            raise ValueError(f"Snapshot {snapshot_id} not found.")

        base: dict[str, Any] | None = None
        if base_snapshot_id is not None:
            base = self.get_snapshot(base_snapshot_id)
            if base is None:
                raise ValueError(f"Snapshot {base_snapshot_id} not found.")
        else:
            with self._connect() as conn:
                prev_row = conn.execute(
                    "SELECT id FROM snapshots WHERE id < ? ORDER BY id DESC LIMIT 1",
                    (int(snapshot_id),),
                ).fetchone()
            if prev_row is not None:
                base = self.get_snapshot(int(prev_row["id"]))

        if base is None:
            return {
                "snapshot": {k: v for k, v in current.items() if k != "records"},
                "base_snapshot": None,
                "changes": [],
            }

        changes = compute_records_diff(base["records"], current["records"])
        return {
            "snapshot": {k: v for k, v in current.items() if k != "records"},
            "base_snapshot": {k: v for k, v in base.items() if k != "records"},
            "changes": changes,
        }

    @staticmethod
    def _serialize_record(record: Mapping[str, Any]) -> dict[str, Any]:
        out = dict(record)
        dta = out.get("dta_atualizacao")
        if hasattr(dta, "isoformat") and not isinstance(dta, str):
            try:
                out["dta_atualizacao"] = dta.isoformat(sep=" ", timespec="seconds")
            except TypeError:
                out["dta_atualizacao"] = dta.isoformat()
        return out
