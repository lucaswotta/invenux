"""In-process SSH server on 127.0.0.1 for tests (paramiko ServerInterface).

It accepts password and public-key logins, answers every exec request with a
canned probe output (or a handler's), and can forward direct-tcpip channels so
it also works as a bastion. `routes` maps names only the bastion knows to
loopback ports, which stands in for a network the operator cannot reach.
Nothing leaves the loopback interface.
"""
from __future__ import annotations

import socket
import threading
from typing import Callable, Optional

import paramiko

PROBE_OUTPUT = "\n".join([
    "__INVENUX_BEGIN_os_release__", 'PRETTY_NAME="Test Linux 1.0"', "NAME=\"Test Linux\"", "__INVENUX_END_os_release__",
    "__INVENUX_BEGIN_hostname__", "test-node", "__INVENUX_END_hostname__",
    "__INVENUX_BEGIN_kernel__", "6.1.0-test", "__INVENUX_END_kernel__",
    "__INVENUX_BEGIN_architecture__", "x86_64", "__INVENUX_END_architecture__",
    "__INVENUX_BEGIN_lscpu__", "Model name: Test CPU", "CPU(s): 2", "Socket(s): 1", "Core(s) per socket: 2",
    "__INVENUX_END_lscpu__",
    "__INVENUX_BEGIN_meminfo__", "MemTotal: 2097152 kB", "MemAvailable: 1048576 kB", "__INVENUX_END_meminfo__",
    "__INVENUX_BEGIN_lsblk__",
    '{"blockdevices": [{"name": "sda", "type": "disk", "size": 64000000000, "rota": false, '
    '"model": "TEST DISK", "vendor": "TEST", "tran": "sata", "rm": false, "fstype": null, "mountpoints": [null]}]}',
    "__INVENUX_END_lsblk__",
    "__INVENUX_BEGIN_dmi__", "__DMI__sys_vendor=Test Vendor", "__DMI__product_name=Test Model", "__INVENUX_END_dmi__",
]) + "\n"

_HOST_KEY: Optional[paramiko.PKey] = None


def host_key() -> paramiko.PKey:
    global _HOST_KEY
    if _HOST_KEY is None:
        _HOST_KEY = paramiko.RSAKey.generate(2048)
    return _HOST_KEY


class FakeSSHServer:
    """Accept connections on an ephemeral loopback port until stop()."""

    def __init__(
        self,
        passwords: Optional[dict[str, str]] = None,
        authorized_keys: tuple[paramiko.PKey, ...] = (),
        exec_handler: Optional[Callable[[str], tuple[str, int]]] = None,
        forwarding: bool = False,
        routes: Optional[dict[tuple[str, int], tuple[str, int]]] = None,
        key: Optional[paramiko.PKey] = None,
    ) -> None:
        self.passwords = passwords or {}
        self.authorized = {k.get_base64() for k in authorized_keys}
        self.exec_handler = exec_handler or (lambda _command: (PROBE_OUTPUT, 0))
        self.forwarding = forwarding
        self.routes = routes or {}
        self.key = key or host_key()
        self.connections = 0
        self.logins: list[tuple[str, str]] = []
        self.commands: list[str] = []
        self.forwarded: list[tuple[str, int]] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self.port = self._sock.getsockname()[1]
        self._transports: list[paramiko.Transport] = []
        self._stopped = threading.Event()
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._stopped.set()
        self._sock.close()
        for transport in self._transports:
            transport.close()

    def __enter__(self) -> "FakeSSHServer":
        return self

    def __exit__(self, *_exc) -> None:
        self.stop()

    def _accept_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                client, _ = self._sock.accept()
            except OSError:
                return
            self.connections += 1
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        transport = paramiko.Transport(client)
        self._transports.append(transport)
        transport.add_server_key(self.key)
        interface = _Interface(self)
        try:
            transport.start_server(server=interface)
        except (paramiko.SSHException, EOFError, OSError):
            return
        while transport.is_active() and not self._stopped.is_set():
            channel = transport.accept(0.2)
            if channel is None:
                continue
            destination = interface.destinations.pop(channel.get_id(), None)
            if destination is not None:
                threading.Thread(target=self._forward, args=(channel, destination), daemon=True).start()

    def _forward(self, channel: paramiko.Channel, destination: tuple[str, int]) -> None:
        try:
            upstream = socket.create_connection(self.routes.get(destination, destination), timeout=5)
        except OSError:
            channel.close()
            return

        def pump(source, sink, receive, send) -> None:
            try:
                while True:
                    data = receive(source)
                    if not data:
                        break
                    send(sink, data)
            except OSError:
                pass
            finally:
                channel.close()
                upstream.close()

        threading.Thread(
            target=pump, args=(channel, upstream, lambda c: c.recv(32768), lambda s, d: s.sendall(d)), daemon=True
        ).start()
        pump(upstream, channel, lambda s: s.recv(32768), lambda c, d: c.sendall(d))


class _Interface(paramiko.ServerInterface):
    def __init__(self, server: FakeSSHServer) -> None:
        self.server = server
        self.destinations: dict[int, tuple[str, int]] = {}

    def get_allowed_auths(self, username: str) -> str:
        return "password,publickey"

    def check_auth_password(self, username: str, password: str) -> int:
        if self.server.passwords.get(username) == password:
            self.server.logins.append((username, "password"))
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        if key.get_base64() in self.server.authorized:
            self.server.logins.append((username, "publickey"))
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_direct_tcpip_request(self, chanid: int, origin, destination) -> int:
        if not self.server.forwarding:
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        self.server.forwarded.append((destination[0], int(destination[1])))
        self.destinations[chanid] = (destination[0], int(destination[1]))
        return paramiko.OPEN_SUCCEEDED

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        text = command.decode("utf-8", errors="replace") if isinstance(command, bytes) else command
        self.server.commands.append(text)
        output, status = self.server.exec_handler(text)

        # The client closes the channel once it has the exit status; closing it here could
        # overtake paramiko's reply to this request and fail exec_command.
        def reply() -> None:
            channel.sendall(output.encode("utf-8"))
            channel.send_exit_status(status)

        threading.Thread(target=reply, daemon=True).start()
        return True
