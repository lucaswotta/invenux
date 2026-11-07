"""Professional, self-contained exports for hardware inventory runs.

The reporting layer intentionally has no dependency on databases or the GUI.
"""
from __future__ import annotations

import base64
import csv
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


BRAND = "Invenux"
PRODUCT_LINE = "Hardware inventory"
BRAND_DARK = "1C1C1E"
BRAND_SURFACE = "262629"
BRAND_HEADER = "2C2C2E"
BRAND_ACCENT = "0A84FF"
ROW_EVEN = "FFFFFF"
ROW_ODD = "F5F5F7"
STATUS_ONLINE_BG = "E8F8EE"
STATUS_ONLINE_FG = "157333"
STATUS_OFFLINE_BG = "FCEBEC"
STATUS_OFFLINE_FG = "B42318"
STATUS_OTHER_BG = "FEF4E6"
STATUS_OTHER_FG = "B54708"

# (source, key, label, group); "record" keys are top-level, "details" keys live in hardware_details.
REPORT_COLUMNS = [
    ("details", "hostname", "Detected hostname", "machine"),
    ("record", "ssh_port", "SSH port", "machine"),
    ("record", "status", "Status", "status"),
    ("record", "dta_atualizacao", "Last collected", "status"),
    ("record", "erro", "Details / error", "status"),
    ("details", "coverage_percent", "Data coverage", "status"),
    ("details", "manufacturer", "Manufacturer", "hardware"),
    ("details", "model", "System model", "hardware"),
    ("record", "placa_mae", "Motherboard", "hardware"),
    ("details", "bios", "BIOS / firmware", "hardware"),
    ("record", "processador", "Processor", "hardware"),
    ("record", "cores_threads", "CPU cores / threads", "hardware"),
    ("details", "cpu_sockets", "CPU sockets", "hardware"),
    ("details", "cpu_max_frequency", "CPU max frequency", "hardware"),
    ("details", "cpu_virtualization", "CPU virtualization", "hardware"),
    ("record", "ram", "Memory", "hardware"),
    ("details", "ram_slots", "Memory slots", "hardware"),
    ("details", "ram_modules", "Memory modules", "hardware"),
    ("details", "ram_max_capacity", "Max memory capacity", "hardware"),
    ("details", "ram_speed", "Memory speed", "hardware"),
    ("details", "ram_used", "RAM used", "hardware"),
    ("details", "ram_available", "RAM available", "hardware"),
    ("record", "disk_type", "Storage type", "hardware"),
    ("record", "disk_size", "Storage capacity", "hardware"),
    ("details", "storage_devices", "Storage devices", "hardware"),
    ("details", "gpu", "Graphics", "hardware"),
    ("details", "network_adapters", "Network adapters", "hardware"),
    ("details", "virtualization", "Virtualization", "hardware"),
    ("details", "system_serial", "System serial (opt-in)", "hardware"),
    ("record", "distro", "Linux distribution", "system"),
    ("details", "os_version", "OS version", "system"),
    ("record", "kernel", "Kernel", "system"),
    ("details", "architecture", "Architecture", "system"),
    ("details", "desktop", "Desktop environment", "system"),
    ("details", "displays", "Displays", "system"),
    ("details", "packages", "Installed packages", "system"),
    ("details", "timezone", "Time zone", "system"),
    ("details", "root_disk_usage", "Root filesystem usage", "system"),
    ("details", "uptime", "System uptime", "system"),
    ("details", "collection_notes", "Collection notes", "collection"),
    ("details", "storage_classification_basis", "Storage classification basis", "collection"),
    ("details", "collection_sources", "Collection sources", "collection"),
]
MULTILINE_KEYS = {
    "ram_modules", "storage_devices", "gpu", "network_adapters", "displays",
    "collection_notes", "storage_classification_basis", "collection_sources", "erro",
}

METADATA_LABELS = {
    "HOSTNAME": "Hostname",
    "ASSET_TAG": "Asset tag",
    "ASSET_ID": "Asset ID",
    "SERIAL_NUMBER": "Serial number",
    "SERIAL": "Serial number",
    "LOCATION": "Location",
    "SITE": "Site",
    "DEPARTMENT": "Department",
    "OWNER": "Owner",
    "ENVIRONMENT": "Environment",
    "ROLE": "Role",
    "NOTES": "Notes",
    "MODEL": "Asset model",
    "MANUFACTURER": "Asset manufacturer",
    "OPERATING_SYSTEM": "Expected operating system",
}
METADATA_LABELS_PT = {
    "HOSTNAME": "Nome do host",
    "ASSET_TAG": "Etiqueta do ativo",
    "ASSET_ID": "ID do ativo",
    "SERIAL_NUMBER": "Número de série",
    "SERIAL": "Número de série",
    "LOCATION": "Localização",
    "SITE": "Unidade",
    "DEPARTMENT": "Departamento",
    "OWNER": "Responsável",
    "ENVIRONMENT": "Ambiente",
    "ROLE": "Função",
    "NOTES": "Observações",
    "MODEL": "Modelo do ativo",
    "MANUFACTURER": "Fabricante do ativo",
    "OPERATING_SYSTEM": "Sistema operacional esperado",
}
METADATA_LABELS_ES = {
    "HOSTNAME": "Nombre del host",
    "ASSET_TAG": "Etiqueta del activo",
    "ASSET_ID": "ID del activo",
    "SERIAL_NUMBER": "Número de serie",
    "SERIAL": "Número de serie",
    "LOCATION": "Ubicación",
    "SITE": "Sede",
    "DEPARTMENT": "Departamento",
    "OWNER": "Responsable",
    "ENVIRONMENT": "Entorno",
    "ROLE": "Función",
    "NOTES": "Notas",
    "MODEL": "Modelo del activo",
    "MANUFACTURER": "Fabricante del activo",
    "OPERATING_SYSTEM": "Sistema operativo esperado",
}
COLUMN_LABELS = {
    "en": {
        "Host / IP": "Host / IP", "Status": "Status", "Motherboard": "Motherboard",
        "Processor": "Processor", "CPU cores / threads": "CPU cores / threads",
        "Memory": "Memory", "Storage type": "Storage type", "Storage capacity": "Storage capacity",
        "Linux distribution": "Linux distribution", "Kernel": "Kernel",
        "Last collected": "Last collected", "Details / error": "Details / error",
        "Detected hostname": "Detected hostname", "SSH port": "SSH port",
        "Manufacturer": "Manufacturer", "System model": "System model",
        "Architecture": "Architecture", "CPU sockets": "CPU sockets",
        "CPU max frequency": "CPU max frequency", "CPU virtualization": "CPU virtualization",
        "Memory speed": "Memory speed", "Memory slots": "Memory slots", "RAM used": "RAM used",
        "RAM available": "RAM available", "Storage devices": "Storage devices", "Graphics": "Graphics",
        "Network adapters": "Network adapters", "BIOS / firmware": "BIOS / firmware",
        "System uptime": "System uptime", "Virtualization": "Virtualization",
        "System serial (opt-in)": "System serial (opt-in)", "Data coverage": "Data coverage",
        "Collection notes": "Collection notes", "Storage classification basis": "Storage classification basis",
        "Collection sources": "Collection sources",
        "Operating system": "Operating system", "OS version": "OS version",
        "Desktop environment": "Desktop environment", "Displays": "Displays",
        "Installed packages": "Installed packages", "Time zone": "Time zone",
        "Root filesystem usage": "Root filesystem usage", "Memory modules": "Memory modules",
        "Max memory capacity": "Max memory capacity",
    },
    "pt-br": {
        "Host / IP": "Host / IP", "Status": "Status", "Motherboard": "Placa-mãe",
        "Processor": "Processador", "CPU cores / threads": "Núcleos / threads da CPU",
        "Memory": "Memória", "Storage type": "Tipo de armazenamento",
        "Storage capacity": "Capacidade de armazenamento", "Linux distribution": "Distribuição Linux",
        "Kernel": "Kernel", "Last collected": "Última coleta", "Details / error": "Detalhes / erro",
        "Detected hostname": "Hostname detectado", "SSH port": "Porta SSH",
        "Manufacturer": "Fabricante", "System model": "Modelo do equipamento",
        "Architecture": "Arquitetura", "CPU sockets": "Soquetes da CPU",
        "CPU max frequency": "Frequência máxima da CPU", "CPU virtualization": "Virtualização da CPU",
        "Memory speed": "Velocidade da memória", "Memory slots": "Slots de memória", "RAM used": "RAM em uso",
        "RAM available": "RAM disponível", "Storage devices": "Unidades de armazenamento", "Graphics": "GPU / gráficos",
        "Network adapters": "Adaptadores de rede", "BIOS / firmware": "BIOS / firmware",
        "System uptime": "Tempo ligado", "Virtualization": "Ambiente virtual",
        "System serial (opt-in)": "Número de série do sistema (opcional)",
        "Data coverage": "Cobertura dos dados", "Collection notes": "Notas da coleta",
        "Storage classification basis": "Critério de classificação do armazenamento",
        "Collection sources": "Fontes utilizadas na coleta",
        "Operating system": "Sistema operacional", "OS version": "Versão do sistema",
        "Desktop environment": "Ambiente gráfico", "Displays": "Telas",
        "Installed packages": "Pacotes instalados", "Time zone": "Fuso horário",
        "Root filesystem usage": "Uso do disco (/)", "Memory modules": "Módulos de memória",
        "Max memory capacity": "Capacidade máxima de memória",
    },
}
COLUMN_LABELS["es"] = {
    "Host / IP": "Host / IP", "Status": "Estado", "Motherboard": "Placa base",
    "Processor": "Procesador", "CPU cores / threads": "Núcleos / hilos de CPU",
    "Memory": "Memoria", "Storage type": "Tipo de almacenamiento",
    "Storage capacity": "Capacidad de almacenamiento", "Linux distribution": "Distribución Linux",
    "Kernel": "Kernel", "Last collected": "Última recopilación", "Details / error": "Detalles / error",
    "Detected hostname": "Hostname detectado", "SSH port": "Puerto SSH",
    "Manufacturer": "Fabricante", "System model": "Modelo del equipo",
    "Architecture": "Arquitectura", "CPU sockets": "Zócalos de CPU",
    "CPU max frequency": "Frecuencia máxima de CPU", "CPU virtualization": "Virtualización de CPU",
    "Memory speed": "Velocidad de memoria", "Memory slots": "Ranuras de memoria", "RAM used": "RAM en uso",
    "RAM available": "RAM disponible", "Storage devices": "Unidades de almacenamiento", "Graphics": "GPU / gráficos",
    "Network adapters": "Adaptadores de red", "BIOS / firmware": "BIOS / firmware",
    "System uptime": "Tiempo encendido", "Virtualization": "Entorno virtual",
    "System serial (opt-in)": "Número de serie del sistema (opcional)",
    "Data coverage": "Cobertura de datos", "Collection notes": "Notas de la recopilación",
    "Storage classification basis": "Criterio de clasificación del almacenamiento",
    "Collection sources": "Fuentes de la recopilación",
    "Operating system": "Sistema operativo", "OS version": "Versión del sistema",
    "Desktop environment": "Entorno gráfico", "Displays": "Pantallas",
    "Installed packages": "Paquetes instalados", "Time zone": "Zona horaria",
    "Root filesystem usage": "Uso del disco (/)", "Memory modules": "Módulos de memoria",
    "Max memory capacity": "Capacidad máxima de memoria",
}
REPORT_TEXT = {
    "en": {
        "title": "Hardware inventory", "kicker": "INVENTORY REPORT",
        "subtitle": "A clear snapshot of your Linux fleet, ready to review and share.",
        "generated": "Generated", "devices_inventoried": "devices inventoried",
        "summary": "Inventory summary", "total": "Total devices", "online": "Online",
        "offline": "Offline", "other": "Other / errors", "search_label": "Search inventory",
        "search_placeholder": "Search host, model, location, owner…", "all_statuses": "All statuses",
        "devices_shown": "devices shown", "footer": "Generated locally by {brand}. Inventory data stays in this report file.",
        "overview_sheet": "Overview", "inventory_sheet": "Inventory", "metric": "METRIC",
        "devices": "DEVICES", "snapshot": "devices in this snapshot",
        "coverage": "Average data coverage", "coverage_suffix": "avg",
        "inventory_hint": "Use the Inventory sheet to filter, sort, and inspect individual devices.",
        "availability": "of the fleet reachable", "share_of_total": "of total", "average": "average",
        "storage_by_type": "Storage by type", "memory_capacity": "Memory capacity",
        "distributions": "Linux distributions", "by_location": "By location", "online_hosts": "online hosts",
        "kind": "Type", "machines": "Machines", "share": "Share", "location": "Location",
        "flash": "Flash", "hdd": "HDD", "groups": {"machine": "MACHINE", "status": "STATUS", "hardware": "HARDWARE", "system": "SYSTEM", "collection": "COLLECTION"},
        "date_format": "yyyy-mm-dd hh:mm", "page": "Page &P of &N",
        "status_options": [("ONLINE", "Online"), ("OFFLINE", "Offline"), ("FALHA_AUTH", "Authentication failed"), ("ERRO_SSH", "SSH error"), ("ERRO_DESCONHECIDO", "Unknown error"), ("ERRO_CHAVE_HOST", "Host key rejected"), ("ERROR", "Error")],
    },
    "pt-br": {
        "title": "Inventário de hardware", "kicker": "RELATÓRIO DE INVENTÁRIO",
        "subtitle": "Uma visão clara do seu parque Linux, pronta para analisar e compartilhar.",
        "generated": "Gerado em", "devices_inventoried": "máquinas inventariadas",
        "summary": "Resumo do inventário", "total": "Total de máquinas", "online": "Acessíveis",
        "offline": "Inacessíveis", "other": "Outros / erros", "search_label": "Pesquisar inventário",
        "search_placeholder": "Buscar host, modelo, local, responsável…", "all_statuses": "Todos os status",
        "devices_shown": "máquinas exibidas", "footer": "Gerado localmente pelo {brand}. Os dados permanecem neste arquivo de relatório.",
        "overview_sheet": "Resumo", "inventory_sheet": "Inventário", "metric": "INDICADOR",
        "devices": "MÁQUINAS", "snapshot": "máquinas nesta coleta",
        "coverage": "Cobertura média dos dados", "coverage_suffix": "média",
        "inventory_hint": "Use a aba Inventário para filtrar, ordenar e inspecionar as máquinas.",
        "availability": "do parque acessível", "share_of_total": "do total", "average": "média",
        "storage_by_type": "Armazenamento por tipo", "memory_capacity": "Memória RAM",
        "distributions": "Distribuições Linux", "by_location": "Por local", "online_hosts": "máquinas acessíveis",
        "kind": "Tipo", "machines": "Máquinas", "share": "Participação", "location": "Local",
        "flash": "Flash", "hdd": "HDD", "groups": {"machine": "MÁQUINA", "status": "SITUAÇÃO", "hardware": "HARDWARE", "system": "SISTEMA", "collection": "COLETA"},
        "date_format": "dd/mm/yyyy hh:mm", "page": "Página &P de &N",
        "status_options": [("ONLINE", "Acessível"), ("OFFLINE", "Inacessível"), ("FALHA_AUTH", "Falha de autenticação"), ("ERRO_SSH", "Erro SSH"), ("ERRO_DESCONHECIDO", "Erro desconhecido"), ("ERRO_CHAVE_HOST", "Chave SSH rejeitada"), ("ERROR", "Erro")],
    },
}


REPORT_TEXT["es"] = {
    "title": "Inventario de hardware", "kicker": "INFORME DE INVENTARIO",
    "subtitle": "Una vista clara de su parque Linux, lista para analizar y compartir.",
    "generated": "Generado el", "devices_inventoried": "equipos inventariados",
    "summary": "Resumen del inventario", "total": "Total de equipos", "online": "Accesibles",
    "offline": "Inaccesibles", "other": "Otros / errores", "search_label": "Buscar en el inventario",
    "search_placeholder": "Buscar host, modelo, ubicación, responsable…", "all_statuses": "Todos los estados",
    "devices_shown": "equipos mostrados", "footer": "Generado localmente por {brand}. Los datos permanecen en este archivo.",
    "overview_sheet": "Resumen", "inventory_sheet": "Inventario", "metric": "INDICADOR",
    "devices": "EQUIPOS", "snapshot": "equipos en esta recopilación",
    "coverage": "Cobertura media de datos", "coverage_suffix": "media",
    "inventory_hint": "Use la hoja Inventario para filtrar, ordenar e inspeccionar los equipos.",
    "availability": "del parque accesible", "share_of_total": "del total", "average": "media",
    "storage_by_type": "Almacenamiento por tipo", "memory_capacity": "Memoria RAM",
    "distributions": "Distribuciones Linux", "by_location": "Por ubicación", "online_hosts": "equipos accesibles",
    "kind": "Tipo", "machines": "Equipos", "share": "Participación", "location": "Ubicación",
    "flash": "Flash", "hdd": "HDD", "groups": {"machine": "EQUIPO", "status": "ESTADO", "hardware": "HARDWARE", "system": "SISTEMA", "collection": "RECOPILACIÓN"},
    "date_format": "dd/mm/yyyy hh:mm", "page": "Página &P de &N",
    "status_options": [("ONLINE", "Accesible"), ("OFFLINE", "Inaccesible"), ("FALHA_AUTH", "Fallo de autenticación"), ("ERRO_SSH", "Error SSH"), ("ERRO_DESCONHECIDO", "Error desconocido"), ("ERRO_CHAVE_HOST", "Clave SSH rechazada"), ("ERROR", "Error")],
}
REPORT_LANGUAGES = ("en", "pt-br", "es")


def report_language(language: str) -> str:
    code = str(language).lower()
    return "pt-br" if code.startswith("pt") else "es" if code.startswith("es") else "en"


# Explanatory phrases the collector writes in English; identifiers and numbers stay untouched.
DETAIL_TEXT = {
    "pt-br": {
        "not_collected": "Não coletado (opcional)", "slots": "{used} de {total} ocupados",
        "modules_one": "1 módulo instalado", "modules_many": "{count} módulo(s) instalado(s)",
        "N/A": "Não disponível", "Not detected": "Não detectado", "Available": "Disponível",
        "Not detected (physical host not independently confirmed)": "Não detectado (host físico não confirmado independentemente)",
        "storage_basis": "Discos virtuais são identificados pelo modelo/fabricante/nome ou por hipervisor detectado (incluindo discos repassados à VM). Nos demais casos, NVMe usa nome/transporte; HDD versus mídia não rotativa usa a flag do kernel Linux.",
        "sources": {"OS:": "Sistema operacional:", "Memory:": "Memória:", "Storage:": "Armazenamento:", "System/board/firmware:": "Sistema/placa/firmware:", "Graphics:": "Gráficos:", "Network:": "Rede:"},
        "core_missing": "Dados essenciais indisponíveis: ", "optional_missing": "Inventário principal coletado; detalhes opcionais indisponíveis: ",
        "core_ok": "Inventário principal coletado. Valores e classificações dependem das interfaces do kernel e das ferramentas disponíveis no sistema.",
        "fields": {
            "Linux distribution": "distribuição Linux", "Kernel version": "versão do kernel", "Machine architecture": "arquitetura da máquina",
            "CPU model": "modelo da CPU", "CPU topology": "topologia da CPU", "Usable RAM total": "memória RAM total",
            "Storage inventory": "inventário de armazenamento", "System vendor/model": "fabricante/modelo do sistema",
            "motherboard": "placa-mãe", "DIMM speed": "velocidade dos módulos de memória", "GPU": "GPU",
            "network adapter detail": "detalhes dos adaptadores de rede",
        },
        "asset_field": "Campo do ativo · {label}",
    },
    "es": {
        "not_collected": "No recopilado (opcional)", "slots": "{used} de {total} ocupadas",
        "modules_one": "1 módulo instalado", "modules_many": "{count} módulo(s) instalado(s)",
        "N/A": "No disponible", "Not detected": "No detectado", "Available": "Disponible",
        "Not detected (physical host not independently confirmed)": "No detectado (equipo físico no confirmado de forma independiente)",
        "storage_basis": "Los discos virtuales se identifican por modelo/fabricante/nombre o por un hipervisor detectado (incluidos los discos pasados a la VM). En los demás casos, NVMe usa nombre/transporte; HDD frente a medio no rotativo usa el indicador del kernel Linux.",
        "sources": {"OS:": "Sistema operativo:", "Memory:": "Memoria:", "Storage:": "Almacenamiento:", "System/board/firmware:": "Sistema/placa/firmware:", "Graphics:": "Gráficos:", "Network:": "Red:"},
        "core_missing": "Datos esenciales no disponibles: ", "optional_missing": "Inventario principal recopilado; detalles opcionales no disponibles: ",
        "core_ok": "Inventario principal recopilado. Los valores y clasificaciones dependen de las interfaces del kernel y de las herramientas disponibles en el sistema.",
        "fields": {
            "Linux distribution": "distribución Linux", "Kernel version": "versión del kernel", "Machine architecture": "arquitectura del equipo",
            "CPU model": "modelo de CPU", "CPU topology": "topología de CPU", "Usable RAM total": "memoria RAM total",
            "Storage inventory": "inventario de almacenamiento", "System vendor/model": "fabricante/modelo del sistema",
            "motherboard": "placa base", "DIMM speed": "velocidad de los módulos de memoria", "GPU": "GPU",
            "network adapter detail": "detalles de los adaptadores de red",
        },
        "asset_field": "Campo del activo · {label}",
    },
}


def _value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat(sep=" ", timespec="seconds")
        except TypeError:
            return value.isoformat()
    text = str(value)
    return "" if text.lower() in {"nan", "nat", "none"} else text


def _spreadsheet_safe(value: Any) -> str:
    text = _value(value)
    # Prefix formula-like text so Excel/LibreOffice will not execute it when opening CSV/XLSX.
    candidate = text.lstrip(" \t\r\n")
    if candidate and candidate[0] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def metadata_label(key: str, language: str = "en") -> str:
    normalized = str(key).strip().upper().replace(" ", "_").replace("-", "_")
    labels = {"pt-br": METADATA_LABELS_PT, "es": METADATA_LABELS_ES}.get(language, METADATA_LABELS)
    label = labels.get(normalized, str(key).strip().replace("_", " ").replace("-", " ").title())
    return _spreadsheet_safe(label)


def _localize_detail_value(key: str, value: Any, language: str) -> str:
    """Translate explanatory labels without changing raw identifiers or numeric facts."""
    text = _value(value)
    phrases = DETAIL_TEXT.get(language)
    if phrases is None or not text:
        return text

    if key == "system_serial" and text == "Not collected (opt-in)":
        return phrases["not_collected"]
    if key == "ram_slots":
        match = re.fullmatch(r"(\d+) of (\d+) populated", text)
        if match:
            return phrases["slots"].format(used=match.group(1), total=match.group(2))
        match = re.fullmatch(r"(\d+) populated", text)
        if match:
            count = int(match.group(1))
            return phrases["modules_one"] if count == 1 else phrases["modules_many"].format(count=count)
    if key in {"virtualization", "cpu_virtualization"}:
        return phrases.get(text, text)
    if key == "storage_classification_basis":
        return phrases["storage_basis"]
    if key == "collection_sources":
        for source, translated in phrases["sources"].items():
            text = text.replace(source, translated)
        return text
    if key == "collection_notes":
        for prefix, english in (("core_missing", "Core data unavailable: "),
                                ("optional_missing", "Core inventory collected; optional detail unavailable: ")):
            if text.startswith(english):
                fields = text.removeprefix(english).split(", ")
                return phrases[prefix] + ", ".join(phrases["fields"].get(field, field) for field in fields)
        if text.startswith("Core inventory collected."):
            return phrases["core_ok"]
    return text

def _brand_mark_data_uri() -> str:
    """Embed the mark so HTML exports remain self-contained and work offline."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    mark_path = base / "brand" / "icon.svg"
    try:
        mark = mark_path.read_bytes()
    except OSError:
        return ""
    encoded = base64.b64encode(mark).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _prepare(
    records: Iterable[Mapping[str, Any]], language: str = "en"
) -> tuple[list[str], list[dict[str, str]]]:
    source = [dict(record) for record in records]
    column_labels = COLUMN_LABELS[language]
    report_columns = [(source, key, column_labels[label]) for source, key, label, _group in REPORT_COLUMNS]
    host_label = column_labels["Host / IP"]
    reserved_labels = {host_label, *(label for _, _, label in report_columns)}

    metadata_columns: dict[str, str] = {}
    custom_columns: list[str] = []
    for record in source:
        metadata = record.get("metadata") or {}
        for raw_key in metadata:
            key = str(raw_key)
            if key in metadata_columns:
                continue
            label = metadata_label(key, language)
            if label in reserved_labels:
                label = DETAIL_TEXT[language]["asset_field"].format(label=label) if language in DETAIL_TEXT else f"Asset field · {label}"
            candidate = label
            suffix = 2
            while candidate in reserved_labels or candidate in custom_columns:
                candidate = f"{label} ({suffix})"
                suffix += 1
            metadata_columns[key] = candidate
            custom_columns.append(candidate)

    columns = [host_label, *custom_columns, *(label for _, _, label in report_columns)]
    rows: list[dict[str, str]] = []
    for record in source:
        row = {column: "" for column in columns}
        row[host_label] = _value(record.get("ip"))
        metadata = record.get("metadata") or {}
        for raw_key, value in metadata.items():
            label = metadata_columns.get(str(raw_key))
            if label:
                row[label] = _value(value)
        hardware_details = record.get("hardware_details") or {}
        for source, key, label in report_columns:
            if source == "record":
                row[label] = _value(record.get(key))
            else:
                row[label] = _localize_detail_value(key, hardware_details.get(key), language)
        rows.append(row)
    return columns, rows


def save_report(
    records: Iterable[Mapping[str, Any]],
    output_format: str,
    output_dir: str | Path = "reports",
    language: str = "en",
) -> Path:
    """Save inventory data as styled XLSX, portable CSV, or interactive HTML."""
    language = report_language(language)
    records = list(records)
    columns, rows = _prepare(records, language)
    if not rows:
        raise ValueError("There are no inventory records to export.")

    output_format = output_format.strip().upper().lstrip(".")
    extensions = {"XLSX": ".xlsx", "CSV": ".csv", "HTML": ".html"}
    if output_format not in extensions:
        raise ValueError(f"Unsupported report format: {output_format}")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = destination / f"hardware_inventory_{timestamp}{extensions[output_format]}"

    if output_format == "CSV":
        _write_csv(path, columns, rows)
    elif output_format == "HTML":
        _write_html(path, columns, rows, language)
    else:
        _write_xlsx(path, columns, rows, language, records)
    return path


_DIFF_HEADERS = {
    "en": ("IP", "Hostname", "Field", "Previous value", "Current value"),
    "pt-br": ("IP", "Hostname", "Campo", "Valor anterior", "Valor atual"),
    "es": ("IP", "Hostname", "Campo", "Valor anterior", "Valor actual"),
}
_DIFF_FIELD_LABELS = {
    "status": "Status", "processador": "Processor", "ram": "Memory", "disk_type": "Storage type",
    "disk_size": "Storage capacity", "placa_mae": "Motherboard", "distro": "Linux distribution", "kernel": "Kernel",
}


def save_snapshot_diff(
    changes: Sequence[Mapping[str, Any]], output_dir: str | Path, snapshot_id: int, language: str = "en"
) -> Path:
    """Save snapshot changes as CSV; values come from remote hosts and are neutralized."""
    language = report_language(language)
    headers = _DIFF_HEADERS[language]
    rows = []
    for change in changes:
        field_label = _DIFF_FIELD_LABELS.get(str(change.get("field_key")))
        field = COLUMN_LABELS[language][field_label] if field_label else _value(change.get("field"))
        values = (change.get("ip"), change.get("hostname"), field, change.get("previous_value"), change.get("current_value"))
        rows.append({header: _value(value) for header, value in zip(headers, values)})
    path = Path(output_dir) / f"snapshot_diff_{int(snapshot_id)}.csv"
    _write_csv(path, list(headers), rows)
    return path

def _write_csv(path: Path, columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), delimiter=";", extrasaction="ignore")
        writer.writeheader()
        safe_rows = [
            {column: _spreadsheet_safe(row.get(column, "")) for column in columns}
            for row in rows
        ]
        writer.writerows(safe_rows)


def _average_coverage(rows: Sequence[Mapping[str, str]], coverage_label: str) -> int:
    values = []
    for row in rows:
        match = re.match(r"^\s*(\d{1,3})\s*%", row.get(coverage_label, ""))
        if match:
            values.append(min(100, int(match.group(1))))
    return round(sum(values) / len(values)) if values else 0


def _status_counts(
    rows: Sequence[Mapping[str, str]], status_label: str = "Status"
) -> tuple[int, int, int]:
    online = sum(row.get(status_label, "").upper() == "ONLINE" for row in rows)
    offline = sum(row.get(status_label, "").upper() == "OFFLINE" for row in rows)
    return online, offline, len(rows) - online - offline


def _write_html(
    path: Path, columns: Sequence[str], rows: Sequence[Mapping[str, str]], language: str = "en"
) -> None:
    copy = REPORT_TEXT[language]
    logo_uri = _brand_mark_data_uri()
    status_label = COLUMN_LABELS[language]["Status"]
    online, offline, other = _status_counts(rows, status_label)
    coverage_label = COLUMN_LABELS[language]["Data coverage"]
    average_coverage = _average_coverage(rows, coverage_label)
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    table_head = "".join(f"<th scope=\"col\">{html.escape(column)}</th>" for column in columns)
    body_rows = []
    for row in rows:
        status = row.get(status_label, "").upper()
        status_labels = dict(copy["status_options"])
        visible_status = status_labels.get(status, status or "UNKNOWN")
        css_status = "online" if status == "ONLINE" else "offline" if status == "OFFLINE" else "other"
        cells = []
        for column in columns:
            value = row.get(column, "")
            if column == status_label:
                cells.append(
                    f'<td class="status-cell"><span class="status-badge {css_status}">'
                    f'<span class="status-dot {css_status}"></span>'
                    f'{html.escape(visible_status)}</span></td>'
                )
            else:
                detail_labels = {
                    COLUMN_LABELS[language]["Storage devices"],
                    COLUMN_LABELS[language]["Graphics"],
                    COLUMN_LABELS[language]["Network adapters"],
                    COLUMN_LABELS[language]["Collection notes"],
                    COLUMN_LABELS[language]["Storage classification basis"],
                    COLUMN_LABELS[language]["Collection sources"],
                }
                cell_class = ' class="detail-cell"' if column in detail_labels else ""
                cells.append(f"<td{cell_class}>{html.escape(value, quote=True)}</td>")
        body_rows.append(
            f'<tr data-status="{html.escape(status, quote=True)}">{"".join(cells)}</tr>'
        )
    escaped_brand = html.escape(BRAND)
    document = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{escaped_brand} — {html.escape(copy["title"])}</title>
<style>
:root{{--ink:#f5f5f7;--muted:#98989d;--line:#38383a;--surface:#262629;--canvas:#1c1c1e;--header:#232326;--accent:#0a84ff;--green:#30d158;--red:#ff453a;--amber:#ff9f0a}}
*{{box-sizing:border-box;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.2) transparent}}::-webkit-scrollbar{{width:8px;height:8px;background:transparent}}::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.2);border-radius:999px;border:2px solid transparent;background-clip:padding-box}}::-webkit-scrollbar-thumb:hover{{background:rgba(255,255,255,0.38);border:2px solid transparent;background-clip:padding-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font:13px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Segoe UI",system-ui,sans-serif;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}}
header{{background:var(--header);color:var(--ink);padding:24px clamp(20px,4vw,48px);border-bottom:1px solid var(--line)}}
.brand-lockup{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.brand-lockup img{{width:32px;height:32px;border-radius:8px;flex:none}}
.brand-name{{font-size:15px;font-weight:600;letter-spacing:-.015em}}
.brand-tag{{font-size:11px;color:var(--muted);margin-left:6px}}
h1{{font-size:clamp(20px,2.5vw,26px);line-height:1.2;margin:6px 0 4px;letter-spacing:-.02em;font-weight:600}}
.sub{{color:var(--muted);margin:0;font-size:13px}}.meta{{margin-top:10px;color:var(--muted);font-size:12px}}
main{{width:100%;margin:0;padding:22px clamp(16px,3vw,48px) 48px}}
.metrics{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:18px}}
.metric{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.metric span{{color:var(--muted);font-size:12px;font-weight:500;display:block}}.metric strong{{font-size:24px;font-weight:600;letter-spacing:-.02em;display:block;margin-top:4px}}
.toolbar{{display:flex;gap:10px;align-items:center;margin:0 0 12px;flex-wrap:wrap}}
input,select{{font:inherit;border:1px solid var(--line);background:var(--surface);border-radius:7px;padding:7px 11px;color:var(--ink);outline:none}}
input:focus,select:focus{{border-color:var(--accent)}}
input{{flex:1;min-width:220px}}select{{min-width:160px}}.result-count{{color:var(--muted);font-size:12px;margin-left:auto}}
.table-wrap{{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:auto}}
table{{width:100%;border-collapse:separate;border-spacing:0;white-space:nowrap;font-size:12.5px}}
td.detail-cell{{white-space:pre-line;min-width:220px;max-width:420px;line-height:1.5}}
th{{position:sticky;top:0;z-index:1;background:#2c2c2e;color:var(--muted);font-size:11.5px;font-weight:500;text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}}
td{{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.06);max-width:340px;overflow:hidden;text-overflow:ellipsis}}
tbody tr:hover{{background:rgba(255,255,255,0.03)}}tbody tr:last-child td{{border-bottom:0}}
.status-badge{{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:400}}
.status-dot{{width:7px;height:7px;border-radius:50%;display:inline-block;flex-shrink:0}}
.status-dot.online{{background:var(--green)}}.status-dot.offline{{background:var(--red)}}.status-dot.other{{background:var(--amber)}}
footer{{padding:18px 0;color:var(--muted);font-size:11.5px;text-align:center}}
@media(max-width:900px){{.metrics{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}
@media(max-width:720px){{.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media print{{
:root{{--ink:#1c1c1e;--muted:#6e6e73;--line:#d1d1d6;--surface:#ffffff;--canvas:#ffffff}}
body{{background:#ffffff;color:#1c1c1e}}
header{{padding:16px;background:#f5f5f7!important;color:#1c1c1e!important;print-color-adjust:exact}}
main{{width:100%;padding:14px 0}}
.toolbar{{display:none}}
.metric{{background:#ffffff;border-color:#d1d1d6}}
.table-wrap{{background:#ffffff;overflow:visible;border:1px solid #d1d1d6}}
table{{white-space:normal;font-size:9px}}
th{{position:static;background:#f5f5f7;color:#1c1c1e;print-color-adjust:exact}}
td{{color:#1c1c1e;border-bottom:1px solid #e5e5ea;overflow:visible;max-width:none}}
}}
</style>
</head>
<body>
<header>
  <div class="brand-lockup">{f'<img src="{logo_uri}" alt="" aria-hidden="true">' if logo_uri else ""}
    <span class="brand-name">{escaped_brand}</span>
    <span class="brand-tag">{html.escape(copy["kicker"])}</span>
  </div>
  <h1>{html.escape(copy["title"])}</h1>
  <p class="sub">{html.escape(copy["subtitle"])}</p>
  <div class="meta">{html.escape(copy["generated"])} {html.escape(generated)} &nbsp;·&nbsp; {len(rows):,} {html.escape(copy["devices_inventoried"])}</div>
</header>
<main>
  <section class="metrics" aria-label="{html.escape(copy["summary"])}">
    <div class="metric"><span>{html.escape(copy["total"])}</span><strong>{len(rows):,}</strong></div>
    <div class="metric"><span>{html.escape(copy["online"])}</span><strong>{online:,}</strong></div>
    <div class="metric"><span>{html.escape(copy["offline"])}</span><strong>{offline:,}</strong></div>
    <div class="metric"><span>{html.escape(copy["other"])}</span><strong>{other:,}</strong></div>
    <div class="metric"><span>{html.escape(copy["coverage"])}</span><strong>{average_coverage}%</strong></div>
  </section>
  <div class="toolbar">
    <input id="search" type="search" aria-label="{html.escape(copy["search_label"])}" placeholder="{html.escape(copy["search_placeholder"], quote=True)}">
    <select id="status" aria-label="{html.escape(copy["all_statuses"])}"><option value="">{html.escape(copy["all_statuses"])}</option>{''.join(f'<option value="{html.escape(value, quote=True)}">{html.escape(label)}</option>' for value, label in copy["status_options"])}</select>
    <span id="result-count" class="result-count">{len(rows):,} {html.escape(copy["devices_shown"])}</span>
  </div>
  <div class="table-wrap"><table id="inventory"><thead><tr>{table_head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>
  <footer>{html.escape(copy["footer"].format(brand=BRAND))}</footer>
</main>
<script>
(()=>{{const search=document.getElementById('search'),status=document.getElementById('status'),rows=[...document.querySelectorAll('#inventory tbody tr')],count=document.getElementById('result-count'),suffix={json.dumps(" " + copy["devices_shown"])};function filter(){{const q=search.value.trim().toLowerCase(),s=status.value;let visible=0;for(const row of rows){{const matchText=row.textContent.toLowerCase().includes(q),matchStatus=!s||row.dataset.status===s,show=matchText&&matchStatus;row.hidden=!show;if(show)visible++}}count.textContent=visible.toLocaleString()+suffix}}search.addEventListener('input',filter);status.addEventListener('change',filter)}})();
</script>
</body></html>"""
    path.write_text(document, encoding="utf-8")


_FONT = "Segoe UI"
_BORDER = "E5E5EA"
_MUTED = "6E6E73"
# compute_fleet_analytics labels its buckets in Portuguese.
_ANALYTICS_LABELS = {
    "en": {
        "SSD SATA / Flash": "SATA SSD / flash", "HDD Mecânico": "Hard disk",
        "Até 4 GB": "Up to 4 GB", "16 GB ou superior": "16 GB or more",
        "Não identificado": "Unidentified", "Geral": "General",
    },
    "es": {
        "SSD SATA / Flash": "SSD SATA / flash", "HDD Mecânico": "Disco duro",
        "Até 4 GB": "Hasta 4 GB", "16 GB ou superior": "16 GB o más",
        "Não identificado": "No identificado", "Geral": "General",
    },
}
_GROUP_TINTS = {
    "machine": "E8F2FF", "status": "EAF8EE", "hardware": "F2ECFB", "system": "FFF4E5", "collection": "F2F2F7",
}


def _logo_image(size: int):
    """The product mark, or None when Pillow (needed by openpyxl images) is missing."""
    try:
        from openpyxl.drawing.image import Image as XLImage

        logo = XLImage(str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "brand" / "icons" / "invenux-128.png"))
    except (ImportError, OSError, ValueError):
        return None
    logo.width = logo.height = size
    return logo


def _parse_timestamp(text: str):
    try:
        return datetime.fromisoformat(text.strip()) if text.strip() else None
    except ValueError:
        return None


def _write_xlsx(
    path: Path,
    columns: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    language: str = "en",
    records: Sequence[Mapping[str, Any]] = (),
) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.formatting.rule import DataBarRule
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        raise RuntimeError("Excel export needs openpyxl. Install the project requirements first.") from exc
    from snapshots import compute_fleet_analytics

    copy = REPORT_TEXT[language]
    labels = COLUMN_LABELS[language]
    status_label = labels["Status"]
    status_names = dict(copy["status_options"])
    online, offline, other = _status_counts(rows, status_label)
    total = len(rows)
    average_coverage = _average_coverage(rows, labels["Data coverage"])
    generated = datetime.now().astimezone()
    generated_text = generated.strftime("%Y-%m-%d %H:%M" if language == "en" else "%d/%m/%Y %H:%M")
    analytics = compute_fleet_analytics(records)

    def font(size=10, bold=False, color="1C1C1E"):
        return Font(name=_FONT, size=size, bold=bold, color=color)

    def fill(color):
        return PatternFill("solid", fgColor=color)

    thin = Side(style="thin", color=_BORDER)

    def label_text(text):
        return _ANALYTICS_LABELS.get(language, {}).get(text, text)

    def band(sheet, last_column, title_cell, logo_size, subtitle):
        for row in (1, 2):
            for column in range(1, last_column + 1):
                sheet.cell(row, column).fill = fill(BRAND_DARK)
        sheet.row_dimensions[1].height = 34
        sheet.row_dimensions[2].height = 20
        sheet[title_cell] = copy["title"]
        sheet[title_cell].font = font(18, True, "F5F5F7")
        sheet[title_cell].alignment = Alignment(vertical="bottom")
        subtitle_cell = sheet.cell(2, sheet[title_cell].column)
        subtitle_cell.value = subtitle
        subtitle_cell.font = font(10, color="98989D")
        subtitle_cell.alignment = Alignment(vertical="top")
        logo = _logo_image(logo_size)
        if logo is not None:
            sheet.add_image(logo, "A1" if title_cell.startswith("B") else "B1")

    subtitle = f"{BRAND} · {copy['generated']} {generated_text} · {total:,} {copy['snapshot']}"

    wb = Workbook()
    overview = wb.active
    overview.title = copy["overview_sheet"]
    overview.sheet_view.showGridLines = False
    overview.column_dimensions["A"].width = 3
    for column in range(2, 13):
        overview.column_dimensions[get_column_letter(column)].width = 13
    band(overview, 12, "C1", 40, subtitle)
    overview.row_dimensions[3].height = 14

    cards = [
        (copy["total"], total, "1C1C1E", copy["devices_inventoried"]),
        (copy["online"], online, STATUS_ONLINE_FG, f"{(online / total * 100 if total else 0):.1f}% {copy['availability']}"),
        (copy["offline"], offline, STATUS_OFFLINE_FG, f"{(offline / total * 100 if total else 0):.1f}% {copy['share_of_total']}"),
        (copy["other"], other, STATUS_OTHER_FG, f"{(other / total * 100 if total else 0):.1f}% {copy['share_of_total']}"),
        (copy["coverage"], f"{average_coverage}%", BRAND_ACCENT, copy["average"]),
    ]
    for index, (title, value, color, note) in enumerate(cards):
        first = 2 + index * 2
        for row, (text, style, height) in enumerate(
            ((title.upper(), font(8, True, _MUTED), 18), (value, font(22, True, color), 32), (note, font(8, color=_MUTED), 16)),
            start=4,
        ):
            overview.merge_cells(start_row=row, start_column=first, end_row=row, end_column=first + 1)
            cell = overview.cell(row, first, text)
            cell.font = style
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            overview.row_dimensions[row].height = height
            for column in (first, first + 1):
                target = overview.cell(row, column)
                target.fill = fill(ROW_ODD)
                target.border = Border(
                    left=Side(style="thick", color=color) if column == first else None,
                    top=thin if row == 4 else None,
                    bottom=thin if row == 6 else None,
                    right=thin if column == first + 1 else None,
                )
    if language != "en":
        for index in range(1, 4):
            cell = overview.cell(6, 2 + index * 2)
            cell.value = str(cell.value).replace(".", ",", 1)

    def distribution(top_row, first_column, title, headers, items):
        """Small titled table; the last column is a share with data bars."""
        overview.cell(top_row, first_column, title).font = font(12, True)
        overview.row_dimensions[top_row].height = 22
        header_row = top_row + 1
        span = len(headers) + 1
        for offset in range(span):
            cell = overview.cell(header_row, first_column + offset)
            cell.fill = fill(BRAND_DARK)
            cell.font = font(9, True, "F5F5F7")
            cell.alignment = Alignment(vertical="center", horizontal="left" if offset < 2 else "right", indent=1 if offset == 0 else 0)
        overview.merge_cells(start_row=header_row, start_column=first_column, end_row=header_row, end_column=first_column + 1)
        overview.cell(header_row, first_column).value = headers[0]
        for offset, header in enumerate(headers[1:], start=2):
            overview.cell(header_row, first_column + offset).value = header
        row = header_row
        for row, values in enumerate(items, start=header_row + 1):
            overview.merge_cells(start_row=row, start_column=first_column, end_row=row, end_column=first_column + 1)
            for offset in range(span):
                cell = overview.cell(row, first_column + offset)
                cell.fill = fill(ROW_EVEN if (row - header_row) % 2 else ROW_ODD)
                cell.border = Border(bottom=thin)
                cell.font = font(10)
            overview.cell(row, first_column, values[0]).alignment = Alignment(indent=1)
            for offset, value in enumerate(values[1:], start=2):
                cell = overview.cell(row, first_column + offset, value)
                cell.alignment = Alignment(horizontal="right")
                if isinstance(value, float):
                    cell.number_format = "0.0%"
        if row > header_row:
            share_column = get_column_letter(first_column + span - 1)
            overview.conditional_formatting.add(
                f"{share_column}{header_row + 1}:{share_column}{row}",
                DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color=BRAND_ACCENT, showValue=True),
            )
        return row

    share_headers = [copy["kind"], copy["machines"], copy["share"]]
    storage = [(label_text(item["label"]), item["count"], item["percent"] / 100) for item in analytics["storage_distribution"]]
    memory = [(label_text(item["label"]), item["count"], item["percent"] / 100) for item in analytics["ram_distribution"]]
    distros = [(label_text(item["label"]), item["count"], item["percent"] / 100) for item in analytics["distro_distribution"]]
    end_left = distribution(9, 2, copy["storage_by_type"], share_headers, storage)
    end_right = distribution(9, 7, copy["memory_capacity"], share_headers, memory)
    next_row = max(end_left, end_right) + 2
    end_left = distribution(next_row, 2, copy["distributions"], share_headers, distros)
    locations = [
        (label_text(item["location"]), item["total"], item["online"], item["flash"], item["online"] / item["total"] if item["total"] else 0.0)
        for item in analytics["locations"]
    ]
    end_right = distribution(
        next_row, 7, copy["by_location"],
        [copy["location"], copy["machines"], copy["online"], copy["flash"], copy["share"]], locations,
    )
    hint_row = max(end_left, end_right) + 2
    overview.cell(hint_row, 2, copy["inventory_hint"]).font = font(9, color=_MUTED)
    overview.freeze_panes = "A4"
    overview.page_setup.orientation = "landscape"
    overview.sheet_properties.pageSetUpPr.fitToPage = True
    overview.page_setup.fitToWidth = 1
    overview.page_setup.fitToHeight = 0

    sheet = wb.create_sheet(copy["inventory_sheet"])
    sheet.sheet_view.showGridLines = False
    last_column = len(columns)
    last_letter = get_column_letter(last_column)
    band(sheet, last_column, "B1", 32, subtitle)

    groups = {labels[label]: group for _source, _key, label, group in REPORT_COLUMNS}
    keys = {labels[label]: key for _source, key, label, _group in REPORT_COLUMNS}
    column_group = [groups.get(label, "machine") for label in columns]
    start = 0
    while start < last_column:
        end = start
        while end + 1 < last_column and column_group[end + 1] == column_group[start]:
            end += 1
        if end > start:
            sheet.merge_cells(start_row=3, start_column=start + 1, end_row=3, end_column=end + 1)
        cell = sheet.cell(3, start + 1, copy["groups"][column_group[start]])
        cell.font = font(8, True, BRAND_ACCENT)
        cell.alignment = Alignment(vertical="center", indent=1)
        for column in range(start + 1, end + 2):
            sheet.cell(3, column).fill = fill(_GROUP_TINTS[column_group[start]])
        start = end + 1
    sheet.row_dimensions[3].height = 18

    for column_index, label in enumerate(columns, start=1):
        cell = sheet.cell(4, column_index, label)
        cell.font = font(9, True, "F5F5F7")
        cell.fill = fill(BRAND_HEADER)
        cell.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        cell.border = Border(bottom=Side(style="medium", color=BRAND_ACCENT))
    sheet.row_dimensions[4].height = 30

    widths = {}
    for column_index, label in enumerate(columns, start=1):
        key = keys.get(label)
        sample = [label] + [row.get(label, "") for row in rows[:250]]
        longest = max((len(line) for value in sample for line in str(value).splitlines() or [""]), default=10)
        cap = 48 if key in MULTILINE_KEYS else 30
        widths[column_index] = max(11, min(longest + 3, cap))
        sheet.column_dimensions[get_column_letter(column_index)].width = widths[column_index]
    widths_by_label = {label: widths[index] for index, label in enumerate(columns, start=1)}

    for row_index, row in enumerate(rows, start=5):
        band_color = ROW_EVEN if row_index % 2 else "F7F7F9"
        line_count = 1
        for column_index, label in enumerate(columns, start=1):
            key = keys.get(label)
            raw = row.get(label, "")
            value: Any = _spreadsheet_safe(raw)
            cell = sheet.cell(row_index, column_index)
            cell.font = font(10)
            cell.fill = fill(band_color)
            cell.border = Border(bottom=thin)
            wrap = key in MULTILINE_KEYS
            if key == "status":
                status = str(raw).upper()
                value = status_names.get(status, raw)
                tone = "ONLINE" if status == "ONLINE" else "OFFLINE" if status == "OFFLINE" else "OTHER"
                cell.fill = fill({"ONLINE": STATUS_ONLINE_BG, "OFFLINE": STATUS_OFFLINE_BG}.get(tone, STATUS_OTHER_BG))
                cell.font = font(10, True, {"ONLINE": STATUS_ONLINE_FG, "OFFLINE": STATUS_OFFLINE_FG}.get(tone, STATUS_OTHER_FG))
            elif key == "dta_atualizacao" and _parse_timestamp(str(raw)):
                value = _parse_timestamp(str(raw))
                cell.number_format = copy["date_format"]
            elif key == "coverage_percent" and re.fullmatch(r"\d{1,3}%", str(raw).strip()):
                value = int(str(raw).strip()[:-1]) / 100
                cell.number_format = "0%"
            elif key == "erro" and raw:
                cell.font = font(10, color=STATUS_OFFLINE_FG)
            elif label == columns[0]:
                cell.font = font(10, True)
            cell.value = value
            cell.alignment = Alignment(vertical="top", wrap_text=wrap, indent=1 if column_index == 1 else 0)
            if wrap and raw:
                width = widths_by_label[label]
                line_count = max(line_count, sum(max(1, -(-len(line) // max(1, width - 2))) for line in str(raw).splitlines()))
        # openpyxl cannot autofit; Excel keeps the default height for wrapped text otherwise.
        sheet.row_dimensions[row_index].height = min(15 * line_count + 4, 160)

    sheet.freeze_panes = "B5"
    sheet.auto_filter.ref = f"A4:{last_letter}{max(4, 4 + len(rows))}"
    # Dozens of columns are unreadable on one page; spread them over a few with the host repeated.
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 4
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.orientation = "landscape"
    sheet.print_title_rows = "3:4"
    sheet.print_title_cols = "A:A"
    for page_sheet in (overview, sheet):
        page_sheet.oddFooter.left.text = BRAND
        page_sheet.oddFooter.right.text = copy["page"]
    wb.properties.title = f"{BRAND} {copy['title']}"
    wb.properties.subject = copy["subtitle"]
    wb.properties.creator = BRAND
    wb.save(path)


TEMPLATE_TEXT = {
    "en": {
        "file": "invenux_targets_template.xlsx", "sheet": "Targets", "guide": "How to fill",
        "title": "Target spreadsheet", "intro": "One machine per row. Keep the header in row 1 and fill from row 2.",
        "required": "Required", "optional": "Optional", "column": "Column", "use": "What it is for",
        "rows": [
            ("IP", True, "Address or name of the machine. HOST, HOSTNAME, ADDRESS, IP_ADDRESS, ENDPOINT or TARGET also work."),
            ("HOSTNAME", False, "Name you know the machine by; the collected hostname is shown too."),
            ("LOCATION", False, "Site or room. Groups the Fleet view and the reports."),
            ("ASSET_TAG", False, "Asset number. Any other column is kept as is in the reports."),
            ("OWNER", False, "Team or person responsible."),
            ("NOTES", False, "Free text."),
        ],
        "tips": "Save as .xlsx or .csv (comma or semicolon). Rows without an address and repeated addresses are skipped and listed after loading.",
        "access": "Machines with a different SSH user, password or port: add a USER, PASSWORD and/or SSH_PORT column and fill only those rows; empty cells use the SSH panel, and rows with an invalid port are skipped and listed after loading. Passwords are plain text in this file, so keep it safe; Invenux keeps them in memory only and never writes them to reports or snapshots.",
        "samples": [
            ["192.0.2.10", "srv-app-01", "HQ · Rack B2", "ASSET-0104", "Infrastructure", "Main server"],
            ["192.0.2.21", "pos-01", "Branch 04 · Front", "ASSET-0419", "Operations", "Linux terminal"],
        ],
    },
    "pt-br": {
        "file": "modelo_alvos_invenux.xlsx", "sheet": "Alvos", "guide": "Como preencher",
        "title": "Planilha de alvos", "intro": "Uma máquina por linha. Mantenha o cabeçalho na linha 1 e preencha a partir da linha 2.",
        "required": "Obrigatória", "optional": "Opcional", "column": "Coluna", "use": "Para que serve",
        "rows": [
            ("IP", True, "Endereço ou nome da máquina. Também vale HOST, HOSTNAME, ADDRESS, IP_ADDRESS, ENDPOINT ou TARGET."),
            ("HOSTNAME", False, "Nome pelo qual você conhece a máquina; o hostname coletado também aparece."),
            ("LOCATION", False, "Unidade ou sala. Agrupa a visão Parque e os relatórios."),
            ("ASSET_TAG", False, "Número de patrimônio. Qualquer outra coluna vai como está para os relatórios."),
            ("OWNER", False, "Equipe ou pessoa responsável."),
            ("NOTES", False, "Texto livre."),
        ],
        "tips": "Salve em .xlsx ou .csv (vírgula ou ponto e vírgula). Linhas sem IP e IPs repetidos são ignorados e listados depois de carregar.",
        "access": "Máquinas com usuário, senha ou porta SSH diferentes: acrescente uma coluna USER, PASSWORD e/ou SSH_PORT e preencha só essas linhas; células vazias usam o painel SSH, e linhas com porta inválida são ignoradas e listadas depois de carregar. A senha fica em texto puro neste arquivo, então guarde-o com cuidado; o Invenux a mantém só na memória e nunca a grava em relatórios ou snapshots.",
        "samples": [
            ["192.0.2.10", "srv-app-01", "Matriz · Rack B2", "PAT-0104", "Infraestrutura", "Servidor principal"],
            ["192.0.2.21", "pdv-01", "Filial 04 · Frente", "PAT-0419", "Operações", "Terminal Linux"],
        ],
    },
    "es": {
        "file": "plantilla_destinos_invenux.xlsx", "sheet": "Destinos", "guide": "Cómo rellenar",
        "title": "Hoja de destinos", "intro": "Un equipo por fila. Mantenga el encabezado en la fila 1 y rellene desde la fila 2.",
        "required": "Obligatoria", "optional": "Opcional", "column": "Columna", "use": "Para qué sirve",
        "rows": [
            ("IP", True, "Dirección o nombre del equipo. También valen HOST, HOSTNAME, ADDRESS, IP_ADDRESS, ENDPOINT o TARGET."),
            ("HOSTNAME", False, "Nombre con el que conoce el equipo; también se muestra el hostname recopilado."),
            ("LOCATION", False, "Sede o sala. Agrupa la vista Parque y los informes."),
            ("ASSET_TAG", False, "Número de activo. Cualquier otra columna pasa tal cual a los informes."),
            ("OWNER", False, "Equipo o persona responsable."),
            ("NOTES", False, "Texto libre."),
        ],
        "tips": "Guarde en .xlsx o .csv (coma o punto y coma). Las filas sin dirección y las direcciones repetidas se omiten y se listan al cargar.",
        "access": "Equipos con usuario, contraseña o puerto SSH distintos: agregue una columna USER, PASSWORD y/o SSH_PORT y complete solo esas filas; las celdas vacías usan el panel SSH, y las filas con un puerto no válido se omiten y se listan al cargar. La contraseña queda en texto plano en este archivo, así que guárdelo con cuidado; Invenux solo la mantiene en memoria y nunca la escribe en informes ni instantáneas.",
        "samples": [
            ["192.0.2.10", "srv-app-01", "Sede central · Rack B2", "ACT-0104", "Infraestructura", "Servidor principal"],
            ["192.0.2.21", "tpv-01", "Sucursal 04 · Frente", "ACT-0419", "Operaciones", "Terminal Linux"],
        ],
    },
}


def template_filename(language: str) -> str:
    return TEMPLATE_TEXT[report_language(language)]["file"]


def create_template_workbook(destination: str | Path, language: str = "pt-br") -> Path:
    """Create the starter target spreadsheet with a filled example and a how-to sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    text = TEMPLATE_TEXT[report_language(language)]
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    targets = wb.active
    targets.title = text["sheet"]
    headers = [name for name, _required, _use in text["rows"]]
    targets.append(headers)
    for row in text["samples"]:
        targets.append(row)
    thin = Side(style="thin", color=_BORDER)
    for column_index, width in enumerate((18, 18, 24, 16, 18, 28), start=1):
        header = targets.cell(1, column_index)
        header.font = Font(name=_FONT, bold=True, color="F5F5F7")
        header.fill = PatternFill("solid", fgColor=BRAND_ACCENT if column_index == 1 else BRAND_HEADER)
        header.alignment = Alignment(vertical="center", indent=1)
        targets.column_dimensions[header.column_letter].width = width
        for row_index in range(2, 2 + len(text["samples"])):
            cell = targets.cell(row_index, column_index)
            cell.font = Font(name=_FONT, color="1C1C1E")
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(indent=1)
    targets.row_dimensions[1].height = 24
    targets.freeze_panes = "A2"

    guide = wb.create_sheet(text["guide"])
    guide.sheet_view.showGridLines = False
    guide.column_dimensions["A"].width = 3
    guide.column_dimensions["B"].width = 16
    guide.column_dimensions["C"].width = 14
    guide.column_dimensions["D"].width = 80
    for column in range(1, 5):
        guide.cell(1, column).fill = PatternFill("solid", fgColor=BRAND_DARK)
    guide.row_dimensions[1].height = 34
    guide["B1"] = f"{BRAND} · {text['title']}"
    guide["B1"].font = Font(name=_FONT, size=16, bold=True, color="F5F5F7")
    guide["B1"].alignment = Alignment(vertical="center")
    guide["B3"] = text["intro"]
    guide["B3"].font = Font(name=_FONT, size=11, color="1C1C1E")
    for column, header in zip("BCD", (text["column"], text["required"] + " / " + text["optional"], text["use"])):
        cell = guide[f"{column}5"]
        cell.value = header
        cell.font = Font(name=_FONT, bold=True, color="F5F5F7", size=10)
        cell.fill = PatternFill("solid", fgColor=BRAND_HEADER)
        cell.alignment = Alignment(vertical="center", indent=1)
    for row_index, (name, required, use) in enumerate(text["rows"], start=6):
        values = (name, text["required"] if required else text["optional"], use)
        for column, value in zip("BCD", values):
            cell = guide[f"{column}{row_index}"]
            cell.value = value
            cell.font = Font(name=_FONT, bold=column == "B", color=BRAND_ACCENT if (required and column != "D") else "1C1C1E")
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="top", wrap_text=True, indent=1)
    tips_row = 7 + len(text["rows"])
    guide[f"B{tips_row}"] = text["tips"]
    guide[f"B{tips_row}"].font = Font(name=_FONT, size=10, color=_MUTED)
    guide[f"B{tips_row + 1}"] = text["access"]
    guide[f"B{tips_row + 1}"].font = Font(name=_FONT, size=10, color=_MUTED)
    wb.save(path)
    wb.close()
    return path
