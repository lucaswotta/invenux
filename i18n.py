# -*- coding: utf-8 -*-
"""Messages produced by the collector and the local server, in pt-BR, English and Spanish.

The interface (`ui/index.html`) has its own catalog for its labels; this module
covers text generated in Python: status lines, errors and log messages. The
language comes from the saved preference or, on first run, from the OS locale.
"""
import json
import locale
import os
import re
from typing import Dict

from paths import get_config_path

CONFIG_FILE = str(get_config_path())
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("pt-br", "en", "es")

STRINGS: Dict[str, Dict[str, str]] = {
    "pt-br": {
        "app_ready": "Pronto para coleta",
        "app_targets_not_found": "Arquivo de alvos não encontrado: {filepath}",
        "app_no_valid_targets": "Nenhum alvo válido encontrado na planilha.",
        "app_rows_without_target": "linhas sem IP ignoradas: {rows}",
        "app_duplicate_rows": "IPs repetidos ignorados: {rows}",
        "app_invalid_port_rows": "linhas com porta SSH inválida ignoradas: {rows}",
        "app_more_rows": "{rows} e mais {count}",
        "app_targets_loaded": "{count} máquinas carregadas de {filename}",
        "app_template_saved": "Modelo salvo em {path}",
        "app_nothing_to_export": "Não há máquinas na tabela para exportar.",
        "app_report_exported": "Relatório exportado: {filename}",
        "app_open_reports_only": "Só é possível abrir arquivos da pasta de relatórios.",
        "app_unknown_location": "Local desconhecido.",
        "app_no_changes_to_export": "Não há alterações neste snapshot para exportar.",
        "app_snapshot_not_found": "Snapshot #{snapshot_id} não encontrado.",
        "app_viewing_snapshot": "Visualizando snapshot de {created_at}",
        "app_scan_running": "Uma coleta já está em andamento.",
        "app_select_targets_first": "Selecione uma planilha de alvos válida antes de iniciar.",
        "app_ssh_user_required": "Informe o usuário SSH antes de iniciar a coleta.",
        "app_ssh_auth_required": "Informe uma chave privada SSH ou a senha SSH.",
        "cli_password_prompt": "Senha SSH de {user}: ",
        "update_check_failed": "Não foi possível verificar atualizações: {error}",
        "update_none_available": "Não há versão nova para instalar.",
        "update_no_package": "A versão nova não tem pacote para este sistema; baixe pela página da release.",
        "update_no_checksum": "O SHA256SUMS da versão nova não lista {name}.",
        "update_checksum_mismatch": "O arquivo baixado ({name}) não confere com o SHA256SUMS e foi descartado.",
        "update_bad_package": "O pacote {name} não tem a pasta com install.sh esperada.",
        "update_install_failed": "A instalação falhou: {error}",
        "update_installed": "Invenux {version} instalado. Feche e abra o programa para usar a versão nova.",
        "update_launched": "Invenux {version} foi baixado e aberto. Feche esta janela.",
        "update_downloaded": "Versão nova baixada em {path}.",
        "update_page_opened": "Abri a página da versão {version}. Pelo código, atualize com git pull.",
        "app_ssh_user_missing_rows": "{count} máquinas estão sem usuário na planilha (ex.: {hosts}). Preencha a coluna USER delas ou informe o usuário no painel SSH.",
        "app_ssh_auth_missing_rows": "{count} máquinas estão sem senha na planilha (ex.: {hosts}). Preencha a coluna PASSWORD delas ou informe senha ou chave no painel SSH.",
        "app_sheet_credentials": "acesso da planilha: usuário em {users} e senha em {passwords} máquinas; as demais usam o painel SSH. Senhas ficam só na memória",
        "app_ssh_key_not_found": "Chave SSH não encontrada: {path}",
        "app_collecting": "Coletando {done}/{total} ({percent}%)...",
        "app_cancelling": "Cancelando coleta...",
        "app_finished": "Concluído em {seconds} s · {percent}% acessíveis",
        "api_host_forbidden": "Host não autorizado.",
        "api_session_forbidden": "Sessão não autorizada.",
        "api_payload_too_large": "O arquivo enviado excede o limite permitido.",
        "api_route_not_found": "Rota não encontrada.",
        "dialog_targets_title": "Selecionar planilha de máquinas",
        "dialog_key_title": "Selecionar chave privada SSH",
        "loader_unsupported_format": "Formatos aceitos: .xlsx, .xlsm e .csv.",
        "loader_empty_file": "O arquivo está vazio ou não tem linha de cabeçalho.",
        "loader_no_columns": "O arquivo não tem nomes de coluna.",
        "loader_duplicate_columns": "Os nomes de coluna precisam ser únicos (por exemplo, IP e ip são a mesma coluna).",
        "loader_no_target_column": "A planilha precisa de uma coluna de endereço, como IP, HOST, HOSTNAME ou ADDRESS.",
        "loader_data_beyond_header": "A linha {row} tem dados depois da última coluna com nome. Confira o cabeçalho.",
        "log_starting": "Iniciando inventário de hardware...",
        "log_file_not_found": "Arquivo não encontrado: {filepath}",
        "log_spreadsheet_format_error": "Erro no formato da planilha: {error}",
        "log_spreadsheet_read_error": "Erro ao ler a planilha {filename}: {error}",
        "log_no_terminals": "Nenhum destino válido encontrado na planilha.",
        "log_terminals_loaded": "{count} destinos carregados. Iniciando coleta...",
        "log_no_data_collected": "Nenhum dado foi coletado.",
        "log_process_cancelled_no_results": "Coleta cancelada antes de qualquer resultado.",
        "log_process_cancelled_with_results": "Coleta cancelada com {count} resultados parciais.",
        "log_collection_finished": "Coleta finalizada: {count} resultados.",
        "log_process_finished": "Inventário concluído: {online} acessíveis, {failed} com falha.",
        "log_process_failed": "Falha ao concluir o inventário: {error}",
        "log_cancelled_by_user": "Coleta cancelada pelo usuário.",
        "log_processing_exception": "Erro ao processar {ip}: {error}",
        "log_circuit_breaker_tripped": "As 10 primeiras conexões falharam. Coleta interrompida.",
        "log_circuit_breaker_hint": "Confira a rede, a VPN, a porta 22 e as credenciais.",
        "log_stopped_early": "Coleta interrompida após {count} falhas de conexão seguidas.",
        "log_cancelled_after": "Coleta cancelada após {processed} de {total} máquinas.",
        "log_collection_success": "Sucesso na coleta de {ip}",
        "log_collection_failure": "Falha em {ip}: {error}",
        "hw_auth_failed": "Falha na autenticação",
        "hw_key_not_found": "Chave SSH não encontrada: {key_path}",
        "hw_connection_timeout": "Sem resposta em {timeout} s (rede lenta, firewall ou máquina travada)",
        "hw_connection_refused": "Conexão recusada na porta {port} (SSH desligado, bloqueado ou em outra porta)",
        "hw_host_unreachable": "Máquina não respondeu na rede (desligada ou IP sem uso)",
        "hw_dns_failed": "Nome não encontrado no DNS: {ip}",
        "hw_host_key_mismatch": "A chave SSH de {ip} não corresponde à chave conhecida. A conexão foi recusada.",
        "hw_ssh_error": "Erro SSH: {error}",
        "hw_unknown_error": "Erro inesperado: {error}",
    },
    "en": {
        "app_ready": "Ready to collect",
        "app_targets_not_found": "Target file not found: {filepath}",
        "app_no_valid_targets": "No valid targets found in the spreadsheet.",
        "app_rows_without_target": "rows without an address skipped: {rows}",
        "app_duplicate_rows": "repeated addresses skipped: {rows}",
        "app_invalid_port_rows": "rows with an invalid SSH port skipped: {rows}",
        "app_more_rows": "{rows} and {count} more",
        "app_targets_loaded": "{count} machines loaded from {filename}",
        "app_template_saved": "Template saved to {path}",
        "app_nothing_to_export": "There are no machines in the table to export.",
        "app_report_exported": "Report exported: {filename}",
        "app_open_reports_only": "Only files in the reports folder can be opened.",
        "app_unknown_location": "Unknown location.",
        "app_no_changes_to_export": "This snapshot has no changes to export.",
        "app_snapshot_not_found": "Snapshot #{snapshot_id} not found.",
        "app_viewing_snapshot": "Viewing the snapshot from {created_at}",
        "app_scan_running": "A collection is already running.",
        "app_select_targets_first": "Choose a valid target spreadsheet before starting.",
        "app_ssh_user_required": "Enter the SSH user before starting the collection.",
        "app_ssh_auth_required": "Enter an SSH private key or the SSH password.",
        "cli_password_prompt": "SSH password for {user}: ",
        "update_check_failed": "Could not check for updates: {error}",
        "update_none_available": "There is no newer version to install.",
        "update_no_package": "The new version has no package for this system; download it from the release page.",
        "update_no_checksum": "The new version's SHA256SUMS does not list {name}.",
        "update_checksum_mismatch": "The downloaded file ({name}) does not match SHA256SUMS and was discarded.",
        "update_bad_package": "The package {name} lacks the expected folder with install.sh.",
        "update_install_failed": "The installation failed: {error}",
        "update_installed": "Invenux {version} is installed. Close and reopen the program to use it.",
        "update_launched": "Invenux {version} was downloaded and opened. Close this window.",
        "update_downloaded": "New version downloaded to {path}.",
        "update_page_opened": "Opened the page of version {version}. From source, update with git pull.",
        "app_ssh_user_missing_rows": "{count} machines have no user in the spreadsheet (e.g. {hosts}). Fill their USER column or enter the user in the SSH panel.",
        "app_ssh_auth_missing_rows": "{count} machines have no password in the spreadsheet (e.g. {hosts}). Fill their PASSWORD column or enter a password or key in the SSH panel.",
        "app_sheet_credentials": "access from the spreadsheet: user for {users} and password for {passwords} machines; the rest use the SSH panel. Passwords stay in memory only",
        "app_ssh_key_not_found": "SSH key not found: {path}",
        "app_collecting": "Collecting {done}/{total} ({percent}%)...",
        "app_cancelling": "Cancelling collection...",
        "app_finished": "Finished in {seconds} s · {percent}% reachable",
        "api_host_forbidden": "Host not allowed.",
        "api_session_forbidden": "Session not authorized.",
        "api_payload_too_large": "The uploaded file exceeds the allowed size.",
        "api_route_not_found": "Route not found.",
        "dialog_targets_title": "Choose the machine spreadsheet",
        "dialog_key_title": "Choose the SSH private key",
        "loader_unsupported_format": "Supported formats are .xlsx, .xlsm and .csv.",
        "loader_empty_file": "The file is empty or has no header row.",
        "loader_no_columns": "The file has no column names.",
        "loader_duplicate_columns": "Column names must be unique (for example, IP and ip are the same column).",
        "loader_no_target_column": "The spreadsheet needs an address column such as IP, HOST, HOSTNAME or ADDRESS.",
        "loader_data_beyond_header": "Row {row} has data beyond the last named column. Check the header row.",
        "log_starting": "Starting hardware inventory...",
        "log_file_not_found": "File not found: {filepath}",
        "log_spreadsheet_format_error": "Spreadsheet format error: {error}",
        "log_spreadsheet_read_error": "Could not read spreadsheet {filename}: {error}",
        "log_no_terminals": "No valid targets found in the spreadsheet.",
        "log_terminals_loaded": "{count} targets loaded. Starting collection...",
        "log_no_data_collected": "No data was collected.",
        "log_process_cancelled_no_results": "Collection cancelled before any result.",
        "log_process_cancelled_with_results": "Collection cancelled with {count} partial results.",
        "log_collection_finished": "Collection finished: {count} results.",
        "log_process_finished": "Inventory finished: {online} reachable, {failed} failed.",
        "log_process_failed": "The inventory failed: {error}",
        "log_cancelled_by_user": "Collection cancelled by the user.",
        "log_processing_exception": "Error while processing {ip}: {error}",
        "log_circuit_breaker_tripped": "The first 10 connections failed. Collection stopped.",
        "log_circuit_breaker_hint": "Check the network, VPN, port 22 and credentials.",
        "log_stopped_early": "Collection stopped after {count} consecutive connection failures.",
        "log_cancelled_after": "Collection cancelled after {processed} of {total} machines.",
        "log_collection_success": "Collected {ip}",
        "log_collection_failure": "Failure on {ip}: {error}",
        "hw_auth_failed": "Authentication failed",
        "hw_key_not_found": "SSH key not found: {key_path}",
        "hw_connection_timeout": "No answer within {timeout} s (slow network, firewall or frozen machine)",
        "hw_connection_refused": "Connection refused on port {port} (SSH stopped, blocked or on another port)",
        "hw_host_unreachable": "Machine did not answer on the network (powered off or unused IP)",
        "hw_dns_failed": "Name not found in DNS: {ip}",
        "hw_host_key_mismatch": "The SSH host key of {ip} does not match the known key. The connection was rejected.",
        "hw_ssh_error": "SSH error: {error}",
        "hw_unknown_error": "Unexpected error: {error}",
    },
    "es": {
        "app_ready": "Listo para recopilar",
        "app_targets_not_found": "No se encontró el archivo de destinos: {filepath}",
        "app_no_valid_targets": "No hay destinos válidos en la hoja de cálculo.",
        "app_rows_without_target": "filas sin dirección omitidas: {rows}",
        "app_duplicate_rows": "direcciones repetidas omitidas: {rows}",
        "app_invalid_port_rows": "filas con puerto SSH no válido omitidas: {rows}",
        "app_more_rows": "{rows} y {count} más",
        "app_targets_loaded": "{count} equipos cargados de {filename}",
        "app_template_saved": "Plantilla guardada en {path}",
        "app_nothing_to_export": "No hay equipos en la tabla para exportar.",
        "app_report_exported": "Informe exportado: {filename}",
        "app_open_reports_only": "Solo se pueden abrir archivos de la carpeta de informes.",
        "app_unknown_location": "Ubicación desconocida.",
        "app_no_changes_to_export": "Esta instantánea no tiene cambios para exportar.",
        "app_snapshot_not_found": "No se encontró la instantánea #{snapshot_id}.",
        "app_viewing_snapshot": "Viendo la instantánea del {created_at}",
        "app_scan_running": "Ya hay una recopilación en curso.",
        "app_select_targets_first": "Elija una hoja de destinos válida antes de empezar.",
        "app_ssh_user_required": "Indique el usuario SSH antes de iniciar la recopilación.",
        "app_ssh_auth_required": "Indique una clave privada SSH o la contraseña SSH.",
        "cli_password_prompt": "Contraseña SSH de {user}: ",
        "update_check_failed": "No se pudo buscar actualizaciones: {error}",
        "update_none_available": "No hay una versión nueva para instalar.",
        "update_no_package": "La versión nueva no tiene paquete para este sistema; descárguela desde la página de la versión.",
        "update_no_checksum": "El SHA256SUMS de la versión nueva no lista {name}.",
        "update_checksum_mismatch": "El archivo descargado ({name}) no coincide con SHA256SUMS y se descartó.",
        "update_bad_package": "El paquete {name} no tiene la carpeta con install.sh esperada.",
        "update_install_failed": "La instalación falló: {error}",
        "update_installed": "Invenux {version} instalado. Cierre y abra el programa para usar la versión nueva.",
        "update_launched": "Invenux {version} se descargó y se abrió. Cierre esta ventana.",
        "update_downloaded": "Versión nueva descargada en {path}.",
        "update_page_opened": "Se abrió la página de la versión {version}. Desde el código, actualice con git pull.",
        "app_ssh_user_missing_rows": "{count} equipos no tienen usuario en la hoja (p. ej. {hosts}). Complete su columna USER o indique el usuario en el panel SSH.",
        "app_ssh_auth_missing_rows": "{count} equipos no tienen contraseña en la hoja (p. ej. {hosts}). Complete su columna PASSWORD o indique contraseña o clave en el panel SSH.",
        "app_sheet_credentials": "acceso desde la hoja: usuario en {users} y contraseña en {passwords} equipos; los demás usan el panel SSH. Las contraseñas solo quedan en memoria",
        "app_ssh_key_not_found": "No se encontró la clave SSH: {path}",
        "app_collecting": "Recopilando {done}/{total} ({percent}%)...",
        "app_cancelling": "Cancelando la recopilación...",
        "app_finished": "Terminado en {seconds} s · {percent}% accesibles",
        "api_host_forbidden": "Host no autorizado.",
        "api_session_forbidden": "Sesión no autorizada.",
        "api_payload_too_large": "El archivo enviado supera el tamaño permitido.",
        "api_route_not_found": "Ruta no encontrada.",
        "dialog_targets_title": "Elegir la hoja de equipos",
        "dialog_key_title": "Elegir la clave privada SSH",
        "loader_unsupported_format": "Formatos admitidos: .xlsx, .xlsm y .csv.",
        "loader_empty_file": "El archivo está vacío o no tiene fila de encabezado.",
        "loader_no_columns": "El archivo no tiene nombres de columna.",
        "loader_duplicate_columns": "Los nombres de columna deben ser únicos (por ejemplo, IP e ip son la misma columna).",
        "loader_no_target_column": "La hoja necesita una columna de dirección, como IP, HOST, HOSTNAME o ADDRESS.",
        "loader_data_beyond_header": "La fila {row} tiene datos después de la última columna con nombre. Revise el encabezado.",
        "log_starting": "Iniciando el inventario de hardware...",
        "log_file_not_found": "Archivo no encontrado: {filepath}",
        "log_spreadsheet_format_error": "Error de formato en la hoja: {error}",
        "log_spreadsheet_read_error": "No se pudo leer la hoja {filename}: {error}",
        "log_no_terminals": "No hay destinos válidos en la hoja de cálculo.",
        "log_terminals_loaded": "{count} destinos cargados. Iniciando la recopilación...",
        "log_no_data_collected": "No se recopiló ningún dato.",
        "log_process_cancelled_no_results": "Recopilación cancelada antes de obtener resultados.",
        "log_process_cancelled_with_results": "Recopilación cancelada con {count} resultados parciales.",
        "log_collection_finished": "Recopilación terminada: {count} resultados.",
        "log_process_finished": "Inventario terminado: {online} accesibles, {failed} con fallos.",
        "log_process_failed": "El inventario falló: {error}",
        "log_cancelled_by_user": "Recopilación cancelada por el usuario.",
        "log_processing_exception": "Error al procesar {ip}: {error}",
        "log_circuit_breaker_tripped": "Las 10 primeras conexiones fallaron. Recopilación detenida.",
        "log_circuit_breaker_hint": "Revise la red, la VPN, el puerto 22 y las credenciales.",
        "log_stopped_early": "Recopilación detenida tras {count} fallos de conexión seguidos.",
        "log_cancelled_after": "Recopilación cancelada tras {processed} de {total} equipos.",
        "log_collection_success": "Recopilado {ip}",
        "log_collection_failure": "Fallo en {ip}: {error}",
        "hw_auth_failed": "Fallo de autenticación",
        "hw_key_not_found": "No se encontró la clave SSH: {key_path}",
        "hw_connection_timeout": "Sin respuesta en {timeout} s (red lenta, cortafuegos o equipo bloqueado)",
        "hw_connection_refused": "Conexión rechazada en el puerto {port} (SSH detenido, bloqueado o en otro puerto)",
        "hw_host_unreachable": "El equipo no respondió en la red (apagado o IP sin uso)",
        "hw_dns_failed": "Nombre no encontrado en el DNS: {ip}",
        "hw_host_key_mismatch": "La clave SSH de {ip} no coincide con la conocida. Se rechazó la conexión.",
        "hw_ssh_error": "Error SSH: {error}",
        "hw_unknown_error": "Error inesperado: {error}",
    },
}


def _language_from_locale(candidate: str | None) -> str | None:
    if not candidate:
        return None
    token = re.split(r"[-_.:@]", candidate.strip().replace(":", "-"), maxsplit=1)[0].casefold()
    if token in {"pt", "portuguese", "português"}:
        return "pt-br"
    if token in {"en", "english"}:
        return "en"
    if token in {"es", "spanish", "español"}:
        return "es"
    return None


def _system_language() -> str:
    """Resolve a supported language from environment or the OS locale."""
    for variable in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(variable, "")
        for candidate in raw.split(":"):
            language = _language_from_locale(candidate)
            if language:
                return language
    try:
        language = _language_from_locale(locale.getlocale()[0])
        if language:
            return language
    except (ValueError, TypeError, AttributeError):
        pass
    return DEFAULT_LANGUAGE


def _load_saved_language() -> str:
    """Use the explicit app preference; otherwise follow the OS language."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
        if isinstance(config, dict) and config.get("language_choice") in SUPPORTED_LANGUAGES:
            return config["language_choice"]
    except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass
    return _system_language()


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language


def system_language() -> str:
    return _system_language()


def t(key: str, **kwargs) -> str:
    """Translate `key` into the active language, falling back to English, then the key."""
    template = STRINGS.get(_current_language, {}).get(key)
    if template is None:
        template = STRINGS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**kwargs) if kwargs else template


def format_decimal(value: float) -> str:
    """One decimal place with the active language's separator."""
    text = f"{value:.1f}"
    return text if _current_language == "en" else text.replace(".", ",")


_current_language = _load_saved_language()
